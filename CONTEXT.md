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
| 5 | hair_m21–25 | Slicked Back | ✅ DONE — horizontal flip of hair pixels + 70% vertical compression |
| 6 | hair_m26–30 | Man-Bun | ✅ DONE — horizontal flip of hair pixels + 70% vertical compression + 5×4 oval bun knot |

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
- **Hair isolation**: diff each hair frame against skin.png frame — any non-transparent pixel that differs from skin by >15 RGB units is a hair pixel
- **Horizontal flip**: mirror hair pixels within their bounding box: `x_flip = min_x + max_x - x`. Front bangs land at the back of the head, giving a naturally swept-back silhouette without any explicit bang removal.
- **Palette mapping**: sample colors from hair_m1–5 and remap per color variant
- **Preview**: composite hair frame 0 over skin.png frame 0, scale 4×, grid of all styles/colors

### Slicked Back approach (hair_m21–25)
1. Start from short hair (hair_m1–5), process each of 70 frames independently
2. Isolate hair pixels (diff against skin.png — non-skin, non-transparent pixels)
3. Find bounding box (min_x, max_x, min_y, max_y) of hair pixels
4. Mirror horizontally within bounding box: place pixel at (x, y) → (min_x + max_x - x, y)
   — front bangs naturally appear at the back, giving a swept-back silhouette
5. Apply 70% vertical compression: `y_new = min_y + int((y - min_y) * 0.70)` to flatten profile

### Man-Bun approach (hair_m26–30)
1. Start from short hair (hair_m1–5), process each of 70 frames independently
2. Isolate hair pixels (diff against skin.png)
3. Find bounding box, mirror horizontally within it (same as slicked)
4. Apply 70% vertical compression
5. Add 5×4px oval bun knot just behind the rightmost flipped-hair cluster:
   - Border = darkest sampled hair color; fill = median hair color
   - Bun placed ~3px to the right of max_x of flipped hair, vertically centered on hair band

---

## Known Issues / History

- **Bang removal approach** (previous): explicitly removing front pixels works but leaves an unnatural cutoff. The horizontal flip approach is more organic — the bang-heavy front side mirrors to the back, naturally suggesting swept/pulled hair.
- **Bleedthrough fix** (zeroing pixels matching short hair base) makes crown look bald — avoid this approach
- **PixelLab inpaint at 80×64** generates full characters, not just hair — don't use
- **Stamping frame 0 across all frames** breaks animation — always process per-frame
- **Preserving front bangs** on pulled-back styles makes them look identical to short hair — horizontal flip solves this without explicit removal
