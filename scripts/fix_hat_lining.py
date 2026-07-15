#!/usr/bin/env python3
"""Add an opaque hat lining to mage/ranger helmets so hair can't bleed through.

Layer order renders helmet ABOVE hair (skin -> pants -> boots -> shirt ->
hair -> helmet), so any transparent pixel inside the hat silhouette shows the
hair underneath. Fix: make the hat itself block the hair with interior fill
pixels ("lining"):

  1. covered skull zone — rows head_top .. head_top+2 (skull-dome tracking
     from rebuild_class_hats.head_dome), x = brim_left .. brim_right (the
     opaque x-span of the hat in those rows). Every transparent pixel in the
     zone is filled with a medium-dark hat lining: the hat's primary color
     scaled to V*0.6 (uniform RGB scale preserves hue/sat).
  2. cone/crown interior — any transparent pixel ABOVE the brim that is fully
     enclosed by the hat silhouette (flood fill from the frame border) is
     filled with the primary color at V*0.5 (the inside of the hat).

Hair stays visible at the SIDES and BELOW the brim (those pixels are outside
the hat silhouette and are never touched).

Applies to helmet_mage1-6.png, helmet_ranger1-6.png and the tier-1 female
sheets (tracked against skin_f1). Run from repo root, then QA with
sprite_qa.py --y-min 2.
"""
import os
import sys
from collections import Counter, deque

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebuild_class_hats as rch

CH = "sprites/preview_assets/char"
W, H, COLS, NFR = 80, 64, 10, 70

LINING_V = 0.6    # skull-zone lining brightness (x primary V)
INSIDE_V = 0.5    # cone/crown interior brightness (x primary V)


def head_dome_for(skin, fi):
    """rebuild_class_hats.head_dome against an arbitrary skin sheet."""
    rch.skin = skin
    return rch.head_dome(fi)


def primary_color(frame, ht):
    """Modal opaque non-outline RGB in the brim rows (fallback: whole frame)."""
    for y0, y1 in ((max(0, ht - 1), ht + 3), (0, H)):
        cnt = Counter()
        for y in range(y0, min(y1, H)):
            for x in range(W):
                r, g, b, a = (int(v) for v in frame[y, x])
                if a > 10 and r + g + b >= 30:
                    cnt[(r, g, b)] += 1
        if cnt:
            return cnt.most_common(1)[0][0]
    return (90, 90, 90)


def enclosed_transparent(op):
    """Transparent pixels NOT 4-connected to the frame border."""
    trans = ~op
    seen = np.zeros_like(trans)
    dq = deque()
    for x in range(W):
        for y in (0, H - 1):
            if trans[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if trans[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and trans[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    return trans & ~seen


def scale_rgb(rgb, k):
    return tuple(min(255, max(0, int(round(c * k)))) for c in rgb)


def line_sheet(name, skin):
    path = f"{CH}/{name}"
    arr = np.array(Image.open(path).convert('RGBA'))
    zone_filled = interior_filled = 0
    for fi in range(NFR):
        c, r = fi % COLS, fi // COLS
        fr = arr[r * H:(r + 1) * H, c * W:(c + 1) * W]
        op = fr[..., 3] > 10
        if not op.any():
            continue
        d = head_dome_for(skin, fi)
        if d is None:
            continue
        ht, _ = d
        prim = primary_color(fr, ht)
        lining = scale_rgb(prim, LINING_V)
        inside = scale_rgb(prim, INSIDE_V)

        # 1) covered skull zone: rows ht..ht+2, brim x-span
        rows = op[ht:ht + 3]
        span = np.flatnonzero(rows.any(0))
        if len(span):
            bx0, bx1 = int(span.min()), int(span.max())
            for y in range(ht, min(ht + 3, H)):
                for x in range(bx0, bx1 + 1):
                    if not op[y, x]:
                        fr[y, x] = (*lining, 255)
                        op[y, x] = True
                        zone_filled += 1

        # 1b) black pixels stranded inside the new lining (they were the
        #     hood's face-opening edge before the fill) become lining too —
        #     an interior lone #000 island fails sprite_qa and reads as a hole
        for y in range(max(0, ht - 1), min(ht + 4, H)):
            for x in range(1, W - 1):
                if not op[y, x] or fr[y, x, :3].astype(int).sum() >= 15:
                    continue
                edge = black_nbr = False
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if not (0 <= ny < H and 0 <= nx < W) or not op[ny, nx]:
                        edge = True
                    elif fr[ny, nx, :3].astype(int).sum() < 15:
                        black_nbr = True
                if not edge and not black_nbr:
                    fr[y, x] = (*lining, 255)
                    zone_filled += 1

        # 2) cone/crown interior above the brim
        enc = enclosed_transparent(op)
        for y in range(0, ht):
            for x in range(W):
                if enc[y, x]:
                    fr[y, x] = (*inside, 255)
                    interior_filled += 1
    Image.fromarray(arr).save(path)
    print(f"{name}: skull-zone lining {zone_filled}px, interior {interior_filled}px")


def main():
    skin_m = np.array(Image.open(f"{CH}/skin_m1.png").convert('RGBA'))
    skin_f = np.array(Image.open(f"{CH}/skin_f1.png").convert('RGBA'))
    for cls in ('mage', 'ranger'):
        for t in range(1, 7):
            line_sheet(f"helmet_{cls}{t}.png", skin_m)
        fname = f"helmet_{cls}1_f.png"
        if os.path.exists(f"{CH}/{fname}"):
            line_sheet(fname, skin_f)


if __name__ == '__main__':
    main()
