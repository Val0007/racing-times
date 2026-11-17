"""Check a Racing Times script against catalog.json, and describe the catalog for prompts.

    python show-catalog/validate.py script.json         # errors -> exit 1
    python show-catalog/validate.py --strict script.json   # newsroom scripts: every sentence needs a kind
    python show-catalog/validate.py --describe          # markdown list of allowed shots + graphics

Renderers import normalize() so both shows fill the same defaults.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CATALOG = json.loads((Path(__file__).parent / "catalog.json").read_text())
GRAPHICS = CATALOG["graphics"]
SHOTS = CATALOG["shots"]
TEAMS = CATALOG["teams"]["codes"]
CAST = {k: v for k, v in CATALOG["cast"].items() if k != "about"}
KINDS = CATALOG["sentence"]["kind"]["enum"]
_ALIAS = {a: k for k, spec in GRAPHICS.items() for a in spec.get("aliases", [])}


def canonical_kind(kind: str) -> str:
    return _ALIAS.get(kind, kind)


def normalize(g: dict, episode: int = 1) -> dict:
    """Resolve aliases and fill catalog defaults. Renderers draw from the result."""
    g = {**g, "kind": canonical_kind(g.get("kind", ""))}
    k = g["kind"]
    if k == "logo":
        g.setdefault("sub", f"EPISODE {episode:02d}")
    elif k == "headlines":
        g.setdefault("title", "THIS WEEK")
    elif k == "p1":
        g.setdefault("pos", "P1")
    elif k == "results":
        g.setdefault("sub", f"TOP {len(g.get('rows', []))} - CLASSIFICATION")
    elif k == "nextup":
        g.setdefault("title", "NEXT RACE")
        g.setdefault("later", [])
    return g


def _check_text(s, maxlen, where, errs):
    if not isinstance(s, str) or not s.strip():
        errs.append(f"{where}: must be a non-empty string")
        return
    if len(s) > maxlen:
        errs.append(f"{where}: {len(s)} chars, max {maxlen}: {s!r}")
    if not s.isascii():
        errs.append(f"{where}: ASCII only (no accents or middle dots): {s!r}")
    if s != s.upper():
        errs.append(f"{where}: must be UPPERCASE: {s!r}")


def check_graphic(g, where: str) -> list[str]:
    errs: list[str] = []
    if not isinstance(g, dict) or "kind" not in g:
        return [f"{where}: needs a 'kind'"]
    kind = canonical_kind(g["kind"])
    spec = GRAPHICS.get(kind)
    if spec is None:
        return [f"{where}: unknown kind {g['kind']!r}; allowed: {', '.join(ready_graphics())}"]
    if spec["status"] != "ready":
        return [f"{where}: kind {kind!r} is planned but not built yet"]
    fields = spec["fields"]
    for extra in set(g) - set(fields) - {"kind"}:
        errs.append(f"{where}: unknown field {extra!r} for {kind}")
    for name, f in fields.items():
        at = f"{where}.{name}"
        if name not in g:
            if f.get("required"):
                errs.append(f"{at}: required")
            continue
        v = g[name]
        if f["type"] == "str":
            _check_text(v, f["max"], at, errs)
        elif f["type"] == "int":
            if not isinstance(v, int) or isinstance(v, bool) or not f.get("min", 0) <= v <= f.get("max", 10**6):
                errs.append(f"{at}: whole number {f.get('min', 0)}-{f.get('max', '')}")
        elif f["type"] == "id":
            if not isinstance(v, str) or not re.fullmatch(r"[a-z0-9_]{1,40}", v):
                errs.append(f"{at}: lowercase id like 'brazil_gp'")
        elif f["type"] == "team":
            if v not in TEAMS:
                errs.append(f"{at}: unknown team code {v!r}; use one of {', '.join(TEAMS)}")
        elif f["type"] == "list":
            if not isinstance(v, list) or not (f.get("min", 0) <= len(v) <= f["max_items"]):
                errs.append(f"{at}: list of {f.get('min', 0)}-{f['max_items']} items")
                continue
            for i, s in enumerate(v):
                _check_text(s, f["max"], f"{at}[{i}]", errs)
        elif f["type"] == "rows":
            cols = f["columns"]
            if not isinstance(v, list) or not (f.get("min", 1) <= len(v) <= f["max_items"]):
                errs.append(f"{at}: {f.get('min', 1)}-{f['max_items']} rows")
                continue
            for i, row in enumerate(v):
                if not isinstance(row, list) or len(row) != len(cols):
                    errs.append(f"{at}[{i}]: must be [{', '.join(c for c, _ in cols)}]")
                    continue
                for (cname, cmax), cell in zip(cols, row):
                    if cname == "team" and cell not in TEAMS:
                        errs.append(f"{at}[{i}].team: unknown team code {cell!r}")
                    else:
                        _check_text(cell, cmax, f"{at}[{i}].{cname}", errs)
    return errs


def _frac(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 1


def check_sentence(s, where: str, seg_speaker: str, strict: bool) -> list[str]:
    errs = []
    if isinstance(s, str):
        if not s.strip():
            errs.append(f"{where}: empty sentence")
        elif strict:
            errs.append(f"{where}: strict scripts need {{text, kind}} objects, not plain strings")
        return errs
    if not isinstance(s, dict) or not isinstance(s.get("text"), str) or not s["text"].strip():
        return [f"{where}: string or {{text, ...}} with non-empty text"]
    allowed = {k for k in CATALOG["sentence"] if k != "about"}
    for extra in set(s) - allowed:
        errs.append(f"{where}: unknown field {extra!r}")
    if "speaker" in s and s["speaker"] not in CAST:
        errs.append(f"{where}.speaker: {s['speaker']!r} is not in the cast ({', '.join(CAST)})")
    kind = s.get("kind")
    if kind is None:
        if strict:
            errs.append(f"{where}.kind: required ({', '.join(KINDS)})")
    elif kind not in KINDS:
        errs.append(f"{where}.kind: {kind!r} not one of {', '.join(KINDS)}")
    if "delivery" in s and s["delivery"] not in CATALOG["sentence"]["delivery"]["enum"]:
        errs.append(f"{where}.delivery: one of {', '.join(CATALOG['sentence']['delivery']['enum'])}")
    if kind == "anecdote" and not str(s.get("source", "")).startswith("http"):
        errs.append(f"{where}: anecdote needs a source URL (from the anecdote-finder)")
    return errs


SLOP = ["delve", "testament to", "in a stunning turn", "a rollercoaster", "buckle up", "it's worth noting", "needless to say",
        "in the world of", "navigate the", "a true masterclass", "showcasing", "game-changer", "game changer", "unprecedented",
        "tapestry", "embark", "a whirlwind", "nail-biting finish", "edge-of-your-seat", "only time will tell", "the stage is set",
        "without further ado", "let's dive in", "in conclusion"]


def check_style(script: dict) -> tuple[list[str], list[str]]:
    """House style (bible/tone.md): every line has a delivery, deliveries vary, no stock AI phrases."""
    errs, warns, seq = [], [], []
    for seg in script.get("segments", []):
        for i, s in enumerate(seg.get("sentences", [])):
            if not isinstance(s, dict):
                continue
            where = f"segments[{seg.get('id')}].sentences[{i}]"
            if "delivery" not in s:
                errs.append(f"{where}.delivery: required in newsroom scripts (bible/tone.md)")
            seq.append((where, s.get("delivery")))
            low = s.get("text", "").lower()
            for p in SLOP:
                if p in low:
                    errs.append(f"{where}: stock phrase '{p}' (bible/tone.md, Not AI slop): say it like a person")
            if len(s.get("text", "").split()) > 32:
                warns.append(f"{where}: {len(s['text'].split())} words; break it up, the show is fast-paced")
    for k in range(2, len(seq)):
        if seq[k][1] and seq[k][1] == seq[k - 1][1] == seq[k - 2][1]:
            errs.append(f"{seq[k][0]}: third '{seq[k][1]}' line in a row; vary the delivery")
    bangs = sum(1 for seg in script.get("segments", []) for s in seg.get("sentences", []) if isinstance(s, dict) and s.get("text", "").rstrip().endswith("!"))
    total = sum(len(seg.get("sentences", [])) for seg in script.get("segments", [])) or 1
    if bangs / total > 0.4:
        warns.append(f"{bangs}/{total} lines end with '!'; save them for real excitement")
    return errs, warns


def validate(script: dict, strict: bool = False) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    for key in ("show", "episode", "date_display", "presenter", "segments", "credits"):
        if key not in script:
            errs.append(f"script: missing {key!r}")
    for i, item in enumerate(script.get("desk_display") or []):
        k = item.get("kind") if isinstance(item, dict) else None
        if k not in CATALOG["desk_display"]["kinds"]:
            errs.append(f"desk_display[{i}].kind: title | live | next")
        elif k == "live" and not (isinstance(item.get("text"), str) and 0 < len(item["text"]) <= 28):
            errs.append(f"desk_display[{i}].text: 1-28 characters")
        elif k == "next" and not (isinstance(item.get("items"), list) and 1 <= len(item["items"]) <= 2
                                  and all(isinstance(x, str) and len(x) <= 40 for x in item["items"])):
            errs.append(f"desk_display[{i}].items: 1-2 headlines, max 40 characters each")
    if not script.get("credits"):
        errs.append("script.credits: required (every source must be credited)")
    seen = set()
    for n, seg in enumerate(script.get("segments", [])):
        sid = seg.get("id", f"#{n}")
        w = f"segments[{sid}]"
        if sid in seen:
            errs.append(f"{w}: duplicate id")
        seen.add(sid)
        for extra in set(seg) - set(CATALOG["segment"]):
            errs.append(f"{w}: unknown field {extra!r}")
        errs += check_graphic(seg.get("graphic"), f"{w}.graphic")
        if "graphic_b" in seg:
            errs += check_graphic(seg["graphic_b"], f"{w}.graphic_b")
            if not _frac(seg.get("graphic_b_at")) or seg.get("graphic_b_at") == 0:
                errs.append(f"{w}.graphic_b_at: required with graphic_b, between 0 and 1")
        shots = seg.get("shots")
        if not isinstance(shots, list) or not shots:
            errs.append(f"{w}.shots: required, e.g. [[0, \"wide\"]]")
        else:
            prev = -1
            for i, s in enumerate(shots):
                if not (isinstance(s, list) and len(s) == 2 and _frac(s[0])):
                    errs.append(f"{w}.shots[{i}]: must be [fraction 0-1, shot]")
                    continue
                if i == 0 and s[0] != 0:
                    errs.append(f"{w}.shots[0]: must start at 0")
                if s[0] <= prev:
                    errs.append(f"{w}.shots[{i}]: fractions must increase")
                prev = s[0]
                spec = SHOTS.get(s[1])
                if spec is None or spec["status"] != "ready":
                    errs.append(f"{w}.shots[{i}]: shot {s[1]!r} not available; use {', '.join(ready_shots())}")
            # readability hint: a results table that never goes full screen
            for gk, start in (("graphic", 0), ("graphic_b", seg.get("graphic_b_at", 1))):
                g = seg.get(gk) or {}
                if canonical_kind(g.get("kind", "")) == "results":
                    if not any(sh == "full" and f >= start - 1e-9 for f, sh in shots if isinstance(f, (int, float))) and \
                       not any(sh == "full" for f, sh in shots if isinstance(f, (int, float)) and f <= start):
                        warns.append(f"{w}: results table is never shown on a 'full' shot")
        lt = seg.get("lower_third")
        if lt is not None:
            mx = CATALOG["segment"]["lower_third"]["max"]
            if not isinstance(lt, dict):
                errs.append(f"{w}.lower_third: must be {{title, sub}}")
            else:
                _check_text(lt.get("title"), mx["title"], f"{w}.lower_third.title", errs)
                _check_text(lt.get("sub"), mx["sub"], f"{w}.lower_third.sub", errs)
        if "lower_third_at" in seg and not _frac(seg["lower_third_at"]):
            errs.append(f"{w}.lower_third_at: between 0 and 1")
        if "point" in seg and not isinstance(seg["point"], bool):
            errs.append(f"{w}.point: true or false")
        spk = seg.get("speaker", "pixie")
        if spk not in CAST:
            errs.append(f"{w}.speaker: {spk!r} is not in the cast ({', '.join(CAST)})")
        sents = seg.get("sentences")
        if not isinstance(sents, list) or not sents:
            errs.append(f"{w}.sentences: required")
        else:
            for i, s in enumerate(sents):
                errs += check_sentence(s, f"{w}.sentences[{i}]", spk, strict)
            if spk == "byte" and strict and not any(isinstance(s, dict) and s.get("kind") == "opinion" for s in sents):
                warns.append(f"{w}: Byte segment without an opinion line (bible/byte.md)")
    if strict:
        e2, w2 = check_style(script)
        errs += e2
        warns += w2
    return errs, warns


def ready_graphics() -> list[str]:
    return [k for k, v in GRAPHICS.items() if v["status"] == "ready"]


def ready_shots() -> list[str]:
    return [k for k, v in SHOTS.items() if v["status"] == "ready"]


def describe(include_planned: bool = False) -> str:
    """Markdown description of the catalog, for prompts and skills."""
    out = ["## Shots"]
    for k, v in SHOTS.items():
        if v["status"] == "ready" or include_planned:
            tag = "" if v["status"] == "ready" else " (PLANNED - do not use)"
            out.append(f"- `{k}`{tag}: {v['desc']} Use for: {v['use']}")
    out += ["", "## Graphics", f"Text rule: {CATALOG['text_rules']['graphic_text']}"]
    for k, v in GRAPHICS.items():
        if v["status"] != "ready" and not include_planned:
            continue
        tag = "" if v["status"] == "ready" else " (PLANNED - do not use)"
        out.append(f"\n### `{k}`{tag}\n{v['desc']} Use for: {v['use']}")
        for name, f in v["fields"].items():
            bits = [f["type"]]
            if "max_items" in f:
                bits.append(f"{f.get('min', 0)}-{f['max_items']} items")
            if "max" in f:
                bits.append(f"max {f['max']} chars")
            if "columns" in f:
                bits.append("columns " + ", ".join(f"{c}<={m}" for c, m in f["columns"]))
            bits.append("required" if f.get("required") else f"optional{', default ' + f['default'] if 'default' in f else ''}")
            note = f" - {f['note']}" if "note" in f else ""
            out.append(f"- `{name}`: {'; '.join(bits)}{note}")
        if "example" in v:
            out.append(f"- example: `{json.dumps(v['example'])}`")
    out += ["", "## Team codes", ", ".join(f"{c} ({t['name']})" for c, t in TEAMS.items())]
    out += ["", "## Cast"]
    for k, v in CAST.items():
        out.append(f"- `{k}`: {v['role']}, on the {v['set']} set. Personality: {v['bible']}")
    out += ["", "## Sentence fields"]
    for k, v in CATALOG["sentence"].items():
        if k != "about":
            req = " (required in newsroom scripts)" if v["required"] == "strict" else " (required)" if v["required"] else ""
            out.append(f"- `{k}`{req}: {v['desc']}")
    out += ["", "## Segment fields"]
    for k, v in CATALOG["segment"].items():
        out.append(f"- `{k}`{' (required)' if v['required'] else ''}: {v['desc']}")
    return "\n".join(out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--describe"]:
        print(describe(include_planned="--all" in sys.argv))
        sys.exit(0)
    bad = 0
    strict = "--strict" in sys.argv
    for path in [a for a in sys.argv[1:] if not a.startswith("--")]:
        errs, warns = validate(json.loads(Path(path).read_text()), strict=strict)
        for w in warns:
            print(f"{path}: warning: {w}")
        for e in errs:
            print(f"{path}: error: {e}")
        import runtime
        est = runtime.estimate(json.loads(Path(path).read_text()))
        if est["total"] > runtime.TARGET_S:
            print(f"{path}: warning: estimated {runtime.fmt(est['total'])}, over the {runtime.fmt(runtime.TARGET_S)} target (hard limit {runtime.fmt(runtime.LIMIT_S)})")
        print(f"{path}: {'OK' if not errs else f'{len(errs)} error(s)'} - estimated length {runtime.fmt(est['total'])}")
        bad += bool(errs)
    sys.exit(1 if bad else 0)
