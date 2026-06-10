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
| 5 | hair_m21–25 | Mohawk | ✅ DONE — spike shape, kept from repo |
| 6 | hair_m26–30 | Man-Bun | ✅ DONE — hand-painted minimal man-bun, June 2026 |

### index.html STYLE_NAMES
```js
['Short', 'Long', 'Medium', 'Ponytail', 'Mohawk', 'Man-Bun']
```

---

## Next Up
- Female hairstyles

---

## Key Workflow Rules

1. **Always update CONTEXT.md before every git push**
2. **Always show preview to user (via Dispatch) BEFORE pushing to GitHub**
3. Generate previews with Python/Pillow writing to `/sessions/<sandbox>/mnt/outputs/`
4. Clone fresh each session (into a writable path like `/sessions/<sandbox>/repo/`):
   ```bash
   mkdir -p /sessions/<sandbox>/repo
   cd /sessions/<sandbox>/repo
   git clone https://mchauth:TOKEN@github.com/mchauth/TaskQuest-HTML.git tq
   cd tq && git config user.email "mchauth@gmail.com" && git config user.name "Matt Hauth"
   ```

---

## Sprite Generation Technique

- **Source**: Manipulate existing sprite sheets frame-by-frame using Python/Pillow
- **Do NOT use PixelLab API** — quality issues at 80×64 (generates full characters, not just hair)
- **Hair isolation**: diff each hair frame against skin.png frame — any non-transparent pixel that differs from skin by >15 RGB units is a hair pixel
- **Palette mapping**: sample colors from hair_m1–5 and remap per color variant
- **Preview**: composite hair frame 0 over skin.png frame 0, scale 4×, grid of all styles/colors

### Man-Bun approach (hair_m26–30) — hand-painted
The man-bun was hand-painted pixel-by-pixel using Python/Pillow. Key pixel map (frame 0, all frames identical):

**Palette:**
- MAIN    = (89, 59, 31)   — base hair brown
- MID     = (64, 45, 32)   — mid shadow
- DARK    = (44, 34, 29)   — dark shadow / diagonal lines
- DARKEST = (19, 19, 28)   — outline / seam / left edge

**Head hair (flat strip on top):**
- y=21: x=37–43 DARK (hairline), x=35 DARKEST (left edge)
- y=22: x=37–43 MAIN, x=35 DARK
- y=23: x=37–43 MAIN
- x=44 col at y=22–25: DARKEST (seam separating head from bun)

**Diagonal lines (upper-right to lower-left, showing pull):**
- Line 1: (21,42)→(22,41)→(23,40) DARKEST/DARK
- Line 2: (21,40)→(22,39)→(23,38) DARKEST/DARK
- Line 3: (24,42)→(25,41)→(26,40) DARK (lower pull continuation)

**Additional hair mass at pull point:**
- y=24: x=42–43 MAIN; y=25: x=43 DARK

**Small round bun (right side, x=44–48):**
- y=23: x=44–47 (top, 4px)
- y=24: x=44–48 (5px)
- y=25: x=44–48 (5px)
- y=26: x=45–47 (bottom, 3px)
- Bun diagonal shade: (23,47)→(24,46)→(25,45) DARK
- Right edge dark: (24,48),(25,48) DARK

**Constraints (do not violate):**
- Tip of hair no higher than y=23
- Bun starts at x=44–47
- All hair to the right of x=35; nothing above y=21

### Slicked Back approach (hair_m21–25)
1. Start from short hair (hair_m1–5), process each of 70 frames independently
2. Isolate hair pixels (diff against skin.png — non-skin, non-transparent pixels)
3. Find bounding box (min_x, max_x, min_y, max_y) of hair pixels
4. Mirror horizontally within bounding box: place pixel at (x, y) → (min_x + max_x - x, y)
5. Apply 70% vertical compression: `y_new = min_y + int((y - min_y) * 0.70)`

---

## Known Issues / History

- **Bang removal approach** (previous): explicitly removing front pixels works but leaves an unnatural cutoff. The horizontal flip approach is more organic.
- **Bleedthrough fix** (zeroing pixels matching short hair base) makes crown look bald — avoid
- **PixelLab inpaint at 80×64** generates full characters, not just hair — don't use
- **Stamping frame 0 across all frames** breaks animation — always process per-frame
- **Old /tmp/tq clone** owned by `nobody` — always clone into `/sessions/<sandbox>/repo/` instead
