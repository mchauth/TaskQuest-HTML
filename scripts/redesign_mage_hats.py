#!/usr/bin/env python3
"""Redesign mage wizard hats (helmet_mage1-6 + helmet_mage1_f) — v4 "worn hat".

Reference: IMG_8154.jpeg (slouchy purple wizard hat, drooping brim, plus-symbol
decorations, soft fabric creases).

Changes vs v3 (rebuild_class_hats.py):
  Brim   : width HW+4 = 13 (2px overhang each side); leftmost/rightmost 2 px droop
           1 row lower; 1px shadow row beneath the drooped pixels; brim row itself
           is mid tone (fabric edge), drooped sides darker.
  Crown  : same cone heights (t1=5..t6=10) but tip leans 1px RIGHT of center;
           base row 1px wider than taper (shoulder bulge, extra px on the LEFT);
           t4+ get a subtle S-curve on the left edge; diagonal crease line
           (V*0.60) from tip to left shoulder; left face V*0.75, right face
           V*1.15; 3 diagonal sheen pixels (L) inside the right edge.
  Symbol : one per tier on the front face — t1 tiny star, t2 plus/cross,
           t3 crescent, t4 gold diamond, t5 gold rune, t6 elaborate gold/silver
           sigil.  Symbol pixels clamped to the cone fill.
  Keeps  : t4/t6 tip star, t5 sparkles, t6 gold brim rim (now on drooped px).

Run from repo root, then:
  python3 scripts/sprite_shade.py sprites/preview_assets/char/helmet_mageN.png
  python3 scripts/sprite_qa.py sprites/preview_assets/char/helmet_mageN.png --y-min 2
"""
import os
import colorsys
import numpy as np
from PIL import Image

CH = "sprites/preview_assets/char"
W, H, COLS, NFR = 80, 64, 10, 70
HW = 9  # constant skull width

MAGE_HAT = {
    1: dict(D=(50, 25, 80),  M=(105, 43, 186), L=(131, 64, 212), A=(192, 192, 192), cone=5),
    2: dict(D=(60, 16, 102), M=(90, 24, 154),  L=(123, 47, 196), A=(192, 192, 192), cone=6),
    3: dict(D=(29, 17, 69),  M=(45, 27, 105),  L=(70, 48, 155),  A=(192, 192, 192), cone=7),
    4: dict(D=(16, 16, 62),  M=(26, 26, 94),   L=(46, 46, 143),  A=(255, 215, 0),
            S=(255, 240, 160), cone=8, tip_star=True),
    5: dict(D=(8, 8, 28),    M=(13, 13, 43),   L=(58, 40, 110),  A=(255, 215, 0),
            S=(226, 226, 255), cone=9, sparkles=True),
    6: dict(D=(5, 5, 16),    M=(10, 10, 26),   L=(93, 58, 150),  A=(240, 230, 140),
            S=(255, 240, 160), cone=10, gold_rim=True, tip_star=True),
}

SILVER = (220, 220, 235)


def scale_v(rgb, factor):
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    v = min(1.0, max(0.0, v * factor))
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r2 * 255)), int(round(g2 * 255)), int(round(b2 * 255)))


# ── Skull-dome head tracking (same as rebuild_class_hats.py) ─────────────────

def runs_of(xs):
    out = []
    if not xs:
        return out
    s = p = xs[0]
    for x in xs[1:]:
        if x == p + 1:
            p = x
        else:
            out.append((s, p)); s = p = x
    out.append((s, p))
    return out


def make_head_dome_fn(skin_arr):
    def head_dome(fi):
        c, r = fi % COLS, fi // COLS
        zone = skin_arr[r*H:(r+1)*H, c*W:(c+1)*W][:32, :, 3] > 0
        op = np.argwhere(zone)
        if len(op) == 0:
            return None
        ymin = int(op[:, 0].min())
        top = op[op[:, 0] <= ymin + 2]
        clusters = runs_of(sorted(set(top[:, 1].tolist())))
        chosen = None
        for a, b in clusters:
            for y in range(ymin, min(ymin + 6, 32)):
                xs = [x for x in range(max(0, a-2), min(W, b+3)) if zone[y, x]]
                if xs and max(e - s + 1 for s, e in runs_of(xs)) >= 7:
                    chosen = (a, b); break
            if chosen:
                break
        if chosen is None:
            chosen = clusters[0]
        a, b = chosen
        hymin = min(y for y in range(32) for x in range(a, b+1) if zone[y, x])
        def rowpix(y):
            return [x for s2, e in runs_of([x for x in range(W) if zone[y, x]])
                    if e >= a and s2 <= b for x in range(s2, e+1)]
        xs2 = [x for y in range(hymin, min(hymin + 2, 32)) for x in rowpix(y)]
        return hymin, int(round(sum(xs2) / len(xs2)))
    return head_dome


# ── Tier symbols: list of (dx, dy) offsets from (cx, sym_cy), plus color ─────

def tier_symbol(tier, P):
    """Return (pixels, color_map) — pixels as {(dx,dy): rgb}."""
    A = P.get('A', SILVER)
    if tier == 1:                                   # tiny 3px star (sparkle)
        return {(0, -1): (215, 205, 245), (0, 0): (252, 248, 255),
                (0, 1): (215, 205, 245)}
    if tier == 2:                                   # 5px plus/cross (as reference)
        c = (240, 232, 255)
        return {(0, 0): (252, 248, 255), (-1, 0): c, (1, 0): c,
                (0, -1): c, (0, 1): c}
    if tier == 3:                                   # 3x5 crescent, open right
        c = (232, 224, 252)
        return {(0, -2): c, (-1, -1): c, (-1, 0): c, (-1, 1): c, (0, 2): c}
    if tier == 4:                                   # 5x5 gold diamond outline
        g = A
        return {(0, -2): g, (-1, -1): g, (1, -1): g, (-2, 0): g, (2, 0): g,
                (-1, 1): g, (1, 1): g, (0, 2): g}
    if tier == 5:                                   # 7px gold rune (Algiz-like)
        g = A
        px = {(0, dy): g for dy in range(-3, 4)}    # vertical staff, 7 tall
        px[(-1, -2)] = g; px[(1, -2)] = g           # raised arms
        px[(-1, 3)] = g; px[(1, 3)] = g             # splayed feet
        return px
    # tier 6: 9px elaborate sigil — staff + double cross arms + silver crown px
    g, s = P['A'], SILVER
    px = {(0, dy): g for dy in range(-4, 5)}        # staff, 9 tall
    px[(-1, 2)] = g; px[(1, 2)] = g                 # lower cross arm
    px[(-1, -1)] = g; px[(1, -1)] = g               # upper cross arm
    px[(0, -4)] = s; px[(0, 0)] = s                 # silver crown + heart
    return px


# ── Hat builder ──────────────────────────────────────────────────────────────

def _finish(fill, over, no_outline_below):
    px = {}
    for (x, y) in set(fill):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in fill and n[1] <= no_outline_below:
                px[n] = (0, 0, 0)
    px.update(fill)
    px.update(over)
    return px


def mage_hat_v4(tier, head_top, cx):
    P = MAGE_HAT[tier]
    M = P['M']
    left_c  = scale_v(M, 0.75)   # deep shadow, left face
    right_c = scale_v(M, 1.15)   # lit right face
    crease_c = scale_v(M, 0.60)  # fabric fold
    fill, over = {}, {}

    # ── Brim: 13 wide, drooping sides, shadow under the droop ────────────────
    brim_y = head_top
    bw = HW + 4
    bx0 = cx - bw // 2
    droop_c  = scale_v(M, 0.72)
    shadow_c = scale_v(M, 0.55)
    for k in range(2, bw - 2):                     # center section, anchor row
        fill[(bx0 + k, brim_y)] = M
    for k in (0, 1, bw - 2, bw - 1):               # sides hang 1px lower
        fill[(bx0 + k, brim_y + 1)] = droop_c
        fill[(bx0 + k, brim_y + 2)] = shadow_c     # brim curling under
    # brighten right half of brim edge (light from upper-right)
    for k in range(bw // 2 + 1, bw - 2):
        fill[(bx0 + k, brim_y)] = scale_v(M, 1.10)

    # ── Crown: slouchy cone with lean, bulge, S-curve ────────────────────────
    Hc = P['cone']
    row_geom = {}                                  # i -> (rx0, wdt, y)
    for i in range(Hc):
        y = (head_top - 1) - i
        t = i / (Hc - 1) if Hc > 1 else 0
        wdt = max(1, int(round(HW * (1 - t) + 1 * t)))
        if i == 0:
            wdt += 1                               # shoulder bulge (extra px left)
        shift = int(round(1 * t))                  # tip leans 1px right
        rx0 = cx - wdt // 2 + shift
        if Hc >= 8 and 0.30 <= t < 0.55:           # t4+: S-curve, left edge out
            rx0 -= 1
            wdt += 1
        row_geom[i] = (rx0, wdt, y)
        for x in range(rx0, rx0 + wdt):
            rel = (x - rx0) / max(1, wdt - 1)
            fill[(x, y)] = (left_c if rel < 0.35 else
                            right_c if rel > 0.65 else M)

    tip_y = head_top - Hc
    rx0_t, wdt_t, _ = row_geom[Hc - 1]
    tip_x = rx0_t + wdt_t // 2

    # crease line: diagonal, tip -> left shoulder, on the left face
    x_base, x_top = cx - 3, tip_x - 1
    for i in range(Hc - 1):
        t = i / (Hc - 1)
        cxx = int(round(x_base + (x_top - x_base) * t))
        rx0, wdt, y = row_geom[i]
        if rx0 <= cxx < rx0 + wdt and (cxx - rx0) / max(1, wdt - 1) < 0.55:
            fill[(cxx, y)] = crease_c

    # sheen: 3 diagonal highlight px just inside the right edge, mid-cone
    for i in (Hc // 2 - 1, Hc // 2, Hc // 2 + 1):
        if 0 <= i < Hc - 1:
            rx0, wdt, y = row_geom[i]
            if wdt >= 3:
                fill[(rx0 + wdt - 2, y)] = P['L']

    # ── Tier symbol on the front face (clamped to cone fill) ─────────────────
    sym_cy = {1: head_top - 3, 2: head_top - 3, 3: head_top - 4,
              4: head_top - 3, 5: head_top - 4, 6: head_top - 5}[tier]
    for (dx, dy), col in tier_symbol(tier, P).items():
        p = (cx + dx, sym_cy + dy)
        if p in fill and p[1] <= head_top - 1:
            over[p] = col

    # ── Flair (kept from v3) ─────────────────────────────────────────────────
    if P.get('tip_star'):
        over[(tip_x, tip_y)] = P['S']
    if P.get('sparkles'):
        over[(tip_x - 2, tip_y + 1)] = P['S']
        over[(tip_x + 2, tip_y + 1)] = P['S']
    if P.get('gold_rim'):                          # t6: gold on drooped rim px
        for k in (0, 1, bw - 2, bw - 1):
            over[(bx0 + k, brim_y + 1)] = P['A']

    return _finish(fill, over, no_outline_below=head_top - 1)


# ── Sheet composition ────────────────────────────────────────────────────────

def get_active_frames(hat_path):
    a = np.array(Image.open(hat_path).convert('RGBA'))
    return [fi for fi in range(NFR)
            if (a[(fi//COLS)*H:(fi//COLS+1)*H, (fi%COLS)*W:(fi%COLS+1)*W, 3] > 0).any()]


def build_sheet(tier, frames, head_dome_fn):
    sheet = np.zeros((H * 7, W * COLS, 4), np.uint8)
    for fi in frames:
        d = head_dome_fn(fi)
        if d is None:
            continue
        head_top, hcx = d
        gx, gy = (fi % COLS) * W, (fi // COLS) * H
        for (x, y), rgb in mage_hat_v4(tier, head_top, hcx).items():
            if 0 <= x < W and 0 <= y < H:
                sheet[gy + y, gx + x] = (*rgb, 255)
    return sheet


def main():
    skin_m = np.array(Image.open(f"{CH}/skin_m1.png").convert('RGBA'))
    skin_f = np.array(Image.open(f"{CH}/skin_f1.png").convert('RGBA'))
    head_dome_m = make_head_dome_fn(skin_m)
    head_dome_f = make_head_dome_fn(skin_f)

    frames_m = get_active_frames(f"{CH}/helmet_mage1.png")
    for tier in range(1, 7):
        sheet = build_sheet(tier, frames_m, head_dome_m)
        Image.fromarray(sheet).save(f"{CH}/helmet_mage{tier}.png")
        print(f"wrote helmet_mage{tier}.png ({len(frames_m)} frames)")

    t1f = f"{CH}/helmet_mage1_f.png"
    if os.path.exists(t1f):
        frames_f = get_active_frames(t1f)
        Image.fromarray(build_sheet(1, frames_f, head_dome_f)).save(t1f)
        print(f"wrote helmet_mage1_f.png ({len(frames_f)} frames)")


if __name__ == '__main__':
    main()
