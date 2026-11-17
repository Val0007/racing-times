---
name: rt-director
description: Racing Times director. Sets shots, cuts, wall graphics, lower thirds and the desk display in an episode's script.json using only what the show catalog allows, builds a voice-free preview timeline and renders review stills for Checkpoint 2. Use after rt-writer, before the fact-check.
---

# Director: script.json → shots, graphics, stills

The catalog is the only menu: `python show-catalog/validate.py --describe`. Never invent a shot or a graphic kind; if one is missing, tell the user instead.

## Grammar (keep it simple)
- **Pixie segments (studio):** start `wide` with `"point": true` when a new wall graphic appears. Go `full` when a table, list or dates must be read. Use `close` for opinions, sensitive stories and the sign-off.
- **Byte segments (grid):** start `wide` (he's in the middle of the grid), then `close` for his opinion and anecdote lines. `full` cuts back to the studio wall for a graphic. Use it sparingly.
- Change shot about every 6-12 seconds. Never twice inside one sentence.
- **Photos everywhere (producer's standard):** every story with approved photos gets at least 2 different photo cards (`n` = 1, 2…). Use `graphic` + `graphic_b`, and split long stories into two segments, so the wall changes every 10–15 seconds. Byte's segments cut to `full` to show his story's photos. Overall, at least one photo card per 25 seconds; `contracts.py` checks this. Results tables still go on `graphic_b` with a `full` shot.
- The studio has no depth-of-field blur (photos behind Pixie stay sharp); only Byte's crowd is blurred. That's in the renderer; nothing to set.
- **Lower thirds:** introduce each person or story once (title ≤ 22 chars, sub ≤ 34).
- **Desk display:** `title`, then `live` ("Live from Stockholm"), then `next` with the next two headlines.

Shot fractions are shares of the segment's spoken length. Line them up with sentence starts using the preview timeline below.

## Preview and stills
```bash
python newsroom/preview_timeline.py episodes/<date>/script.json episodes/<date>/build/preview_timeline.json
python3 show-3d/serve.py &      # http://127.0.0.1:8765 (repo root)
python show-3d/capture.py stills "<t1>,<t2>,..." episodes/<date>/stills/s \
       --episode episodes/<date> --timeline build/preview_timeline.json
```
Pick one time per segment, in the middle of its main shot (the preview timeline has the start and end times). Plus one Byte close-up and one desk-display moment. Then make a contact sheet:
```bash
python show-3d/contact_sheet.py episodes/<date>/stills
```
Look at every still yourself before showing the user. Check for cut-off text, a wrong photo, an empty wall, or Byte or Pixie hidden. Fix the script, re-render the affected stills, then present the sheet at Checkpoint 2.

Finally: `python show-catalog/validate.py --strict episodes/<date>/script.json` must pass.
