---
name: rt-photo-desk
description: Racing Times photo desk. Finds up to three credited photos for every story in editor_notes.json, looks at every image, and records an approved / rejected / needs_check decision with the credit in episodes/<date>/photos/photos.json. Use after Checkpoint 1.
---

# Photo desk: editor_notes.json → photos/

```bash
python show-3d/fetch_photos.py episodes/<date>/editor_notes.json episodes/<date>/photos --per-story 3 --all
```
**Always these flags** (producer's standard): up to 3 photos for **every** story, not just the lead. Each comes from a different source article (robots.txt respected), saved as `<story>_<n>`, with `n` in `photos.json` and every entry `needs_check`. Target: **at least 2 approved photos per story**. If a story ends up with fewer than 2, look for more on the team, series or FIA media pages for it.

## Decide, one by one
Make a contact sheet of all candidates and open it with the Read tool, then any image you're unsure of at full size. Then set `status` and a one-line `note`:
- **approved:** a real news photo that matches the story: the right event, series and team context. Cropping to a wide wall is fine.
- **rejected:** a logo, a promo graphic with text printed on it, a generic placeholder, the wrong story, or anything showing race footage frames.
- **needs_check:** you can't tell whether it shows the right person or event. **Never guess who a person is from their face.** Judge by the visible context (team kit, branding, event, caption). If that's not enough, it's needs_check and the user decides.

## Better sources
For the lead and any story with no approved photo, prefer images released for editorial use: team media and news pages, series and FIA media pages (listed in `newsroom/sources.yaml`). Images from outlets like The Race or Autosport are usually agency photos licensed to that outlet. Mark those `"rights": "outlet image - internal preview only"`. The user decides at Checkpoint 2 whether to publish.

## Every entry keeps
`story, file, article, image, credit, status, note, rights`. The credit appears on the wall ("PHOTO: …") and in the description.

```bash
python newsroom/contracts.py episodes/<date>/photos/photos.json
```
Photos are never committed to git (`.gitignore`).
