#!/usr/bin/env python3
"""
draw_inspired_weapons.py
Draw ORIGINAL pixel-art weapon sprites for tiers t7–t11.

Designs are hand-coded from scratch using Bezier and Bresenham drawing
functions.  The visual style of each tier is informed by the reference images
(IMG_8320, IMG_8321) as creative inspiration, but NO pixels are copied from
those images.

Outputs:
  sprites/preview_assets/char/bow_ranger_t{7-11}_{m,f}.png
  sprites/preview_assets/char/sword_warrior_t{7-11}_{m,f}.png
  sprites/preview_assets/char/staff_mage_t{7-11}_{m,f}.png

Existing t1–t6 (and any other) sprite files are NEVER touched.
"""

import os, sys, io, contextlib
import numpy as np
from PIL import Image

# ── Run from TaskQuest root ───────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT       = os.path.dirname(SCRIPT_DIR)
os.chdir(ROOT)

# ── Import helpers from gen_weapons_v2 ────────────────────────────────────────
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    sys.path.insert(0, SCRIPT_DIR)
    import gen_weapons_v2 as gw

FW, FH          = gw.FW, gw.FH          # 80, 64
_bresenham      = gw._bresenham
_bezier2        = gw._bezier2
build_sheet     = gw.build_sheet
rotate_pixels   = gw.rotate_pixels
translate_pixels= gw.translate_pixels
centroid_of     = gw.centroid_of
WHITE_TRAIL     = gw.WHITE_TRAIL
LAV_TRAIL       = gw.LAV_TRAIL

OUT_DIR  = 'sprites/preview_assets/char/'
SRC_PATH = f'{OUT_DIR}sword.png'
SKIN_PATHS = {'m': f'{OUT_DIR}skin.png',        'f': f'{OUT_DIR}skin_f1.png'}
ARM_PATHS  = {'m': f'{OUT_DIR}skin_arm_m1.png', 'f': f'{OUT_DIR}skin_arm_f1.png'}

NEW_TIERS = ['t7', 't8', 't9', 't10', 't11']

# ── Utility ───────────────────────────────────────────────────────────────────

def _put(pix, x, y, col, overwrite=True):
    if 0 <= x < FW and 0 <= y < FH:
        if overwrite or (x, y) not in pix:
            pix[(x, y)] = col

def _line(pix, x0, y0, x1, y1, col, overwrite=True):
    for x, y in _bresenham(x0, y0, x1, y1):
        _put(pix, x, y, col, overwrite)

def _bezier_stroke(pix, p0, ctrl, p2, col, n=60, overwrite=True):
    pts = _bezier2(p0, ctrl, p2, n)
    for x, y in pts:
        _put(pix, x, y, col, overwrite)

def _outline(pix, base_set, outline_col):
    """Draw 1px 4-connected outline around base_set pixels, without overwriting."""
    for (x, y) in list(base_set):
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            _put(pix, x+dx, y+dy, outline_col, overwrite=False)


# ═══════════════════════════════════════════════════════════════════════════════
#  BOW DESIGNS  (t7–t11)
#  Coordinate convention: UPPER_TIP upper-right, LOWER_TIP lower-left, GRIP mid.
#  build_sheet with weapon_type='bow' handles all animation frames.
# ═══════════════════════════════════════════════════════════════════════════════

def make_bow_t7():
    """
    Two-tone split-limb bow.
    Upper limb: dark espresso hardwood. Lower limb: warm medium wood.
    Bronze wrapped grip band. Style: sturdy recurve, two-tone contrast.
    Inspired visual concept: angular two-tone split-limb from reference row 0.
    """
    pix = {}
    UPPER_TIP = (52, 17); LOWER_TIP = (30, 61); GRIP = (36, 39)
    DARK_WOOD  = (22, 12,  5, 255)
    UPPER_MID  = (55, 28, 10, 255)   # dark espresso upper limb
    UPPER_LT   = (75, 40, 15, 255)
    LOWER_MID  = (110, 68, 22, 255)  # warm chestnut lower limb
    LOWER_LT   = (145, 95, 38, 255)
    BRONZE     = (140, 100, 45, 255)
    BRONZE_LT  = (175, 135, 65, 255)
    STR_COL    = (210, 200, 170, 255)

    # Upper limb: single recurve segment
    upper_pts = _bezier2(UPPER_TIP, (44, 26), GRIP)
    for i, (x, y) in enumerate(upper_pts):
        t = i / max(len(upper_pts)-1, 1)
        col = UPPER_LT if t < 0.4 else UPPER_MID
        _put(pix, x, y, col)
        _put(pix, x-1, y, DARK_WOOD, overwrite=False)   # dark inner edge

    # Lower limb: single recurve segment (warmer wood)
    lower_pts = _bezier2(GRIP, (33, 51), LOWER_TIP)
    for i, (x, y) in enumerate(lower_pts[1:]):
        t = i / max(len(lower_pts)-2, 1)
        col = LOWER_MID if t < 0.6 else LOWER_LT
        _put(pix, x, y, col)
        _put(pix, x+1, y, DARK_WOOD, overwrite=False)   # dark outer edge

    # Bronze grip band: 3px wrap at grip center
    for y in range(37, 42):
        for x in range(35, 38):
            _put(pix, x, y, BRONZE)
    # Small bronze highlight
    _put(pix, 36, 38, BRONZE_LT)

    # String: from upper tip inner → lower tip inner
    str_u = (UPPER_TIP[0]+1, UPPER_TIP[1]+1)
    str_l = (LOWER_TIP[0]+1, LOWER_TIP[1]-1)
    for x, y in _bresenham(str_u[0], str_u[1], str_l[0], str_l[1]):
        _put(pix, x, y, STR_COL, overwrite=False)

    return pix, str_u, str_l, STR_COL


def make_bow_t8():
    """
    Crystal-tipped recurve.
    Ice-blue gradient arc with 3-pixel diamond crystal at each tip, 2×2 gem at grip.
    Style: elegant magical recurve, ice palette.
    Inspired visual concept: crystal blue recurve with gem accents, reference row 1.
    """
    pix = {}
    UPPER_TIP = (52, 17); LOWER_TIP = (30, 61); GRIP = (36, 39)
    DARK_ICE = (25,  60, 115, 255)
    MID_ICE  = (65, 130, 195, 255)
    LITE_ICE = (130, 195, 240, 255)
    CRYSTAL  = (200, 235, 255, 255)    # tip crystal
    GEM      = (180, 230, 255, 255)
    STR_COL  = (195, 225, 250, 255)

    upper_pts = _bezier2(UPPER_TIP, (43, 26), GRIP)
    lower_pts = _bezier2(GRIP, (32, 51), LOWER_TIP)
    all_pts   = upper_pts + lower_pts[1:]
    n = max(1, len(all_pts)-1)
    for i, (x, y) in enumerate(all_pts):
        t = i / n
        col = LITE_ICE if (t < 0.2 or t > 0.8) else MID_ICE
        _put(pix, x, y, col)
        _put(pix, x-1, y, DARK_ICE, overwrite=False)
        _put(pix, x+1, y, DARK_ICE, overwrite=False)

    # Crystal points at tips: diamond shape (3px)
    for tx, ty in [UPPER_TIP, LOWER_TIP]:
        _put(pix, tx, ty, CRYSTAL)
        _put(pix, tx+1, ty, CRYSTAL)
        _put(pix, tx-1, ty, CRYSTAL, overwrite=False)

    # 2×2 gem at grip center
    for gx, gy in [(35,38),(36,38),(35,39),(36,39)]:
        _put(pix, gx, gy, GEM)

    str_u = (UPPER_TIP[0]+1, UPPER_TIP[1]+1)
    str_l = (LOWER_TIP[0]+1, LOWER_TIP[1]-1)
    for x, y in _bresenham(str_u[0], str_u[1], str_l[0], str_l[1]):
        _put(pix, x, y, STR_COL, overwrite=False)

    return pix, str_u, str_l, STR_COL


def make_bow_t9():
    """
    Dark angular compound.
    Near-black body with aggressive outward flare at both tips, single electric-blue
    highlight pixel on inner edge every 3 steps. Minimal decorations — clean power.
    Inspired visual concept: dark angular black recurve from reference row 1.
    """
    pix = {}
    UPPER_TIP = (54, 14); LOWER_TIP = (28, 63); GRIP = (36, 39)
    BODY      = (12,  12,  35, 255)   # near-black with blue undertone
    EDGE      = ( 6,   6,  18, 255)   # darker outline
    HI_BLUE   = (70,  90, 210, 255)   # electric-blue highlight
    STR_COL   = (100, 120, 210, 255)

    # Each limb: two segments for angular flare at tip
    seg1u = _bezier2(UPPER_TIP, (54, 22), (44, 27))
    seg2u = _bezier2((44, 27),  (40, 32), GRIP)
    seg1l = _bezier2(GRIP,      (32, 46), (22, 57))
    seg2l = _bezier2((22, 57),  (25, 61), LOWER_TIP)
    all_pts = seg1u + seg2u[1:] + seg1l[1:] + seg2l[1:]

    for i, (x, y) in enumerate(all_pts):
        _put(pix, x, y, BODY)
        _put(pix, x-1, y, EDGE, overwrite=False)
        _put(pix, x+1, y, EDGE, overwrite=False)
        # Electric-blue inner edge accent every 3 pts
        if i % 3 == 0:
            _put(pix, x+1, y, HI_BLUE, overwrite=False)

    str_u = (UPPER_TIP[0]+1, UPPER_TIP[1]+1)
    str_l = (LOWER_TIP[0]+1, LOWER_TIP[1]-1)
    for x, y in _bresenham(str_u[0], str_u[1], str_l[0], str_l[1]):
        _put(pix, x, y, STR_COL, overwrite=False)

    return pix, str_u, str_l, STR_COL


def make_bow_t10():
    """
    Nature-vine organic compound.
    Three-segment S-curve per limb (organic flow), deep forest green, orange gem
    at grip, 3px leaf accent at each limb mid-point.
    Inspired visual concept: green nature compound with foliage from reference row 2.
    """
    pix = {}
    UPPER_TIP = (52, 17); LOWER_TIP = (30, 61); GRIP = (36, 39)
    VINE_DARK  = (12,  38,  8, 255)
    VINE_MID   = (30,  75, 22, 255)
    VINE_LT    = (65, 150, 45, 255)
    GEM_ORG    = (230, 110, 25, 255)
    LEAF       = (80,  175, 55, 255)
    STR_COL    = (185, 225, 145, 255)

    # Upper limb: 3 bezier segments for organic S-curve
    seg1u = _bezier2(UPPER_TIP, (56, 20), (48, 26))
    seg2u = _bezier2((48, 26),  (42, 31), (39, 34))
    seg3u = _bezier2((39, 34),  (37, 37), GRIP)
    upper_pts = seg1u + seg2u[1:] + seg3u[1:]

    # Lower limb: 3 bezier segments
    seg1l = _bezier2(GRIP,      (33, 43), (31, 48))
    seg2l = _bezier2((31, 48),  (28, 54), (30, 57))
    seg3l = _bezier2((30, 57),  (29, 59), LOWER_TIP)
    lower_pts = seg1l + seg2l[1:] + seg3l[1:]

    all_pts = upper_pts + lower_pts[1:]
    n = max(1, len(all_pts)-1)
    for i, (x, y) in enumerate(all_pts):
        t = i / n
        col = VINE_LT if (t < 0.2 or t > 0.8) else VINE_MID
        _put(pix, x, y, col)
        _put(pix, x-1, y, VINE_DARK, overwrite=False)
        _put(pix, x+1, y, VINE_DARK, overwrite=False)

    # 3px orange gem at grip
    for gx, gy in [(34,38),(35,38),(36,38)]:
        _put(pix, gx, gy, GEM_ORG)

    # Leaf accent at upper-limb mid: 3 pixels branching off
    for lx, ly in [(48,25),(47,26),(49,25)]:
        _put(pix, lx, ly, LEAF, overwrite=False)
    # Leaf accent at lower-limb mid: 3 pixels
    for lx, ly in [(30,54),(29,54),(31,53)]:
        _put(pix, lx, ly, LEAF, overwrite=False)

    str_u = (UPPER_TIP[0]+1, UPPER_TIP[1]+1)
    str_l = (LOWER_TIP[0]+1, LOWER_TIP[1]-1)
    for x, y in _bresenham(str_u[0], str_u[1], str_l[0], str_l[1]):
        _put(pix, x, y, STR_COL, overwrite=False)

    return pix, str_u, str_l, STR_COL


def make_bow_t11():
    """
    Celestial ornate compound.
    Widest spread, royal purple limbs, gold accent line, 3×3 pink-gold gem at grip,
    bright violet-white glow dot at each tip.
    Inspired visual concept: ornate purple/pink bow with gem embellishments, reference row 3.
    """
    pix = {}
    UPPER_TIP = (56, 12); LOWER_TIP = (26, 62); GRIP = (36, 39)
    PURPLE_DK  = (55, 20, 85, 255)
    PURPLE_MID = (130, 60, 190, 255)
    GOLD       = (225, 175, 55, 255)
    GEM_PK     = (240, 175, 220, 255)
    TIP_GLO    = (255, 235, 255, 255)
    STR_COL    = (240, 200, 255, 255)

    seg1u = _bezier2(UPPER_TIP, (60, 18), (50, 25))
    seg2u = _bezier2((50, 25),  (42, 32), GRIP)
    seg1l = _bezier2(GRIP,      (28, 47), (18, 55))
    seg2l = _bezier2((18, 55),  (22, 60), LOWER_TIP)
    all_pts = seg1u + seg2u[1:] + seg1l[1:] + seg2l[1:]
    n = max(1, len(all_pts)-1)
    for i, (x, y) in enumerate(all_pts):
        t = i / n
        col = PURPLE_MID if 0.2 < t < 0.8 else PURPLE_DK
        _put(pix, x, y, col)
        _put(pix, x-1, y, PURPLE_DK, overwrite=False)
        _put(pix, x+1, y, PURPLE_DK, overwrite=False)
        # Gold accent every 4th pixel along outer edge
        if i % 4 == 0:
            _put(pix, x-1, y, GOLD)

    # 3×3 pink-gold gem cluster at grip center
    for gx in [34, 35, 36]:
        for gy in [37, 38, 39]:
            _put(pix, gx, gy, GEM_PK)

    # Bright tip glow dots
    for tx, ty in [UPPER_TIP, LOWER_TIP]:
        _put(pix, tx, ty, TIP_GLO)
        _put(pix, tx+1, ty, TIP_GLO)

    str_u = (UPPER_TIP[0]+1, UPPER_TIP[1]+1)
    str_l = (LOWER_TIP[0]+1, LOWER_TIP[1]-1)
    for x, y in _bresenham(str_u[0], str_u[1], str_l[0], str_l[1]):
        _put(pix, x, y, STR_COL, overwrite=False)

    return pix, str_u, str_l, STR_COL


BOW_MAKERS = {
    't7':  make_bow_t7,
    't8':  make_bow_t8,
    't9':  make_bow_t9,
    't10': make_bow_t10,
    't11': make_bow_t11,
}

BOW_DESCS = {
    't7':  'Two-tone split-limb recurve — dark espresso upper / warm chestnut lower, bronze grip band',
    't8':  'Crystal-tipped recurve — ice-blue gradient, 3px crystal diamonds at tips, gem at grip',
    't9':  'Dark angular compound — near-black body, aggressive tip flare, electric-blue inner highlight',
    't10': 'Nature-vine organic — S-curve 3-segment limbs, forest green, orange gem, leaf accents',
    't11': 'Celestial ornate compound — widest spread, royal purple, gold accents, pink-gold gem, glow tips',
}


def rotate_90cw(pix):
    """90° CW in screen coords: (x,y) → ((y-cy)+cx, -(x-cx)+cy)"""
    if not pix:
        return {}
    xs = [p[0] for p in pix]; ys = [p[1] for p in pix]
    cx, cy = float(np.mean(xs)), float(np.mean(ys))
    result = {}
    for (x, y), col in pix.items():
        nx = round((y - cy) + cx)
        ny = round(-(x - cx) + cy)
        if 0 <= nx < FW and 0 <= ny < FH and (nx, ny) not in result:
            result[(nx, ny)] = col
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  SWORD / AXE DESIGNS  (t7–t11)
#  Blade diagonal from grip(28,43) to tip(45,15). Crossguard at y≈36.
# ═══════════════════════════════════════════════════════════════════════════════

BLADE_PTS = _bresenham(28, 43, 45, 15)


def make_sword_t7():
    """
    Needle spear.
    Ultra-narrow 1px silver shaft, no blade width, small 2px crossguard prongs,
    tiny dark sphere pommel.  Slender and fast — low-tier feel but elegant reach.
    Inspired visual concept: narrow-bladed spear/pike from reference.
    """
    pix = {}
    SILVER = (170, 175, 192, 255)
    DARK   = ( 70,  75,  90, 255)
    GUARD  = (120, 125, 140, 255)
    POMMEL = ( 55,  60,  75, 255)
    GRIP   = ( 65,  40,  18, 255)

    # 1px needle blade
    for x, y in BLADE_PTS:
        _put(pix, x, y, SILVER)

    # Tiny 2px crossguard prongs at y=37, extending x±2
    for xi in [31, 32, 35, 36]:
        _put(pix, xi, 37, GUARD)

    # 2×2 pommel
    for gx, gy in [(26,44),(27,44),(26,45),(27,45)]:
        _put(pix, gx, gy, POMMEL)

    # Grip
    for x, y in _bresenham(28, 43, 33, 37):
        _put(pix, x, y, GRIP, overwrite=False)

    # Dark outline on non-grip blade
    for x, y in BLADE_PTS[3:]:
        _put(pix, x-1, y, DARK, overwrite=False)

    return pix


def make_sword_t8():
    """
    Rune longsword.
    4px ivory-cream blade with gold edge line, 3-pronged golden crossguard
    (center bar + upper/lower tips extending 2px), green gem channel at center.
    Inspired visual concept: gold ornate sword with elaborate crossguard from reference.
    """
    pix = {}
    IVORY   = (215, 210, 195, 255)
    IVHI    = (235, 232, 220, 255)
    GOLD    = (200, 170,  45, 255)
    GOLDDIM = (140, 110,  25, 255)
    RUNE    = ( 60, 195,  80, 255)
    POMMEL  = (190, 155,  40, 255)
    GRIP    = ( 85,  50,  18, 255)

    # 4px blade: center 2 pixels ivory, outer gold edge
    for x, y in BLADE_PTS:
        _put(pix, x, y, IVORY)
        _put(pix, x-1, y, GOLDDIM, overwrite=False)
        _put(pix, x+1, y, IVHI, overwrite=False)

    # Green gem channel every 3rd blade pixel (rune engravings)
    for i, (x, y) in enumerate(BLADE_PTS):
        if 2 <= i <= len(BLADE_PTS)-4 and i % 3 == 0:
            _put(pix, x, y, RUNE)

    # 3-pronged crossguard: 9px horizontal bar at y=36 + 2px prong tips
    for xi in range(28, 42):
        _put(pix, xi, 36, GOLD)
    for xi in [28, 29, 40, 41]:    # prong tips flare up/down
        _put(pix, xi, 35, GOLD)
        _put(pix, xi, 37, GOLD)

    # 2×2 gold pommel
    for gx, gy in [(25,44),(26,44),(25,45),(26,45)]:
        _put(pix, gx, gy, POMMEL)

    # Grip
    for x, y in _bresenham(28, 43, 33, 37):
        _put(pix, x, y, GRIP, overwrite=False)

    return pix


def make_sword_t9():
    """
    Flame blade.
    Wavy irregular blade achieved by alternating the center x ±1 every 3 steps.
    Copper-orange primary, dark amber edge, organic twisted crossguard (2 diagonal pixels each side).
    Inspired visual concept: twisted organic flame-style blade from reference.
    """
    pix = {}
    COPPER  = (180,  88,  28, 255)
    COPPHI  = (220, 130,  50, 255)
    DARK_A  = ( 75,  35,   8, 255)
    AMBER   = (210, 155,  40, 255)
    GRIP    = ( 50,  22,   5, 255)
    POMMEL  = (100,  55,  15, 255)

    # Wavy blade: alternate x offset creates organic look
    for i, (x, y) in enumerate(BLADE_PTS):
        wave = 1 if (i // 3) % 2 == 0 else 0
        _put(pix, x + wave, y, COPPER)
        _put(pix, x + wave - 1, y, DARK_A, overwrite=False)
        _put(pix, x + wave + 1, y, COPPHI, overwrite=False)

    # Organic twisted crossguard: diagonal pixels instead of horizontal bar
    # Left side: (29,38)→(31,36) (diagonal)
    for x, y in _bresenham(29, 38, 31, 36):
        _put(pix, x, y, AMBER)
    for x, y in _bresenham(31, 36, 29, 34):
        _put(pix, x, y, AMBER)
    # Right side: (36,37)→(39,36)
    for x, y in _bresenham(36, 37, 39, 34):
        _put(pix, x, y, AMBER)

    # 2×2 pommel (dark wood)
    for gx, gy in [(25,44),(26,44),(25,45),(26,45)]:
        _put(pix, gx, gy, POMMEL)

    for x, y in _bresenham(28, 43, 33, 37):
        _put(pix, x, y, GRIP, overwrite=False)

    return pix


def make_sword_t10():
    """
    Crystal greatsword.
    Wide 4px mint/teal blade — lighter mint center, pale inner shimmer, dark teal edge.
    Silver 7px crossguard with blue gem.  Elegant and wide.
    Inspired visual concept: mint/teal crystal greatsword from reference.
    """
    pix = {}
    MINT     = ( 75, 208, 198, 255)
    PALE     = (155, 232, 228, 255)
    TEAL_DK  = ( 22,  88,  98, 255)
    SILVER   = (180, 185, 192, 255)
    SILV_HI  = (210, 215, 220, 255)
    GEM_BLUE = ( 80, 158, 238, 255)
    POMMEL   = (160, 168, 176, 255)
    GRIP     = (112, 118, 128, 255)

    # 4px mint blade
    for x, y in BLADE_PTS:
        _put(pix, x, y, MINT)
        _put(pix, x-1, y, TEAL_DK, overwrite=False)
        _put(pix, x+1, y, PALE, overwrite=False)
        _put(pix, x+2, y, TEAL_DK, overwrite=False)

    # 7px silver crossguard at y=36, x=29-38
    for xi in range(29, 39):
        col = GEM_BLUE if abs(xi - 33) <= 1 else SILVER
        _put(pix, xi, 36, col)
    for xi in [29, 30, 37, 38]:    # tips flare
        _put(pix, xi, 35, SILV_HI)
        _put(pix, xi, 37, SILV_HI)

    # 2×2 pommel
    for gx, gy in [(25,44),(26,44),(25,45),(26,45)]:
        _put(pix, gx, gy, POMMEL)
    for x, y in _bresenham(28, 43, 33, 37):
        _put(pix, x, y, GRIP, overwrite=False)

    return pix


def make_sword_t11():
    """
    Warlord axe.
    Axe-head silhouette adapted to the sword diagonal.  Haft from (28,43)→(38,26),
    crescent axe head drawn with 2 bezier arcs — outer cutting edge and inner spine —
    filled with dark steel. Blue gem accent inset on the cheek.
    Inspired visual concept: battle axe with dark steel and blue gem from reference.
    """
    pix = {}
    STEEL_DK  = (40,  45,  62, 255)
    STEEL_MID = (70,  78, 100, 255)
    STEEL_HI  = (120, 130, 158, 255)
    BLUE_GEM  = ( 55, 130, 230, 255)
    GEM_GLOW  = (120, 185, 255, 255)
    GRIP      = ( 45,  28,  12, 255)
    GRIP_BAND = ( 70,  45,  18, 255)

    # Haft: dark wood from grip to axe neck
    haft_pts = _bresenham(28, 43, 38, 27)
    for x, y in haft_pts:
        _put(pix, x, y, GRIP)
    # 2px grip wrap bands at two points along haft
    for bx, by in haft_pts[2:4] + haft_pts[6:8]:
        _put(pix, bx-1, by, GRIP_BAND, overwrite=False)
        _put(pix, bx+1, by, GRIP_BAND, overwrite=False)

    # Axe head: two bezier arcs forming the crescent
    # Inner spine arc: tight concave sweep
    inner_pts = _bezier2((36, 28), (40, 22), (47, 17))
    # Outer cutting edge: wider convex sweep
    outer_pts = _bezier2((34, 30), (38, 16), (49, 13))

    for x, y in inner_pts:
        _put(pix, x, y, STEEL_MID)
    for x, y in outer_pts:
        _put(pix, x, y, STEEL_DK)

    # Fill crescent body: for each y in the head region, fill x between inner and outer
    for y in range(12, 32):
        row_inner = [x for x, ry in inner_pts if ry == y]
        row_outer = [x for x, ry in outer_pts if ry == y]
        if row_inner and row_outer:
            x_in  = min(row_inner)
            x_out = max(row_outer)
            for x in range(x_in, x_out + 1):
                _put(pix, x, y, STEEL_DK, overwrite=False)
                # Highlight the upper blade edge
                if y <= 16:
                    _put(pix, x, y, STEEL_HI, overwrite=False)

    # Blue gem inset on axe cheek at ~(40, 23)
    for gx, gy in [(39,22),(40,22),(39,23),(40,23)]:
        _put(pix, gx, gy, BLUE_GEM)
    for gx, gy in [(38,21),(41,21),(38,24),(41,24)]:
        _put(pix, gx, gy, GEM_GLOW, overwrite=False)

    # Highlight the outer edge of the cutting blade
    for x, y in outer_pts:
        _put(pix, x+1, y, STEEL_HI, overwrite=False)
        _put(pix, x, y-1, STEEL_HI, overwrite=False)

    # Axe poll (back of the head) at left of inner arc: connect to haft
    poll_pts = _bezier2((36, 28), (34, 26), (35, 23))
    for x, y in poll_pts:
        _put(pix, x, y, STEEL_MID, overwrite=False)

    return pix


SWORD_MAKERS = {
    't7':  make_sword_t7,
    't8':  make_sword_t8,
    't9':  make_sword_t9,
    't10': make_sword_t10,
    't11': make_sword_t11,
}

SWORD_DESCS = {
    't7':  'Needle spear — 1px silver shaft, small prong crossguard, sphere pommel',
    't8':  'Rune longsword — 4px ivory/gold blade, 3-pronged golden crossguard, green gem channel',
    't9':  'Flame blade — wavy copper-orange, twisted amber crossguard, organic flow',
    't10': 'Crystal greatsword — 4px mint/teal, silver 7px crossguard, blue gem accent',
    't11': 'Warlord axe — crescent axe head via dual bezier arcs, dark steel fill, blue gem cheek inset',
}

SWORD_TRAILS = {
    't7':  ((200, 210, 230, 255), (160, 170, 195, 255)),   # silver trail
    't8':  ((220, 200, 100, 255), (160, 140,  60, 255)),   # gold trail
    't9':  ((230, 130,  40, 255), (180,  80,  20, 255)),   # flame trail
    't10': ((100, 230, 220, 255), ( 50, 160, 160, 255)),   # teal trail
    't11': ((180, 190, 210, 255), (100, 115, 145, 255)),   # steel trail
}


# ═══════════════════════════════════════════════════════════════════════════════
#  STAFF DESIGNS  (t7–t11)
#  Shaft: bezier (27,42)→(38,17). build_sheet applies -45° before each frame.
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_shaft(pix, tier_col):
    """Draw staff shaft from grip (27,42) to neck (38,17) in tier color."""
    sd, sm, sl = tier_col
    shaft_pts = _bezier2((27, 42), (32, 29), (38, 17))
    n = max(1, len(shaft_pts)-1)
    for i, (x, y) in enumerate(shaft_pts):
        t = i / n
        col = sd if t < 0.3 else (sm if t < 0.7 else sl)
        _put(pix, x, y, col)
        _put(pix, x+1, y, sd, overwrite=False)


def make_staff_t7():
    """
    Solar disc staff.
    12-point sun disc at top: 1px circle ring in gold + 4 cardinal spike lines,
    bright yellow core. Warm teak shaft.
    """
    pix = {}
    GOLD  = (215, 165,  35, 255)
    GOLD2 = (240, 200,  60, 255)
    SUN_C = (255, 235, 100, 255)
    _draw_shaft(pix, ((50, 30, 8, 255), (88, 60, 22, 255), (110, 78, 32, 255)))

    cx, cy = 40, 14
    # Circle ring radius 4
    import math
    for deg in range(0, 360, 10):
        rx = round(cx + 4 * math.cos(math.radians(deg)))
        ry = round(cy + 4 * math.sin(math.radians(deg)))
        _put(pix, rx, ry, GOLD)
    # 4 cardinal spikes, 3px
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        for r in range(5, 8):
            _put(pix, cx + dx*r, cy + dy*r, GOLD2, overwrite=False)
    # Bright core 2×2
    for gx, gy in [(39,13),(40,13),(39,14),(40,14)]:
        _put(pix, gx, gy, SUN_C)
    return pix


def make_staff_t8():
    """
    Forked branch staff.
    Shaft splits into two curved branch arms at the top: left branch to (34,11),
    right branch to (45,11). Berry cluster (3 small red dots) at branch fork.
    Forest-green tones.
    """
    pix = {}
    GREEN_DK = (18,  52,  12, 255)
    GREEN_MID= (40,  90,  25, 255)
    GREEN_LT = (75, 148,  48, 255)
    BERRY    = (185,  38,  38, 255)
    BARK     = (60,  38,  12, 255)
    _draw_shaft(pix, (GREEN_DK, GREEN_MID, GREEN_LT))

    # Left branch: shaft top (38,17) → (33,10)
    for x, y in _bezier2((38, 17), (34, 14), (33, 10)):
        _put(pix, x, y, GREEN_MID)
        _put(pix, x-1, y, GREEN_DK, overwrite=False)
    # Right branch: (38,17) → (45,10)
    for x, y in _bezier2((38, 17), (42, 14), (45, 10)):
        _put(pix, x, y, GREEN_MID)
        _put(pix, x+1, y, GREEN_DK, overwrite=False)
    # Berry cluster at fork (38,17)
    for bx, by in [(37,16),(38,15),(39,16)]:
        _put(pix, bx, by, BERRY)
    return pix


def make_staff_t9():
    """
    Void crystal staff.
    Obsidian shaft, 4-pointed void star at top (40,14) in deep purple,
    near-black orb center with single bright core pixel.
    """
    pix = {}
    OBS_DK  = (12,   8,  22, 255)
    OBS_MID = (30,  20,  52, 255)
    OBS_LT  = (55,  35,  90, 255)
    VOID_P  = (48,  18,  80, 255)
    VOID_DK = (10,   4,  18, 255)
    STAR_C  = (165, 120, 240, 255)
    _draw_shaft(pix, (OBS_DK, OBS_MID, OBS_LT))

    cx, cy = 40, 14
    # 4-pointed star: diagonal spikes 3px each direction
    for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
        for r in range(1, 4):
            _put(pix, cx + dx*r, cy + dy*r, VOID_P)
    # Near-black orb center
    for gx, gy in [(39,13),(40,13),(39,14),(40,14)]:
        _put(pix, gx, gy, VOID_DK)
    # Single star-bright core
    _put(pix, 40, 13, STAR_C)
    return pix


def make_staff_t10():
    """
    Ruby claw staff.
    Three prong arcs (left/center/right) bracket a crimson 2×2 gem at top.
    Dark silver shaft with crimson accent band.
    """
    pix = {}
    SILV_DK = (55,  58,  68, 255)
    SILV_MID= (90,  96, 112, 255)
    SILV_LT = (140, 148, 165, 255)
    RUBY    = (200,  28,  48, 255)
    RUBY_HI = (240, 100, 115, 255)
    GOLD    = (200, 168,  42, 255)
    _draw_shaft(pix, (SILV_DK, SILV_MID, SILV_LT))

    # Crimson ruby gem 2×2 at center (39,13)
    for gx, gy in [(39,13),(40,13),(39,14),(40,14)]:
        _put(pix, gx, gy, RUBY)
    _put(pix, 39, 13, RUBY_HI)  # highlight facet

    # Three claw prongs: left, center, right — short curved arcs around gem
    for pts in [
        _bezier2((38, 15), (35, 13), (36, 10)),   # left claw
        _bezier2((39, 12), (39,  9), (40, 10)),   # center claw
        _bezier2((41, 15), (44, 13), (43, 10)),   # right claw
    ]:
        for x, y in pts:
            _put(pix, x, y, SILV_LT, overwrite=False)

    # Gold accent band on shaft at y=26
    for xi in range(33, 38):
        _put(pix, xi, 26, GOLD)
    return pix


def make_staff_t11():
    """
    Arcane prism staff.
    7-pixel hexagonal crystal cluster at top, each pixel a spectrum color
    (the prism rainbow: red→orange→yellow→green→cyan→blue→violet).
    Celestial silver shaft with purple accent band.
    """
    pix = {}
    SILV_DK = (42,  30,  62, 255)
    SILV_MID= (75,  55, 100, 255)
    SILV_LT = (115,  90, 148, 255)
    BAND_P  = (130,  60, 200, 255)
    _draw_shaft(pix, (SILV_DK, SILV_MID, SILV_LT))

    # Hexagonal pixel cluster at (40,13) center — 7 pixels
    spectrum = [
        (220,  40,  40, 255),   # red
        (225, 130,  30, 255),   # orange
        (230, 220,  40, 255),   # yellow
        ( 60, 195,  60, 255),   # green
        ( 40, 210, 210, 255),   # cyan
        ( 55, 100, 225, 255),   # blue
        (175,  50, 230, 255),   # violet
    ]
    hex_positions = [(40,13),(39,13),(41,13),(40,12),(40,14),(39,12),(41,14)]
    for (gx, gy), col in zip(hex_positions, spectrum):
        _put(pix, gx, gy, col)

    # 1px white glow ring around the cluster
    for gx, gy in hex_positions:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            _put(pix, gx+dx, gy+dy, (240,240,240,200), overwrite=False)

    # Purple band on shaft
    for xi in range(33, 38):
        _put(pix, xi, 28, BAND_P)
    return pix


STAFF_MAKERS = {
    't7':  make_staff_t7,
    't8':  make_staff_t8,
    't9':  make_staff_t9,
    't10': make_staff_t10,
    't11': make_staff_t11,
}

STAFF_DESCS = {
    't7':  'Solar disc — 12-pt gold sun ring + 4 cardinal spikes + bright yellow core',
    't8':  'Forked branch — twin bezier branch arms, berry cluster at fork, forest green',
    't9':  'Void crystal — obsidian shaft, 4-pt purple star, near-black orb + bright core',
    't10': 'Ruby claw — silver shaft, 3 prong arcs + 2×2 crimson gem with gold accent band',
    't11': 'Arcane prism — 7-px rainbow hexagonal crystal cluster, silver/purple shaft',
}

STAFF_TRAILS = {
    't7':  ((255, 230,  80, 255), (255, 180,  50, 200)),   # gold sun trail
    't8':  (( 80, 185,  55, 255), (160, 230, 120, 200)),   # green nature
    't9':  ((140,  60, 230, 255), ( 80,  20, 160, 180)),   # void purple
    't10': ((230,  45,  65, 255), (180,  20,  40, 200)),   # crimson ruby
    't11': ((200, 160, 255, 255), (120,  80, 210, 200)),   # prismatic
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
    protected_hashes = {}
    for w in ['bow_ranger', 'sword_warrior', 'staff_mage']:
        for t in ['t1','t2','t3','t4','t5','t6']:
            for g in ['m','f']:
                p = f'{OUT_DIR}{w}_{t}_{g}.png'
                if os.path.isfile(p):
                    protected_hashes[p] = md5(p)

    print("=== draw_inspired_weapons.py ===")
    print(f"Working dir: {os.getcwd()}")
    print(f"Generating tiers: {NEW_TIERS}")

    # ── Bows ──────────────────────────────────────────────────────────────────
    print("\n=== Bows (original drawn designs) ===")
    for tier in NEW_TIERS:
        maker = BOW_MAKERS[tier]
        diag_bow, str_t1, str_t2, str_col = maker()

        # Compute string tip positions after rotate_90cw
        xs_d = [p[0] for p in diag_bow]; ys_d = [p[1] for p in diag_bow]
        cx_d = float(np.mean(xs_d)); cy_d = float(np.mean(ys_d))
        def _rotate_tip(pt):
            return (round((pt[1] - cy_d) + cx_d), round(-(pt[0] - cx_d) + cy_d))
        tip1_f0 = _rotate_tip(str_t1)
        tip2_f0 = _rotate_tip(str_t2)

        f0 = rotate_90cw(diag_bow)
        bow_str_col = np.array(str_col, dtype=np.uint8)

        for g in ['m', 'f']:
            out = f'{OUT_DIR}bow_ranger_{tier}_{g}.png'
            skin_p = SKIN_PATHS[g] if os.path.isfile(SKIN_PATHS[g]) else None
            arm_p  = ARM_PATHS[g]  if os.path.isfile(ARM_PATHS[g])  else None
            build_sheet(
                f0, SRC_PATH, out,
                weapon_type='bow',
                trail_c=(220, 200, 140, 255),
                trail_e=(180, 160, 100, 255),
                skin_mask_path=skin_p,
                arm_mask_path=arm_p,
                string_tips=(tip1_f0, tip2_f0),
                bow_str_col=bow_str_col,
            )
        print(f"  {tier}: {BOW_DESCS[tier]}")

    # ── Swords ────────────────────────────────────────────────────────────────
    print("\n=== Swords (original drawn designs) ===")
    for tier in NEW_TIERS:
        f0 = SWORD_MAKERS[tier]()
        tc, te = SWORD_TRAILS.get(tier, (WHITE_TRAIL, LAV_TRAIL))
        for g in ['m', 'f']:
            out = f'{OUT_DIR}sword_warrior_{tier}_{g}.png'
            build_sheet(f0, SRC_PATH, out, weapon_type='sword', trail_c=tc, trail_e=te)
        print(f"  {tier}: {SWORD_DESCS[tier]}")

    # ── Staffs ────────────────────────────────────────────────────────────────
    print("\n=== Staffs (original drawn designs) ===")
    for tier in NEW_TIERS:
        f0 = STAFF_MAKERS[tier]()
        tc, te = STAFF_TRAILS[tier]
        for g in ['m', 'f']:
            out = f'{OUT_DIR}staff_mage_{tier}_{g}.png'
            build_sheet(f0, SRC_PATH, out, weapon_type='staff', trail_c=tc, trail_e=te)
        print(f"  {tier}: {STAFF_DESCS[tier]}")

    # ── Verify protected files untouched ──────────────────────────────────────
    print("\n=== Protected file verification (t1–t6) ===")
    all_ok = True
    for path, orig in protected_hashes.items():
        curr = md5(path)
        if curr != orig:
            print(f"  MODIFIED: {os.path.basename(path)} !!!")
            all_ok = False
    if all_ok:
        print(f"  All {len(protected_hashes)} protected files unchanged ✓")

    print("\nDone. New files written to t7–t11.")


if __name__ == '__main__':
    main()
