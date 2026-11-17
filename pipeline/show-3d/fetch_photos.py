"""Download a candidate photo (og:image) for each story marked photo:true in editor_notes.json.

    python show-3d/fetch_photos.py episodes/<date>/editor_notes.json episodes/<date>/photos [--per-story 3] [--all]

Writes <out>/<story id>.<ext> and <out>/photos.json with status "needs_check" for every photo:
the photo desk (rt-photo-desk) looks at each image and decides.
Respects robots.txt, one request per second. Stdlib only.

Rights: photos on independent outlets (The Race, Autosport...) are usually agency images
(Getty, Motorsport Images) licensed to that outlet. For published episodes prefer team,
series and FIA media pages, whose photos are released for editorial use; always show the credit.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

UA = "RacingTimesBot/0.1 (weekly motorsport digest)"
MAX_BYTES = 6_000_000
_robots: dict[str, RobotFileParser] = {}


def allowed(url: str) -> bool:
    root = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if root not in _robots:
        rp = RobotFileParser(root + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[root] = rp
    rp = _robots[root]
    return True if rp is None else rp.can_fetch(UA, url)


def get(url: str) -> bytes:
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(MAX_BYTES + 1)


def meta(html: str, prop: str) -> str | None:
    m = re.search(rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I) or \
        re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{prop}["\']', html, re.I)
    return m.group(1).replace("&amp;", "&") if m else None


def is_image(b: bytes) -> str | None:
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    return None


def main(notes_path: str, out_dir: str, per_story: int = 1, all_stories: bool = False) -> None:
    notes = json.loads(Path(notes_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stories = [(s["id"], s) for s in notes["stories"] if s.get("photo") or all_stories]
    results, seen_images = [], set()
    for sid, story in stories:
        got = 0
        for src in story.get("sources", []):
            if got >= per_story:
                break
            url = src["url"]
            try:
                if not allowed(url):
                    print(f"  robots.txt disallows {url}")
                    continue
                html = get(url).decode("utf-8", "replace")
                img = meta(html, "og:image")
                if not img:
                    continue
                img = urljoin(url, img)
                if img in seen_images or not allowed(img):
                    continue
                data = get(img)
                ext = is_image(data)
                if not ext or len(data) > MAX_BYTES:
                    continue
                got += 1
                seen_images.add(img)
                f = out / f"{sid}_{got}.{ext}"
                f.write_bytes(data)
                credit = meta(html, "og:site_name") or src["name"]
                results.append({"story": sid, "n": got, "file": f.name, "article": url, "image": img, "credit": credit,
                                "status": "needs_check", "note": "", "rights": ""})
                print(f"  {sid} #{got}: {f.name} ({len(data) // 1024} KB) from {src['name']}")
            except Exception as ex:
                print(f"  {sid}: {src['name']} failed: {ex}")
    (out / "photos.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    print(f"{len(results)}/{len(stories)} stories have a photo")


if __name__ == "__main__":
    # python show-3d/fetch_photos.py notes.json photos/ [--per-story 3] [--all]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    per = int(sys.argv[sys.argv.index("--per-story") + 1]) if "--per-story" in sys.argv else 1
    if "--per-story" in sys.argv:
        args.remove(str(per))
    main(args[0], args[1], per, "--all" in sys.argv)
