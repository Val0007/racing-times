# Racing Times

A weekly motorsport news show, made by an agentic newsroom. Every week it collects news from F1, F2, F3, Formula E, IndyCar and the teams' own sites, picks and fact-checks the stories, writes a script, and renders a **ten-minute 3D show**. Pixie presents from the Stockholm studio; Byte reports from the starting grid and has an opinion on every fact.

**Watch:** https://val0007.github.io/racing-times/

> Principle: **models read, choose and write JSON; plain code renders.** No model makes per-frame decisions. Every stage hands the next one a file, and a script checks that file before anyone uses it.

```
racing-times/
├── docs/       the public site (GitHub Pages serves only this folder)
├── pipeline/   the newsroom + renderer that makes each episode (not deployed)
└── sync_pipeline.sh   copies the working project into pipeline/
```

---

## The pipeline at a glance

```
 RSS + news pages ──► Collect ──► Journalist ──► Editor ──► ✋ 1 story list
                                                               │
              ┌────────────────────────────────────────────────┘
              ▼
         Photo desk ─┐
                     ├──► Writer ──► Director ──► ✋ 2 the look ──► Fact-check ──► Produce ──► ✋ 3 final cut
   Anecdote finders ─┘
```

Each run lives in one folder, `episodes/<monday-date>/`. It runs in **Claude Code** as the `/rt-weekly` skill, which calls the stage skills and agents in order and stops at three human checkpoints. `python newsroom/episode.py status <date>` shows what's done and what's next.

| # | Stage | Who does it | Reads | Writes |
|---|---|---|---|---|
| 1 | **Collect** | `newsroom/collect.py` (RSS, robots.txt-aware); news pages via `article-reader` agents | `newsroom/sources.yaml` | `articles.jsonl` |
| 2 | **Journalist** | skill `rt-journalist` + `article-reader` agents (Haiku, in parallel) | `articles.jsonl` | `wire.json`: stories grouped and ranked by "heat" |
| 3 | **Editor** | skill `rt-editor` + the show's memory `data/storylines.json` | `wire.json` | `editor_notes.json`: 6–8 stories, the lead, who presents what, facts allowed |
| ✋ | **Checkpoint 1** | the producer approves the story list | | `approvals.json` |
| 4 | **Photo desk** | skill `rt-photo-desk` + `show-3d/fetch_photos.py` | editor notes | `photos/photos.json`: up to 3 credited photos per story, each approved / rejected / needs_check |
| 5 | **Writer** | skill `rt-writer` + `anecdote-finder` agents (Haiku, in parallel) | notes, photos, `bible/` | `anecdotes.json` (every number quoted from its source), `script.json` |
| 6 | **Director** | skill `rt-director` | script, catalog | shots, wall graphics, lower thirds; preview timeline + review stills |
| ✋ | **Checkpoint 2** | the producer approves the look | | |
| 7 | **Fact-check** | agent `fact-checker` (Sonnet, read-only, independent) | script + every source URL | `factcheck.json`, tied to the script's hash: any later edit voids it |
| 8 | **Produce** | skill `rt-produce` (code only) | approved script | voices, lip sync, 3D render, score, mix → `out/episode.mp4`, `out/description.md` |
| ✋ | **Checkpoint 3** | the producer approves the final cut and publishes it | | |

Approvals only come from the producer's own words. The pipeline never uploads or publishes anything itself.

### What checks what
- **`newsroom/contracts.py`**: a schema and rules check for every stage file. Examples: exactly one lead; sensitive stories never go to Byte; anecdotes carry evidence; every photo file exists; at least 2 photo cards per story and one per 25 s; the fact-check matches the current script.
- **`.claude/hooks/check_on_save.py`**: a Claude Code hook that runs those checks the moment any stage file is written.
- **`show-catalog/validate.py --strict`**: the script may only use shots and graphics from `catalog.json`. Every line needs a `kind` and a `delivery`; banned "AI slop" phrases are rejected.
- **`show-catalog/runtime.py`**: the 10:00 hard limit (the writer aims for 9:30) and a fixed cut order: briefs → banter → Pixie's opinions → Byte's extras → lowest-ranked stories.

---

## The pieces

### Skills and agents (`pipeline/.claude/`)
| | Name | Job |
|---|---|---|
| skill | `rt-weekly` | Orchestrator: runs the stages in order, stops at the checkpoints |
| skill | `rt-journalist` | Collects, reads and groups articles; ranks stories by heat |
| skill | `rt-editor` | Picks and orders stories, sets angles, assigns Pixie/Byte, keeps storyline memory |
| skill | `rt-photo-desk` | Fetches and judges photos; records credits and rights |
| skill | `rt-writer` | Writes the script in house style within the catalog and the time limit |
| skill | `rt-director` | Shots, cuts, wall cards, lower thirds, desk display, review stills |
| skill | `rt-produce` | Voice → lip sync → render → score → mix → description |
| agent | `article-reader` (Haiku) | Summarises a batch of articles into factual JSON |
| agent | `anecdote-finder` (Haiku) | Finds a sourced historical comparison for one fact, quoting the page for every number |
| agent | `fact-checker` (Sonnet) | Checks every fact and anecdote line against its source; read-only |

### Code
| Folder | What's in it |
|---|---|
| `newsroom/` | `collect.py` (RSS + pages → SQLite), `contracts.py`, `episode.py` (status + approvals), `preview_timeline.py` (voice-free timing), `credits.py` (the description), `llm.py`, `sources.yaml` |
| `show-catalog/` | `catalog.json`: the only menu of shots, graphics, cast and line kinds; `validate.py`; `runtime.py` |
| `bible/` | `pixie.md`, `byte.md`, `tone.md`: personalities, house style, banned phrases |
| `show-pixel/` | `audio.py`: voices per speaker (ElevenLabs v3 by default, Kokoro as a free fallback), Rhubarb lip sync, `timeline.json`; `eleven.py`: voice design + takes; the original pixel-art renderer and an API-only route (`script_writer.py`, `make_episode.py`) |
| `show-3d/` | the three.js show: `show/show.js` (timeline → frames), `sets.js` (studio + grid), `characters.js` (Pixie, Byte), `wallcards.js`; `capture.py` (headless Chromium → frames → ffmpeg), `fetch_photos.py`, `score.py`, `serve.py`, `contact_sheet.py` |
| `episodes/2026-11-16/` | Episode 1's editor notes, anecdotes, script and fact-check: the reference episode the writer imitates |

### The script format
A script is a list of segments: `{id, speaker, graphic, graphic_b, shots: [[fraction, "wide"|"close"|"full"]], lower_third, sentences}`. Each sentence is `{text, kind: fact|opinion|anecdote|link, delivery, say?, source?}`. The renderer takes **timing** from the timeline (sentence times and mouth cues from the recorded audio) and **content** from the script, matched by segment id. A new week's news never needs new rendering code, only a new script.

---

## Running it

```bash
cd pipeline
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m playwright install chromium
cd show-3d && npm install && cd ..
```
You also need **ffmpeg**, the **Rhubarb** lip-sync binary for your OS (see `show-pixel/README.md`), and for the default voices an **ElevenLabs** key in `pipeline/.env` (`ELEVENLABS_API_KEY=...`, never committed). Without a key, `RT_VOICE=kokoro` uses the free local Kokoro model.

Then open `pipeline/` in [Claude Code](https://claude.com/claude-code) and run:
```
/rt-weekly
```
Or step by step:
```bash
python newsroom/episode.py new 2026-11-23
python newsroom/episode.py status 2026-11-23
python3 show-3d/serve.py      # preview: http://127.0.0.1:8765/show-3d/show/index.html?episode=/episodes/<date>&timeline=build/preview_timeline.json
```
A 6-minute episode takes about 90 minutes to render on a laptop GPU.

## Adding an episode to the site
1. Copy `out/episode.mp4` to `docs/videos/` (each file under 100 MB) and a poster frame to `docs/assets/img/`.
2. Copy `out/description.md` to `docs/content/episodes/`.
3. Add an entry at the **top** of `docs/content/episodes.md`:
   ```markdown
   ## Episode 2 · 23 Nov 2026
   One-line teaser.

   Video: videos/ep02-2026-11-23.mp4
   Poster: assets/img/ep02-poster.jpg
   Notes: content/episodes/ep02-2026-11-23.md
   Runtime: 9:40
   ```
4. `./sync_pipeline.sh` to refresh `pipeline/`, then commit and push. GitHub Pages serves `docs/`; there is no build step.

---

## Rules the newsroom keeps
- **Summaries, not reproduction.** Every story is in the show's own words; any quote is under 15 words, at most one per source; every source is credited and linked in the episode notes.
- **No invented quotes, no fake interviews, no real people's likenesses or cloned voices.** Pixie and Byte are original characters with voices designed from text descriptions.
- **No race footage.** Only graphics, the presenters and credited photos.
- **Facts only from collected sources.** Anything that can't be verified is held, not aired.
- **Respect robots.txt and rate limits** when collecting articles and photos.

Photos belong to their credited owners.
