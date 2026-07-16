#!/usr/bin/env python3
"""Rebuild mage/ranger tier 1-6 helmets FROM SCRATCH with LOWERED brim.

Reference image shows the hat brim sitting at EYE/FOREHEAD level, not at the
skull top.  The previous version placed the brim at head_top (y=21 in frame 0),
leaving the entire forehead exposed — the hat read as perched on the crown.

NEW placement (eye_row = head_top + 5, detected in frame 0 at y=26):
  brim_bottom = head_top + 4   (just above eyes at head_top+5)
  brim rows   = head_top+2 .. head_top+4  (3 rows)
  hatband     = head_top + 1
  cone base   = head_top (rises upward from there)
  lining      = head_top .. head_top+4  (blocks hair showing through)

This places the brim 2 rows lower than the previous version, overlapping the
forehead visually so the hat looks WORN rather than balanced on top.

Male skin (skin_m1.png):   head_top=21, eye_row=26
Female skin (skin_f1.png): head_top=22, eye_row=27

Skull-dome head tracking (same HANDOFF.md method as propagate_rare_helmets.py):
  1. head zone = opaque skin pixels y<32 per frame
  2. top 3 rows -> contiguous x clusters, scanned left to right
  3. accept the first cluster that widens to >=7px within 6 rows
  4. re-anchor at that cluster's own ymin (head_top), centroid x (head_cx)

Hat width fixed to frame-0 skull width (9px) to prevent arm-raise flicker.

Run from repo root, then:
  python3 scripts/sprite_shade.py sprites/preview_assets/char/helmet_*.png
  python3 scripts/sprite_qa.py sprites/preview_assets/char/helmet_*.png --y-min 2
"""
import os
import colorsys
import numpy as np
from PIL import Image

CH = "sprites/preview_assets/char"
W, H, COLS, NFR = 80, 64, 10, 70

# ── Tier palettes (D dark / M mid / L highlight / A accent / S star) ─────────

MAGE_HAT = {
    1: dict(D=(50, 25, 80),  M=(105, 43, 186), L=(131, 64, 212), A=(192, 192, 192), cone=8),
    2: dict(D=(60, 16, 102), M=(90, 24, 154),  L=(123, 47, 196), A=(192, 192, 192), cone=10),
    3: dict(D=(29, 17, 69),  M=(45, 27, 105),  L=(70, 48, 155),  A=(192, 192, 192), cone=12),
    4: dict(D=(16, 16, 62),  M=(26, 26, 94),   L=(46, 46, 143),  A=(255, 215, 0),
            S=(255, 240, 160), cone=13, tip_star=True),
    5: dict(D=(8, 8, 28),    M=(13, 13, 43),   L=(58, 40, 110),  A=(255, 215, 0),
            S=(226, 226, 255), cone=14, lean=-1, sparkles=True),
    6: dict(D=(5, 5, 16),    M=(10, 10, 26),   L=(93, 58, 150),  A=(240, 230, 140),
            S=(255, 240, 160), cone=15, wide=True, gold_rim=True, tip_star=True),
}

RANGER_HAT = {
    1: dict(D=(45, 72, 31),  M=(72, 108, 61),  L=(90, 151, 76),
            F=[(139, 105, 20)] * 3),
    2: dict(D=(36, 66, 31),  M=(58, 107, 53),  L=(79, 143, 73),
            F=[(139, 105, 20)] * 3),
    3: dict(D=(18, 41, 14),  M=(31, 71, 24),   L=(50, 109, 40),
            F=[(184, 134, 11)] * 4),
    4: dict(D=(14, 33, 16),  M=(26, 58, 21),   L=(44, 92, 36),  A=(184, 115, 51),
            F=[(232, 232, 232)] * 3 + [(85, 85, 85)], dome=6),
    5: dict(D=(8, 26, 6),    M=(15, 46, 10),   L=(30, 74, 24),  A=(192, 192, 192),
            F=[(245, 245, 245)] * 5, dome=6),
    6: dict(D=(5, 13, 5),    M=(10, 20, 10),   L=(28, 51, 24),  A=(255, 215, 0),
            F=[(45, 90, 39)] * 3 + [(240, 240, 240)] * 2 + [(255, 215, 0)],
            dome=6, rim2=True),
}

# ── Color helpers ─────────────────────────────────────────────────────────────

def scale_v(rgb, factor):
    """Return rgb with HSV V multiplied by factor (clamped 0..1)."""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    v = min(1.0, max(0.0, v * factor))
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(r2 * 255)), int(round(g2 * 255)), int(round(b2 * 255)))


# ── Skull-dome head tracking ──────────────────────────────────────────────────

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
    """Return a head_dome(fi) -> (head_top, head_cx) | None function for skin_arr."""
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


skin_m = np.array(Image.open(f"{CH}/skin_m1.png").convert('RGBA'))
skin_f = np.array(Image.open(f"{CH}/skin_f1.png").convert('RGBA'))
head_dome_m = make_head_dome_fn(skin_m)
head_dome_f = make_head_dome_fn(skin_f)

HW = 9   # frame-0 skull width (constant across frames; prevents arm-raise flicker)

# ── Hat authoring, relative to (head_top, cx) ────────────────────────────────
#
# NEW layout (all offsets relative to head_top):
#   head_top+0 : cone base (widest cone row)
#   head_top+1 : hatband (accent color, skull width)
#   head_top+2 : brim top row (brim width = skull+4, or +6 for wide)
#   head_top+3 : brim middle row
#   head_top+4 : brim bottom/shadow row (darkest)
#   head_top+5 : eye row (hat covers everything above this)
#
# Lining fills head_top..head_top+4 at skull width to block hair showing through.

def _finish(fill, over, no_outline_below):
    """Exterior black outline around fill (restricted to y <= no_outline_below),
    then overlay accents on top."""
    px = {}
    for (x, y) in set(fill):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in fill and n[1] <= no_outline_below:
                px[n] = (0, 0, 0)
    px.update(fill)
    px.update(over)
    return px


def mage_hat(tier, head_top, cx):
    P = MAGE_HAT[tier]
    fill, over = {}, {}
    bw = HW + 4 + (2 if P.get('wide') else 0)   # skull(9) + 2px overhang/side (+2 for wide t6)
    bx0 = cx - bw // 2

    # Lining: fills skull area head_top..head_top+4 to block hair showing through
    lining = scale_v(P['M'], 0.55)
    for y in range(head_top, head_top + 5):
        for x in range(cx - HW // 2 - 1, cx + HW // 2 + 2):
            fill[(x, y)] = lining

    # Brim: 3 rows at head_top+2..head_top+4, full brim width
    for x in range(bx0, bx0 + bw):
        fill[(x, head_top + 2)] = P['M']   # brim top
        fill[(x, head_top + 3)] = P['M']   # brim middle
        fill[(x, head_top + 4)] = P['D']   # brim shadow (darkest row)

    # Hatband: 1px row at head_top+1, skull width, in accent color
    for x in range(cx - HW // 2, cx + HW // 2 + 1):
        fill[(x, head_top + 1)] = P['A']

    # Cone: starts at head_top (= brim_top - 2), tapers to 1px at tip
    Hc, lean = P['cone'], P.get('lean', 0)
    for i in range(Hc):
        y = head_top - i          # i=0 at head_top, rises upward
        t = i / (Hc - 1)
        wdt = max(1, int(round(HW * (1 - t) + 1 * t)))
        rx0 = cx - wdt // 2 + int(round(lean * t))
        for x in range(rx0, rx0 + wdt):
            rel = (x - rx0) / max(1, wdt - 1)
            fill[(x, y)] = (P['D'] if rel < 0.33 else
                            P['L'] if 0.55 <= rel <= 0.85 else P['M'])

    # tip row = head_top - (Hc - 1)
    tip_y = head_top - Hc + 1
    tip_x = cx + int(round(lean))
    if P.get('tip_star'):
        over[(tip_x, tip_y)] = P['S']
    if P.get('sparkles'):                        # t5 flanking sparkles
        over[(tip_x - 2, tip_y + 1)] = P['S']
        over[(tip_x + 2, tip_y + 1)] = P['S']
    if P.get('gold_rim'):                        # t6 glowing brim rim accents
        for x in (bx0, bx0 + 1, bx0 + bw - 2, bx0 + bw - 1):
            over[(x, head_top + 2)] = P['A']

    # Outline restricted to above hatband (no outline on brim — it sits on head)
    return _finish(fill, over, no_outline_below=head_top + 1)


def ranger_hat(tier, head_top, cx):
    P = RANGER_HAT[tier]
    fill, over = {}, {}
    bw = HW + 4                             # skull(9) + 2px overhang/side
    bx0 = cx - bw // 2

    # Lining: skull area to block hair
    lining = scale_v(P['M'], 0.55)
    for y in range(head_top, head_top + 5):
        for x in range(cx - HW // 2 - 1, cx + HW // 2 + 2):
            fill[(x, y)] = lining

    # Brim: head_top+2..head_top+4, full width
    for x in range(bx0, bx0 + bw):
        fill[(x, head_top + 2)] = P['M']
        fill[(x, head_top + 3)] = P['M']
        fill[(x, head_top + 4)] = P['D']

    # Robin Hood tilt: left 2px dip one extra row
    for x in (bx0, bx0 + 1):
        fill[(x, head_top + 5)] = P['D']

    # Crown dome offset right; hatband below dome
    ccx = cx + 1
    cw = HW - 2
    for x in range(ccx - cw // 2, ccx - cw // 2 + cw):  # hatband at head_top+1
        fill[(x, head_top + 1)] = P['D']

    n = P.get('dome', 5)
    for j in range(n):                      # domed crown from head_top upward
        y = head_top - j
        wdt = max(2, int(round(cw - (cw - 2) * j / (n - 1))))
        rx0 = ccx - wdt // 2
        for x in range(rx0, rx0 + wdt):
            if j == n - 1 or x == rx0 + wdt - 1:
                fill[(x, y)] = P['L']      # top row + lit right edge
            else:
                fill[(x, y)] = P['M']
        if j < n - 1 and rx0 <= ccx < rx0 + wdt:
            fill[(ccx, y)] = P['D']        # center crease

    # Feather: up-right 45° from crown top-right
    # dome tip is at y = head_top - (n-1); feather sy offset +4 from there for visual anchor
    sx = ccx + 3
    sy = head_top - n + 4                  # shifted +2 vs old (head_top - n + 2) to match new dome pos
    for i, col in enumerate(P['F']):
        over[(sx + min(i, 4), sy - i)] = col
    if len(P['F']) >= 4:                   # thicker plume base
        over[(sx, sy + 1)] = P['F'][0]

    if 'A' in P:                           # metal brim rim at new brim corners
        rim = [(bx0, head_top + 4), (bx0 + bw - 1, head_top + 2)]
        if P.get('rim2'):
            rim += [(bx0 + 1, head_top + 4), (bx0 + bw - 2, head_top + 2)]
        for p in rim:
            over[p] = P['A']

    # Outline up to brim bottom (no outline below brim — it sits on head)
    return _finish(fill, over, no_outline_below=head_top + 4)


# ── Sheet composition ────────────────────────────────────────────────────────

def get_active_frames(hat_path):
    """Return list of frame indices with any opaque pixel in the hat sprite."""
    a = np.array(Image.open(hat_path).convert('RGBA'))
    return [fi for fi in range(NFR)
            if (a[(fi//COLS)*H:(fi//COLS+1)*H, (fi%COLS)*W:(fi%COLS+1)*W, 3] > 0).any()]


def build_sheet(builder, tier, frames, head_dome_fn):
    sheet = np.zeros((H * 7, W * COLS, 4), np.uint8)
    for fi in frames:
        d = head_dome_fn(fi)
        if d is None:
            continue
        head_top, hcx = d
        c, r = fi % COLS, fi // COLS
        gx, gy = c * W, r * H
        for (x, y), rgb in builder(tier, head_top, hcx).items():
            if 0 <= x < W and 0 <= y < H:
                sheet[gy + y, gx + x] = (*rgb, 255)
    return sheet


def main():
    for cls, builder in (('mage', mage_hat), ('ranger', ranger_hat)):
        # ── Male helmets, tiers 1-6 ──────────────────────────────────────────
        # Read active frames from existing tier-1 file (42 frames; sleep frames empty)
        t1_path = f"{CH}/helmet_{cls}1.png"
        frames_m = get_active_frames(t1_path)

        for tier in range(1, 7):
            sheet = build_sheet(builder, tier, frames_m, head_dome_m)
            name = f"helmet_{cls}{tier}.png"
            Image.fromarray(sheet).save(f"{CH}/{name}")
            print(f"wrote {name} ({len(frames_m)} frames)")

        # ── Female tier-1 helmet (uses skin_f1.png) ──────────────────────────
        t1f_path = f"{CH}/helmet_{cls}1_f.png"
        if os.path.exists(t1f_path):
            frames_f = get_active_frames(t1f_path)
            sheet_f = build_sheet(builder, 1, frames_f, head_dome_f)
            Image.fromarray(sheet_f).save(t1f_path)
            print(f"wrote helmet_{cls}1_f.png ({len(frames_f)} frames)")


if __name__ == '__main__':
    main()
