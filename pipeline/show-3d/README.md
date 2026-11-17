# Racing Times 3D show

three.js studio and grid, rendered frame by frame in headless Chromium, encoded with ffmpeg.

```
script.json + timeline.json (+ photos/) --> show/show.js  (window.renderAt(t))
                                             sets.js        studio (wall, desk display, Pixie) + grid (Byte, crowd)
                                             characters.js  Pixie, Byte, RT palette, wordmark
                                             wallcards.js   catalog cards on the wall
capture.py (Playwright) --> frames --> ffmpeg;  score.py --> music under the voice
```

## Run
```bash
npm install                                   # in show-3d/
python3 show-3d/serve.py &                    # from the repo root: http://127.0.0.1:8765
# stills for review (no voice needed: build a preview timeline first)
python newsroom/preview_timeline.py episodes/<date>/script.json episodes/<date>/build/preview_timeline.json
python show-3d/capture.py stills "10,30,60" episodes/<date>/stills/s --episode episodes/<date> --timeline build/preview_timeline.json
python show-3d/contact_sheet.py episodes/<date>/stills
# full render after rt-produce has made build/timeline.json + narration.wav: see .claude/skills/rt-produce/SKILL.md
```
Preview in a browser: `/show-3d/show/index.html?episode=/episodes/<date>&timeline=build/preview_timeline.json`, then `renderAt(42)` in the console. With no parameters it plays the pilot in `show/data/`.

On a Mac the capture uses the GPU. On a Linux server without a GPU it falls back to software WebGL (about 1.9 s per frame).
