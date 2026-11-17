"""A timeline.json made from the script alone (no voice), so the director can render stills and
check pacing before any TTS time is spent. Same format as show-pixel/audio.py writes, plus
"preview": true. Sentence lengths come from the runtime estimate; mouth shapes are a simple
talking loop for whoever is speaking.

    python newsroom/preview_timeline.py episodes/<date>/script.json episodes/<date>/build/preview_timeline.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "show-catalog"))
import runtime  # noqa: E402

TALK = "BCDCBEFCBDCHB"


def build(script: dict) -> dict:
    cast = script.get("cast", {})
    t = runtime.INTRO_S
    tl = {"preview": True, "intro": [0, runtime.INTRO_S], "segments": [], "mouth": []}
    for seg in script["segments"]:
        s0, sents = t, []
        for s in seg["sentences"]:
            text = s if isinstance(s, str) else s["text"]
            spk = (s.get("speaker") if isinstance(s, dict) else None) or seg.get("speaker", "pixie")
            dur = max(0.6, runtime.words(s) / (runtime.WPM * cast.get(spk, {}).get("speed", 1.0)) * 60)
            sents.append({"text": text, "speaker": spk, "start": round(t, 3), "end": round(t + dur, 3)})
            k, m = 0, t
            while m < t + dur - 0.05:
                tl["mouth"].append([round(m, 3), round(min(m + 0.11, t + dur), 3), TALK[k % len(TALK)]])
                m += 0.11
                k += 1
            t += dur + runtime.SENT_GAP_S
        tl["segments"].append({**{k: v for k, v in seg.items() if k != "sentences"}, "start": round(s0, 3), "end": round(t, 3), "sentences": sents})
        t += runtime.SEG_GAP_S
    tl["outro"] = [round(t, 3), round(t + runtime.OUTRO_S, 3)]
    tl["duration"] = round(t + runtime.OUTRO_S, 3)
    return tl


if __name__ == "__main__":
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    tl = build(json.loads(Path(sys.argv[1]).read_text()))
    out.write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    print(f"preview timeline {runtime.fmt(tl['duration'])} -> {out}")
