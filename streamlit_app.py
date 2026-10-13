"""Clipza — AI Clipping Tool (by JONNY PRODUCTIONS)

Upload a long video -> AI finds the best moments -> download ready 9:16 clips
with a Whop-ready posting package (titles, hashtags, tracking sheet).
No burned-in captions — clean clips only.
"""
import os
import tempfile
import zipfile

import streamlit as st

import clipcore

# Some environments ship no_proxy with bracketed IPv6 entries that crash httpx
# inside huggingface_hub (model download). Strip them defensively.
for _k in ("no_proxy", "NO_PROXY"):
    _v = os.environ.get(_k)
    if _v and "[" in _v:
        os.environ[_k] = ",".join(p for p in _v.split(",") if "[" not in p)

st.set_page_config(page_title="Clipza — AI Clipping Tool", page_icon="✂️", layout="wide")

# ------------------------------------------------------------------- style ---
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  .stApp { background: radial-gradient(1200px 600px at 20% -10%, #1c1706 0%, #0b0b0f 55%) fixed; }
  * { font-family: 'Inter', sans-serif !important; }

  .ck-hero {
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #14141b 0%, #241c05 60%, #2e2404 100%);
    border: 1px solid #3a3208; border-radius: 22px;
    padding: 34px 36px; margin-bottom: 18px;
    box-shadow: 0 12px 40px rgba(245,197,24,0.07);
  }
  .ck-hero::before {
    content: ""; position: absolute; inset: -60%; z-index: 0;
    background: conic-gradient(from 0deg, transparent 0 70%, rgba(245,197,24,0.10) 85%, transparent 100%);
    animation: ck-spin 9s linear infinite;
  }
  @keyframes ck-spin { to { transform: rotate(360deg); } }
  .ck-hero h1 {
    position: relative; z-index: 1; margin: 0; font-size: 2.7rem; font-weight: 800; letter-spacing: -1px;
    background: linear-gradient(92deg, #ffe08a, #f5c518 45%, #fff6cf 80%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .ck-hero p { position: relative; z-index: 1; color: #cfcfda; margin: 10px 0 0 0; font-size: 1.04rem; line-height: 1.55; }
  .ck-hero .ck-tag {
    position: relative; z-index: 1; display: inline-block; margin-bottom: 10px;
    background: rgba(245,197,24,0.12); color: #ffd94d; border: 1px solid rgba(245,197,24,0.35);
    font-size: 0.72rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;
    border-radius: 999px; padding: 5px 14px;
  }

  .ck-card {
    background: linear-gradient(180deg, #16161d, #131318);
    border: 1px solid #26262f; border-radius: 18px;
    padding: 20px 22px; margin-bottom: 16px;
    transition: border-color .2s, transform .2s;
  }
  .ck-card:hover { border-color: #4a4210; transform: translateY(-1px); }

  .ck-badge { display: inline-block; font-weight: 800; border-radius: 999px;
    padding: 3px 14px; font-size: 0.88rem; }
  .ck-badge.gold { background: linear-gradient(135deg, #ffe08a, #f5c518); color: #161105;
    box-shadow: 0 3px 14px rgba(245,197,24,0.35); }
  .ck-badge.green { background: rgba(46,204,113,0.16); color: #5df08f; border: 1px solid rgba(46,204,113,0.45); }
  .ck-badge.blue { background: rgba(93,156,255,0.14); color: #8db8ff; border: 1px solid rgba(93,156,255,0.4); }
  .ck-chip { display: inline-block; background: #22222b; color: #b9b9c6;
    border-radius: 999px; padding: 2px 11px; font-size: 0.78rem; margin-right: 6px; }

  .ck-quote { border-left: 3px solid #f5c518; padding: 6px 0 6px 14px;
    color: #a9a9b8; font-size: 0.9rem; font-style: italic; margin: 10px 0; }
  .ck-reason { color: #8f8f9c; font-size: 0.86rem; margin-top: 6px; }

  .ck-stepper { display: flex; gap: 8px; margin: 4px 0 20px 0; flex-wrap: wrap; }
  .ck-pill { flex: 1 1 0; min-width: 130px; border-radius: 14px; padding: 10px 14px;
    font-size: 0.82rem; font-weight: 700; color: #8a8a96; background: #14141b;
    border: 1px solid #23232c; text-align: center; }
  .ck-pill.done { color: #5df08f; border-color: rgba(46,204,113,0.4); background: rgba(46,204,113,0.06); }
  .ck-pill.active { color: #161105; background: linear-gradient(135deg, #ffe08a, #f5c518);
    border-color: transparent; box-shadow: 0 4px 18px rgba(245,197,24,0.30); }

  .ck-step { color: #f5c518; font-weight: 800; letter-spacing: 2px; font-size: 0.78rem;
             text-transform: uppercase; margin: 22px 0 10px 0; }
  .ck-muted { color: #9a9aa5; font-size: 0.9rem; }

  .ck-summary { display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 18px 0; }
  .ck-stat { flex: 1 1 0; min-width: 140px; background: linear-gradient(180deg, #181824, #121218);
    border: 1px solid #2b2b36; border-radius: 16px; padding: 16px 18px; text-align: center; }
  .ck-stat .n { font-size: 1.9rem; font-weight: 800; color: #ffd94d; }
  .ck-stat .l { font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; color: #8a8a96; margin-top: 4px; }

  div[data-testid="stFileUploader"] section {
    background: #14141b; border: 1.5px dashed #4a4210; border-radius: 18px; transition: border-color .2s;
  }
  div[data-testid="stFileUploader"] section:hover { border-color: #f5c518; }
  .stButton > button, .stDownloadButton > button { border-radius: 12px; font-weight: 700; transition: transform .15s; }
  .stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
  .stButton > button[kind="primary"], .stDownloadButton > button {
    background: linear-gradient(135deg, #ffe08a, #f5c518); color: #161105; border: none;
    box-shadow: 0 6px 22px rgba(245,197,24,0.28);
  }
  .stProgress > div > div > div > div { background: linear-gradient(90deg, #ffe08a, #f5c518); }
  video { border-radius: 14px; }
  .ck-footer { text-align: center; color: #6d6d78; font-size: 0.8rem; margin: 30px 0 10px 0; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------- helpers ---
def score_badge(score):
    tier = "gold" if score >= 90 else "green" if score >= 75 else "blue"
    return f"<span class='ck-badge {tier}'>🔥 {score}</span>"


def render_stepper(step):
    labels = ["① Upload", "② Find moments", "③ Review clips", "④ Download"]
    pills = []
    for i, label in enumerate(labels, 1):
        cls = "done" if i < step else "active" if i == step else ""
        mark = "✓ " if i < step else ""
        pills.append(f"<div class='ck-pill {cls}'>{mark}{label}</div>")
    st.markdown(f"<div class='ck-stepper'>{''.join(pills)}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------- state ---
for key, default in [("video_path", None), ("video_name", ""), ("duration", 0.0),
                     ("segments", None), ("moments", None), ("clips", None),
                     ("workdir", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------------------------------------------------------- hero ----
st.markdown("""
<div class="ck-hero">
  <span class="ck-tag">AI Clipping Tool</span>
  <h1>✂️ Clipza</h1>
  <p>Give it a long video — AI finds the best moments and turns them into <b>9:16 Shorts / Reels / TikTok</b>
  clips. With a ready-to-post Whop Content Rewards package: titles, hashtags and a tracking sheet.</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------- sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    language = st.selectbox("Video language",
                            ["Auto-detect", "Urdu", "Hindi", "English"])
    lang_code = {"Auto-detect": None, "Urdu": "ur", "Hindi": "hi",
                 "English": "en"}[language]
    clip_count = st.slider("How many clips?", 1, 8, 5)
    layout_label = st.radio("Clip style",
                            ["Blur Fit — full frame visible",
                             "Full Crop — fills the screen"])
    layout = "blur" if layout_label.startswith("Blur") else "crop"
    st.markdown("---")
    st.markdown("**🤖 Smart AI detection (optional)**")
    _secret_key = ""
    try:
        _secret_key = st.secrets.get("GEMINI_API_KEY", "") or ""
    except Exception:
        _secret_key = ""
    gemini_key_input = st.text_input(
        "Gemini API key", type="password",
        help="Free key from Google AI Studio. Without one, the built-in detection is used.")
    gemini_key = gemini_key_input or _secret_key
    if _secret_key and not gemini_key_input:
        st.caption("✅ Gemini AI is connected — smart detection is ON.")
    st.markdown("---")
    st.markdown("<span class='ck-muted'>Clipza by <b>JONNY PRODUCTIONS</b><br>"
                "Clean clips — no burned-in captions.</span>",
                unsafe_allow_html=True)

# current step for the stepper
if st.session_state.clips:
    _step = 4
elif st.session_state.moments:
    _step = 3
elif st.session_state.video_path:
    _step = 2
else:
    _step = 1
render_stepper(_step)

# -------------------------------------------------------------- step 1: file --
st.markdown("<div class='ck-step'>Step 1 — Upload your video</div>",
            unsafe_allow_html=True)
uploaded = st.file_uploader("MP4 / MOV / MKV / WEBM (max ~200MB, up to ~60 min works best)",
                            type=["mp4", "mov", "mkv", "webm"])
if uploaded is not None and uploaded.name != st.session_state.video_name:
    workdir = tempfile.mkdtemp(prefix="clipza_")
    path = os.path.join(workdir, uploaded.name)
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    st.session_state.update(video_path=path, video_name=uploaded.name,
                            workdir=workdir, segments=None, moments=None,
                            clips=None, duration=clipcore.probe_duration(path))
    st.success(f"Video received: **{uploaded.name}** "
               f"({clipcore.fmt_time(st.session_state.duration)} long)")

if st.session_state.video_path:
    st.video(st.session_state.video_path)

    # ----------------------------------------------------- step 2: moments --
    st.markdown("<div class='ck-step'>Step 2 — Find the best moments</div>",
                unsafe_allow_html=True)
    if st.button("🔍 Find moments", type="primary"):
        with st.spinner("Transcribing first, then picking the best moments... "
                        "Long videos can take a few minutes."):
            try:
                wav = os.path.join(st.session_state.workdir, "audio.wav")
                clipcore.extract_audio(st.session_state.video_path, wav)
                segments = clipcore.transcribe(wav, language=lang_code)
                st.session_state.segments = segments
                if not segments:
                    st.error("No speech found in this video — moments can't be detected.")
                else:
                    moments = None
                    if gemini_key:
                        try:
                            moments = clipcore.detect_moments_gemini(
                                segments, gemini_key, count=clip_count,
                                duration=st.session_state.duration)
                            st.info("🤖 Moments picked by Gemini AI.")
                        except Exception as exc:  # fall back silently to heuristic
                            st.warning(f"Gemini didn't work ({exc}). "
                                       "Using the built-in detection instead.")
                    if moments is None:
                        moments = clipcore.detect_moments_heuristic(
                            segments, wav, count=clip_count,
                            duration=st.session_state.duration)
                    st.session_state.moments = moments
                    st.session_state.clips = None
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")

    # -------------------------------------------------- step 3: pick & edit --
    if st.session_state.moments:
        st.markdown("<div class='ck-step'>Step 3 — Review moments, then make clips</div>",
                    unsafe_allow_html=True)
        sel1, sel2, _ = st.columns([1, 1, 4])
        with sel1:
            if st.button("Select all"):
                for i in range(len(st.session_state.moments)):
                    st.session_state[f"keep_{i}"] = True
                st.rerun()
        with sel2:
            if st.button("Clear all"):
                for i in range(len(st.session_state.moments)):
                    st.session_state[f"keep_{i}"] = False
                st.rerun()
        edited = []
        for i, m in enumerate(st.session_state.moments):
            dur = m["end"] - m["start"]
            with st.container():
                st.markdown(f"<div class='ck-card'>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 3, 2])
                with c1:
                    st.markdown(score_badge(m["score"]), unsafe_allow_html=True)
                    st.markdown(f"<span class='chip-wrap'><span class='ck-chip'>"
                                f"{clipcore.fmt_time(m['start'])} → {clipcore.fmt_time(m['end'])}</span>"
                                f"<span class='ck-chip'>{dur:.0f}s</span></span>",
                                unsafe_allow_html=True)
                with c2:
                    title = st.text_input("Post title", m["title"],
                                          key=f"title_{i}", label_visibility="collapsed")
                    st.markdown(f"<div class='ck-reason'>{m.get('reason', '')}</div>",
                                unsafe_allow_html=True)
                    if m.get("text"):
                        st.markdown(f"<div class='ck-quote'>“{m['text'][:180]}…”</div>",
                                    unsafe_allow_html=True)
                with c3:
                    keep = st.checkbox("Make this clip", value=True, key=f"keep_{i}")
                    new_start = st.number_input(
                        "Start (sec)", 0.0, st.session_state.duration,
                        float(m["start"]), 1.0, key=f"start_{i}")
                    new_end = st.number_input(
                        "End (sec)", 0.0, st.session_state.duration,
                        float(m["end"]), 1.0, key=f"end_{i}")
                    hashtags = st.text_input("Hashtags", m.get("hashtags", ""),
                                             key=f"tags_{i}", label_visibility="collapsed")
                st.markdown("</div>", unsafe_allow_html=True)
                if keep and new_end > new_start:
                    edited.append({"start": new_start, "end": new_end, "title": title,
                                   "score": m["score"], "reason": m.get("reason", ""),
                                   "hashtags": hashtags})

        if st.button("✂️ Make clips", type="primary"):
            if not edited:
                st.warning("No moment selected.")
            else:
                out_dir = os.path.join(st.session_state.workdir, "clips")
                os.makedirs(out_dir, exist_ok=True)
                made = []
                progress = st.progress(0.0, text="Making clips...")
                for idx, m in enumerate(edited):
                    name = f"clip_{idx + 1:02d}.mp4"
                    out_path = os.path.join(out_dir, name)
                    try:
                        clipcore.make_clip(st.session_state.video_path,
                                           m["start"], m["end"], out_path,
                                           layout=layout)
                        made.append({**m, "name": name, "path": out_path,
                                     "duration": round(m["end"] - m["start"])})
                    except Exception as exc:
                        st.error(f"{name} failed: {exc}")
                    progress.progress((idx + 1) / len(edited),
                                      text=f"Making clips... {idx + 1}/{len(edited)}")
                progress.empty()
                st.session_state.clips = made
                if made:
                    st.success(f"🎉 {len(made)} clips are ready!")

    # ------------------------------------------------------ step 4: results --
    if st.session_state.clips:
        st.markdown("<div class='ck-step'>Step 4 — Download & post your clips</div>",
                    unsafe_allow_html=True)
        total_secs = sum(c["duration"] for c in st.session_state.clips)
        st.markdown(f"""
        <div class="ck-summary">
          <div class="ck-stat"><div class="n">{len(st.session_state.clips)}</div><div class="l">Clips ready</div></div>
          <div class="ck-stat"><div class="n">{total_secs // 60}:{total_secs % 60:02d}</div><div class="l">Total clip time</div></div>
          <div class="ck-stat"><div class="n">{clipcore.fmt_time(st.session_state.duration)}</div><div class="l">Source video</div></div>
        </div>
        """, unsafe_allow_html=True)
        for c in st.session_state.clips:
            st.markdown("<div class='ck-card'>", unsafe_allow_html=True)
            vcol, tcol = st.columns([1, 2])
            with vcol:
                st.video(c["path"])
            with tcol:
                st.markdown(f"{score_badge(c['score'])} &nbsp;**{c['title']}**",
                            unsafe_allow_html=True)
                st.markdown(f"<span class='ck-muted'>{c['name']} • "
                            f"{c['duration']} sec</span>",
                            unsafe_allow_html=True)
                st.code(f"{c['title']}\n{c['hashtags']}", language=None)
                with open(c["path"], "rb") as f:
                    st.download_button(f"⬇️ Download {c['name']}", f.read(),
                                       file_name=c["name"], mime="video/mp4",
                                       key=f"dl_{c['name']}")
            st.markdown("</div>", unsafe_allow_html=True)

        # ZIP of all clips + Whop tracking sheet
        zip_path = os.path.join(st.session_state.workdir, "clipza_clips.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for c in st.session_state.clips:
                zf.write(c["path"], c["name"])
            zf.writestr("whop_tracker.csv",
                        clipcore.build_tracker_csv(st.session_state.clips,
                                                   st.session_state.video_name))
        with open(zip_path, "rb") as f:
            st.download_button("📦 All clips + Whop tracking sheet (ZIP)", f.read(),
                               file_name="clipza_clips.zip",
                               mime="application/zip", type="primary")
        st.markdown("<span class='ck-muted'>How Whop works: post each clip to your "
                    "TikTok / Shorts / Reels, then submit its link in the Whop "
                    "campaign. Keep logging links and views in the tracking "
                    "sheet — everything stays organised.</span>",
                    unsafe_allow_html=True)

st.markdown("<div class='ck-footer'>✂️ Clipza by <b>JONNY PRODUCTIONS</b> • Made for creators</div>",
            unsafe_allow_html=True)
