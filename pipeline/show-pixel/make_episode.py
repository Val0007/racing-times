"""One command (API route), editor notes in -> finished pixel episode out.

    python make_episode.py ../episodes/<date>/editor_notes.json --minutes 10   (API route; the newsroom uses rt-produce)
    python make_episode.py --script pilot.json            # skip the writer, use a script you edited
"""
import argparse
import json
import sys
from pathlib import Path

import audio
import render

ap = argparse.ArgumentParser()
ap.add_argument("edition", nargs="?")
ap.add_argument("--script")
ap.add_argument("--minutes", type=float, default=10)
ap.add_argument("--out", default="episode.mp4")
a = ap.parse_args()

if a.script:
    script_path = a.script
else:
    from script_writer import write_script
    ed = json.loads(Path(a.edition).read_text())
    script_path = f"episode_{ed['episode']:02d}.json"
    Path(script_path).write_text(json.dumps(write_script(ed, a.minutes), indent=1, ensure_ascii=False))
    print("1/3 script written ->", script_path)

# Gate: never spend TTS time on a script the renderers can't draw.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "show-catalog"))
from validate import validate  # noqa: E402

errs, warns = validate(json.loads(Path(script_path).read_text()))
for w in warns:
    print("warning:", w)
if errs:
    sys.exit("script does not match show-catalog/catalog.json:\n  " + "\n  ".join(errs))
import runtime  # noqa: E402
print(f"estimated length {runtime.fmt(runtime.estimate(json.loads(Path(script_path).read_text()))['total'])} (limit 10:00)")

build = Path("build") / Path(script_path).stem
tl = audio.build(script_path, str(build))
print(f"2/3 voice, lip sync and music done ({tl['duration']:.0f}s)")
# Hard limit: never render an episode longer than 10:00. Say where the time went.
import runtime  # noqa: E402
if tl["duration"] > runtime.LIMIT_S:
    segs = sorted(((s["id"], s["end"] - s["start"]) for s in tl["segments"]), key=lambda x: -x[1])
    sys.exit(f"episode is {runtime.fmt(tl['duration'])}, over the {runtime.fmt(runtime.LIMIT_S)} limit by "
             f"{tl['duration'] - runtime.LIMIT_S:.0f}s. Trim the script (longest: "
             + ", ".join(f"{i} {t:.0f}s" for i, t in segs[:5]) + f") and re-run with --script {script_path}.")
render.render(script_path, str(build), a.out)
print("3/3 rendered ->", a.out)
