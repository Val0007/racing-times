"""Write out/description.md for an episode: the running order and every source and photo credit,
linked. Required for publishing (CLAUDE.md: always credit and link originals).

    python newsroom/credits.py episodes/<date>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(folder: Path) -> Path:
    notes = json.loads((folder / "editor_notes.json").read_text())
    photos_file = folder / "photos" / "photos.json"
    photos = {(p["story"], p.get("n", 1)): p for p in json.loads(photos_file.read_text())} if photos_file.exists() else {}
    script = json.loads((folder / "script.json").read_text()) if (folder / "script.json").exists() else {}
    used_photos = {(g.get("story"), g.get("n", 1)) for seg in script.get("segments", []) for g in (seg.get("graphic"), seg.get("graphic_b"))
                   if g and g.get("kind") == "photo"}
    anecdotes = json.loads((folder / "anecdotes.json").read_text()) if (folder / "anecdotes.json").exists() else []
    used_anec = {x.get("source") for seg in script.get("segments", []) for x in seg.get("sentences", []) if isinstance(x, dict)}

    lines = [f"# Racing Times, Episode {notes['episode']} ({notes['date_display'].title()})", "",
             f"Presented by Pixie, live from {notes.get('city', 'Stockholm')}, with Byte on the grid. "
             "Every story is a short summary of the reporting linked below. The full articles, photos and quotes belong to their publishers.", "",
             "## In this episode"]
    for s in sorted(notes["stories"], key=lambda s: s["rank"]):
        lines.append(f"- **{s['headline']}** ({s['series']})")
    lines += ["", "## Sources"]
    for s in sorted(notes["stories"], key=lambda s: s["rank"]):
        lines.append(f"**{s['headline']}**")
        for src in s["sources"]:
            lines.append(f"- {src['name']}: [{src.get('title', src['name'])}]({src['url']})")
    if notes.get("briefs"):
        lines.append("**In brief**")
        for b in notes["briefs"]:
            lines.append(f"- {b['source']['name']}: [{b['text'][:70]}…]({b['source']['url']})")
    hist = [a for a in anecdotes if a["source_url"] in used_anec]
    if hist:
        lines += ["", "## History corner (Byte's facts)"]
        for a in hist:
            lines.append(f"- {a['claim']} ([{a.get('source_name', 'source')}]({a['source_url']}))")
    shown = [p for k, p in photos.items() if k in used_photos and p.get("status") == "approved"]
    if shown:
        lines += ["", "## Photos"]
        for p in shown:
            lines.append(f"- {p['story']} ({p.get('n', 1)}): photo {p['credit']}, from [{p['article']}]({p['article']})")
    lines += ["", "Racing Times is an independent digest. No race footage is used. Pixie and Byte are original characters."]
    out = folder / "out" / "description.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    return out


if __name__ == "__main__":
    print(f"wrote {main(Path(sys.argv[1]))}")
