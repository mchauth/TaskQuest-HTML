#!/usr/bin/env python3
"""
fix_weapons_t7t11.py — Redraw t7–t11 sword and staff weapons from scratch.

Fixes:
  1. Correct grip positioning: sword grip at (28,43), staff grip at (27,42)
  2. Centroid balance aligned with t1–t6 reference (sword ~35.4,30.9)
     — sword_t11 (previously an axe with centroid at 38.8,23.8) is redesigned
       as a proper greatsword so slash rotation pivots correctly
  3. More detailed, ornate pixel art designs (gems, runes, elaborate guards)

Outputs overwrite:
  sprites/preview_assets/char/sword_warrior_t{7-11}_{m,f}.png
  sprites/preview_assets/char/staff_mage_t{7-11}_{m,f}.png

Does NOT touch t1–t6 files or bow files.
Run from TaskQuest root:  python3 scripts/fix_weapons_t7t11.py
"""

import os, sys, io, contextlib, math
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT       = os.path.dirname(SCRIPT_DIR)
os.chdir(ROOT)

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    sys.path.insert(0, SCRIPT_DIR)
    import gen_weapons_v2 as gw

FW, FH           = gw.FW, gw.FH
_bresenham       = gw._bresenham
_bezier2         = gw._bezier2
build_sheet      = gw.build_sheet
rotate_pixels    = gw.rotate_pixels
translate_pixels = gw.translate_pixels
centroid_of      = gw.centroid_of
WHITE_TRAIL      = gw.WHITE_TRAIL
LAV_TRAIL        = gw.LAV_TRAIL

OUT_DIR  = 'sprites/preview_assets/char/'
SRC_PATH = f'{OUT_DIR}sword.png'

TIERS = ['t7', 't8', 't9', 't10', 't11']

# ── Utility ───────────────────────────────────────────────────────────────────

def _put(pix, x, y, col, overwrite=True):
    if 0 <= x < FW and 0 <= y < FH:
        if overwrite or (x, y) not in pix:
            pix[(x, y)] = col

def _line(pix, x0, y0, x1, y1, col, overwrite=True):
    for x, y in _bresenham(x0, y0, x1, y1):
        _put(pix, x, y, col, overwrite)

def _bez(pix, p0, ctrl, p2, col, n=60, overwrite=True):
    for x, y in _bezier2(p0, ctrl, p2, n):
        _put(pix, x, y, col, overwrite)

# Standard blade path: grip at (28,43), tip at (45,15)
BLADE_PTS = list(_bresenham(28, 43, 45, 15))

def _draw_grip(pix, grip_col, grip_shadow, pommel_col, pommel_hi):
    """Standard 2px grip wrap + 3×2 pommel. Keeps centroid near (35,31)."""
    # Grip section from (28,43) to (33,37)
    for x, y in _bresenham(28, 43, 33, 37):
        _put(pix, x,   y, grip_col)
        _put(pix, x+1, y, grip_shadow, overwrite=False)
    # 3×2 pommel at (25-27, 44-45)
    for gx in [25, 26, 27]:
        for gy in [44, 45]:
            _put(pix, gx, gy, pommel_col)
    _put(pix, 25, 44, pommel_hi)


# ═══════════════════════════════════════════════════════════════════════════════
#  SWORD DESIGNS  t7–t11
#  Target centroid ≈ (35, 31), grip at (28,43), tip at (45,15).
# ═══════════════════════════════════════════════════════════════════════════════

def make_sword_t7():
    """
    Runic Knight Longsword.
    3px two-tone steel blade (light center, dark shadow face, highlight face).
    Blue rune notch every 5th step along blade channel.
    11px swept crossguard (x=25–37) with 2px wing tips at y=35 and y=37.
    Wrapped leather grip, rounded steel pommel with highlight pip.
    """
    pix = {}
    BLADE_MID  = (175, 180, 195, 255)
    BLADE_HI   = (218, 222, 232, 255)
    BLADE_DK   = ( 78,  82,  98, 255)
    RUNE_BLUE  = ( 78, 138, 232, 255)
    RUNE_GLOW  = (140, 190, 255, 200)
    GUARD      = (132, 136, 150, 255)
    GUARD_WING = ( 98, 102, 118, 255)
    GRIP_W     = ( 60,  34,  12, 255)
    GRIP_B     = ( 42,  22,   7, 255)
    POMMEL     = (155, 160, 175, 255)
    POMMEL_HI  = (210, 215, 228, 255)

    # 3px blade
    for i, (x, y) in enumerate(BLADE_PTS):
        _put(pix, x,   y, BLADE_MID)
        _put(pix, x-1, y, BLADE_DK,  overwrite=False)
        _put(pix, x+1, y, BLADE_HI,  overwrite=False)
    # Rune channel: blue notch every 5th blade pixel
    for i in range(2, len(BLADE_PTS) - 4, 5):
        bx, by = BLADE_PTS[i]
        _put(pix, bx, by, RUNE_BLUE)
        _put(pix, bx+1, by, RUNE_GLOW, overwrite=False)

    # 11px swept crossguard at y=36 (x=25–37)
    for xi in range(25, 38):
        _put(pix, xi, 36, GUARD)
    # 2px wing-tip flares
    for xi in [25, 26, 36, 37]:
        _put(pix, xi, 35, GUARD_WING)
        _put(pix, xi, 37, GUARD_WING)

    _draw_grip(pix, GRIP_W, GRIP_B, POMMEL, POMMEL_HI)
    return pix


def make_sword_t8():
    """
    Storm Edge — serrated silver-blue blade.
    2px silver main face + 1px bright highlight right side.
    Serrated outer (left) edge: jagged offset every 2px.
    Diagonal electric-blue lightning engraving zigzagging up center.
    Asymmetric hooked crossguard: long left hook (x=24–32) curves 2px down at tips,
    shorter right flange (x=36–40) curves 1px up.  2×2 amber gem at center.
    Grip and rounded pommel.
    """
    pix = {}
    SILVER    = (198, 202, 218, 255)
    SILV_HI   = (232, 236, 244, 255)
    SILV_DK   = ( 72,  76,  92, 255)
    ELEC      = ( 55, 158, 255, 255)
    ELEC_DIM  = ( 28,  88, 178, 255)
    GUARD_L   = (100, 108, 138, 255)
    GUARD_HI  = (142, 152, 178, 255)
    AMBER     = (222, 155,  40, 255)
    AMBER_HI  = (255, 210,  80, 255)
    GRIP_W    = ( 55,  32,  10, 255)
    GRIP_B    = ( 38,  20,   6, 255)
    POMMEL    = (180, 186, 202, 255)
    POMMEL_HI = (225, 230, 242, 255)

    # 2px + highlight blade
    for x, y in BLADE_PTS:
        _put(pix, x,   y, SILVER)
        _put(pix, x+1, y, SILV_HI, overwrite=False)
        _put(pix, x-1, y, SILV_DK, overwrite=False)
    # Jagged serrations on outer (left) edge every 2px
    for i, (x, y) in enumerate(BLADE_PTS[3:-3]):
        if i % 2 == 0:
            _put(pix, x-2, y, SILV_DK, overwrite=False)
    # Lightning zigzag: alternate left/center/right on blade center
    for i, (x, y) in enumerate(BLADE_PTS[2:-2]):
        phase = i % 6
        if phase in (0, 1):
            _put(pix, x,   y, ELEC)
        elif phase in (2, 3):
            _put(pix, x-1, y, ELEC_DIM, overwrite=False)
        elif phase in (4, 5):
            _put(pix, x+1, y, ELEC_DIM, overwrite=False)

    # Asymmetric crossguard
    for xi in range(24, 41):
        _put(pix, xi, 36, GUARD_L)
    for xi in [24, 25, 26, 27]:   # left hook curves down
        _put(pix, xi, 37, GUARD_L)
        _put(pix, xi, 38, GUARD_L)
    for xi in [38, 39, 40]:        # right flange curves up
        _put(pix, xi, 35, GUARD_HI)
    # 2×2 amber gem
    for gx, gy in [(31, 35), (32, 35), (31, 36), (32, 36)]:
        _put(pix, gx, gy, AMBER)
    _put(pix, 31, 35, AMBER_HI)

    _draw_grip(pix, GRIP_W, GRIP_B, POMMEL, POMMEL_HI)
    return pix


def make_sword_t9():
    """
    Demon Fang — obsidian blade with bone-white outer trim.
    Dark obsidian center (2px), bone-white outer edge with occasional fang notch.
    Serpentine S-curve crossguard: left prong bezier curves up-left,
    right prong bezier curves down-right.  2×2 crimson gem with highlight facet.
    Bone pommel.
    """
    pix = {}
    OBS      = ( 28,  22,  45, 255)
    OBS_MID  = ( 55,  47,  78, 255)
    BONE     = (212, 206, 188, 255)
    BONE_DK  = (155, 148, 130, 255)
    BONE_HI  = (238, 234, 220, 255)
    CRIMSON  = (202,  24,  50, 255)
    CRIM_HI  = (245, 105, 118, 255)
    GUARD    = ( 88,  84, 108, 255)
    GUARD_HI = (128, 122, 150, 255)
    GRIP_W   = ( 50,  28,   8, 255)
    GRIP_B   = ( 34,  17,   5, 255)
    POMMEL   = (175, 168, 148, 255)
    POMMEL_HI= (218, 212, 195, 255)

    # 2px obsidian blade center
    for x, y in BLADE_PTS:
        _put(pix, x,   y, OBS_MID)
        _put(pix, x-1, y, OBS, overwrite=False)
    # Bone-white outer edge right side, with fang notch every 4px
    for i, (x, y) in enumerate(BLADE_PTS):
        _put(pix, x+1, y, BONE, overwrite=False)
        if i % 4 == 0 and i > 0:
            _put(pix, x+2, y, BONE_DK, overwrite=False)
            _put(pix, x+1, y, BONE_HI)  # fang tip highlight

    # Serpentine crossguard base bar (x=27–37)
    for xi in range(27, 38):
        _put(pix, xi, 36, GUARD)
    # Left prong curves up-left via bezier
    for x, y in _bezier2((27, 36), (25, 34), (24, 32)):
        _put(pix, x, y, GUARD_HI)
    # Right prong curves down-right via bezier
    for x, y in _bezier2((37, 36), (39, 38), (40, 40)):
        _put(pix, x, y, GUARD)
    # 2×2 crimson gem at crossguard center
    for gx, gy in [(31, 35), (32, 35), (31, 36), (32, 36)]:
        _put(pix, gx, gy, CRIMSON)
    _put(pix, 31, 35, CRIM_HI)

    _draw_grip(pix, GRIP_W, GRIP_B, POMMEL, POMMEL_HI)
    return pix


def make_sword_t10():
    """
    Prismatic Crystal Greatsword.
    Wide 4px mint-teal blade: dark teal left edge, mint center, pale shimmer right,
    dark right edge.  Refraction shimmer stripe every 4px alternates pale/dark.
    9px diamond-cut crossguard (x=26–36) with notched corners at y=35/37.
    2×2 aquamarine gem at guard center with highlight.
    Steel grip and rounded silver pommel.
    """
    pix = {}
    MINT     = ( 68, 212, 200, 255)
    MINT_LT  = (148, 234, 228, 255)
    TEAL_DK  = ( 20,  88,  96, 255)
    AQUA     = ( 62, 192, 240, 255)
    AQUA_HI  = (162, 228, 255, 255)
    GUARD    = (140, 148, 165, 255)
    GUARD_HI = (192, 200, 212, 255)
    GEM      = ( 88, 204, 250, 255)
    GEM_HI   = (200, 240, 255, 255)
    GRIP_W   = (100, 105, 118, 255)
    GRIP_B   = ( 68,  72,  86, 255)
    POMMEL   = (182, 188, 200, 255)
    POMMEL_HI= (225, 230, 240, 255)

    # 4px mint-teal blade
    for i, (x, y) in enumerate(BLADE_PTS):
        _put(pix, x,   y, MINT)
        _put(pix, x-1, y, TEAL_DK, overwrite=False)
        _put(pix, x+1, y, MINT_LT, overwrite=False)
        _put(pix, x+2, y, TEAL_DK, overwrite=False)
        # Refraction shimmer every 4px
        phase = i % 4
        if phase == 2:
            _put(pix, x, y, MINT_LT)
        elif phase == 3:
            _put(pix, x, y, TEAL_DK)

    # 9px diamond-cut crossguard
    for xi in range(26, 37):
        col = GUARD_HI if abs(xi - 31) <= 1 else GUARD
        _put(pix, xi, 36, col)
    # Notched diamond corners
    for xi in [26, 27, 35, 36]:
        _put(pix, xi, 35, GUARD_HI)
        _put(pix, xi, 37, GUARD_HI)
    # 2×2 aquamarine gem
    for gx, gy in [(30, 35), (31, 35), (30, 36), (31, 36)]:
        _put(pix, gx, gy, GEM)
    _put(pix, 30, 35, GEM_HI)

    _draw_grip(pix, GRIP_W, GRIP_B, POMMEL, POMMEL_HI)
    _put(pix, 25, 44, POMMEL_HI)
    return pix


def make_sword_t11():
    """
    Solar Champion Greatsword.
    Wide 4px golden blade with flame-orange serrations on outer (left) edge every 2px.
    Extra bright highlight tip at (45,15).
    Massive 13px radiant crossguard (x=23–39) with 4 diagonal accent pixels at 45°
    above and below bar ends.  3×3 sun-red gem at guard center with glow ring.
    Thick wrapped grip, 3×3 gold sunburst pommel with bright highlight.
    Centroid kept near (35,31) by balancing grip+pommel mass against blade.
    """
    pix = {}
    GOLD     = (235, 190,  42, 255)
    GOLD_HI  = (255, 228,  90, 255)
    GOLD_DK  = (165, 120,  18, 255)
    FLAME    = (242,  88,  22, 255)
    FLAME_HI = (255, 148,  52, 255)
    SUN_RED  = (222,  38,  40, 255)
    SUN_HI   = (255, 128, 128, 255)
    SUN_GLOW = (255, 180, 100, 180)
    GUARD    = (222, 175,  38, 255)
    GUARD_DK = (148, 108,  18, 255)
    GUARD_HI = (255, 220,  80, 255)
    GRIP_W   = (155,  88,  20, 255)
    GRIP_B   = ( 90,  48,  10, 255)
    POMMEL   = (215, 170,  35, 255)
    POMMEL_HI= (255, 228,  85, 255)

    # 4px golden blade
    for i, (x, y) in enumerate(BLADE_PTS):
        _put(pix, x,   y, GOLD)
        _put(pix, x-1, y, GOLD_DK, overwrite=False)
        _put(pix, x+1, y, GOLD_HI, overwrite=False)
        _put(pix, x+2, y, GOLD_DK, overwrite=False)
    # Bright tip
    tx, ty = BLADE_PTS[0]
    _put(pix, tx, ty, GOLD_HI)
    _put(pix, tx+1, ty, GOLD_HI, overwrite=False)
    # Flame serrations on outer (left) edge every 2px (skipping tip and grip areas)
    for i, (x, y) in enumerate(BLADE_PTS[2:-4]):
        if i % 2 == 0:
            _put(pix, x-2, y, FLAME, overwrite=False)
            _put(pix, x-3, y, FLAME_HI, overwrite=False)

    # 13px radiant crossguard at y=36, x=23–39
    for xi in range(23, 40):
        col = GUARD_DK if xi in [23, 24, 38, 39] else GUARD
        _put(pix, xi, 36, col)
    # Diagonal accent pixels at 45° from bar ends (radiant burst effect)
    for xi, yi in [(24, 35), (25, 34), (38, 35), (37, 34)]:
        _put(pix, xi, yi, GUARD_HI)
    for xi, yi in [(24, 37), (25, 38), (38, 37), (37, 38)]:
        _put(pix, xi, yi, GUARD)
    # 3×3 sun-red gem at center with 1px glow ring
    for gx in [30, 31, 32]:
        for gy in [35, 36, 37]:
            _put(pix, gx, gy, SUN_RED)
    _put(pix, 30, 35, SUN_HI)  # highlight facet
    # Glow ring around gem
    for gx, gy in [(29, 36), (33, 36), (31, 34), (31, 38)]:
        _put(pix, gx, gy, SUN_GLOW, overwrite=False)

    # Thick wrapped grip (x offset +1 for visual grip width)
    for x, y in _bresenham(28, 43, 32, 39):
        _put(pix, x,   y, GRIP_W)
        _put(pix, x+1, y, GRIP_B, overwrite=False)
    # 3×3 sunburst pommel (x=24–26, y=44–46)
    for gx in [24, 25, 26]:
        for gy in [44, 45, 46]:
            _put(pix, gx, gy, POMMEL)
    _put(pix, 25, 44, POMMEL_HI)
    _put(pix, 24, 45, POMMEL_HI)
    return pix


SWORD_MAKERS = {
    't7':  make_sword_t7,
    't8':  make_sword_t8,
    't9':  make_sword_t9,
    't10': make_sword_t10,
    't11': make_sword_t11,
}

SWORD_TRAILS = {
    't7':  ((210, 215, 228, 255), (155, 160, 180, 255)),  # cool steel
    't8':  ((118, 195, 255, 255), ( 58, 128, 212, 255)),  # electric blue
    't9':  (( 82,  55, 122, 255), ( 48,  32,  78, 255)),  # dark void
    't10': ((108, 232, 218, 255), ( 52, 162, 155, 255)),  # prismatic teal
    't11': ((255, 215,  75, 255), (222, 140,  30, 255)),  # solar gold
}

SWORD_DESCS = {
    't7':  'Runic longsword — 3px steel, rune channel, 11px swept guard w/ wing tips',
    't8':  'Storm blade — serrated silver, lightning engraving, hooked guard, amber gem',
    't9':  'Demon fang — obsidian + bone-white trim, serpentine guard, crimson gem',
    't10': 'Prismatic crystal — 4px mint-teal, refraction shimmer, diamond guard, aqua gem',
    't11': 'Solar greatsword — 4px gold, flame serrations, 13px sunburst guard, 3×3 sun gem',
}


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF DESIGNS  t7–t11
#  Shaft: bezier (27,42)→(38,17). build_sheet applies -45° rotation per frame.
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_staff_shaft(pix, dark, mid, light, band_col=None, band_y=28):
    """Staff shaft from grip (27,42) to neck (38,17), 2px wide + optional band."""
    shaft_pts = _bezier2((27, 42), (32, 29), (38, 17))
    n = max(1, len(shaft_pts) - 1)
    for i, (x, y) in enumerate(shaft_pts):
        t = i / n
        col = dark if t < 0.3 else (mid if t < 0.7 else light)
        _put(pix, x,   y, col)
        _put(pix, x+1, y, dark, overwrite=False)
    if band_col:
        for xi in range(33, 38):
            _put(pix, xi, band_y, band_col)


def make_staff_t7():
    """
    Solar Crown Staff.
    Warm brass shaft.  Top: 8-ray sunburst crown — outer ring radius 4 (every 18°),
    8 cardinal+diagonal spoke rays 4–7px long in gold/gold-bright, 2×2 brilliant
    yellow-white core.  Gold accent band on shaft.
    """
    pix = {}
    SHAFT_DK = ( 60,  38,  10, 255)
    SHAFT_MD = (100,  65,  22, 255)
    SHAFT_LT = (132,  88,  35, 255)
    GOLD     = (218, 170,  40, 255)
    GOLD_LT  = (252, 215,  72, 255)
    SUN_CORE = (255, 245, 110, 255)
    BAND     = (168, 125,  30, 255)
    _draw_staff_shaft(pix, SHAFT_DK, SHAFT_MD, SHAFT_LT, BAND, 28)

    cx, cy = 40, 13
    # 8 spoke rays at 45° intervals (cardinal + diagonal)
    for deg in range(0, 360, 45):
        rad = math.radians(deg)
        for r in range(4, 8):
            rx = round(cx + r * math.cos(rad))
            ry = round(cy + r * math.sin(rad))
            col = GOLD if r <= 5 else GOLD_LT
            _put(pix, rx, ry, col)
    # Outer ring at radius 4 (every 18° for density)
    for deg in range(0, 360, 18):
        rx = round(cx + 4 * math.cos(math.radians(deg)))
        ry = round(cy + 4 * math.sin(math.radians(deg)))
        _put(pix, rx, ry, GOLD)
    # 2×2 brilliant core
    for gx, gy in [(39, 12), (40, 12), (39, 13), (40, 13)]:
        _put(pix, gx, gy, SUN_CORE)
    return pix


def make_staff_t8():
    """
    Crescent Moon Staff.
    Dark steel shaft with moonstone band.
    Top: silver crescent arc (outer bezier) with inner cutout area cleared,
    large sapphire orb (radius 3) nestled inside the crescent hollow.
    Silver glow pixel at crescent horn tips.
    """
    pix = {}
    SHAFT_DK = ( 38,  42,  58, 255)
    SHAFT_MD = ( 68,  75, 100, 255)
    SHAFT_LT = (105, 115, 145, 255)
    SILVER   = (190, 196, 212, 255)
    SILV_HI  = (230, 235, 245, 255)
    SAPH     = ( 55, 132, 232, 255)
    SAPH_HI  = (132, 198, 255, 255)
    SAPH_DK  = ( 28,  60, 132, 255)
    BAND     = (155, 162, 185, 255)
    _draw_staff_shaft(pix, SHAFT_DK, SHAFT_MD, SHAFT_LT, BAND, 28)

    # Outer crescent arc from (34,8) through (50,9) to (44,20)
    outer_pts = _bezier2((34, 8), (50, 8), (44, 20))
    for x, y in outer_pts:
        _put(pix, x, y, SILVER)
        _put(pix, x+1, y, SILV_HI, overwrite=False)
    # Inner cutout: erase interior pixels (create crescent hollow)
    inner_pts = _bezier2((37, 11), (46, 12), (42, 19))
    for x, y in inner_pts:
        _put(pix, x, y, (0, 0, 0, 0))   # transparent
    # Silver horn tips
    for pt in [outer_pts[0], outer_pts[-1]]:
        _put(pix, pt[0], pt[1], SILV_HI)
        _put(pix, pt[0]+1, pt[1], SILV_HI, overwrite=False)

    # Sapphire orb inside crescent hollow, center (41,13), radius 3
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            dist = (dx*dx + dy*dy) ** 0.5
            gx, gy = 41+dx, 13+dy
            if 0 <= gx < FW and 0 <= gy < FH:
                if dist <= 1.2:
                    _put(pix, gx, gy, SAPH_HI)
                elif dist <= 2.8:
                    _put(pix, gx, gy, SAPH)
                elif dist <= 3.2:
                    _put(pix, gx, gy, SAPH_DK, overwrite=False)
    return pix


def make_staff_t9():
    """
    Void Shard Staff.
    Obsidian shaft.  Top: 5-pointed dark star — 5 spike arms at 72° intervals,
    3px long, in deep purple.  Near-black orb 2×2 center.  Single bright
    violet-white flare pixel as the star core.
    Purple accent band on shaft.
    """
    pix = {}
    OBS_DK  = ( 14,   8,  28, 255)
    OBS_MD  = ( 32,  20,  58, 255)
    OBS_LT  = ( 60,  38,  98, 255)
    VOID_P  = ( 52,  20,  90, 255)
    VOID_MD = ( 88,  48, 140, 255)
    VOID_DK = ( 12,   5,  22, 255)
    STAR_HI = (232, 215, 255, 255)
    STAR_C  = (178, 132, 252, 255)
    BAND    = ( 72,  48, 118, 255)
    _draw_staff_shaft(pix, OBS_DK, OBS_MD, OBS_LT, BAND, 28)

    cx, cy = 40, 13
    # 5-pointed star spikes at 72° intervals starting from top (−90°)
    for i in range(5):
        deg = -90 + i * 72
        rad = math.radians(deg)
        for r in range(1, 5):
            sx = round(cx + r * math.cos(rad))
            sy = round(cy + r * math.sin(rad))
            col = VOID_MD if r <= 2 else VOID_P
            _put(pix, sx, sy, col)
    # Inter-spike fill: shorter 2px arms between spikes
    for i in range(5):
        deg = -90 + i * 72 + 36
        rad = math.radians(deg)
        for r in range(1, 3):
            sx = round(cx + r * math.cos(rad))
            sy = round(cy + r * math.sin(rad))
            _put(pix, sx, sy, OBS_DK, overwrite=False)
    # Dark orb center 2×2
    for gx, gy in [(39, 12), (40, 12), (39, 13), (40, 13)]:
        _put(pix, gx, gy, VOID_DK)
    # Bright flare core
    _put(pix, 40, 12, STAR_HI)
    _put(pix, 39, 13, STAR_C)
    return pix


def make_staff_t10():
    """
    Dragon Claw Staff.
    Dark steel shaft with gold ring + silver accent bands.
    Top: three dramatic claw arcs (left, center, right) in dark/light steel
    encircle a faceted 3×3 crimson ruby gem.  Claw tips curve outward; each arc
    has a 1px dark outline.  Gold ring accent at y=26, silver band at y=30.
    """
    pix = {}
    SHAFT_DK = ( 50,  52,  65, 255)
    SHAFT_MD = ( 85,  90, 108, 255)
    SHAFT_LT = (130, 138, 162, 255)
    RUBY     = (205,  24,  48, 255)
    RUBY_HI  = (250, 108, 122, 255)
    RUBY_DK  = (138,  12,  28, 255)
    CLAW_DK  = ( 58,  62,  78, 255)
    CLAW_MID = (105, 112, 135, 255)
    CLAW_LT  = (158, 165, 188, 255)
    GOLD     = (208, 172,  45, 255)
    BAND     = (145, 152, 175, 255)
    _draw_staff_shaft(pix, SHAFT_DK, SHAFT_MD, SHAFT_LT)
    # Gold ring and silver band
    for xi in range(33, 38):
        _put(pix, xi, 26, GOLD)
    for xi in range(33, 38):
        _put(pix, xi, 30, BAND)

    # 3×3 ruby gem at center (38–40, 12–14)
    for gx in [38, 39, 40]:
        for gy in [12, 13, 14]:
            _put(pix, gx, gy, RUBY)
    _put(pix, 38, 12, RUBY_HI)
    _put(pix, 40, 14, RUBY_DK)
    _put(pix, 40, 12, RUBY_HI, overwrite=False)

    # Three claw arcs around the gem
    claws = [
        _bezier2((37, 15), (33, 13), (35,  9)),   # left claw
        _bezier2((39, 11), (39,  7), (41,  9)),   # center top claw
        _bezier2((41, 15), (45, 13), (43,  9)),   # right claw
    ]
    for arc in claws:
        for x, y in arc:
            _put(pix, x, y, CLAW_MID, overwrite=False)
            _put(pix, x, y, CLAW_LT)            # bright face
        # Dark outline
        for x, y in arc:
            _put(pix, x-1, y, CLAW_DK, overwrite=False)
            _put(pix, x+1, y, CLAW_DK, overwrite=False)
            _put(pix, x, y-1, CLAW_DK, overwrite=False)
    return pix


def make_staff_t11():
    """
    Celestial Radiant Prism Staff.
    Royal purple shaft with two winding bands (gold, silver-purple).
    Top: 12-ray starburst crown — 8 major gold rays + 4 minor purple rays at 22.5°
    offset, all emanating from (40,12).  7-pixel hexagonal rainbow gem cluster at
    center (one pixel each ROYGCBV spectrum).  White-glow aura ring radius 1
    around cluster.
    """
    pix = {}
    SHAFT_DK = ( 44,  28,  65, 255)
    SHAFT_MD = ( 78,  52, 108, 255)
    SHAFT_LT = (118,  82, 158, 255)
    BAND_G   = (155, 108, 215, 255)
    BAND_S   = (188, 150, 240, 255)
    RAY_GOLD = (230, 178,  48, 255)
    RAY_PURP = (145,  58, 215, 255)
    GLOW     = (240, 238, 252, 200)
    _draw_staff_shaft(pix, SHAFT_DK, SHAFT_MD, SHAFT_LT)
    for xi in range(33, 38):
        _put(pix, xi, 26, BAND_G)
        _put(pix, xi, 31, BAND_S)

    cx, cy = 40, 12
    # 8 major gold rays at 45° intervals, 4–7px
    for deg in range(0, 360, 45):
        rad = math.radians(deg)
        for r in range(4, 8):
            rx = round(cx + r * math.cos(rad))
            ry = round(cy + r * math.sin(rad))
            _put(pix, rx, ry, RAY_GOLD)
    # 4 minor purple rays at 22.5° offset, 3–5px
    for deg in range(22, 360, 90):
        rad = math.radians(deg)
        for r in range(3, 6):
            rx = round(cx + r * math.cos(rad))
            ry = round(cy + r * math.sin(rad))
            _put(pix, rx, ry, RAY_PURP, overwrite=False)

    # 7-pixel rainbow hexagonal gem cluster
    spectrum = [
        (225,  42,  42, 255),  # red
        (228, 132,  32, 255),  # orange
        (238, 228,  42, 255),  # yellow
        ( 58, 200,  62, 255),  # green
        ( 42, 215, 212, 255),  # cyan
        ( 55, 102, 230, 255),  # blue
        (178,  50, 235, 255),  # violet
    ]
    hex_pos = [(40,12),(39,12),(41,12),(40,11),(40,13),(39,11),(41,13)]
    for (gx, gy), col in zip(hex_pos, spectrum):
        _put(pix, gx, gy, col)
    # White-glow 1px ring around cluster
    for gx, gy in hex_pos:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            _put(pix, gx+dx, gy+dy, GLOW, overwrite=False)
    return pix


STAFF_MAKERS = {
    't7':  make_staff_t7,
    't8':  make_staff_t8,
    't9':  make_staff_t9,
    't10': make_staff_t10,
    't11': make_staff_t11,
}

STAFF_TRAILS = {
    't7':  ((255, 234,  82, 255), (255, 175,  45, 200)),  # gold sun
    't8':  (( 80, 165, 242, 255), (125, 198, 255, 200)),  # moonlight blue
    't9':  ((148,  62, 235, 255), ( 82,  22, 162, 180)),  # void purple
    't10': ((218,  28,  52, 255), (165,  12,  30, 200)),  # ruby red
    't11': ((205, 162, 255, 255), (125,  82, 215, 200)),  # prismatic purple
}

STAFF_DESCS = {
    't7':  'Solar crown — 8-ray sunburst + outer ring, 2×2 brilliant core, gold band',
    't8':  'Crescent moon — silver arc + cutout, sapphire orb inside, moonstone band',
    't9':  'Void shard — 5-pt dark star, 2×2 dark orb, bright violet flare core',
    't10': 'Dragon claw — 3 prong arcs + 3×3 ruby gem, gold ring + silver band',
    't11': 'Celestial prism — 12-ray crown (8 gold + 4 purple), 7px rainbow hex gem',
}


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import hashlib
    def md5(p):
        with open(p, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    # Record t1-t6 hashes — must be unchanged at end
    protected = {}
    for w in ['bow_ranger', 'sword_warrior', 'staff_mage']:
        for t in ['t1', 't2', 't3', 't4', 't5', 't6']:
            for g in ['m', 'f']:
                p = f'{OUT_DIR}{w}_{t}_{g}.png'
                if os.path.isfile(p):
                    protected[p] = md5(p)

    print("=== fix_weapons_t7t11.py ===")
    print(f"Working dir: {os.getcwd()}")
    print(f"Regenerating tiers: {TIERS}")

    # ── Swords ────────────────────────────────────────────────────────────────
    print("\n=== Swords ===")
    for tier in TIERS:
        f0 = SWORD_MAKERS[tier]()
        cx, cy = centroid_of(f0)
        # Grip region check
        grip = [(x,y) for (x,y) in f0 if 38 <= y <= 50]
        gcx = sum(p[0] for p in grip) / len(grip) if grip else -1
        gcy = sum(p[1] for p in grip) / len(grip) if grip else -1
        print(f"  {tier}: {SWORD_DESCS[tier]}")
        print(f"    centroid=({cx:.1f},{cy:.1f}), grip_region=({gcx:.1f},{gcy:.1f}), px={len(f0)}")
        tc, te = SWORD_TRAILS[tier]
        for g in ['m', 'f']:
            out = f'{OUT_DIR}sword_warrior_{tier}_{g}.png'
            build_sheet(f0, SRC_PATH, out, weapon_type='sword', trail_c=tc, trail_e=te)

    # ── Staffs ────────────────────────────────────────────────────────────────
    print("\n=== Staffs ===")
    for tier in TIERS:
        f0 = STAFF_MAKERS[tier]()
        cx, cy = centroid_of(f0)
        grip = [(x,y) for (x,y) in f0 if 38 <= y <= 50]
        gcx = sum(p[0] for p in grip) / len(grip) if grip else -1
        gcy = sum(p[1] for p in grip) / len(grip) if grip else -1
        print(f"  {tier}: {STAFF_DESCS[tier]}")
        print(f"    centroid=({cx:.1f},{cy:.1f}), grip_region=({gcx:.1f},{gcy:.1f}), px={len(f0)}")
        tc, te = STAFF_TRAILS[tier]
        for g in ['m', 'f']:
            out = f'{OUT_DIR}staff_mage_{tier}_{g}.png'
            build_sheet(f0, SRC_PATH, out, weapon_type='staff', trail_c=tc, trail_e=te)

    # ── Verify protected files unchanged ──────────────────────────────────────
    print("\n=== Protected file check ===")
    ok = True
    for path, orig in protected.items():
        if md5(path) != orig:
            print(f"  MODIFIED: {os.path.basename(path)} !!!")
            ok = False
    if ok:
        print(f"  All {len(protected)} protected files unchanged ✓")

    print("\nDone.")


if __name__ == '__main__':
    main()
