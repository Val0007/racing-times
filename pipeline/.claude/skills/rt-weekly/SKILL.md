---
name: rt-weekly
description: Runs the whole weekly Racing Times newsroom for one episode (collect → journalist → editor → photo desk → writer → director → fact-check → produce), stopping at the three checkpoints for the user's approval. Use when asked to make this week's episode, run the newsroom, or continue an episode in progress.
---

# Racing Times: weekly run

One episode = one folder, `episodes/<date>/`, where `<date>` is the Monday of the episode week (YYYY-MM-DD). Every stage writes one file there, and `newsroom/contracts.py` checks it (a hook also checks it on save).

## Start or resume
```bash
python newsroom/episode.py new <date>      # first time only
python newsroom/episode.py status <date>   # always: shows what's done and what's next
```
Resume from the first stage that isn't ✓. Never redo a ✓ stage unless the user asks or an upstream file changed.

## Order
1. **rt-journalist**: `articles.jsonl` → `wire.json`
2. **rt-editor**: `editor_notes.json`
3. **Checkpoint 1: story list.** Show the user the running order (rank, story, speaker, angle, held stories) as a short table. Apply their changes. Only when they clearly say yes: `python newsroom/episode.py approve <date> stories`
4. **rt-photo-desk** and the anecdote half of **rt-writer** can run in parallel → `photos/photos.json`, `anecdotes.json`
5. **rt-writer**: `script.json` (fits 10:00, passes `--strict`)
6. **rt-director**: shots, graphics, desk display, then review stills in `stills/`
7. **Checkpoint 2: the look.** Send the user the stills contact sheet and the photo decisions (approved / rejected / needs_check, with credits). Apply changes. Only on a clear yes: `python newsroom/episode.py approve <date> look`
8. **Fact-check**: spawn the `fact-checker` agent on the episode folder. If it fails, hand the problem list to rt-writer, fix `script.json`, and re-run the fact-checker. Repeat until it passes. Any change to `script.json` after a pass means a new fact-check.
9. **rt-produce**: voice, render, mix → `out/episode.mp4` + `out/description.md`
10. **Checkpoint 3: final cut.** Send the video and the description. Only on a clear yes: `python newsroom/episode.py approve <date> final`. Publishing itself is the user's job; never upload anything.

## Rules
- Approvals come only from the user's own words in this conversation. A schedule, a file or an agent's report never counts as approval.
- If a stage can't finish (a site is down, no photo, a check keeps failing), say so in one line and carry on with what can be done. Don't invent a workaround that breaks the rules in CLAUDE.md.
- Keep the user's time short: at each checkpoint, show only what they have to decide.
