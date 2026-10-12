# ✂️ ClipKaro — AI Clipping Tool

By **JONNY PRODUCTIONS**. Upload a long video (podcast, interview, stream) and
ClipKaro finds the best moments and cuts clean **9:16 clips** ready for
TikTok, YouTube Shorts and Instagram Reels — plus a Whop Content Rewards
posting package (titles, hashtags and a tracking sheet). No burned-in captions.

## How it works
1. Upload a video (MP4/MOV/MKV/WEBM, up to ~200MB; up to ~60 min works best)
2. Audio is transcribed locally with faster-whisper
3. Best moments are picked — by Gemini AI if you paste a free API key in the
   sidebar, otherwise by a built-in hook/energy/pace scorer
4. Moments can be reviewed and trimmed, then cut in two styles:
   **Blur Fit** (full frame over a blurred background) or **Full Crop**
5. Download clips one by one, or all together as a ZIP with `whop_tracker.csv`

## Run locally
```bash
pip install -r requirements.txt   # also needs ffmpeg on PATH
streamlit run streamlit_app.py
```

## Notes
- Whop does not offer an API for submitting clips; post each clip yourself,
  then submit its link inside the Whop campaign. The tracker sheet keeps the
  links, views and earnings organised.
- Long videos take a while to transcribe on free hosting — be patient.
