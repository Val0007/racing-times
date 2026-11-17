# Racing Times

An agentic motorsport newsroom. Every week it collects news from F1, F2, F3, Formula E, IndyCar and the teams' own sites, picks and checks the stories, and makes a **ten-minute 3D show**. Pixie presents from the Stockholm studio; Byte reports from the starting grid. There is no newspaper product any more (removed 16 Nov 2026; it's in git history).

Principle: **models read, choose and write JSON; plain code renders.** No model makes per-frame decisions. Every stage hands the next one a file, and a script checks that file.

## The weekly run (`/rt-weekly`)
One folder per episode: `episodes/<monday-date>/`. `python newsroom/episode.py status <date>` shows what's done and what's next.

| # | Stage | Who | Writes |
|---|---|---|---|
| 1 | Collect | `newsroom/collect.py` (RSS; news pages via article-reader agents) | `articles.jsonl` |
| 2 | Journalist | skill `rt-journalist` + `article-reader` agents (Haiku, parallel) | `wire.json` |
| 3 | Editor | skill `rt-editor` (+ `data/storylines.json` memory) | `editor_notes.json` |
| ✋ | **Checkpoint 1**: you approve the story list | `episode.py approve <date> stories` | `approvals.json` |
| 4 | Photo desk | skill `rt-photo-desk` + `show-3d/fetch_photos.py` | `photos/photos.json` |
| 5 | Writer | skill `rt-writer` + `anecdote-finder` agents (Haiku, parallel) | `anecdotes.json`, `script.json` |
| 6 | Director | skill `rt-director`, preview timeline, stills | `script.json`, `stills/` |
| ✋ | **Checkpoint 2**: you approve the look | `episode.py approve <date> look` | |
| 7 | Fact-check | agent `fact-checker` (Sonnet, read-only, independent) | `factcheck.json` (tied to the script's hash) |
| 8 | Produce | skill `rt-produce` (code only) | `build/`, `out/episode.mp4`, `out/description.md` |
| ✋ | **Checkpoint 3**: you approve the final cut; you publish | `episode.py approve <date> final` | |

Approvals come only from the user's own words in chat. Never upload or publish anything.

## Layout
```
.claude/skills/    rt-weekly, rt-journalist, rt-editor, rt-writer, rt-director, rt-photo-desk, rt-produce
.claude/agents/    article-reader (Haiku), anecdote-finder (Haiku), fact-checker (Sonnet)
.claude/hooks/     check_on_save.py: checks any stage file in episodes/ the moment it's written (settings.json)
bible/             pixie.md, byte.md, tone.md: personalities and tone rules
show-catalog/      catalog.json (allowed shots, graphics, cast, line kinds), validate.py, runtime.py (10:00 limit)
newsroom/          collect.py, sources.yaml, contracts.py (checks every stage file), episode.py (status +
                   approvals), preview_timeline.py (timeline without voice), credits.py (description), llm.py (API route)
show-3d/           the show: show/show.js (timeline → frames), sets.js (studio + grid), characters.js (Pixie, Byte,
                   RT palette), wallcards.js (catalog cards); serve.py, capture.py, contact_sheet.py, score.py, fetch_photos.py
show-pixel/        audio.py (TTS per speaker, Rhubarb lip sync, timeline) used by both shows; the original pixel-art
                   renderer; script_writer.py + make_episode.py = API route (needs an API key)
episodes/<date>/   one folder per episode (photos, stills, build and out are git-ignored)
data/              racing_times.db (articles), storylines.json (show memory); git-ignored
pilots/            the two 82 s pilots (git-ignored)
```

## Script format
Segments with `id`, `speaker` (pixie | byte), `graphic` (+ `graphic_b`, `graphic_b_at`), `shots` `[[fraction, "wide"|"close"|"full"], ...]`, `point`, `lower_third`/`lower_third_at`, and `sentences`: `{text, kind, say?, speaker?, source?}`. Optional top-level `desk_display`. All allowed values live in `show-catalog/catalog.json`; `python show-catalog/validate.py --describe` prints them and `--strict` checks a newsroom script. Graphic kinds: logo, headlines, p1, results, champions, bigword (alias gen4), nextup, photo. Planned: quote, standings, driver, briefs, and the `two_shot` shot. Graphic text is UPPERCASE ASCII.

The renderer takes timing (sentences, mouth cues) from the timeline and content from the script, matched by segment id. Each line plays on its speaker's set (Pixie: studio, Byte: grid); `full` always frames the studio wall. Preview any episode: `python3 show-3d/serve.py` then `http://127.0.0.1:8765/show-3d/show/index.html?episode=/episodes/<date>&timeline=build/preview_timeline.json`.

## Characters (bible/)
- **Pixie**, she/her, presenter: funny, charismatic, gives an opinion now and then (at most one per story, clearly framed). Charcoal three-piece suit, red tie, headset.
- **Byte**, he/him, paddock reporter: bonkers, a superfan, an opinion on every fact, compares it with racing history. Racing Times merch bomber, press pass, RT cap with a little generic race car on top.
- Every line has `kind` fact | opinion | anecdote | link. Anecdotes and "first since…" stats need a `source` from the anecdote-finder (which quotes the page for every number). Sensitive stories (death, injury, illness) go to Pixie only, with no jokes.

## Producer's standards (17 Nov 2026): defaults, never per-episode settings
- **Writing:** fast, exciting, human. The reference is `episodes/2026-11-16/script.json`; the rules are in `bible/tone.md` (house style + banned "AI slop" phrases). `validate.py --strict` requires a `delivery` on every line, at most two of the same in a row, and no banned phrases.
- **Photos:** the photo desk always fetches up to 3 photos per story (`fetch_photos.py --per-story 3 --all`). Scripts use at least 2 photo cards per story that has them, and about one per 25 seconds overall (`contracts.py` checks this). Long stories are split so the wall changes every 10–15 s, and Byte's segments cut to photos too.
- **Voices:** ElevenLabs v3 by default (key in `.env`; voices designed with `show-pixel/eleven.py`, ids in `show-pixel/voices/voices.json`: Pixie "natural" design 1, Byte design 1). One take per run of a speaker's lines, steady stability and a fixed seed, so each voice stays consistent. Delivery becomes an inline v3 tag. Takes are cached in `data/tts_cache/`. `RT_VOICE=kokoro` is the free fallback.
- **Picture:** no depth-of-field blur in the studio; both eyes blink; brows, nods and head tilt follow each line's delivery; wall photos slowly zoom.

## Look (approved 16 Nov 2026)
Palette: ink #1b1a17, paper #f4efe4, one red #a3141b. No gold, no glow. Wordmark: the newspaper's blackletter masthead (UnifrakturMaguntia). Studio: curved full-width LED wall behind Pixie (story photo with headline and credit, or a catalog card on the right), a long black desk with a centre display cycling title / "Live from Stockholm" / next stories. Grid: Byte between the slot boxes, pit wall with RT boards, crowd blurred.

## Episode length
Hard limit 10:00 including intro and credits (`show-catalog/runtime.py`). The writer aims for 9:30 by estimate (170 wpm per speaker speed, plus pauses). If it's over, the cut order is: briefs, banter, Pixie's opinions, Byte's extras, the lowest-ranked stories. The cold open, headlines, lead facts, sign-off and credits are never cut. `rt-produce` checks the real recorded length. Kokoro measured 182 wpm; set `RT_WPM` if the voice changes.

## Setup and status
- `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m playwright install chromium`; `cd show-3d && npm install`.
- Not on this Mac yet: `show-pixel/vendor/` (Kokoro model, voices, Rhubarb **macOS** build, see show-pixel/README.md) and **ffmpeg**. Until then, everything up to Checkpoint 2 runs (preview timeline + stills); rt-produce can't.
- Byte's voice (`bm_lewis`) hasn't been heard yet.
- `episodes/_test-2026-11-16/` is the test fixture: editor notes, anecdotes, photos (decided), a strict 4:15 test script, stills, description.
- Next: schedule `/rt-weekly` (laptop scheduled task recommended) after one full run with voice.

## Public site
`site/` is its own git repo, **Val0007/racing-times** (GitHub Pages: https://val0007.github.io/racing-times/), git-ignored here. One page lists the episodes from `site/content/episodes.md` (newest first); videos live in `site/videos/` (keep each under 100 MB), notes are the episode's `out/description.md`. `site/README.md` has the steps. Add and push an episode only when the user asks in chat, after Checkpoint 3. It's linked from the Fun Stuff tab of the user's portfolio (Val0007/Portfolio-md).

## Rules (keep these)
- **Summaries, not reproduction.** Own words; any quote under 15 words, at most one per source; always credit and link originals. The video's credits roll and `out/description.md` are required.
- **No invented quotes or fake interviews with real people**, and no real people's likeness or cloned voices. Byte relays only real, attributed quotes from team press releases and series reports.
- **No race footage** (F1 enforces video rights). Use graphics, the presenters and credited photos only; prefer team, series and FIA media (released for editorial use). Outlet photos are internal preview only unless you clear them. Never identify a person in a photo from their face.
- Facts only from the collected sources; re-verify anything time-sensitive. Hold anything you can't verify (for example, Edition 1's Tsolov item, which was a headline only).
- Respect robots.txt and rate limits (`collect.py` and `fetch_photos.py` do both).
