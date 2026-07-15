#!/usr/bin/env python3
"""Redesign mage & ranger armor tiers 2-6 from scratch (male + female).

Scraps the recolor-of-tier-1 approach entirely. Every garment is rebuilt:

  1. take ONLY the alpha mask of the tier-1 sheet (the clean warrior-template
     silhouette; frame-0 shirt 135px / f 91px, pants 98px / f leggings 252px,
     boots 46px / f 59px) — no source colors survive
  2. flood the mask with the tier's flat primary color
  3. paint hand-authored structural details pixel-by-pixel, anchored to
     per-frame anatomy (collar = top row, chest center = (xc, y0+5),
     hem = bottom rows, cuffs = sleeve-end columns) so the frame-0 authored
     design tracks every animation frame
  4. shade with sprite_shade (shirts: ADJ_MIN=-0.20 ADJ_MAX=0.25,
     BELL_WIDTH=0.7; pants/boots: defaults). The flat base means the
     band-smoothing pass has nothing to smear — no random splotches, just
     the smooth cosine gradient.

Tier identity comes from STRUCTURE, not palette swaps:

  mage   2 Adept Robes           gold chest clasp, dark hem
         3 Conjurer's Vestment   shoulder line, silver runic circle,
                                 lighter under-robe cuffs
         4 Arcane Mantle         double-breasted gold buttons, epaulets,
                                 azure collar + cuff lining
         5 Archmage's Robes      gold trim columns, octagonal medallion,
                                 wide dark collar w/ gold edge, purple cuffs
         6 Void Archmage         asymmetric purple stripe, left pauldron,
                                 pale-gold rune glyph, dark-gold trim
  ranger 2 Tracker's Leathers    diagonal chest strap, quiver loop
         3 Pathfinder Armor      squared chest plate + corner rivets
         4 Warden's Coat         scale rows on shoulders, leather center
                                 panel, bronze buckle
         5 Shadow Ranger         raised collar + fur trim, crossed straps
         6 Shadowstalker         split panels, bronze shoulder guard +
                                 stripes, emerald gem

Pants: tier primary + seam/edge pass. Boots: tier family color + accent cuff.

Run from repo root:  python3 scripts/redesign_tiers_v3.py [mage|ranger]
QA: sprite_qa.py (shirts), --y-max 62 (pants m), --y-max 63 (pants f, boots)
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_shade
from gen_mage_ranger_tiers import hx, frames, load, shade, pants_details, CHAR

FW, FH = 80, 64

# ── Tier palettes ────────────────────────────────────────────────────────────

BASE = {
    ('mage', 2): '#4A0080', ('mage', 3): '#2A1555', ('mage', 4): '#1A1040',
    ('mage', 5): '#0D0820', ('mage', 6): '#050010',
    ('ranger', 2): '#2D5A27', ('ranger', 3): '#1A3D15', ('ranger', 4): '#122B0E',
    ('ranger', 5): '#0A1E08', ('ranger', 6): '#040C03',
}
ACCENT = {
    ('mage', 2): '#C0C0C0', ('mage', 3): '#C0C0C0', ('mage', 4): '#FFD700',
    ('mage', 5): '#FFD700', ('mage', 6): '#C0A000',
    ('ranger', 2): '#3B2A1A', ('ranger', 3): '#C3B091', ('ranger', 4): '#B87333',
    ('ranger', 5): '#C8C0A8', ('ranger', 6): '#8B4513',
}

GOLD = '#FFD700'
PALE_GOLD = '#E8D48A'
AZURE = '#4169E1'
SILVER = '#C0C0C0'
BRONZE = '#B87333'
DARK_BRONZE = '#8B4513'
EMERALD = '#50C878'
VOID_PURPLE = '#9B59B6'
DEEP_PURPLE = '#4A0080'
UNDER_ROBE = '#8A70D6'
FUR = '#C8C0A8'
PLATE_GREEN = '#0F2A0C'
LEATHER_BROWN = '#3A331C'
PANEL_GREEN = '#1A4A14'


# ── Primitives ───────────────────────────────────────────────────────────────

def put(fr, paint, y, x, hexs):
    if 0 <= y < FH and 0 <= x < FW and paint[y, x]:
        fr[y, x, :3] = hx(hexs)
        fr[y, x, 3] = 255


def mul(fr, paint, y, x, k):
    if 0 <= y < FH and 0 <= x < FW and paint[y, x]:
        fr[y, x, :3] = np.clip(fr[y, x, :3].astype(np.float32) * k, 3, 255
                               ).astype(np.uint8)


def anatomy(mask):
    """Per-frame anchors: bbox, chest center, per-column top/bot, arm runs."""
    ys, xs = np.where(mask)
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    cols = [int(x) for x in np.unique(xs)]
    top = {x: int(ys[xs == x].min()) for x in cols}
    bot = {x: int(ys[xs == x].max()) for x in cols}
    ychest = min(y0 + 3, y1)
    row = np.flatnonzero(mask[ychest])
    xc = int(round(row.mean())) if len(row) else (x0 + x1) // 2
    arms = [x for x in cols if bot[x] <= y1 - 3]      # sleeve-end columns
    return dict(y0=y0, y1=y1, x0=x0, x1=x1, xc=xc, cols=cols,
                top=top, bot=bot, arms=arms)


def cuffs(fr, paint, an, hexs, rows=2):
    """Paint the bottom `rows` pixels of every sleeve-end column."""
    for x in an['arms']:
        for dy in range(rows):
            put(fr, paint, an['bot'][x] - dy, x, hexs)


def collar_cols(an, lo=0.28, hi=0.72):
    """Columns whose silhouette top is the collar (center span of top rows)."""
    x0, x1, top, y0 = an['x0'], an['x1'], an['top'], an['y0']
    w = max(1, x1 - x0)
    return [x for x in an['cols']
            if lo <= (x - x0) / w <= hi and top[x] <= y0 + 1]


# ── Mage shirt structures ────────────────────────────────────────────────────

def mage_shirt(fr, paint, an, tier):
    y0, y1, xc, x0, x1 = an['y0'], an['y1'], an['xc'], an['x0'], an['x1']
    top, bot = an['top'], an['bot']

    if tier == 2:                                  # Adept Robes
        for y in (y1 - 1, y1):                     # darker hem
            for x in an['cols']:
                if bot[x] >= y:
                    mul(fr, paint, y, x, 0.62)
        for dy in (-1, 0, 1):                      # 3x3 gold clasp, chest center
            for dx in (-1, 0, 1):
                put(fr, paint, y0 + 5 + dy, xc + dx, GOLD)

    elif tier == 3:                                # Conjurer's Vestment
        for x in an['cols']:                       # 2px shoulder line
            if top[x] <= y0 + 1:
                mul(fr, paint, y0 + 2, x, 0.58)
                mul(fr, paint, y0 + 3, x, 0.72)
        cy = y0 + 6                                # silver runic circle (d=5)
        ring = [(-2, -1), (-2, 0), (-2, 1), (-1, -2), (-1, 2), (0, -2), (0, 2),
                (1, -2), (1, 2), (2, -1), (2, 0), (2, 1)]
        for dy, dx in ring:
            put(fr, paint, cy + dy, xc + dx, SILVER)
        cuffs(fr, paint, an, UNDER_ROBE)           # lighter under-robe at cuffs

    elif tier == 4:                                # Arcane Mantle
        for x in collar_cols(an):                  # azure collar stripe
            put(fr, paint, top[x], x, AZURE)
            put(fr, paint, top[x] + 1, x, AZURE)
        for side in (x0, x1 - 2):                  # epaulet shoulder pads
            for x in range(side, side + 3):
                for y in (y0 + 1, y0 + 2):
                    if x in top and top[x] <= y:
                        mul(fr, paint, y, x, 0.52)
        for dy in (3, 6, 9):                       # double-breasted gold buttons
            put(fr, paint, y0 + dy, xc - 1, GOLD)
            put(fr, paint, y0 + dy, xc + 2, GOLD)
        cuffs(fr, paint, an, AZURE)                # azure inner lining

    elif tier == 5:                                # Archmage's Robes
        for x in an['cols']:                       # dramatic wide collar
            if top[x] <= y0 + 1:
                mul(fr, paint, top[x], x, 0.45)
                mul(fr, paint, top[x] + 1, x, 0.45)
        for x in collar_cols(an, 0.22, 0.78):      # 1px gold collar edge
            put(fr, paint, y0 + 2, x, GOLD)
        for x in (xc - 3, xc + 3):                 # gold trim columns, full height
            if x in top:
                for y in range(y0 + 3, bot[x] + 1):
                    put(fr, paint, y, x, GOLD)
        cy = y0 + 6                                # octagonal gold medallion
        ring = [(-2, -1), (-2, 0), (-2, 1), (-1, -2), (-1, 2), (0, -2), (0, 2),
                (1, -2), (1, 2), (2, -1), (2, 0), (2, 1)]
        for dy in (-1, 0, 1):                      # near-black fill first
            for dx in (-1, 0, 1):
                put(fr, paint, cy + dy, xc + dx, '#030303')
        for dy, dx in ring:
            put(fr, paint, cy + dy, xc + dx, GOLD)
        cuffs(fr, paint, an, DEEP_PURPLE)          # deep purple inner lining

    else:                                          # 6: Void Archmage Vestments
        for x in range(xc + 1, xc + 5):            # bright purple right stripe
            if x in top:
                for y in range(top[x], bot[x] + 1):
                    put(fr, paint, y, x, VOID_PURPLE)
        if xc + 1 in top:                          # dashed dark-gold trim on the
            for y in range(top[xc + 1], bot[xc + 1] + 1, 2):   # stripe's edge
                put(fr, paint, y, xc + 1, '#C0A000')
        for x in range(x0, x0 + 4):                # left shoulder armor block
            for y in range(y0 + 1, y0 + 5):
                if (x, y) == (x0, y0 + 1):         # rounded corner
                    continue
                if x in top and top[x] <= y:
                    put(fr, paint, y, x, '#2A2048')
        for x in range(x0, x0 + 4):                # dark-gold block edge
            if x in top and top[x] <= y0 + 5:
                put(fr, paint, y0 + 5, x, '#C0A000')
        gx, gy = xc - 2, y0 + 4                    # pale-gold rune glyph (3x5)
        glyph = [(0, 1), (1, 0), (1, 2), (2, 1), (3, 1), (4, 0), (4, 1), (4, 2)]
        for dy, dx in glyph:
            put(fr, paint, gy + dy, gx + dx, PALE_GOLD)


# ── Ranger shirt structures ──────────────────────────────────────────────────

def ranger_shirt(fr, paint, an, tier):
    y0, y1, xc, x0, x1 = an['y0'], an['y1'], an['xc'], an['x0'], an['x1']
    top, bot = an['top'], an['bot']

    if tier == 2:                                  # Tracker's Leathers
        ya, yb = y0 + 1, y1 - 2                    # diagonal strap, 2px wide
        xa, xb = xc - 4, xc + 3                    # left shoulder -> right hip
        for y in range(ya, yb + 1):
            t = (y - ya) / max(1, yb - ya)
            x = int(round(xa + t * (xb - xa)))
            mul(fr, paint, y, x, 0.42)
            mul(fr, paint, y, x + 1, 0.42)
        for dy, dx in ((4, -1), (5, 0), (6, 0)):   # quiver loop arc, back-right
            mul(fr, paint, y0 + dy, x1 - 1 + dx, 0.40)

    elif tier == 3:                                # Pathfinder Armor
        px0, px1 = xc - 3, xc + 3                  # squared chest plate overlay
        py0, py1 = y0 + 3, y0 + 9
        for y in range(py0, py1 + 1):
            for x in range(px0, px1 + 1):
                if y in (py0, py1) or x in (px0, px1):
                    put(fr, paint, y, x, '#040A03')    # near-black plate border
                else:                                  # (outline-class: stays
                    put(fr, paint, y, x, PLATE_GREEN)  # crisp through shading)
        for y, x in ((py0, px0), (py0, px1), (py1, px0), (py1, px1)):
            put(fr, paint, y, x, ACCENT[('ranger', 3)])   # corner rivets

    elif tier == 4:                                # Warden's Coat
        for side in (x0, x1 - 3):                  # shoulder scale rows
            for x in range(side, side + 4):
                for y in range(y0 + 1, y0 + 5):
                    if x in top and top[x] <= y:
                        mul(fr, paint, y, x, 1.45 if (y - y0) % 2 else 0.62)
        for x in range(xc - 2, xc + 3):            # leather center panel
            if x in top:
                for y in range(y0 + 3, min(y1 - 1, bot[x]) + 1):
                    put(fr, paint, y, x, LEATHER_BROWN)
        for dy in (6, 7, 8):                       # bronze buckle 3x3+tongue
            for dx in (-1, 0, 1):
                put(fr, paint, y0 + dy, xc + dx, BRONZE)
        put(fr, paint, y0 + 7, xc, '#3A2410')      # buckle center

    elif tier == 5:                                # Shadow Ranger
        for x in an['cols']:                       # raised dark collar band
            if top[x] <= y0 + 1:
                mul(fr, paint, top[x], x, 0.42)
                mul(fr, paint, top[x] + 1, x, 0.42)
                mul(fr, paint, top[x] + 2, x, 0.42)
        for x in an['cols']:                       # fur trim along collar edge
            if x % 2 == 0 and top[x] <= y0 + 2:
                put(fr, paint, y0 + 3, x, FUR)
        ya, yb = y0 + 4, y0 + 10                   # crossed chest straps (X):
        for y in range(ya, yb + 1):                # dark brown leather so they
            t = (y - ya) / max(1, yb - ya)         # read against the green
            xl = int(round(xc - 3 + t * 6))
            xr = int(round(xc + 3 - t * 6))
            put(fr, paint, y, xl, '#241708')
            put(fr, paint, y, xr, '#241708')
        put(fr, paint, (ya + yb) // 2, xc, SILVER)  # strap cross clasp

    else:                                          # 6: Shadowstalker
        for x in an['cols']:                       # dark green right panel
            if x >= xc + 1:
                for y in range(top[x], bot[x] + 1):
                    put(fr, paint, y, x, PANEL_GREEN)
        for x in range(x1 - 3, x1 + 1):            # bronze shoulder guard
            for y in range(y0 + 1, y0 + 5):
                if (x, y) == (x1, y0 + 1):         # rounded corner
                    continue
                if x in top and top[x] <= y:
                    put(fr, paint, y, x, DARK_BRONZE)
        for dy in (5, 7, 9):                       # bronze accent stripes
            for x in range(xc + 1, xc + 5):
                put(fr, paint, y0 + dy, x, DARK_BRONZE)
        for dy in (-2, -1, 0, 1, 2):               # emerald gem, dark outline
            for dx in (-2, -1, 0, 1, 2):
                cheb = max(abs(dy), abs(dx))
                if cheb == 2 and abs(dy) + abs(dx) == 4:
                    continue                       # rounded outline corners
                col = EMERALD if cheb <= 1 else '#030803'
                put(fr, paint, y0 + 6 + dy, xc + dx, col)


# ── Sheet builders ───────────────────────────────────────────────────────────

def rebuild(src_name, base_hex, detail=None, v_scale=1.0):
    """Blank sheet from src alpha mask, flat fill, optional detail pass."""
    src = load(src_name)
    out = np.zeros_like(src)
    mask_all = src[..., 3] > 10
    rgb = tuple(min(255, int(round(c * v_scale))) for c in hx(base_hex))
    out[mask_all] = (*rgb, 255)
    for sy, sx in frames():
        fr = out[sy, sx]
        m = fr[..., 3] > 10
        if not m.any():
            continue
        if detail is not None:
            detail(fr, m, anatomy(m))
    return out


def boots_trim(fr, paint, an, acc):
    """1px accent cuff along the top edge of each boot column."""
    for x in an['cols']:
        put(fr, paint, an['top'][x], x, acc)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    made = []
    for cls in ('mage', 'ranger'):
        if only and cls != only:
            continue
        author = mage_shirt if cls == 'mage' else ranger_shirt
        for tier in range(2, 7):
            base = BASE[(cls, tier)]
            acc = ACCENT[(cls, tier)]
            for suf in ('', '_f'):
                # shirt: flat fill + authored structure + spec shading
                arr = rebuild('shirt_%s1%s.png' % (cls, suf), base,
                              detail=lambda fr, m, an: author(fr, m, an, tier))
                arr = shade(arr, adj_min=-0.20, adj_max=0.25)
                name = 'shirt_%s%d%s.png' % (cls, tier, suf)
                Image.fromarray(arr).save(CHAR + name)
                made.append(name)
                # pants: primary color + seams/edge darkening + default shade
                arr = rebuild('pants_%s1%s.png' % (cls, suf), base)
                pants_details(arr)
                arr = shade(arr)
                name = 'pants_%s%d%s.png' % (cls, tier, suf)
                Image.fromarray(arr).save(CHAR + name)
                made.append(name)
                # boots: family color + accent cuff trim + default shade
                arr = rebuild('boots_%s1%s.png' % (cls, suf), base,
                              detail=lambda fr, m, an: boots_trim(fr, m, an, acc),
                              v_scale=0.85)
                arr = shade(arr)
                name = 'boots_%s%d%s.png' % (cls, tier, suf)
                Image.fromarray(arr).save(CHAR + name)
                made.append(name)
            print('tier %s%d done' % (cls, tier))
    print('%d sheets generated' % len(made))


if __name__ == '__main__':
    main()
