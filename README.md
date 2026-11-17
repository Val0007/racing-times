# Racing Times

A weekly motorsport news show made by an agentic newsroom: models read the week's F1, F2, F3, Formula E and IndyCar news, pick and fact-check the stories and write the script; plain code renders the 3D show. Pixie presents from the Stockholm studio, Byte reports from the grid.

Live: https://val0007.github.io/racing-times/

## Adding an episode
1. Put the video in `videos/` and a poster frame in `assets/img/`.
2. Put the episode description (Markdown) in `content/episodes/`.
3. Add an entry at the **top** of `content/episodes.md`:

```markdown
## Episode 2 · 23 Nov 2026
One-line teaser.

Video: videos/ep02-2026-11-23.mp4
Poster: assets/img/ep02-poster.jpg
Notes: content/episodes/ep02-2026-11-23.md
Runtime: 9:40
```

Commit and push; GitHub Pages updates. No build step.

Every story is a short summary of reporting linked in each episode's notes. Photos belong to their credited owners. No race footage is used; Pixie and Byte are original characters.
