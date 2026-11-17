"""Checks for every file that passes between newsroom stages. One function per file; no dependencies.

    python newsroom/contracts.py episodes/2026-11-16/editor_notes.json   # kind from the file name
    python newsroom/contracts.py episodes/2026-11-16                      # every known file in the folder

Files (in episodes/<date>/):
  wire.json          journalist  -> ranked story clusters
  editor_notes.json  editor      -> chosen stories, facts, angles, sources
  anecdotes.json     writer      -> verified history for Byte (anecdote-finder)
  script.json        writer/director -> checked by show-catalog/validate.py --strict
  photos/photos.json photo desk  -> one photo per story, with credit and a decision
  factcheck.json     fact-checker -> pass / fail, tied to the exact script it checked
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "show-catalog"))
from validate import CAST, validate  # noqa: E402
import runtime  # noqa: E402

URL = re.compile(r"^https?://")


def _need(d, keys, where, errs):
    for k in keys:
        if k not in d:
            errs.append(f"{where}: missing {k!r}")


def _src(s, where, errs):
    if not isinstance(s, dict) or not URL.match(str(s.get("url", ""))) or not s.get("name"):
        errs.append(f"{where}: needs {{name, url}} with an http(s) url")


def check_wire(w: dict) -> list[str]:
    errs = []
    _need(w, ["generated", "window_days", "stories"], "wire", errs)
    ids = set()
    for i, s in enumerate(w.get("stories", [])):
        at = f"wire.stories[{i}]"
        _need(s, ["id", "series", "title", "summary", "heat", "heat_reasons", "outlets", "official", "articles"], at, errs)
        if s.get("id") in ids:
            errs.append(f"{at}: duplicate id {s.get('id')!r}")
        ids.add(s.get("id"))
        if not isinstance(s.get("heat"), (int, float)) or not 0 <= s.get("heat", -1) <= 100:
            errs.append(f"{at}.heat: number 0-100")
        if not s.get("articles"):
            errs.append(f"{at}.articles: at least one")
        for j, a in enumerate(s.get("articles", [])):
            if not URL.match(str(a.get("url", ""))):
                errs.append(f"{at}.articles[{j}]: needs a url")
    heats = [s.get("heat", 0) for s in w.get("stories", [])]
    if heats != sorted(heats, reverse=True):
        errs.append("wire.stories: must be sorted by heat, hottest first")
    return errs


def check_editor_notes(n: dict) -> list[str]:
    errs = []
    _need(n, ["episode", "date", "date_display", "city", "cold_open_hook", "stories", "briefs", "next_week_hook"], "notes", errs)
    stories = n.get("stories", [])
    if not stories:
        errs.append("notes.stories: at least one")
    if sum(s.get("emphasis") == "lead" for s in stories) != 1:
        errs.append("notes.stories: exactly one story has emphasis 'lead'")
    ranks = [s.get("rank") for s in stories]
    if sorted(ranks) != list(range(1, len(stories) + 1)):
        errs.append("notes.stories: ranks must be 1..N with no gaps")
    for i, s in enumerate(stories):
        at = f"notes.stories[{s.get('id', i)}]"
        _need(s, ["id", "rank", "emphasis", "speaker", "series", "kicker", "headline", "angle", "facts", "sources",
                  "photo", "sensitive", "anecdote_facts"], at, errs)
        if s.get("emphasis") not in ("lead", "major", "minor"):
            errs.append(f"{at}.emphasis: lead | major | minor")
        if s.get("speaker") not in CAST:
            errs.append(f"{at}.speaker: one of {', '.join(CAST)}")
        if not s.get("facts"):
            errs.append(f"{at}.facts: at least one fact (the writer may use only these)")
        if not s.get("sources"):
            errs.append(f"{at}.sources: at least one")
        for j, src in enumerate(s.get("sources", [])):
            _src(src, f"{at}.sources[{j}]", errs)
        if s.get("sensitive") and s.get("speaker") == "byte":
            errs.append(f"{at}: sensitive stories go to Pixie, not Byte (bible/tone.md)")
    if not any(s.get("speaker") == "byte" for s in stories):
        errs.append("notes.stories: give Byte at least one story")
    q = n.get("quote")
    if q:
        _need(q, ["text", "speaker", "source_name", "source_url"], "notes.quote", errs)
        if len(str(q.get("text", "")).split()) >= 15:
            errs.append("notes.quote.text: under 15 words")
        if not URL.match(str(q.get("source_url", ""))):
            errs.append("notes.quote.source_url: needs a url")
    for i, b in enumerate(n.get("briefs", [])):
        _need(b, ["series", "text", "source"], f"notes.briefs[{i}]", errs)
        _src(b.get("source"), f"notes.briefs[{i}].source", errs)
    return errs


def check_anecdotes(a: list) -> list[str]:
    errs = []
    if not isinstance(a, list):
        return ["anecdotes: a list"]
    for i, x in enumerate(a):
        at = f"anecdotes[{i}]"
        _need(x, ["fact", "claim", "source_url", "supported_wording", "evidence"], at, errs)
        if not URL.match(str(x.get("source_url", ""))):
            errs.append(f"{at}.source_url: needs a url")
        if not x.get("evidence"):
            errs.append(f"{at}.evidence: quote the page for every number in the claim")
    return errs


def check_photos(p: list, folder: Path) -> list[str]:
    errs = []
    if not isinstance(p, list):
        return ["photos: a list"]
    seen = set()
    for i, x in enumerate(p):
        at = f"photos[{x.get('story', i)}#{x.get('n', 1)}]"
        key = (x.get("story"), x.get("n", 1))
        if key in seen:
            errs.append(f"{at}: duplicate story + n")
        seen.add(key)
        _need(x, ["story", "file", "article", "credit", "status"], at, errs)
        if x.get("status") not in ("approved", "rejected", "needs_check"):
            errs.append(f"{at}.status: approved | rejected | needs_check")
        if x.get("status") != "rejected" and not (folder / str(x.get("file"))).exists():
            errs.append(f"{at}.file: {x.get('file')} not found")
        if x.get("status") == "approved" and not x.get("credit"):
            errs.append(f"{at}.credit: approved photos need a credit")
    return errs


def script_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def check_factcheck(f: dict, folder: Path) -> list[str]:
    errs = []
    _need(f, ["script_sha", "checked_at", "result", "lines"], "factcheck", errs)
    if f.get("result") not in ("pass", "fail"):
        errs.append("factcheck.result: pass | fail")
    bad = [l for l in f.get("lines", []) if l.get("verdict") in ("wrong", "unsupported")]
    if f.get("result") == "pass" and bad:
        errs.append(f"factcheck: result is 'pass' but {len(bad)} line(s) are wrong/unsupported")
    for i, l in enumerate(f.get("lines", [])):
        _need(l, ["segment", "index", "kind", "verdict"], f"factcheck.lines[{i}]", errs)
        if l.get("verdict") not in ("ok", "wrong", "unsupported", "skip"):
            errs.append(f"factcheck.lines[{i}].verdict: ok | wrong | unsupported | skip")
    script = folder / "script.json"
    if script.exists() and f.get("script_sha") != script_hash(script):
        errs.append("factcheck: script.json changed after this fact-check; run the fact-checker again")
    return errs


def check_photo_use(s: dict, folder: Path) -> list[str]:
    """Every story with approved photos gets photo cards: at least min(approved, 2), and the whole episode at
    least one photo card per 25 seconds (estimate). Producer's standard, 17 Nov 2026."""
    pj = folder / "photos" / "photos.json"
    if not pj.exists():
        return []
    approved = {}
    for p in json.loads(pj.read_text()):
        if p.get("status") == "approved":
            approved[p["story"]] = approved.get(p["story"], 0) + 1
    used = {}
    for seg in s.get("segments", []):
        for g in (seg.get("graphic"), seg.get("graphic_b")):
            if g and g.get("kind") == "photo":
                used[g["story"]] = used.get(g["story"], set()) | {g.get("n", 1)}
    errs = []
    for story, n in approved.items():
        need = min(n, 2)
        have = len(used.get(story, set()))
        if have < need:
            errs.append(f"script: story '{story}' has {n} approved photo(s) but only {have} photo card(s); use at least {need} (rt-director)")
    cards = sum(len(v) for v in used.values())
    est = runtime.estimate(s)["total"]
    if approved and cards < est / 25:
        errs.append(f"script: {cards} photo cards for about {runtime.fmt(est)}; aim for one per 25 seconds ({int(est / 25) + 1}+)")
    return errs


def check_script(s: dict, folder: Path | None = None) -> list[str]:
    errs, _ = validate(s, strict=True)
    if folder is not None:
        errs += check_photo_use(s, folder)
    est = runtime.estimate(s)["total"]
    if est > runtime.LIMIT_S:
        errs.append(f"script: estimated {runtime.fmt(est)}, over the 10:00 limit")
    return errs


def check_file(path: Path) -> list[str]:
    name = path.name
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as ex:
        return [f"{name}: not valid JSON ({ex})"]
    folder = path.parent
    if name == "wire.json":
        return check_wire(data)
    if name == "editor_notes.json":
        return check_editor_notes(data)
    if name == "anecdotes.json":
        return check_anecdotes(data)
    if name == "photos.json":
        return check_photos(data, folder)
    if name == "factcheck.json":
        return check_factcheck(data, folder)
    if name == "script.json":
        return check_script(data, folder)
    return []


KNOWN = ["wire.json", "editor_notes.json", "anecdotes.json", "photos/photos.json", "script.json", "factcheck.json"]

if __name__ == "__main__":
    bad = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        files = [p / k for k in KNOWN if (p / k).exists()] if p.is_dir() else [p]
        for f in files:
            errs = check_file(f)
            for e in errs:
                print(f"{f}: {e}")
            print(f"{f}: {'OK' if not errs else f'{len(errs)} problem(s)'}")
            bad += bool(errs)
    sys.exit(1 if bad else 0)
