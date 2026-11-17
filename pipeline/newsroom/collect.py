"""Stage 1: Collect. Finds new articles on every source and stores them in data/racing_times.db.

    python newsroom/collect.py collect                 # RSS feeds; news pages too if an API key is set
    python newsroom/collect.py pages > pages.json      # news-page sources that need link extraction
    python newsroom/collect.py add links.json          # fetch + store articles from a list of links
    python newsroom/collect.py dump --days 7 --out episodes/<date>/articles.jsonl [--since 2026-11-01]

RSS is parsed directly. News pages without a feed need someone to pick the article links out:
with RT_LLM=anthropic (and an API key) a small model does it here; otherwise the rt-journalist
skill hands each page to an article-reader agent and feeds the result back with `add`.
Respects robots.txt and waits a second between requests.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
import trafilatura
import yaml

ROOT = Path(__file__).resolve().parent.parent
UA = "RacingTimesBot/0.1 (weekly motorsport digest)"
DB = ROOT / "data" / "racing_times.db"
SOURCES = Path(__file__).resolve().parent / "sources.yaml"
_robots: dict[str, RobotFileParser] = {}


def db() -> sqlite3.Connection:
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS articles(
        url TEXT PRIMARY KEY, source TEXT, series TEXT, title TEXT, published TEXT,
        author TEXT, text TEXT, image TEXT, image_credit TEXT, fetched_at TEXT)""")
    return con


def allowed(url: str) -> bool:
    root = re.match(r"https?://[^/]+", url).group(0)
    if root not in _robots:
        rp = RobotFileParser(root + "/robots.txt")
        try:
            rp.read()
        except Exception:
            pass
        _robots[root] = rp
    try:
        return _robots[root].can_fetch(UA, url)
    except Exception:
        return True


def get(url: str) -> httpx.Response:
    time.sleep(1.0)  # be polite
    return httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)


def sources() -> list[dict]:
    return yaml.safe_load(SOURCES.read_text())["sources"]


# ── link discovery ──────────────────────────────────────────
def links_from_rss(src: dict) -> list[dict]:
    feed = feedparser.parse(src["url"], agent=UA)
    return [{"url": e.link, "title": e.get("title", "")} for e in feed.entries[:30]]


def links_from_page(src: dict) -> list[dict]:
    from llm import FAST_MODEL, ask_json  # only when an API is configured
    html = get(src["url"]).text
    anchors = re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, flags=re.S | re.I)
    cand = []
    for href, inner in anchors:
        text = re.sub(r"<[^>]+>|\s+", " ", inner).strip()
        if len(text) > 25:
            cand.append(f"{urljoin(src['url'], href)} | {text[:160]}")
    cand = list(dict.fromkeys(cand))[:250]
    out = ask_json(
        f"These links come from the news page of {src['name']} ({src['series']}).\n"
        "Return only links to individual news articles (not navigation, shop, video hubs, tickets).\n\n"
        + "\n".join(cand),
        {"type": "object", "properties": {"articles": {"type": "array", "items": {
            "type": "object", "properties": {"url": {"type": "string"}, "title": {"type": "string"}},
            "required": ["url", "title"]}}}, "required": ["articles"]},
        model=FAST_MODEL,
    )
    return out["articles"][:30]


# ── article fetch ───────────────────────────────────────────
def _meta(html: str, prop: str) -> str | None:
    m = re.search(rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]+)"', html, re.I) or \
        re.search(rf'<meta[^>]+content="([^"]+)"[^>]+(?:property|name)="{prop}"', html, re.I)
    return m.group(1) if m else None


def fetch_article(url: str) -> dict | None:
    if not allowed(url):
        return None
    r = get(url)
    if r.status_code != 200:
        return None
    html = r.text
    meta = trafilatura.extract_metadata(html)
    text = trafilatura.extract(html, include_comments=False) or ""
    return {
        "title": (meta.title if meta else None) or _meta(html, "og:title") or "",
        "published": (meta.date if meta else None) or _meta(html, "article:published_time"),
        "author": meta.author if meta else None,
        "text": text[:12000],
        "image": _meta(html, "og:image"),
        "image_credit": _meta(html, "og:site_name") or (meta.sitename if meta else None),
    }


def store(con, links: list[dict], src: dict) -> int:
    new = 0
    for link in links:
        if con.execute("SELECT 1 FROM articles WHERE url=?", (link["url"],)).fetchone():
            continue
        art = fetch_article(link["url"])
        if not art or len(art["text"]) < 300:
            continue
        con.execute("INSERT OR IGNORE INTO articles VALUES (?,?,?,?,?,?,?,?,?,?)", (
            link["url"], src["name"], src["series"], art["title"] or link.get("title", ""), art["published"],
            art["author"], art["text"], art["image"], art["image_credit"],
            datetime.now(timezone.utc).isoformat()))
        con.commit()
        new += 1
    return new


def collect(rss_only: bool) -> int:
    con, new = db(), 0
    for src in sources():
        if src["kind"] != "rss" and rss_only:
            continue
        try:
            links = links_from_rss(src) if src["kind"] == "rss" else links_from_page(src)
        except Exception as ex:
            print(f"  ! {src['name']}: {ex}", file=sys.stderr)
            continue
        n = store(con, links, src)
        new += n
        print(f"  ✓ {src['name']}: {n} new", file=sys.stderr)
    return new


def add(links_file: str) -> int:
    """links.json: [{url, title, source}], source = a name from sources.yaml."""
    by_name = {s["name"]: s for s in sources()}
    con, new = db(), 0
    for link in json.loads(Path(links_file).read_text()):
        src = by_name.get(link.get("source"), {"name": link.get("source", "?"), "series": link.get("series", "ALL")})
        new += store(con, [link], src)
    return new


def recent(days: float = 7) -> list[dict]:
    con = db()
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM articles WHERE datetime(fetched_at) >= datetime('now', ?) ORDER BY fetched_at DESC",
                       (f"-{days * 24:.0f} hours",)).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("--rss-only", action="store_true")
    sub.add_parser("pages")
    a = sub.add_parser("add"); a.add_argument("links")
    d = sub.add_parser("dump"); d.add_argument("--days", type=float, default=7); d.add_argument("--out", required=True)
    d.add_argument("--since", help="YYYY-MM-DD: keep articles published on or after this date (unknown dates are kept)")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if args.cmd == "collect":
        rss_only = args.rss_only or os.getenv("RT_LLM") != "anthropic"
        print(f"{collect(rss_only)} new articles" + (" (RSS only; run `pages` for the rest)" if rss_only else ""))
    elif args.cmd == "pages":
        print(json.dumps([s for s in sources() if s["kind"] != "rss"], indent=1))
    elif args.cmd == "add":
        print(f"{add(args.links)} new articles")
    elif args.cmd == "dump":
        rows = recent(args.days)
        if args.since:
            rows = [r for r in rows if not r["published"] or str(r["published"])[:10] >= args.since]
        with open(args.out, "w") as f:
            for r in rows:
                f.write(json.dumps({k: r[k] for k in ("url", "source", "series", "title", "published", "text", "image", "image_credit")},
                                   ensure_ascii=False) + "\n")
        print(f"{len(rows)} articles -> {args.out}")
