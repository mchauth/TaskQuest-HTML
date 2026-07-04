# TaskQuest — Session Handoff

> **Purpose:** Compact context file for starting a new Dispatch session after context reset.  
> **Last updated:** 2026-06-18  
> **Repo:** https://github.com/mchauth/TaskQuest-HTML (GitHub Pages, auto-deploys on push to main)  
> **Live URL:** https://mchauth.github.io/TaskQuest-HTML/

---

## Project Overview

Single-file HTML/CSS/JS RPG habit/quest app. All code lives in `index.html`. Backend is Supabase (auth + Postgres). Pixel art sprites served as static files alongside the HTML.

**Core gameplay loop:** Create quests → complete them → earn XP/gold → upgrade home scene → customise character.

---

## Tech Stack

- **Frontend:** Vanilla JS + HTML5, no bundler — everything in `index.html`
- **Database:** Supabase (PostgreSQL + Auth). Key tables: `profiles`, `tasks`, `habits`, `avatar_items`
- **Sprites:** Gandalfhardcore FREE Platformer Asset Pack (800×448 sprite sheets, 80×64 per frame, 10 cols × 7 rows)
- **AI sprites:** PixelLab API (`api.pixellab.ai/v1`) — inpaint & pixflux endpoints
- **PixelLab API key:** `3bb7dcfa-b77f-4da7-bb9c-df390c610cf0`
- **GitHub PAT:** (set via `git remote set-url` — do not commit tokens here)
- **Deploy:** `git push origin main` from a fresh clone of the repo (SSH or HTTPS+PAT)

---

## Directory Structure

```
~/Projects/TaskQuest/
├── index.html                          ← ENTIRE app (HTML + CSS + JS)
├── HANDOFF.md                          ← this file
├── sprites/
│   ├── generate_stone_house.py         ← PixelLab generation script (run locally)
│   ├── CONTEXT.md                      ← older context doc
│   └── preview_assets/
│       ├── char/                       ← character layer sprites (see below)
│       ├── home/                       ← home scene structures & props
│       ├── bg/                         ← parallax bg layers (layer1-5.png)
│       ├── anim/                       ← fire animation frames (fire_f0-15.png)
│       ├── clothing/male/ & female/    ← loot drop clothing items
│       ├── chest.png                   ← 384×48, 8 frames, chest open anim
│       └── enemy_portal.png            ← 640×64, 10 frames, portal enemy
└── Downloads/
    ├── GandalfHardcore FREE Platformer Assets/  ← source art pack
    └── GandalfHardcore Character Asset Pack-2/  ← source character pack
```

---

## Character Layer System

**Sprite sheets:** 800×448px, frames are 80×64px (10 cols × 7 rows = 70 frames).

**Rendering order (DOM, bottom→top):** skin → boots → pants → shirt → sword → hair  
*(skin MUST be first/lowest or it covers clothing)*

**Layer file IDs used in JS:**
- Home scene: `hsSkin`, `hsBoots`, `hsPants`, `hsShirt`, `hsSword`, `hsHair`
- Quest scene: `qsSkin`, `qsBoots`, `qsPants`, `qsShirt`, `qsSword`, `qsHair`
- Profile avatar: `avSkin`, `avBoots`, `avPants`, `avShirt`, `avSword`, `avHair`
- Combat overlay: `coSkin`, `coBoots`, `coPants`, `coShirt`, `coSword`, `coHair`

**Default state:** No clothing shown unless a loot item is equipped. Skin-only by default.

---

## Hair System (KEY — lots of recent work here)

**File naming:** `hair_m{N}.png` and `hair_f{N}.png`  
**Formula:** `fileNum = (hairStyle - 1) * 5 + hairNum`

| Style# | Name     | Male files   | Female files |
|--------|----------|--------------|--------------|
| 1      | Short    | hair_m1–5    | hair_f1–5    |
| 2      | Long     | hair_m6–10   | (pending)    |
| 3      | Medium   | hair_m11–15  | (rough, low quality) |
| 4      | Ponytail | hair_m16–20  | (pending)    |
| 5      | Mohawk   | hair_m21–25  | (rough, low quality) |
| 6      | Bun      | hair_m26–30  | (rough, low quality) |

**Customization keys in `S.customization`:**
- `hairStyle` (1–6) — which style
- `hairNum` (1–5) — which color within that style
- Color labels: Dark / Auburn / Red / Blonde / Silver

**UI:** Profile screen has a "Style" chip row + "Color" thumbnail row. Chips update the thumbnails.

**⚠️ Outstanding issue:** Styles 2–6 are built on top of the original short hair (hair_m1) as a base, so the short hair bleeds through. A re-generation with a full-head mask (not just extension mask) is needed to give each style a truly distinct look. Styles 3 (Medium), 5 (Mohawk), 6 (Bun) are low-quality and user wants them replaced. Styles 1 (Short), 2 (Long), 4 (Ponytail) are acceptable but Long/Ponytail should be re-done with full-head inpaint.

---

## Home Scene (HOME_TIERS)

| Tier | Name              | Structure file                            |
|------|-------------------|-------------------------------------------|
| 0    | Wanderer's Camp   | `home_t0_tent.png`                        |
| 1    | Ranger's Outpost  | `home_t1_stone_house_v1.png` (PixelLab)  |
| 2    | Stone Cottage     | `home_t3_house.png`                       |
| 3    | Fortified Estate  | `home_t3_house.png`                       |

Ranger's Outpost was recently updated — old camp props removed, new stone house from PixelLab added.

---

## Animation Frame Map (sprite sheet rows)

| Row | Animation | Frames | FPS  | Notes |
|-----|-----------|--------|------|-------|
| 0   | Idle      | 5      | 6    |       |
| 1   | Walk      | 8      | 10   |       |
| 2   | Run       | 8      | 10   |       |
| 3   | (unused)  | 4      | —    |       |
| 4   | (unused)  | 4      | —    |       |
| 5   | Slash     | 6      | 10   | Combat attack |
| 6   | Sleep     | 10     | 1.2  | startCol:8 |

Combat: row 5 plays when active quests exist; row 6 (sleep) when idle.

---

## Class System

`S.customization.class` (default `'warrior'`) stores the player's chosen class.

**Class selector UI** in `renderCustomizeUI()` — three buttons (Warrior / Mage / Ranger), same toggle pattern as gender selector, no lock, changes immediately refresh inventory.

**LOOT_TABLE** items now carry three extra fields:
- `rarity` — `common | uncommon | rare | super_rare | legendary`
- `levelReq` — minimum level to see the item
- `classes` — array of eligible class strings (e.g. `['warrior']`)

`renderInventory()` filters by the active class; item cards show a colored left border by rarity tier:

| Rarity     | Color     |
|------------|-----------|
| common     | `#9d9d9d` |
| uncommon   | `#1eff00` |
| rare       | `#0070dd` |
| super_rare | `#a335ee` |
| legendary  | `#ff8000` |

---

## Loot / Inventory System

Clothing drops every 3rd completed quest (`S.profile.completed % 3 === 0`).  
Items stored in `S.profile.inventory` (array of item IDs) and `S.profile.equippedItems` (slot→itemId map).  
Slots: `shirt`, `pants`, `boots`.  
**Supabase columns:** `profiles.inventory` (JSONB), `profiles.equipped_items` (JSONB).

### LOOT_TABLE Schema

Defined in `index.html` as `var LOOT_TABLE = [...]` (~line 1964). Each entry:

```js
{ id: 'armor_chest_2',          // unique string key — used in inventory array & equippedItems map
  name: 'Studded Leather',       // display name in inventory UI
  gender: 'm',                   // 'm' or 'f' — only shown to matching gender
  slot: 'shirt',                 // 'shirt' | 'pants' | 'boots'
  file: 'sprites/preview_assets/char/armor_chest_2.png',  // path relative to project root
  level: 5 }                     // minimum player level for this item to appear in loot drops
```

`rollLoot()` filters by `gender === playerGender && level <= playerLevel`, then picks randomly from items not yet owned. No rarity or class filtering is currently implemented.

### How to Add a New Armor Tier to LOOT_TABLE

1. Generate the spritesheet and commit it to `sprites/preview_assets/char/armor_chest_N.png`
2. In `index.html` find the `// ── Male armor ────` block (~line 1979) and add an entry:
   ```js
   { id:'armor_chest_3', name:'Chainmail Hauberk', gender:'m', slot:'shirt',
     file:'sprites/preview_assets/char/armor_chest_3.png', level:10 },
   ```
3. If the armor has a female variant, add a matching entry in the `// ── Female ────` block with `gender:'f'`.
4. The item will start appearing in loot drops for players at or above the specified level. Existing players won't see it until they reach that level.

### Clothing Files

Standard clothing (non-armor) lives under `sprites/preview_assets/clothing/{male,female}/` with underscored filenames (`Blue_Shirt_v2.png`, etc.). Armor spritesheets go in `sprites/preview_assets/char/` alongside the base layers.

---

## Combat Overlay

- Portal enemy: `enemy_portal.png` — 640×64, 10 frames of 64×64, displayed at 2×
- Chest: `chest.png` — 384×48, 8 frames of 48×48 (frames 0–3 closed, 4–7 opening)
- Hero in combat: skin+hair+equipment layers, `transform: scale(2) scaleX(-1)`, `left:40px`
- VICTORY text (no loot): gold pulse glow CSS animation
- Chest open (loot): item name + sprite preview shown after chest anim

---

## Armor Sprite Pipeline

Armor sprites occupy the character's `shirt.png` slot. They use the same 800×448 spritesheet format — 80×64 px per frame, 10 cols × 7 rows = 70 frame slots, ~45 active (any frame whose `shirt.png` crop contains ≥1 opaque pixel).

**Frame addressing:** `fi = row*10 + col`; global pixel offset `gx = col*80`, `gy = row*64`.  
**Animation rows:** 0=Idle (5f), 1=Walk (8f), 2=Run (8f), 5=Slash (6f), 6=Sleep (10f, startCol=8).

---

### Step-by-Step Pipeline for a New Armor Tier

#### Step 1 — Build the leather base (zero-drift foundation)

For every armor tier, start by recoloring `shirt.png` pixel-for-pixel into the leather palette. Do **not** skip this step even if the new tier will cover most of the leather with plate — it guarantees frame-perfect tracking with no drift.

```python
from PIL import Image
import numpy as np

shirt = np.array(Image.open("sprites/preview_assets/char/shirt.png").convert('RGBA'))

# Shirt source colors → leather target colors (nearest Euclidean RGB)
MAPPING = [
    ((97, 75, 68),   (30, 20, 10, 255)),   # dark outline
    ((163,137,130),  (120, 75, 35, 255)),   # mid
    ((191,176,168),  (120, 75, 35, 255)),   # mid-light (maps same)
    ((229,218,209),  (175,120, 60, 255)),   # highlight
]

def nearest(px):
    r,g,b,a = px
    if a == 0: return (0,0,0,0)
    best = min(MAPPING, key=lambda m: (r-m[0][0])**2+(g-m[0][1])**2+(b-m[0][2])**2)
    return best[1]

out = np.zeros_like(shirt)
for y in range(shirt.shape[0]):
    for x in range(shirt.shape[1]):
        out[y,x] = nearest(tuple(shirt[y,x]))
Image.fromarray(out).save("sprites/preview_assets/char/leather_armor_N.png")
```

#### Step 2 — Hand-paint the plate overlay on frame 0

Create an 80×64 PNG on the Desktop (e.g. `~/Desktop/armor_chest_N_frame0.png`). Start from the leather frame 0 crop as the base. Paint iron-grey pixels using the palette below. Do **not** edit the spritesheet directly — keep the approved frame 0 as the source of truth.

**Plate zone reference (frame 0, local coords):**
- Pauldrons: y=33–36; right shoulder x≈34–37 (recedes, darker); left shoulder x≈43–46 (faces viewer, brighter)
- Chest plate top rim: y=37, full width x=34–46 (gradient dark-left → bright-right)
- Chest plate body: y=38–41, x=35–46 (right edge absent at y≥41 due to shirt mask)
- Chest plate bottom: y=42–43, x=36–41 (full shadow, no highlights)

**Pauldron corner softening:** On the bottom row of each pauldron (y=35), replace the outermost 1–2 `#1A1A1A` pixels with `#3A3A3A`. Without this the pauldron bottom looks square-cut.

**Art conventions at this scale (~13×15 usable body px):**
- 3/4 left-facing perspective — character's right side recedes (darker), left side faces viewer (brighter)
- Use 4 tones max per material; no bright `#E0E0E0` specular unless it's a single-pixel rim highlight
- Pauldrons at y=33–35, collar/transition at y=36, chest plate y=37–43

#### Step 3 — Approve frame 0 before propagating

Inspect the Desktop frame 0 PNG. Confirm:
- Zero leather/brown pixels (`R>80 and G<80 and B<40`) in the plate zone (y=33–47, x=30–50)
- All iron-grey pixels are from the 4-tone palette exactly (no stray off-tones)
- Pauldron corners softened as desired

#### Step 4 — Propagate across all frames

```python
from PIL import Image
import numpy as np

CHAR  = "sprites/preview_assets/char"
DESK  = "/Users/matthauth/Desktop"
FRAME_W, FRAME_H, COLS, ROWS = 80, 64, 10, 7

PLATE_COLORS = {(26,26,26,255),(58,58,58,255),(96,96,96,255),(140,140,140,255)}
O = (26,26,26,255)   # #1A1A1A  outline/deep
D = (58,58,58,255)   # #3A3A3A  dark shadow
S = (96,96,96,255)   # #606060  mid shadow
M = (140,140,140,255)# #8C8C8C  base highlight

leather = np.array(Image.open(f"{CHAR}/leather_armor_N.png").convert('RGBA'))
shirt   = np.array(Image.open(f"{CHAR}/shirt.png").convert('RGBA'))
frame0  = np.array(Image.open(f"{DESK}/armor_chest_N_frame0.png").convert('RGBA'))

# Extract iron-grey pixels from approved frame 0 only
plate = {(x,y): tuple(frame0[y,x])
         for y in range(FRAME_H) for x in range(FRAME_W)
         if tuple(frame0[y,x]) in PLATE_COLORS}

# Add any targeted fixes that can't be baked into the frame0 design
# (e.g. edge pixels that only exist in specific animation frames)
# plate[(45,38)] = O   # example

# Frame 0 shirt centroid (anchor for offset calculation)
f0_op = np.argwhere(shirt[:FRAME_H,:FRAME_W,3] > 0)
cx0, cy0 = float(np.mean(f0_op[:,1])), float(np.mean(f0_op[:,0]))

out = leather.copy()
for fi in range(COLS * ROWS):
    col, row = fi % COLS, fi // COLS
    gx, gy   = col * FRAME_W, row * FRAME_H
    fs = shirt[gy:gy+FRAME_H, gx:gx+FRAME_W]
    op = np.argwhere(fs[:,:,3] > 0)
    if len(op) == 0:
        continue
    # Per-frame centroid offset (rounds to nearest pixel)
    dx = round(float(np.mean(op[:,1])) - cx0)
    dy = round(float(np.mean(op[:,0])) - cy0)
    mask = set(zip(op[:,1].tolist(), op[:,0].tolist()))
    for (lx,ly), color in plate.items():
        nx, ny = lx+dx, ly+dy
        if (nx,ny) in mask:          # clamp: only paint within shirt mask
            out[gy+ny, gx+nx] = color

Image.fromarray(out).save(f"{CHAR}/armor_chest_N.png")
```

#### Step 5 — Post-pass: scan for brown drift escapes (REQUIRED)

Even with shirt-mask clamping, edge-adjacent plate pixels can blink between brown and iron across animation frames (the character's idle bob shifts pixels in and out by 1 px). Scan the full plate zone after propagation and overwrite any leather pixel that slipped through.

```python
# Run immediately after the propagation loop above, before saving
for fi in range(COLS * ROWS):
    col, row = fi % COLS, fi // COLS
    gx, gy = col * FRAME_W, row * FRAME_H
    fs = shirt[gy:gy+FRAME_H, gx:gx+FRAME_W]
    op = np.argwhere(fs[:,:,3] > 0)
    if len(op) == 0:
        continue
    mask = set(zip(op[:,1].tolist(), op[:,0].tolist()))
    for ly in range(33, 47):        # plate zone rows
        for lx in range(30, 50):    # plate zone cols — adjust per tier
            if (lx, ly) not in mask:
                continue
            r,g,b,a = out[gy+ly, gx+lx]
            if a > 0 and (r,g,b,a) not in PLATE_COLORS:
                out[gy+ly, gx+lx] = O  # seal with outline tone
```

After saving, re-inspect frame 0's plate zone to confirm zero brown pixels. If any remain, add them as explicit entries in `plate` dict (Step 4) and re-run.

---

### What NOT To Do

| Don't | Why |
|-------|-----|
| Use centroid-offset propagation **without** shirt-mask clamping | Plate pixels escape the body silhouette; single rows appear/disappear during idle animation bob |
| Skip the post-pass brown-pixel scan | Edge pixels still blink brown on certain animation frames even with mask clamping |
| Use PixelLab Bitforge for clothing | Regenerates the whole character pose — can't isolate edits to the clothing layer |
| Paint plate pixels directly onto the full spritesheet | Bypasses the propagation system; frame 0 design file is the source of truth |
| Commit a file that hardcodes a GitHub PAT | Push protection will block it; token goes in `git remote set-url` only |

---

### Color Palettes (Locked In)

**Leather base — shirt-to-leather mapping:**

| Shirt source RGB | Leather target RGB | Role |
|---|---|---|
| (97, 75, 68) | (30, 20, 10) | Dark outline |
| (163, 137, 130) | (120, 75, 35) | Mid tone |
| (191, 176, 168) | (120, 75, 35) | Mid-light (same as mid) |
| (229, 218, 209) | (175, 120, 60) | Highlight |

**Iron plate — 4-tone palette:**

| Hex | RGB | Role |
|---|---|---|
| `#1A1A1A` | (26, 26, 26) | Outline / deepest shadow |
| `#3A3A3A` | (58, 58, 58) | Dark shadow / softened corners |
| `#606060` | (96, 96, 96) | Mid shadow |
| `#8C8C8C` | (140, 140, 140) | Base / highlight face |

---

### Armor Tier Roadmap

| Tier | Shirt | Pants | Boots | Helmet | Level |
|------|-------|-------|-------|--------|-------|
| 1 | `leather_armor_1` ✅ | `leather_pants_1` ✅ | `leather_boots_1` ✅ | `leather_helmet_1` ✅ | 1 |
| 2 | `armor_chest_2` ✅ | `armor_pants_2` ✅ | `armor_boots_2` ✅ | `helmet_2` ✅ | 5 |
| 3 | `armor_chest_3` ✅ | `armor_pants_3` ✅ | `armor_boots_3` ✅ | `helmet_3` ✅ | 10 |
| 4 | `armor_chest_4` ✅ | `armor_pants_4` ✅ | `armor_boots_4` ✅ | `helmet_4` ✅ | 20 |
| 5 | `armor_chest_5` ✅ | `armor_pants_5` ✅ | `armor_boots_5` ✅ | `helmet_5` ✅ | 30 |
| 6 | `armor_chest_6` ✅ | `armor_pants_6` ✅ | `armor_boots_6` ✅ | `helmet_6` ✅ | 40 |

All tiers: 800×448 spritesheet, `sprites/preview_assets/char/`, indexed in LOOT_TABLE with `slot:'shirt'`.

### Rare Warrior Sets (Legendary Prestige Skins)

Not part of the tier progression — unlockable prestige skins. Generated pixel-by-pixel with PIL using palette-swap + centroid/head-top propagation. Level 25 req, `rarity:'legendary'`, `classes:['warrior']`.

| Set | Files | Color Identity | Signature |
|-----|-------|---------------|-----------|
| Crimson Sentinel | `helmet_rare1`, `shirt_rare1`, `pants_rare1` | Deep red + gold | Full-face gold visor, white star emblem, T-bar slot |
| Shadow Warden | `helmet_rare2`, `shirt_rare2`, `pants_rare2` | Near-black + teal | Full-face teal visor, 3-bar teal grate, teal diamond |
| Solar Paladin | `helmet_rare3`, `shirt_rare3`, `pants_rare3` | Rich gold + ivory | Full-face ivory visor, white sun emblem, T-bar slot |

**Design approach:** Palette-swap from `shirt.png`/`pants.png` mask + explicit helm pixel dicts. Generation script at `outputs/gen_rare_armor.py`. Accent pixels (emblem, visor) painted on frame 0 before propagation.

---

## Helmet Sprite Pipeline

Helmets occupy the `helmet` equipment slot, rendering above all other character layers (DOM order: skin → boots → pants → shirt → sword → hair → helmet). When a helmet is equipped, `getCharLayers()` returns `hair: null` so hair is hidden under the helmet. Hair is dynamically re-shown during sleep animation via `qsSetCharFrame()`.

### Head Pixel Reference (skin_m1.png frame 0)

| Row | x range | Description |
|-----|---------|-------------|
| y=21 | x=38–42 (5px) | Skull top (all outline `#13131C`) |
| y=22 | x=37–43 (7px) | Upper skull |
| y=23–24 | x=36–44 (9px) | Forehead |
| y=25 | x=36–44 (9px) | Brow / upper face |
| y=26 | x=36–44 (9px) | **Eyes** (dark pixels at x=37, 39–41) |
| y=27 | x=36–44 (9px) | Nose bridge |
| y=28–30 | x=36–44 → x=36–42 | Mouth, chin (narrows) |
| y=31 | x=37–42 (6px) | Neck |

### Helmet Zone Layout (frame 0 local coords)

- **Dome:** y=22–25 — covers skull and forehead. Max width x=35–44 (1px beyond head edge). Dome top no higher than y=22.
- **Brow ridge:** y=25 — darkened row separating dome from face zone.
- **Eye opening:** y=26–27 — open on left/face side (x=35–40), solid plate on right/back side (x=41–44). 3/4 asymmetric.
- **Face plate:** y=28–31 — solid plate with T-bar slot or grate. Breathing slit possible.
- **T-bar slot:** Vertical void 1px wide at x=38, runs y=28–30. Flares to 3px (x=37–39) at bottom row y=30 (keyhole shape).
- **T6 grate:** Void bars at x=37/39/41, solid plate at x=38/40 between bars, runs y=28–30.

### 3/4 Perspective Shading (character faces LEFT)

- **Viewer-left (x=35–38):** Highlight / brightest tones — the face side catches light.
- **Center (x=39–41):** Mid tones.
- **Viewer-right (x=42–44):** Shadow / darkest fill — the back side recedes.
- **Black outline (#000000):** On ALL exposed edges.
- **Face openings:** Only on x=35–40 (viewer-left). x=41–44 is always solid closed plate.
- **Interior depth:** Fill eye/face voids with near-black (#050505 or #0A0A0A).

### Propagation

Use `skin_m1.png` head bounding box (y<32) for per-frame tracking:
1. For each frame, find the **top-of-head y** (minimum opaque y in head zone) — NOT centroid.
2. Find **centroid x** of head pixels for horizontal positioning.
3. Compute `dy = frame_top_y - f0_top_y` and `dx = round(frame_cx - f0_cx)`.
4. Shift all helmet pixels by (dx, dy). Bounds-check before painting.
5. The 1px idle bob (top_y alternates 20↔21) is captured correctly by top-of-head tracking.

### Sleep Frames (68–69)

- **No helmet pixels** rendered in frames 68–69 (spritesheet is transparent there).
- **Hair visibility:** `qsSetCharFrame()` dynamically swaps the hair element's `backgroundImage` — loads the hair sprite URL when `qsAnim === 'sleep'` and helmet is equipped, sets to `'none'` otherwise. This runs every animation tick.
- Do NOT attempt to rotate the frame-0 helmet for prone — pixel rotation produces artifacts.

### Helmet Tier Status

| Tier | File | Level | Type |
|------|------|-------|------|
| 1 | `leather_helmet_1.png` | 1 | Leather skullcap (open face) |
| 2 | `helmet_2.png` | 5 | Iron kettle helm + nasal bar |
| 3 | `helmet_3.png` | 10 | Chainmail coif + side drapes + face plate |
| 4 | `helmet_4.png` | 20 | Silver sallet + T-bar visor |
| 5 | `helmet_5.png` | 30 | Gold barbute + T-bar + keyhole |
| 6 | `helmet_6.png` | 40 | Dark armet + grate + crown spike + red gem |

### Design Preview Workflow

1. Generate a bare head composite: `skin_m1.png` frame 0 on dark background, 20× zoom.
2. Design helmet pixels in a dict `{(x,y): (r,g,b,a)}`.
3. Composite helmet over bare head at 20× and save to Desktop for review.
4. Iterate on the design before propagation — propagation is fast but design review is what takes time.
5. After approval, propagate across all 45 frames and push.

---

## PixelLab Integration (Chrome extension approach)

Sandbox bash CANNOT reach `api.pixellab.ai` (proxy blocks it).  
**Working approach:** Use Claude-in-Chrome extension with a tab open on `https://api.pixellab.ai/v1/docs`.  
Make API calls via `fetch('/v1/...', ...)` from that tab (same-origin, no CORS).  
Retrieve image data as pipe-delimited 4-char groups (`str.match(/.{1,4}/g).join('|')`) to avoid base64 filter.  
Reassemble in Python: `''.join(c.replace('|','') for c in chunks)`.

**Inpaint for new hair styles:**
- Base image: skin-only frame (no hair), saved as PNG → base64
- Mask: RGB PNG, white where hair should be generated, black elsewhere
- Use `init_image_strength` NOT used (inpaint endpoint uses inpainting_image + mask_image)
- Extract new pixels: compare result vs skin-only frame; pixels that changed in mask area = new hair
- Build 800×448 sprite sheet by stamping those pixels at each frame's anchor position
- Color variants: map palette from short hair (hair_m1→hair_m2-5) and apply to new style

---

## Key JS Functions to Know

| Function | What it does |
|----------|-------------|
| `getCharLayers()` | Returns file paths for all 6 layers based on `S.customization` + equipped items |
| `refreshHomeLayers()` | Updates home scene layer background-images |
| `refreshSceneLayers()` | Updates quest scene layer background-images |
| `refreshAvatarPreview()` | Updates profile avatar (also rebuilds DOM if needed) |
| `renderInventory()` | Renders loot inventory grouped by slot, filtered by gender **and active class**; item cards show colored rarity border |
| `renderCustomizeUI()` | Renders gender/skin/hair style+color pickers + class selector (Warrior/Mage/Ranger) |
| `setCustom(key, val)` | Updates S.customization, saves, re-renders |
| `equipItem(itemId)` | Toggle-equips/unequips a loot item, saves to Supabase |
| `openCombatOverlay(xp, gold, loot)` | Shows combat screen after quest completion |
| `renderHomeScene()` | Full re-render of home scene (structure + props + layers) |

---

## What's Left / Next Steps

1. **Armor tiers 3–6 (`armor_chest_3.png` through `armor_chest_6.png`):** Design and generate the remaining chest armor progression (chainmail → plate, etc.) using the confirmed shirt-mask method (see Armor Sprite Pipeline above).
3. **Class-filtered loot content:** Currently only warrior items have rarity/class fields. Populate Mage and Ranger loot with correct `classes` values and matching sprites.
4. **Hair re-generation:** Re-do Long (style 2) and Ponytail (style 4) with full-head inpaint mask (not just extension) so short hair doesn't bleed through. Remove or redo styles 3/5/6.
5. **Female hairstyles:** All female styles (hair_f1–5) are currently just 5 color variants of one short style. Need the same style expansion as male.
6. **More PixelLab assets:** Trees, props, and other scene objects via Chrome API pipeline.

---

## Deployment

```bash
# From scratch each session:
cd /tmp && git clone https://mchauth:<GITHUB_PAT>@github.com/mchauth/TaskQuest-HTML.git tq_push
cd /tmp/tq_push
git config user.email "mchauth@gmail.com"
git config user.name "Matt Hauth"
# ... make changes, copy files ...
git add -A && git commit -m "message" && git push origin main
```

GitHub Pages deploys automatically ~1 min after push.
