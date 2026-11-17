"""Where is this week's episode? One folder per episode, one file per stage.

    python newsroom/episode.py new 2026-11-23
    python newsroom/episode.py status 2026-11-23          # which stages are done, what's next
    python newsroom/episode.py approve 2026-11-23 stories # record a checkpoint approval (stories | look | final)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contracts import check_file  # noqa: E402

CHECKPOINTS = {"stories": "Checkpoint 1: story list", "look": "Checkpoint 2: stills and photos", "final": "Checkpoint 3: final cut"}

# (label, path in the episode folder, skill that makes it, checkpoint that must come before it)
STAGES = [
    ("Collect", "articles.jsonl", "rt-journalist (collect.py dump)", None),
    ("Journalist", "wire.json", "rt-journalist", None),
    ("Editor", "editor_notes.json", "rt-editor", None),
    ("Writer: anecdotes", "anecdotes.json", "rt-writer (anecdote-finder)", "stories"),
    ("Writer: script", "script.json", "rt-writer", "stories"),
    ("Photo desk", "photos/photos.json", "rt-photo-desk", "stories"),
    ("Director: stills", "stills", "rt-director", "stories"),
    ("Fact-check", "factcheck.json", "fact-checker agent", "look"),
    ("Produce: voice", "build/timeline.json", "rt-produce", "look"),
    ("Produce: video", "out/episode.mp4", "rt-produce", "look"),
]


def folder(date: str) -> Path:
    return ROOT / "episodes" / date


def approvals(date: str) -> dict:
    p = folder(date) / "approvals.json"
    return json.loads(p.read_text()) if p.exists() else {}


def status(date: str) -> list[dict]:
    f, ap, rows = folder(date), approvals(date), []
    for label, rel, who, gate in STAGES:
        p = f / rel
        done = p.exists() and (not p.is_dir() or any(p.iterdir()))
        problems = check_file(p) if done and p.suffix == ".json" else []
        if rel == "factcheck.json" and done and not problems and json.loads(p.read_text()).get("result") != "pass":
            problems = ["fact-check result is 'fail': fix the script and re-check"]
        rows.append({"stage": label, "file": rel, "by": who, "done": done, "ok": done and not problems,
                     "problems": problems, "blocked_by": gate if gate and gate not in ap else None})
    return rows


def main():
    cmd, date = sys.argv[1], sys.argv[2]
    f = folder(date)
    if cmd == "new":
        (f / "photos").mkdir(parents=True, exist_ok=True)
        print(f"created {f.relative_to(ROOT)}")
    elif cmd == "approve":
        cp = sys.argv[3]
        if cp not in CHECKPOINTS:
            sys.exit(f"checkpoint must be one of {', '.join(CHECKPOINTS)}")
        ap = approvals(date)
        ap[cp] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        (f / "approvals.json").write_text(json.dumps(ap, indent=1))
        print(f"recorded {CHECKPOINTS[cp]}")
    elif cmd == "status":
        nxt = None
        for r in status(date):
            mark = "✓" if r["ok"] else ("!" if r["done"] else "·")
            gate = f"  (waits for {CHECKPOINTS[r['blocked_by']]})" if r["blocked_by"] and not r["done"] else ""
            print(f" {mark} {r['stage']:<20} {r['file']:<22} {r['by']}{gate}")
            for p in r["problems"][:5]:
                print(f"     - {p}")
            if nxt is None and not r["ok"]:
                nxt = r
        ap = approvals(date)
        print("\n approvals: " + (", ".join(f"{CHECKPOINTS[k]} ({v[:10]})" for k, v in ap.items()) or "none yet"))
        if nxt:
            print(f" next: {nxt['stage']} -> {nxt['by']}" + (f" after {CHECKPOINTS[nxt['blocked_by']]}" if nxt["blocked_by"] else ""))
        elif "final" not in ap:
            print(f" next: {CHECKPOINTS['final']}")
        else:
            print(" episode approved for publishing")


if __name__ == "__main__":
    main()
