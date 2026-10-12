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
  .stApp { background: #0b0b0f; }
  .ck-hero {
    background: linear-gradient(135deg, #16161d 0%, #1f1a05 55%, #2a2103 100%);
    border: 1px solid #3a3208; border-radius: 20px; padding: 30px 34px; margin-bottom: 8px;
  }
  .ck-hero h1 {
    margin: 0; font-size: 2.5rem; font-weight: 800; letter-spacing: -0.5px;
    background: linear-gradient(90deg, #ffd94d, #f5c518 45%, #fff3b0);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .ck-hero p { color: #c9c9d4; margin: 8px 0 0 0; font-size: 1.02rem; }
  .ck-card {
    background: #14141b; border: 1px solid #26262f; border-radius: 16px;
    padding: 18px 20px; margin-bottom: 14px;
  }
  .ck-score {
    display: inline-block; background: #f5c518; color: #111; font-weight: 800;
    border-radius: 999px; padding: 2px 12px; font-size: 0.85rem;
  }
  .ck-step { color: #f5c518; font-weight: 700; letter-spacing: 1.5px; font-size: 0.8rem;
             text-transform: uppercase; }
  .ck-muted { color: #9a9aa5; font-size: 0.9rem; }
  div[data-testid="stFileUploader"] section {
    background: #14141b; border: 1.5px dashed #4a4210; border-radius: 16px;
  }
  .stButton > button, .stDownloadButton > button {
    border-radius: 12px; font-weight: 700;
  }
  .stButton > button[kind="primary"], .stDownloadButton > button {
    background: #f5c518; color: #111; border: none;
  }
</style>
<div class="ck-hero">
  <h1>✂️ Clipza</h1>
  <p>Give it a long video — AI finds the best moments and turns them into <b>9:16 Shorts / Reels / TikTok</b>
  clips. With a ready-to-post Whop Content Rewards package.</p>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------- state ---
for key, default in [("video_path", None), ("video_name", ""), ("duration", 0.0),
                     ("segments", None), ("moments", None), ("clips", None),
                     ("workdir", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

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
        edited = []
        for i, m in enumerate(st.session_state.moments):
            with st.container():
                st.markdown(f"<div class='ck-card'>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([1, 3, 2])
                with c1:
                    st.markdown(f"<span class='ck-score'>🔥 {m['score']}</span>",
                                unsafe_allow_html=True)
                    st.markdown(f"<span class='ck-muted'>"
                                f"{clipcore.fmt_time(m['start'])} → "
                                f"{clipcore.fmt_time(m['end'])}</span>",
                                unsafe_allow_html=True)
                with c2:
                    title = st.text_input("Post title", m["title"],
                                          key=f"title_{i}", label_visibility="collapsed")
                    st.markdown(f"<span class='ck-muted'>{m.get('reason', '')}</span>",
                                unsafe_allow_html=True)
                    if m.get("text"):
                        st.markdown(f"<span class='ck-muted'>“{m['text'][:180]}…”</span>",
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
        for c in st.session_state.clips:
            st.markdown("<div class='ck-card'>", unsafe_allow_html=True)
            vcol, tcol = st.columns([1, 2])
            with vcol:
                st.video(c["path"])
            with tcol:
                st.markdown(f"**{c['title']}**")
                st.markdown(f"<span class='ck-muted'>{c['name']} • "
                            f"{c['duration']} sec • Score {c['score']}</span>",
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
