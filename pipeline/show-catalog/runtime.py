"""Episode length: one hard limit, one simple estimate.

Every episode is at most 10:00 including the intro and credits. The writer aims for 9:30 by
estimate, which leaves room for TTS being slower than expected; make_episode checks the real
length after recording.

Estimate = intro + outro + spoken words at WPM (per speaker speed) + pauses.
Kokoro measured 182 wpm on the pilot; 170 is used so the estimate runs a little long (safe).
"""
from __future__ import annotations

import os
import re

LIMIT_S = 600          # hard limit: 10:00
TARGET_S = 570         # what the writer aims for (30 s of safety)
WPM = float(os.getenv("RT_WPM", "170"))
INTRO_S, OUTRO_S, SENT_GAP_S, SEG_GAP_S = 4.2, 6.0, 0.22, 0.55   # same as show-pixel/audio.py

_WORD = re.compile(r"[\w'-]+")


def words(s) -> int:
    t = s if isinstance(s, str) else s.get("say", s.get("text", ""))
    return len(_WORD.findall(t))


def estimate(script: dict) -> dict:
    """Seconds per segment and in total."""
    cast = script.get("cast", {})
    per_seg, total = [], INTRO_S + OUTRO_S
    for seg in script.get("segments", []):
        t = 0.0
        for s in seg.get("sentences", []):
            spk = (s.get("speaker") if isinstance(s, dict) else None) or seg.get("speaker", "pixie")
            speed = cast.get(spk, {}).get("speed", 1.0)
            t += words(s) / (WPM * speed) * 60 + SENT_GAP_S
        t += SEG_GAP_S
        per_seg.append((seg.get("id", "?"), round(t, 1)))
        total += t
    return {"total": round(total, 1), "segments": per_seg}


def fmt(sec: float) -> str:
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def draft_words(target_s: float = TARGET_S) -> int:
    """Word budget for a first draft (allows ~20% of time for pauses and the open/close)."""
    return int((target_s - INTRO_S - OUTRO_S) * 0.92 / 60 * WPM)


# Cut order the writer follows when a draft is too long. Keep it boring and predictable.
CUT_ORDER = """Cut in this order until it fits, re-reading after each step:
1. Briefs round: drop briefs from the end of the list.
2. Banter: extra link lines (keep the hello, each hand-off and the sign-off).
3. Pixie's opinions: keep only her best ones.
4. Byte: keep one opinion and his single best anecdote per segment; drop the rest.
5. The lowest-ranked stories (latest in the running order): cut to one or two sentences, or drop them.
Never cut: the cold open, the headlines, the lead story's facts, the sign-off or the credits.
Don't speed up the wording to cram more in; remove whole sentences."""
