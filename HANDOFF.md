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

**LOOT_TABLE** in index.html maps item IDs → `{ id, name, gender, slot, file, level, rarity, levelReq, classes }`.  
Files live under `sprites/preview_assets/clothing/{male,female}/`.  
All filenames use underscores (spaces were renamed early in dev).

**Supabase columns:** `profiles.inventory` (JSONB), `profiles.equipped_items` (JSONB).

---

## Combat Overlay

- Portal enemy: `enemy_portal.png` — 640×64, 10 frames of 64×64, displayed at 2×
- Chest: `chest.png` — 384×48, 8 frames of 48×48 (frames 0–3 closed, 4–7 opening)
- Hero in combat: skin+hair+equipment layers, `transform: scale(2) scaleX(-1)`, `left:40px`
- VICTORY text (no loot): gold pulse glow CSS animation
- Chest open (loot): item name + sprite preview shown after chest anim

---

## Armor Sprite Pipeline

Armor sprites are layered on top of the character's `shirt.png` slot, sharing the same 800×448 spritesheet format (80×64 frames, 10×7 = 70 frames).

**What works (confirmed):**
- **Direct shirt-pixel recolor** — load `shirt.png`, apply Euclidean nearest-match color mapping to every opaque pixel, output the recolored sprite sheet. Zero drift, pixel-perfect tracking across all animation frames. This is the canonical approach for all armor tiers.
- **Leather palette mapping** (shirt RGB → leather RGB):
  - `(97,75,68)` → `(30,20,10)` outline
  - `(163,137,130)` → `(120,75,35)` mid
  - `(191,176,168)` → `(120,75,35)` mid
  - `(229,218,209)` → `(175,120,60)` highlight
- **Plate overlay via shirt-mask zones** — define plate regions relative to the shirt pixel mask per frame (e.g. top 2 rows of shirt pixels = pauldrons, center columns of mid rows = chest plate); paint iron-grey tones directly onto matching shirt pixel positions. 4-tone iron palette: `#1A1A1A / #3A3A3A / #606060 / #8C8C8C`.
- **Aseprite MCP** (`mcp__plugin_pixel-plugin_aseprite__*`) — available for hand-editing individual frame pixel fixes after generation.

**What does NOT work:**
- **Centroid-offset propagation** — shifts the entire armor shape by an average offset per frame; causes rows to drift in/out of position during idle animation (the character's up/down bob makes single pixel rows appear/disappear). Do not use.
- **PixelLab Bitforge for clothing** — regenerates the whole character in a new pose; cannot isolate edits to just the clothing layer.

**Palette / art conventions at 80×64 (~13×15 usable body px):**
- Use 4–5 tones; no bright specular (looks like a white line at this scale).
- 3/4 left-facing perspective; pauldrons at y=34–35, single leather gap at y=36, chest plate y=37–43.

**Armor tier status:**

| Tier | File                 | Status      | Notes |
|------|----------------------|-------------|-------|
| 1    | `leather_armor_1.png`| ✅ COMMITTED | Direct shirt recolor; full frame set; clean |
| 2    | `armor_chest_2.png`  | ✅ COMMITTED | Leather base + iron plate overlay via shirt-mask method |
| 3    | `armor_chest_3.png`  | ❌ Not created | — |
| 4    | `armor_chest_4.png`  | ❌ Not created | — |
| 5    | `armor_chest_5.png`  | ❌ Not created | — |
| 6    | `armor_chest_6.png`  | ❌ Not created | — |

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
# From scratch each session (PAT expires occasionally):
cd /tmp && git clone https://mchauth:<PAT>@github.com/mchauth/TaskQuest-HTML.git tq_push
cd /tmp/tq_push
git config user.email "mchauth@gmail.com"
git config user.name "Matt Hauth"
# ... make changes, copy files ...
git add -A && git commit -m "message" && git push origin main
```

GitHub Pages deploys automatically ~1 min after push.
