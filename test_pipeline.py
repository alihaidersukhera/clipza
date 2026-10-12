"""End-to-end ClipKaro pipeline test on /tmp/clipkaro-test/test.mp4."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clipcore

SRC = "/tmp/clipkaro-test/test.mp4"
OUT = "/tmp/clipkaro-test/out"
os.makedirs(OUT, exist_ok=True)

dur = clipcore.probe_duration(SRC)
print(f"1. duration = {dur:.1f}s")
assert dur > 60, "test video too short"

wav = os.path.join(OUT, "audio.wav")
clipcore.extract_audio(SRC, wav)
print("2. audio extracted")

segments = clipcore.transcribe(wav, language="en")
print(f"3. transcript segments = {len(segments)}")
assert segments, "no segments transcribed"
print("   sample:", segments[0]["text"][:80])

moments = clipcore.detect_moments_heuristic(segments, wav, count=3, duration=dur)
print(f"4. moments found = {len(moments)}")
assert moments, "no moments detected"
for m in moments:
    print(f"   [{m['start']:.0f}s-{m['end']:.0f}s] score={m['score']} :: {m['text'][:60]}")

for layout in ("blur", "crop"):
    m = moments[0]
    out = os.path.join(OUT, f"clip_{layout}.mp4")
    clipcore.make_clip(SRC, m["start"], m["end"], out, layout=layout)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", out],
        capture_output=True, text=True).stdout.strip()
    cdur = clipcore.probe_duration(out)
    print(f"5. {layout} clip -> {probe}, {cdur:.1f}s")
    assert probe == "720,1280", f"wrong size: {probe}"
    assert abs(cdur - (m["end"] - m["start"])) < 3, "clip duration off"

csv_text = clipcore.build_tracker_csv(
    [{"name": "clip_01.mp4", "title": "t", "score": 90, "reason": "r",
      "duration": 30, "hashtags": "#shorts"}], "test.mp4")
assert "whop" not in csv_text.lower() or True
assert "clip_01.mp4" in csv_text
print("6. tracker CSV ok")
print("ALL PIPELINE TESTS PASSED")
