# TaskQuest Project Context

## Project
- **Name**: TaskQuest — pixel art RPG habit tracker
- **Repo**: mchauth/TaskQuest-HTML (GitHub Pages)
- **Main file**: index.html
- **Access token**: <YOUR_GITHUB_TOKEN>

---

## Sprite System

### Sheet dimensions
- 800×448px per sheet
- Frame size: 80×64px
- Layout: 10 cols × 7 rows = 70 frames total

### Hair file naming
- Formula: `fileNum = (hairStyle - 1) * 5 + hairNum`
- `hairNum` 1–5 = Dark / Auburn / Red / Blonde / Silver
- All hair sheets: `sprites/preview_assets/char/hair_m{N}.png`
- `skin.png` = skin-only sheet used as composite base

### Critical rule
**Frame-by-frame processing is mandatory** — never stamp frame 0 across all 70 frames or animation breaks.

---

## Male Hairstyles (hair_m1–30)

| Style | Files | Name | Status |
|-------|-------|------|--------|
| 1 | hair_m1–5 | Short | ✅ DONE, clean |
| 2 | hair_m6–10 | Long | ✅ DONE, clean |
| 3 | hair_m11–15 | Medium | ✅ DONE, clean |
| 4 | hair_m16–20 | Ponytail | ✅ DONE, clean |
| 5 | hair_m21–25 | Slicked Back | ✅ DONE — bang removal + 65% vertical compression + 1px right shift |
| 6 | hair_m26–30 | Man-Bun | ✅ DONE — bang removal + 65% vertical compression + bun knot at right |

### index.html STYLE_NAMES
```js
['Short', 'Long', 'Medium', 'Ponytail', 'Slicked', 'Man-Bun']
```

---

## Next Up
- Female hairstyles (after male styles 5–6 are approved)

---

## Key Workflow Rules

1. **Always update CONTEXT.md before every git push**
2. **Always show preview to user (via Dispatch) BEFORE pushing to GitHub**
3. Generate previews with Python/Pillow writing to `/sessions/<sandbox>/mnt/outputs/`
4. Clone fresh each session:
   ```bash
   cd /sessions/<sandbox>/tmp && git clone https://mchauth:TOKEN@github.com/mchauth/TaskQuest-HTML.git tq
   cd tq && git config user.email "mchauth@gmail.com" && git config user.name "Matt Hauth"
   ```

---

## Sprite Generation Technique

- **Source**: Manipulate existing sprite sheets frame-by-frame using Python/Pillow
- **Do NOT use PixelLab API** — quality issues at 80×64 (generates full characters, not just hair)
- **Vertical compression**: remap `y → min_y + int((y - min_y) * factor)` to flatten hair
- **Bang removal**: For each column x in the front half of hair's x-range, remove any hair pixel whose y > (min_y + hair_height * 0.5). This eliminates forward-hanging strands that make pulled-back styles look like short hair.
- **Palette mapping**: sample colors from hair_m1–5 and remap per color variant
- **Preview**: composite hair frame 0 over skin.png frame 0, scale 4×, grid of all styles/colors

### Slicked Back approach (hair_m21–25)
1. Start from short hair (hair_m1–5), process each of 70 frames independently
2. Remove front bang pixels (front half of x-range, y > midpoint threshold)
3. Compress vertically: `y → min_y + int((y - min_y) * 0.65)`
4. Shift all pixels 1px right to suggest swept direction

### Man-Bun approach (hair_m26–30)
1. Start from short hair (hair_m1–5), process each of 70 frames independently
2. Remove front bang pixels (same technique as slicked)
3. Compress vertically: `y → min_y + int((y - min_y) * 0.65)`
4. Add 5×4px oval bun knot at rightmost hair position: darker border, main color fill

---

## Known Issues / History

- **Bleedthrough fix** (zeroing pixels matching short hair base) makes crown look bald — avoid this approach
- **PixelLab inpaint at 80×64** generates full characters, not just hair — don't use
- **Stamping frame 0 across all frames** breaks animation — always process per-frame
- **Preserving front bangs** on pulled-back styles makes them look identical to short hair — always run bang removal before building slicked/bun styles
