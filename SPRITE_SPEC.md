# TaskQuest SPRITE_SPEC.md — Authoritative Sprite Reference

> **Purpose:** Read this at the start of any sprite session. Every measurement here was
> extracted from the committed scripts and measured with PIL from the committed sprite
> sheets (2026-07). Do NOT re-derive these values — they are ground truth.
>
> Companion tooling: `scripts/sprite_shade.py` (shader), `scripts/sprite_qa.py` (QA),
> `scripts/sprite_pipeline.py` (shade → QA → auto-fix → re-QA loop),
> `scripts/rebuild_class_hats.py` (hat authoring), `scripts/propagate_rare_helmets.py`
> (frame propagation), `scripts/redesign_tiers_v3.py` (tier armor authoring).

---

## 1. Sprite sheet format

| Property | Value |
|---|---|
| Sheet size | **800 × 448** px, RGBA PNG |
| Grid | **10 columns × 7 rows** = 70 frame slots |
| Frame size | **80 × 64** px (`FRAME_W=80, FRAME_H=64`) |
| Frame index | `fi`: `col = fi % 10`, `row = fi // 10`; pixel origin `gx = col*80`, `gy = row*64` |
| Character zone | **x = 30..54** within each frame (`CHAR_X0=30, CHAR_X1=54`) |
| Active frames | 42 of 70 (rest fully transparent) |

Animation rows (from HANDOFF.md + PIL frame occupancy):

| Row | Anim | Active frames | Notes |
|---|---|---|---|
| 0 | Idle | 0–4 (5f) | 1px idle bob: head_top alternates (m: 21↔20) |
| 1 | Walk | 10–17 (8f) | |
| 2 | Run | 20–27 (8f) | head shifts left: cx=38 (m) / 39 (f) |
| 3 | Jump | 30–33 (4f) | head rises: head_top=17 (m) / 18 (f) |
| 4 | Cheer (both arms raised) | 40–43 (4f) | raised arms merge with head zone — see §2 warning |
| 5 | Slash | 50–55 (6f) | combat attack; head shifts x hard (cx 37→45 m) |
| 6 | Sleep | 60–66 (7f drawn) | startCol:8 in engine; frames (6,7)–(6,9) empty in skin; hats never drawn on (6,8),(6,9) |

Combat behavior: row 5 plays when active quests exist; row 6 when idle.

---

## 2. Head measurements (PIL-measured from skin_m1.png / skin_f1.png)

Measured with the skull-dome tracker (§5). **Canonical constants:**

| | Male | Female |
|---|---|---|
| head_top (frame 0, idle) | **21** | **22** |
| head_cx (frame 0) | **40** | **40** |
| skull width `HW` | **9** (constant, all frames) | **9** |
| Skull full-width row (frame 0) | y=23 | y=24 |
| Eye row | y=26 (pupils), eyebrows y≈21–22 | y=27 |
| Mouth row | y=27 (color 39,19,15) | y=28 |
| Face outline color | (19,19,28) — NOT pure black | same |
| BRIM_Y (hat brim row) | **21** | **22** |

**WARNING — row 4 (cheer) frames 40–43:** raw fullest-span measurement returns
w=13 (m) / w=14 (f) because both raised arms merge with the head blob. This is why all
hat scripts use the constant `HW = 9` instead of per-frame width (prevents arm-raise
flicker). Never trust per-frame width on row 4.

**WARNING — face outline is (19,19,28), not #000.** The sprite_qa pure-black check and
sprite_shade outline classifier (`R+G+B < 15`) do NOT match the face outline. Only armor
outlines are pure black.

### Per-frame table — MALE skin_m1.png (head_top / head_cx / width@fullest-row)

| fi | (row,col) | head_top | head_cx | w | fullest row |
|---|---|---|---|---|---|
| 0 | (0,0) | 21 | 40.0 | 9 | 23 |
| 1 | (0,1) | 21 | 40.0 | 9 | 23 |
| 2 | (0,2) | 20 | 40.0 | 9 | 22 |
| 3 | (0,3) | 20 | 40.0 | 9 | 22 |
| 4 | (0,4) | 20 | 40.0 | 9 | 22 |
| 10 | (1,0) | 21 | 40.0 | 9 | 23 |
| 11 | (1,1) | 21 | 40.0 | 9 | 23 |
| 12 | (1,2) | 20 | 40.0 | 9 | 22 |
| 13 | (1,3) | 20 | 40.0 | 9 | 22 |
| 14 | (1,4) | 21 | 40.0 | 9 | 23 |
| 15 | (1,5) | 21 | 40.0 | 9 | 23 |
| 16 | (1,6) | 20 | 40.0 | 9 | 22 |
| 17 | (1,7) | 20 | 40.0 | 9 | 22 |
| 20–27 | (2,0–7) | 20/21 bob | 38.0 | 9 | 22/23 |
| 30–33 | (3,0–3) | 17 | 38.0 | 9 | 19 |
| 40–43 | (4,0–3) | 19 | 39.0 | (13 raw — use 9) | 21 |
| 50 | (5,0) | 21 | 40.0 | 9 | 23 |
| 51 | (5,1) | 21 | 41.0 | 9 | 23 |
| 52 | (5,2) | 20 | 45.0 | 9 | 22 |
| 53 | (5,3) | 20 | 45.0 | 9 | 22 |
| 54 | (5,4) | 23 | 37.0 | 9 | 25 |
| 55 | (5,5) | 21 | 37.0 | 9 | 23 |
| 60 | (6,0) | 21 | 40.0 | 9 | 23 |
| 61 | (6,1) | 23 | 38.0 | 9 | 25 |
| 62 | (6,2) | 28 | 34.0 | 9 | 30 |
| 63 | (6,3) | 29 | 32.0 | 9 | 31 |
| 64 | (6,4) | 28 | 33.0 | 9 | 30 |
| 65 | (6,5) | 29 | 30.0 | 9 | 31 |
| 66 | (6,6) | 29 | 27.0 | 9 | 31 |

### Per-frame table — FEMALE skin_f1.png

| fi | (row,col) | head_top | head_cx | w | fullest row |
|---|---|---|---|---|---|
| 0 | (0,0) | 22 | 40.0 | 9 | 24 |
| 1 | (0,1) | 22 | 40.0 | 9 | 24 |
| 2 | (0,2) | 21 | 40.0 | 9 | 23 |
| 3 | (0,3) | 21 | 40.0 | 9 | 23 |
| 4 | (0,4) | 21 | 40.0 | 9 | 23 |
| 10 | (1,0) | 22 | 40.0 | 9 | 24 |
| 11 | (1,1) | 22 | 40.0 | 9 | 24 |
| 12 | (1,2) | 21 | 40.0 | 9 | 23 |
| 13 | (1,3) | 21 | 40.0 | 9 | 23 |
| 14 | (1,4) | 22 | 40.0 | 9 | 24 |
| 15 | (1,5) | 22 | 40.0 | 9 | 24 |
| 16 | (1,6) | 21 | 40.0 | 9 | 23 |
| 17 | (1,7) | 21 | 40.0 | 9 | 23 |
| 20–27 | (2,0–7) | 21/22 bob | 39.0 | 9 | 23/24 |
| 30–33 | (3,0–3) | 18 | 38.0 | 9 | 20 |
| 40–43 | (4,0–3) | 21 | 37.5 | (14 raw — use 9) | 27 |
| 50 | (5,0) | 22 | 40.0 | 9 | 24 |
| 51 | (5,1) | 22 | 42.0 | 9 | 24 |
| 52 | (5,2) | 21 | 46.0 | 9 | 23 |
| 53 | (5,3) | 21 | 46.0 | 9 | 23 |
| 54 | (5,4) | 23 | 38.0 | 9 | 25 |
| 55 | (5,5) | 22 | 38.0 | 9 | 24 |
| 60 | (6,0) | 22 | 40.0 | 9 | 24 |
| 61 | (6,1) | 24 | 39.0 | 9 | 26 |
| 62 | (6,2) | 30 | 35.0 | 7 | 31 |
| 63 | (6,3) | 31 | 34.0 | 5 | 31 |
| 64 | (6,4) | 30 | 35.0 | 7 | 31 |
| 65 | (6,5) | 31 | 32.0 | 5 | 31 |
| 66 | (6,6) | 31 | 29.0 | 5 | 31 |

Female sleep frames 62–66 measure narrower (5–7 px) because the head is partially
occluded lying down — another reason to keep `HW=9` fixed.

Female head sits exactly **1 px lower** than male in every non-jump frame; the run-row
cx differs (m 38 vs f 39), and slash-row extremes are 1 px wider for f (cx up to 46).

---

## 3. Layer system

7 character layers, composited by explicit inline z-index (`applyLegLayerOrder()` in
index.html), element id = prefix + part, prefixes `['qs','hs','co','av']` (quest scene,
home scene, customize, avatar):

| z | Layer | Notes |
|---|---|---|
| 1 | Skin | `skin_{g}{n}.png`, n = 1..5 |
| 2 | Pants | ...swaps to 3 when a skirt is equipped |
| 3 | Boots | ...swaps to 2 when a skirt is equipped |
| 4 | Shirt | |
| 5 | Sword | `sword_m.png` / `sword_f.png` |
| 6 | Hair | `hair_{g}{fileNum}.png`, `fileNum = (hairStyle-1)*5 + hairNum` |
| 7 | Helmet | topmost |

**Skirt swap:** items with `skirt:true` in LOOT_TABLE (e.g. `pants_mage1_f`,
`pants_ranger1_f`, `f_skirt`) render ABOVE boots (hem hangs over the shaft). Regular
trousers/leggings tuck UNDER boots. `isSkirtEquipped()` decides.

**Gender gating:** `getCharLayers()` never renders a cross-gender sprite — items with
`gender` set only render when it matches the current character gender.

**hatType:'partial' behavior** (all mage cones and ranger Robin Hood hats carry
`hatType:'partial'` in LOOT_TABLE):
- Full helmets (no hatType, i.e. warrior helmets & rares): hair layer set to `null` — hidden entirely.
- Partial hats: hair still renders, but if the hair fileNum is in `TALL_HAIR_NUMS[g]`
  a canvas-baked masked COPY of the hair sheet is used
  (`buildMaskedHairSheet`): for every frame key in `HAIR_MASK_FRAMES[g]`,
  `ctx.clearRect(col*80 + skullLeft, row*64, skullRight-skullLeft+1, headTop+2)`
  erases the skull zone rows `0..headTop+1`. Side strands / ponytails outside the skull
  columns survive. Fallback on canvas failure: hard `clip-path: inset(BRIM_Y px 0 0 0)`.
- `BRIM_Y = { m: 21, f: 22 }`.

**LOOT_TABLE item shape** (index.html ~line 1968):
```js
{ id:'shirt_mage4', name:'Arcane Vestments', slot:'shirt'|'pants'|'boots'|'helmet',
  file:'sprites/preview_assets/char/shirt_mage4.png', level:20,
  rarity:'common'|'uncommon'|'rare'|'legendary', classes:['mage'],   // omit = any class
  gender:'m'|'f', hatType:'partial',   // helmets only, partial hats only
  skirt:true }                          // skirt pants only
```
Tier→level mapping: t1=1, t2=5, t3=10, t4=20, t5=30, t6=40. Rares are level 25 legendary.

---

## 4. Shading constants (scripts/sprite_shade.py)

Cosine-falloff lighting, light source upper-right. Applied to HSV V only (uniform RGB
scale — hue/sat preserved). Constants:

| Constant | Value | Meaning |
|---|---|---|
| `PEAK` | **0.55** | highlight peak position in norm_x (0..1 across x=30..54) |
| `BELL_WIDTH` | **0.7** | cosine bell widening factor (wider = smoother) |
| `ADJ_MIN, ADJ_MAX` | **−0.12, +0.30** | horizontal adjustment range |
| `VERT_AMPL` | 0.05 | ±5% sine bulge per contiguous column segment |
| `EDGE_DARK_MAX` | 0.08 | max shadow adjacent to outline pixel |
| `EDGE_DIST` | 3 | edge shadow falloff radius (quadratic ramp) |
| `SMOOTH_ITERS` | 3 | band-smoothing diffusion iterations |
| `SMOOTH_ALPHA` | 0.45 | per-iteration blend toward 3×3 armor-neighbor mean V |
| `OUTLINE_SUM_MAX` | 15 | R+G+B < 15 at alpha 255 = outline (never shaded) |
| `ARMOR_MIN_BRIGHT` | 4 | mean RGB > 4 = armor (dark shadow tones stay armor) |
| `HAIR_Y_MAX` | 28 | hair exclusion only above this row |
| `METALLIC_PEAK` | 0.30 | cosine peak rescale for metallic (sat>0.35 & val>0.55) |
| `MATTE_CAP` | 0.15 | positive-adj cap for matte (sat≤0.35) |
| `MET_SAT, MET_VAL` | 0.35, 0.55 | metallic HSV thresholds |
| `SKIN_RGB ± SKIN_TOL` | #F4A460 ± 25 | skin pixels skipped |
| `HAIR_TOL` | 15 | Chebyshev tolerance vs 10-color hair palette |

Shading loop per frame: (0) hue-preserving V diffusion smooths authored tone bands
(accent gold/teal pixels frozen but act as glow sources) → (1) horizontal cosine LUT:
`norm_x=(x−30)/24`, `intensity=cos((norm_x−0.55)·π·0.7)`, mapped to [−0.12, +0.30] →
(2) vertical sine bulge per contiguous armor run per column → (3) quadratic
distance-from-outline shadow → (4) material caps/rescale → (5) accents forced to adj 0 →
apply `V *= (1+adj)`.

Accent detection: gold `r≥230 & g≥190`; teal `g≥190 & b≥160 & r≤g & r≤b`.

**Shirt override (redesign_tiers_v3.py):** shirts are shaded with
`ADJ_MIN=−0.20, ADJ_MAX=+0.25` (BELL_WIDTH 0.7); pants/boots use defaults.

CLI: `python3 scripts/sprite_shade.py in.png [out.png] [--dry-run] [--frame N]`
(overwrites input if out omitted; warns if sheet isn't 800×448).

---

## 5. Skull-dome head tracking (propagate_rare_helmets.py / rebuild_class_hats.py)

Full-head centroid FAILS: slash frames put raised-arm skin at x=52–57, y<32; cheer
frames 40–43 raise BOTH arms. The skull-dome algorithm (per frame of `skin_{g}1.png`,
head zone = opaque pixels y<32):

1. Take the TOP 3 pixel rows (global ymin..ymin+2); split their x-columns into
   contiguous runs (clusters).
2. Scan clusters LEFT→RIGHT; accept the first whose region widens to a contiguous
   width ≥ 7 px within 6 rows below (skull widens 5→7→9; arms stay 4–5 wide).
3. Re-anchor at the chosen cluster's own top row `hymin` (a raised arm can set the
   global ymin above the skull).
4. Head position = dome centroid: `cx` over rows hymin..hymin+1 (only runs overlapping
   the cluster), `cy` over rows hymin..hymin+2.
5. Propagation: `dx,dy = round(centroid_f − centroid_frame0)`; stamp the frame-0 design
   shifted by (dx,dy). Frames with no pixels in the committed sheet stay empty.

`rebuild_class_hats.py` uses the same tracker but returns `(head_top=hymin, cx)` and
builds each frame from scratch rather than shifting frame 0.

---

## 6. Hat placement rules (rebuild_class_hats.py, v3 "minimal brim")

All offsets relative to per-frame `(head_top, cx)` from the skull-dome tracker.
`HW = 9` (frame-0 skull width, constant across frames).

- **Brim:** single row at `y = head_top`. Width = `HW` exactly (0 px overhang);
  mage t6 (`wide`) gets `HW+2`. `bx0 = cx − bw//2`. Color = lining =
  `scale_v(M, 0.55)` (tier mid color at 55% V). No hatband.
- **Mage cone:** rows `head_top−1` (base, width HW) up to `head_top−cone` (tip, 1 px),
  linear taper `wdt = round(HW·(1−t) + 1·t)`. Cone heights: **t1=5, t2=6, t3=7, t4=8,
  t5=9 (lean −1), t6=10 (wide, gold rim)**. Per-row coloring by relative x:
  `rel<0.33 → D`, `0.55≤rel≤0.85 → L`, else `M`. t4/t6 tip star `S`; t5 sparkles at
  `(tip_x±2, tip_y+1)`; t6 gold rim at the 2 outer brim pixels each side.
- **Ranger crown dome:** 3 rows tall, centered at `cx+1`, base width `HW−2`, tapering
  to 2; top row + right edge = L, center crease = D, rest = M. Robin Hood tilt: 2 px of
  D at `(bx0, brim_y+1)` and `(bx0+1, brim_y+1)`. Feather: 45° up-right from
  `(cx+4, head_top−1)`, colors from tier `F` list; ≥4 feathers get a thicker plume base.
  t4–t6 metal rim accents at brim corners (t6 `rim2` = 2 px each side).
- **Outline:** exterior 1-px black outline around fill, only at `y ≤ head_top−1` for
  mage (nothing on/below brim) and `y ≤ brim_y+1` for ranger.
- **Active frames:** copy the active-frame set from the existing tier-1 helmet sheet
  (`get_active_frames`); sleep frames (6,8)/(6,9) never get hat pixels.
- After building: shade with sprite_shade.py, then QA with `--y-min 2`.

---

## 7. Tier color palettes

### Warrior armor chest tiers (sampled dominant colors, frame 0)

| Tier | Item | Base / dominant hexes |
|---|---|---|
| t1 (L1) | Leather Armor | #AF783C mid, #784B23 dark, #1E140A shadow |
| t2 (L5) | Studded Leather | #1A1A1A, #3A3A3A, #8C8C8C studs, #606060 |
| t3 (L10) | Chainmail | #2E2E2E, #4A4A4A, #0D0D0D, #1A1A1A |
| t4 (L20) | Silver Plate | #282828, #505050, #E0E0E0 highlight, #888888 |
| t5 (L30) | Gold Plate | #1A0800, #7A4200, #C07800, #FFD050 highlight |
| t6 (L40) | Diamond Plate | #001040, #0050A0, #3090D0, #B0E4FF highlight |

Rare warrior sets (level 25 legendary): **rare1 Crimson Sentinel** #FF1818 + gold
#FFD700; **rare2 Shadow Warden** near-black + electric teal #00FEE3/#14C9C9;
**rare3 Solar Paladin** #FFB106 / #FFD700 + ivory.

### Mage / Ranger garment base + accent (redesign_tiers_v3.py, tiers 2–6)

| Tier | Mage base | Mage accent | Ranger base | Ranger accent |
|---|---|---|---|---|
| 2 | #4A0080 | #C0C0C0 | #2D5A27 | #3B2A1A |
| 3 | #2A1555 | #C0C0C0 | #1A3D15 | #C3B091 |
| 4 | #1A1040 | #FFD700 | #122B0E | #B87333 |
| 5 | #0D0820 | #FFD700 | #0A1E08 | #C8C0A8 |
| 6 | #050010 | #C0A000 | #040C03 | #8B4513 |

Tier 1 (sampled): mage shirt #AB35FF bright purple + #FFD700 gold; ranger shirt
#58944B green. Named accents: GOLD #FFD700, PALE_GOLD #E8D48A, AZURE #4169E1,
SILVER #C0C0C0, BRONZE #B87333, DARK_BRONZE #8B4513, EMERALD #50C878,
VOID_PURPLE #9B59B6, UNDER_ROBE #8A70D6, FUR #C8C0A8.

### Hat palettes (rebuild_class_hats.py; D dark / M mid / L highlight / A accent / S star)

MAGE_HAT:
| t | D | M | L | A | S | cone |
|---|---|---|---|---|---|---|
| 1 | (50,25,80) | (105,43,186) | (131,64,212) | (192,192,192) | — | 5 |
| 2 | (60,16,102) | (90,24,154) | (123,47,196) | (192,192,192) | — | 6 |
| 3 | (29,17,69) | (45,27,105) | (70,48,155) | (192,192,192) | — | 7 |
| 4 | (16,16,62) | (26,26,94) | (46,46,143) | (255,215,0) | (255,240,160) | 8 tip_star |
| 5 | (8,8,28) | (13,13,43) | (58,40,110) | (255,215,0) | (226,226,255) | 9 lean−1 sparkles |
| 6 | (5,5,16) | (10,10,26) | (93,58,150) | (240,230,140) | (255,240,160) | 10 wide gold_rim tip_star |

RANGER_HAT (all dome=3):
| t | D | M | L | A | Feather F |
|---|---|---|---|---|---|
| 1 | (45,72,31) | (72,108,61) | (90,151,76) | — | (139,105,20)×3 |
| 2 | (36,66,31) | (58,107,53) | (79,143,73) | — | (139,105,20)×3 |
| 3 | (18,41,14) | (31,71,24) | (50,109,40) | — | (184,134,11)×4 |
| 4 | (14,33,16) | (26,58,21) | (44,92,36) | (184,115,51) | (232,232,232)×3+(85,85,85) |
| 5 | (8,26,6) | (15,46,10) | (30,74,24) | (192,192,192) | (245,245,245)×5 |
| 6 | (5,13,5) | (10,20,10) | (28,51,24) | (255,215,0) | (45,90,39)×3+(240,240,240)×2+(255,215,0), rim2 |

---

## 8. QA rules (scripts/sprite_qa.py)

Checks **frame 0 only** (top-left 80×64 crop). Exit 0 = all pass, 1 = failures.

1. **ISOLATED** — opaque pixel with zero opaque 8-neighbors.
2. **LONE INNER BLACK** — pure #000000 not on an outline edge (adjacent to transparent
   or frame border) AND with no 4-adjacent black neighbor. Black seams/plates pass.
3. **BACKGROUND BLEED** — opaque pixel outside the box
   `x in [30..55]`, `y in [y_min..y_max]`. Defaults: `y_min=16`, `y_max=52`.
4. **PALETTE MISMATCH** (only with `--palette r,g,b ...`) — non-black pixel farther
   than dist² 400 (~20/channel) from every declared color.

**Recommended invocation per sprite type:**

| Type | Flags |
|---|---|
| Helmets / hats (tall headgear) | `--y-min 2` |
| Shirts / chest | defaults (y 16..52) |
| Pants (male) | `--y-max 62` |
| Pants (female leggings) | `--y-max 63` |
| Boots | `--y-max 63` |

---

## 9. File naming convention (sprites/preview_assets/char/)

| Pattern | Meaning | Examples |
|---|---|---|
| `skin_{g}{n}.png` | body base, g=m/f, n=1..5 | skin_m1.png, skin_f3.png |
| `hair_{g}{n}.png` | hair; m n=1..30, f n=1..20; fileNum=(hairStyle−1)*5+hairNum | hair_m7.png, hair_f16.png |
| `sword_{g}.png`, `sword.png` | weapon layer | |
| `helmet_{cls}{t}[_f].png` | class hats, cls=mage/ranger, t=1..6; `_f` = female (t1 only exists as _f) | helmet_mage1_f.png |
| `helmet_{t}.png` | warrior helmets t=2..6 (t1 = leather_helmet_1.png) | helmet_4.png |
| `helmet_rare{n}.png` | rare warrior helmets n=1..3 (male only) | |
| `shirt_{cls}{t}[_f].png` | mage/ranger chest t=1..6 | shirt_ranger4_f.png |
| `pants_{cls}{t}[_f].png` | mage/ranger legs; female t1 are skirts | pants_mage2_f.png |
| `boots_{cls}{t}[_f].png` | mage/ranger boots | |
| `{shirt,pants,boots}_rare{n}[_f].png` | rare warrior set pieces n=1..3 | boots_rare2_f.png |
| `armor_chest_{t}[_f].png` | warrior chest t=2..6 | armor_chest_2_f.png |
| `armor_pants_{t}[_f].png` | warrior legs t=2..6 | |
| `armor_boots_{t}.png` | warrior boots t=2..6 (male sheets only) | |
| `leather_{armor,pants,boots,helmet}_1[_f].png` | warrior tier 1 set | leather_armor_1_f.png |
| `warrior_{shirt,pants}_{color}_{g}.png`, `warrior_{boots,shoes}_{g}.png` | legacy starter clothing | |

Rule of thumb: `_f` suffix = female sheet; absence = male. Female sheets are separate
files with their own silhouettes (frame-0 pixel counts: shirt 135 m / 91 f, pants 98 m /
252 f leggings, boots 46 m / 59 f) — never render a male sheet on a female body.

---

## 10. Deploy pattern

GitHub Pages auto-deploys ~1 min after push to main of
`github.com/mchauth/TaskQuest-HTML`. Live: https://mchauth.github.io/TaskQuest-HTML/.
**Never commit the PAT** (push protection blocks it); it lives only in the clone URL.

```bash
cd /tmp && rm -rf tq_push
git clone https://mchauth:GITHUB_PAT@github.com/mchauth/TaskQuest-HTML.git tq_push
cd /tmp/tq_push
git config user.email "mchauth@gmail.com" && git config user.name "Matt Hauth"
# copy changed files from the working tree into the clone, preserving paths, e.g.:
cp /path/to/TaskQuest/sprites/preview_assets/char/helmet_mage3.png sprites/preview_assets/char/
git add -A && git commit -m "message" && git push origin main
rm -rf /tmp/tq_push
```

---

## 11. Known-good runtime constants (index.html)

**TALL_HAIR_NUMS** — hair fileNums with pixels above y=20 (poke through partial hats;
verified via PIL, min_y < 20 in frame 0):
```js
{ m: [1..25],            // ALL male styles 1-5 are tall
  f: [16,17,18,19,20] }  // female style 4 only
```

**BRIM_Y** = `{ m: 21, f: 22 }` (hard clip-path fallback row).

**HAIR_MASK_FRAMES** — per-frame skull rectangles `[skullLeft, skullRight, headTop]`
keyed `"row,col"`, for canvas hair masking under partial hats. Erase rect =
columns skullLeft..skullRight, rows 0..headTop+1. Frames absent from the table
(e.g. sleep (6,8),(6,9)) have no hat pixels and hair is untouched. Representative
values (full tables live at index.html ~line 2917):

- m: `"0,0":[36,44,21]`, `"2,0":[34,42,20]`, `"3,0":[34,42,17]`, `"4,0":[34,43,17]`,
  `"5,2":[41,49,20]`, `"5,4":[33,41,23]`, `"6,6":[23,31,29]`
- f: `"0,0":[36,44,22]`, `"2,0":[35,43,21]`, `"3,0":[34,42,18]`, `"4,0":[33,42,21]`,
  `"5,2":[42,50,21]`, `"6,6":[25,33,31]`

Note: the mask-table headTop values for rows 3/4 (`m 17`, `f 18/21`) match the PIL
measurements in §2; the skull x-range is `cx−4 .. cx+4` (width 9). The (4,x) male
entries use skull width 10 (`[34,43]`) — measured, keep as committed.

**Luminance QA (scripts/lum_stats.py):** set-consistency is judged on
`lum = 0.299R + 0.587G + 0.114B` over opaque, non-black (R+G+B≥15), non-accent pixels
(gold r≥230,g≥190,b<100; teal g≥170,b≥150,r<g). Compare a sprite's median against the
median of its SET, where a set = class family + tier (shirt/pants/boots/helmet, m+f —
they share one palette). Never compare across tiers: tier progression legitimately
darkens (mage t1 bright purple → t6 near-void). sprite_pipeline.py auto-corrects >25%
deviation by uniform V-scale (clamped ×0.70–×1.40), only for sets with ≥3 sheets.
