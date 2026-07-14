#!/usr/bin/env python3
"""Rebuild mage/ranger tier 2-6 helmets FROM SCRATCH on blank sheets.

Replaces the compose_helmet() output of redesign_mage_ranger_tiers.py, which
painted the wizard/Robin Hood hats ON TOP of the recolored tier-1 hood. Here
the hood is gone entirely: each sheet starts fully transparent and the hat is
painted directly against the bare head, per frame, using the SKULL-DOME head
tracking documented in HANDOFF.md (same method as propagate_rare_helmets.py):

  1. head zone = opaque skin_m1 pixels y<32 per frame
  2. top 3 rows -> contiguous x clusters, scanned left to right
  3. accept the first cluster that widens to >=7px contiguous within 6 rows
     (skull dome widens 5->7->9; a raised arm stays 4-5 wide)
  4. re-anchor at the cluster's own top row (head_top) and take the dome
     centroid x over the top two rows (head_center_x)

Hat width is fixed to the frame-0 skull width (9px): frames 40-43 raise both
arms and merge arm+head into a 13px run, and a per-frame width would make the
hat flicker. head_top / head_center_x remain per-frame so the hat rides the
1px idle bob and all walk/slash/jump offsets.

Active frames are taken from the tier-1 helmet sheets (42 frames; sleep 68-69
stay empty). Run from repo root, then sprite_shade.py + sprite_qa.py --y-min 2.
"""
import os
import sys
import numpy as np
from PIL import Image

CH = "sprites/preview_assets/char"
W, H, COLS, NFR = 80, 64, 10, 70

# ── Tier palettes (D dark / M mid / L highlight / A accent / S star) ─────────

MAGE_HAT = {
    2: dict(D=(60, 16, 102), M=(90, 24, 154), L=(123, 47, 196), A=(192, 192, 192), cone=9),
    3: dict(D=(29, 17, 69),  M=(45, 27, 105), L=(70, 48, 155),  A=(192, 192, 192), cone=11),
    4: dict(D=(16, 16, 62),  M=(26, 26, 94),  L=(46, 46, 143),  A=(255, 215, 0),
            S=(255, 240, 160), cone=13, tip_star=True),
    5: dict(D=(8, 8, 28),    M=(13, 13, 43),  L=(58, 40, 110),  A=(255, 215, 0),
            S=(226, 226, 255), cone=14, lean=-1, sparkles=True),
    6: dict(D=(5, 5, 16),    M=(10, 10, 26),  L=(93, 58, 150),  A=(240, 230, 140),
            S=(255, 240, 160), cone=15, wide=True, gold_rim=True, tip_star=True),
}

RANGER_HAT = {
    2: dict(D=(36, 66, 31),  M=(58, 107, 53), L=(79, 143, 73),
            F=[(139, 105, 20)] * 3),
    3: dict(D=(18, 41, 14),  M=(31, 71, 24),  L=(50, 109, 40),
            F=[(184, 134, 11)] * 4),
    4: dict(D=(14, 33, 16),  M=(26, 58, 21),  L=(44, 92, 36),  A=(184, 115, 51),
            F=[(232, 232, 232)] * 3 + [(85, 85, 85)], dome=6),
    5: dict(D=(8, 26, 6),    M=(15, 46, 10),  L=(30, 74, 24),  A=(192, 192, 192),
            F=[(245, 245, 245)] * 5, dome=6),
    6: dict(D=(5, 13, 5),    M=(10, 20, 10),  L=(28, 51, 24),  A=(255, 215, 0),
            F=[(45, 90, 39)] * 3 + [(240, 240, 240)] * 2 + [(255, 215, 0)],
            dome=6, rim2=True),
}

# ── Skull-dome head tracking (HANDOFF.md method) ─────────────────────────────

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


skin = np.array(Image.open(f"{CH}/skin_m1.png").convert('RGBA'))


def head_dome(fi):
    """Return (head_top, head_center_x) for frame fi, or None."""
    c, r = fi % COLS, fi // COLS
    zone = skin[r*H:(r+1)*H, c*W:(c+1)*W][:32, :, 3] > 0
    op = np.argwhere(zone)
    if len(op) == 0:
        return None
    ymin = int(op[:, 0].min())
    top = op[op[:, 0] <= ymin + 2]
    clusters = runs_of(sorted(set(top[:, 1].tolist())))
    chosen = None
    for a, b in clusters:                                # leftmost first
        for y in range(ymin, min(ymin + 6, 32)):         # skull-width test
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
        return [x for s, e in runs_of([x for x in range(W) if zone[y, x]])
                if e >= a and s <= b for x in range(s, e+1)]
    xs2 = [x for y in range(hymin, min(hymin + 2, 32)) for x in rowpix(y)]
    return hymin, int(round(sum(xs2) / len(xs2)))


HW = 9   # frame-0 skull width (constant across frames; see module docstring)

# ── Hat authoring, relative to (head_top, cx) ────────────────────────────────

def _finish(fill, over, no_outline_below):
    """Exterior black outline around `fill`, minus pixels below the brim,
    then overlay accents (feather/stars/rim) painted over anything."""
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
    bw = HW + 2 + (4 if P.get('wide') else 0)            # brim width
    bx0 = cx - bw // 2
    for x in range(bx0, bx0 + bw):                       # brim: 2px tall band
        fill[(x, head_top - 1)] = P['M']                 # lit top edge
        fill[(x, head_top)] = P['D']                     # dark underside
    for x in range(cx - HW // 2, cx + HW // 2 + 1):      # hatband
        fill[(x, head_top - 2)] = P['A']
    Hc, lean = P['cone'], P.get('lean', 0)
    for i in range(Hc):                                  # tapering cone
        y = head_top - 3 - i
        t = i / (Hc - 1)
        wdt = max(1, int(round(HW * (1 - t) + 1 * t)))
        rx0 = cx - wdt // 2 + int(round(lean * t))
        for x in range(rx0, rx0 + wdt):
            rel = (x - rx0) / max(1, wdt - 1)
            fill[(x, y)] = (P['D'] if rel < 0.33 else    # left third shadow
                            P['L'] if 0.55 <= rel <= 0.85 else P['M'])
    tip_y = head_top - 2 - Hc
    tip_x = cx + int(round(lean))
    if P.get('tip_star'):
        over[(tip_x, tip_y)] = P['S']
    if P.get('sparkles'):                                # t5 flanking sparkles
        over[(tip_x - 2, tip_y + 1)] = P['S']
        over[(tip_x + 2, tip_y + 1)] = P['S']
    if P.get('gold_rim'):                                # t6 glowing brim rim
        for x in (bx0, bx0 + 1, bx0 + bw - 2, bx0 + bw - 1):
            over[(x, head_top - 1)] = P['A']
    return _finish(fill, over, no_outline_below=head_top)


def ranger_hat(tier, head_top, cx):
    P = RANGER_HAT[tier]
    fill, over = {}, {}
    bw = HW + 3
    bx0 = cx - bw // 2
    for x in range(bx0, bx0 + bw):                       # tilted brim
        if x < cx:                                       # left side 1px lower
            fill[(x, head_top)] = P['M']
            fill[(x, head_top + 1)] = P['D']
        else:
            fill[(x, head_top - 1)] = P['M']
            fill[(x, head_top)] = P['D']
    ccx = cx + 1                                         # crown over right half
    cw = HW - 2
    for x in range(ccx - cw // 2, ccx - cw // 2 + cw):   # hatband (darker)
        fill[(x, head_top - 2)] = P['D']
    n = P.get('dome', 5)
    for j in range(n):                                   # domed crown
        y = head_top - 3 - j
        wdt = max(2, int(round(cw - (cw - 2) * j / (n - 1))))
        rx0 = ccx - wdt // 2
        for x in range(rx0, rx0 + wdt):
            if j == n - 1 or x == rx0 + wdt - 1:
                fill[(x, y)] = P['L']                    # top + lit right edge
            else:
                fill[(x, y)] = P['M']
        if j < n - 1 and rx0 <= ccx < rx0 + wdt:
            fill[(ccx, y)] = P['D']                      # center crease
    sx, sy = ccx + 3, head_top - n + 1                   # feather up-right 45°
    for i, col in enumerate(P['F']):
        over[(sx + min(i, 4), sy - i)] = col
    if len(P['F']) >= 4:                                 # thicker plume base
        over[(sx, sy + 1)] = P['F'][0]
    if 'A' in P:                                         # metal brim rim
        rim = [(bx0, head_top), (bx0 + bw - 1, head_top - 1)]
        if P.get('rim2'):
            rim += [(bx0 + 1, head_top), (bx0 + bw - 2, head_top - 1)]
        for p in rim:
            over[p] = P['A']
    return _finish(fill, over, no_outline_below=head_top + 1)


# ── Sheet composition ────────────────────────────────────────────────────────

def active_frames(cls):
    a = np.array(Image.open(f"{CH}/helmet_{cls}1.png").convert('RGBA'))
    return [fi for fi in range(NFR)
            if (a[(fi//COLS)*H:(fi//COLS+1)*H, (fi%COLS)*W:(fi%COLS+1)*W, 3] > 0).any()]


def main():
    for cls, builder in (('mage', mage_hat), ('ranger', ranger_hat)):
        frames = active_frames(cls)
        for tier in range(2, 7):
            sheet = np.zeros((H * 7, W * COLS, 4), np.uint8)   # blank: no hood
            for fi in frames:
                d = head_dome(fi)
                if d is None:
                    continue
                head_top, hcx = d
                c, r = fi % COLS, fi // COLS
                gx, gy = c * W, r * H
                for (x, y), rgb in builder(tier, head_top, hcx).items():
                    if 0 <= x < W and 0 <= y < H:
                        sheet[gy + y, gx + x] = (*rgb, 255)
            name = f"helmet_{cls}{tier}.png"
            Image.fromarray(sheet).save(f"{CH}/{name}")
            print(f"wrote {name} ({len(frames)} frames)")


if __name__ == '__main__':
    main()
