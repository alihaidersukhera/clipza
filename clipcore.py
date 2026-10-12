"""ClipKaro core logic — no Streamlit imports here so it can be tested standalone.

Pipeline: extract audio -> transcribe (faster-whisper) -> find best moments
(heuristic scoring, or Gemini when an API key is supplied) -> cut 9:16 clips
with ffmpeg -> Whop-ready tracker CSV.
"""
import csv
import io
import json
import os
import re
import subprocess
import urllib.request
import wave

import numpy as np

# Defensive: some environments ship no_proxy with bracketed IPv6 entries
# ([::1]) which crash httpx inside huggingface_hub. Strip them.
for _k in ("no_proxy", "NO_PROXY"):
    _v = os.environ.get(_k)
    if _v and "[" in _v:
        os.environ[_k] = ",".join(p for p in _v.split(",") if "[" not in p)

# ---------------------------------------------------------------- ffmpeg ---

def run_ffmpeg(args):
    proc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()[:400]}")
    return proc


def probe_duration(path):
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def extract_audio(video_path, out_wav):
    run_ffmpeg(["-i", video_path, "-vn", "-ac", "1", "-ar", "16000", out_wav])
    return out_wav


# ------------------------------------------------------------- transcribe ---

_MODEL = None


def get_model(model_size="small"):
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _MODEL


def transcribe(wav_path, language=None, model_size="small"):
    """Return list of {start, end, text} segment dicts."""
    model = get_model(model_size)
    segments, _info = model.transcribe(wav_path, language=language, vad_filter=True)
    out = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            out.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    return out


# --------------------------------------------------------- moment scoring ---

HOOK_WORDS = [
    # English hooks
    "secret", "nobody", "never", "always", "stop", "listen", "truth", "mistake",
    "money", "free", "how", "why", "believe", "imagine", "story", "problem",
    "shocking", "amazing", "important", "remember", "watch", "wait",
    # Roman Urdu / Hindi hooks
    "kya", "kyun", "kaise", "suno", "dekho", "galti", "sach", "raaz", "paisa",
    "zaroor", "matlab", "yaar", "bhai", "socho", "kabhi", "hamesha",
]


def _load_samples(wav_path):
    with wave.open(wav_path, "rb") as wf:
        rate = wf.getframerate()
        n = wf.getnframes()
        raw = wf.readframes(n)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, rate


def _window_energy(samples, rate, start, end):
    a = int(start * rate)
    b = min(int(end * rate), len(samples))
    if b <= a:
        return 0.0
    chunk = samples[a:b]
    return float(np.sqrt(np.mean(chunk ** 2)) + 1e-9)


def build_windows(segments, min_len=20.0, max_len=60.0, target_len=40.0):
    """Merge consecutive transcript segments into candidate clip windows."""
    windows = []
    i = 0
    while i < len(segments):
        start = segments[i]["start"]
        texts = []
        j = i
        while j < len(segments):
            texts.append(segments[j]["text"])
            length = segments[j]["end"] - start
            j += 1
            if length >= target_len:
                break
        end = segments[j - 1]["end"]
        length = end - start
        if length >= min_len:
            windows.append({"start": start, "end": min(end, start + max_len),
                            "text": " ".join(texts)})
        i = j
    return windows


def score_window(window, samples, rate):
    text = window["text"]
    low = text.lower()
    words = re.findall(r"\w+", low)
    n_words = max(len(words), 1)
    length = max(window["end"] - window["start"], 1.0)

    hook_hits = sum(1 for w in words if w in HOOK_WORDS)
    hook_density = hook_hits / n_words * 10.0            # hooks per 10 words
    punct = (text.count("!") + text.count("?")) / n_words * 10.0
    rate_score = min(n_words / length, 3.0) / 3.0        # speech pace 0..1
    energy = _window_energy(samples, rate, window["start"], window["end"])

    return {"hook": hook_density, "punct": punct, "pace": rate_score, "energy": energy}


def _normalize(values):
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def detect_moments_heuristic(segments, wav_path, count=5, duration=None):
    """Score candidate windows and return the top non-overlapping moments."""
    if not segments:
        return []
    windows = build_windows(segments)
    if not windows:
        return []
    samples, rate = _load_samples(wav_path)
    feats = [score_window(w, samples, rate) for w in windows]
    e_n = _normalize([f["energy"] for f in feats])
    h_n = _normalize([f["hook"] for f in feats])
    p_n = _normalize([f["punct"] for f in feats])
    for idx, w in enumerate(windows):
        raw = 0.35 * e_n[idx] + 0.30 * h_n[idx] + 0.15 * p_n[idx] + 0.20 * feats[idx]["pace"]
        w["score"] = int(round(raw * 100))
        w["reason"] = "Strong hook words, energy and pace in this part"
    ranked = sorted(windows, key=lambda w: -w["score"])
    chosen = []
    for w in ranked:
        if all(w["end"] <= c["start"] - 3 or w["start"] >= c["end"] + 3 for c in chosen):
            chosen.append(w)
        if len(chosen) >= count:
            break
    chosen.sort(key=lambda w: w["start"])
    for i, w in enumerate(chosen, 1):
        w["title"] = f"Clip {i} — {w['text'][:60].strip()}..."
        w["hashtags"] = "#shorts #viral #clips"
    return chosen


# ---------------------------------------------------------------- Gemini ---

def detect_moments_gemini(segments, api_key, count=5, duration=0.0):
    """Ask Gemini for the best moments. Returns moments list or raises."""
    lines = "\n".join(f"[{s['start']:.0f}s] {s['text']}" for s in segments)
    prompt = (
        "You are an expert short-form video clipper for Whop Content Rewards campaigns.\n"
        f"Below is a timestamped transcript of a video ({duration:.0f} seconds long).\n"
        f"Pick the {count} MOST viral-worthy moments for TikTok / YouTube Shorts / Reels.\n"
        "Each moment must be 20 to 60 seconds long, start on a strong hook line, and make "
        "sense on its own. Reply with ONLY a JSON array, no markdown fences, like:\n"
        '[{"start": 12, "end": 45, "title": "short catchy post title", '
        '"reason": "why this will perform", "score": 87, '
        '"hashtags": "#shorts #viral"}]\n\nTranscript:\n' + lines
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4},
    }).encode("utf-8")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.0-flash:generateContent?key={api_key}")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("Gemini did not return a JSON list")
    moments = json.loads(match.group(0))
    clean = []
    for m in moments:
        try:
            start = float(m["start"])
            end = float(m["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if duration:
            start = max(0.0, min(start, duration - 5))
            end = max(start + 10, min(end, duration))
        clean.append({
            "start": start, "end": end,
            "title": str(m.get("title", "Clip"))[:120],
            "reason": str(m.get("reason", ""))[:240],
            "score": int(m.get("score", 70)),
            "hashtags": str(m.get("hashtags", "#shorts #viral #clips")),
            "text": "",
        })
    if not clean:
        raise ValueError("Gemini returned no usable moments")
    # attach transcript text for context
    for m in clean:
        m["text"] = " ".join(s["text"] for s in segments
                             if s["end"] > m["start"] and s["start"] < m["end"])[:400]
    return clean[:count]


# ---------------------------------------------------------------- cutting ---

def make_clip(video_path, start, end, out_path, layout="blur"):
    """Cut [start, end] from video_path into a 720x1280 clip at out_path."""
    dur = max(end - start, 1.0)
    if layout == "crop":
        vf = ("scale=720:1280:force_original_aspect_ratio=increase,"
              "crop=720:1280,format=yuv420p")
        args = ["-ss", f"{start:.2f}", "-i", video_path, "-t", f"{dur:.2f}",
                "-vf", vf, "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", out_path]
    else:  # blur fit — full frame visible over a blurred copy of itself
        fc = ("[0:v]scale=720:1280:force_original_aspect_ratio=increase,"
              "crop=720:1280,boxblur=20:5[bg];"
              "[0:v]scale=720:-2[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
        args = ["-ss", f"{start:.2f}", "-i", video_path, "-t", f"{dur:.2f}",
                "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", out_path]
    run_ffmpeg(args)
    return out_path


# ---------------------------------------------------------------- tracker ---

def build_tracker_csv(clips, source_name):
    """clips: list of dicts with name/title/score/reason/duration/hashtags."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Clip File", "Post Title", "Source Video", "Duration (s)",
                     "Virality Score", "Why This Moment", "Caption / Hashtags",
                     "Platform Posted", "Post Link", "Views", "Earnings ($)"])
    for c in clips:
        writer.writerow([c.get("name", ""), c.get("title", ""), source_name,
                         c.get("duration", ""), c.get("score", ""),
                         c.get("reason", ""), c.get("hashtags", ""), "", "", "", ""])
    return buf.getvalue()


def fmt_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"
