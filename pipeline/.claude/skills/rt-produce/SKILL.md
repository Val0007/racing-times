---
name: rt-produce
description: Racing Times production. Turns an approved, fact-checked episode script into the finished video (voices, lip sync, 3D render, score, mix) and the YouTube-style description with every source linked. Code only, no writing. Use after Checkpoint 2 and a passing fact-check.
---

# Produce: script.json → out/episode.mp4 + out/description.md

## Gate (stop if any fails)
```bash
python newsroom/episode.py status <date>      # needs: "look" approved, factcheck ✓ (and tied to this exact script)
python newsroom/contracts.py episodes/<date>   # everything OK
```
If `script.json` changed after the fact-check, `contracts.py` says so. Run the fact-checker again first.

## Steps
```bash
E=episodes/<date>
# 1. voices + lip sync + timing (stops if over 10:00)
#    ElevenLabs v3 by default (key in .env, voices in show-pixel/voices/voices.json): one take per run of a
#    speaker's consecutive lines, so each voice stays consistent; delivery = inline emotion tag; takes are cached.
#    RT_VOICE=kokoro for the free local fallback.
python show-pixel/audio.py $E/script.json $E/build
python -c "import json,sys; d=json.load(open('$E/build/timeline.json'))['duration']; sys.exit(d>600 and f'{d:.0f}s is over 10:00')"
# 2. 3D video (serve the repo root first: python3 show-3d/serve.py &)
python show-3d/capture.py video $E/build/video_only.mp4 24 0 999 --episode $E --timeline build/timeline.json
# 3. score + mix + loudness
python show-3d/score.py $E/build/timeline.json $E/build/narration.wav $E/build/mix.wav
ffmpeg -y -i $E/build/video_only.mp4 -i $E/build/mix.wav -c:v libx264 -crf 20 -af loudnorm=I=-14:TP=-1.5 -c:a aac -b:a 192k -shortest $E/out/episode.mp4
# 4. description with every source link
python newsroom/credits.py $E
```
Needs: Rhubarb (macOS build in `show-pixel/vendor/`), ffmpeg (`.venv/bin/ffmpeg`), Playwright Chromium, the ElevenLabs key in `.env` (Text to Speech, Voices read). Put `.venv/bin` on PATH. Keep the laptop lid open during the render: about 90 minutes for a 6-minute episode.

## Check before Checkpoint 3
- Duration ≤ 10:00. Watch the first 20 seconds, Byte's segment and the credits roll.
- `out/description.md` lists every source and photo credit.
- Then hand back to rt-weekly for Checkpoint 3. Never upload or publish anything yourself.
