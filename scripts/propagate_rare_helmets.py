#!/usr/bin/env python3
"""Rare helmet propagation with SKULL-DOME head tracking.

Run from repo root:  python3 scripts/propagate_rare_helmets.py

Why not full-head centroid: during slash frames (row 5) the raised arm puts
skin pixels at x=52-57, y<32, which contaminates a full-head centroid and
drags the helmet right (same bug fixed for T1-T6 helmets). Frames 40-43 raise
BOTH arms, contaminating the centroid vertically too.

Method (per frame of skin_m1.png, head zone = opaque skin pixels y<32):
 1. Take the TOP 3 pixel rows (global ymin..ymin+2) and split their x-columns
    into contiguous runs (clusters).
 2. Scan clusters LEFT to RIGHT; accept the first whose region widens to a
    contiguous width >= 7px within 6 rows below (the skull dome widens
    5->7->9; arms stay 4-5 wide). This keeps the "leftmost cluster" rule for
    slash frames while rejecting a raised LEFT arm in frames 40-43.
 3. Re-anchor at the chosen cluster's own top row (hymin), since a raised arm
    can set the global ymin above the skull.
 4. Head position = centroid of the dome: cx over rows hymin..hymin+1 (runs
    overlapping the cluster only, so an adjacent arm can't skew x), cy over
    rows hymin..hymin+2.
 5. dx,dy = round(centroid - frame0 centroid); stamp the frame-0 helmet
    design shifted by (dx,dy). Frames with no helmet pixels in the committed
    sheet (sleep 68/69 etc.) stay empty.
"""
from PIL import Image
import numpy as np

CH = "sprites/preview_assets/char"
W, H, COLS, ROWS = 80, 64, 10, 7
HELMETS = ["helmet_rare1.png", "helmet_rare2.png", "helmet_rare3.png"]

def runs_of(xs):
    out = []
    if not xs: return out
    s = p = xs[0]
    for x in xs[1:]:
        if x == p + 1: p = x
        else: out.append((s, p)); s = p = x
    out.append((s, p))
    return out

skin = np.array(Image.open(f"{CH}/skin_m1.png").convert('RGBA'))

def head_dome(fi):
    c, r = fi % COLS, fi // COLS
    zone = skin[r*H:(r+1)*H, c*W:(c+1)*W][:32, :, 3] > 0
    op = np.argwhere(zone)
    if len(op) == 0: return None
    ymin = int(op[:, 0].min())
    top = op[op[:, 0] <= ymin + 2]
    clusters = runs_of(sorted(set(top[:, 1].tolist())))
    chosen = None
    for a, b in clusters:                                  # leftmost first
        for y in range(ymin, min(ymin + 6, 32)):           # skull-width test
            xs = [x for x in range(max(0, a-2), min(W, b+3)) if zone[y, x]]
            if xs and max(e - s + 1 for s, e in runs_of(xs)) >= 7:
                chosen = (a, b); break
        if chosen: break
    if chosen is None: chosen = clusters[0]
    a, b = chosen
    hymin = min(y for y in range(32) for x in range(a, b+1) if zone[y, x])
    def rowpix(y):
        return [x for s, e in runs_of([x for x in range(W) if zone[y, x]])
                if e >= a and s <= b for x in range(s, e+1)]
    xs2  = [x for y in range(hymin, min(hymin+2, 32)) for x in rowpix(y)]
    pts3 = [(x, y) for y in range(hymin, min(hymin+3, 32)) for x in rowpix(y)]
    return (sum(xs2)/len(xs2), sum(p[1] for p in pts3)/len(pts3))

cx0, cy0 = head_dome(0)

for name in HELMETS:
    path = f"{CH}/{name}"
    img = np.array(Image.open(path).convert('RGBA'))
    out = img.copy()
    design = {(x, y): tuple(int(v) for v in img[y, x])
              for y in range(H) for x in range(W) if img[y, x, 3] > 0}
    for fi in range(COLS * ROWS):
        c, r = fi % COLS, fi // COLS
        gy, gx = r * H, c * W
        if not (img[gy:gy+H, gx:gx+W, 3] > 0).any():
            continue                                       # inactive frame
        d = head_dome(fi)
        if d is None:
            print(f"{name} f{fi}: no head pixels, left untouched"); continue
        dx, dy = round(d[0] - cx0), round(d[1] - cy0)
        out[gy:gy+H, gx:gx+W] = 0
        for (x, y), col in design.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                out[gy+ny, gx+nx] = col
    Image.fromarray(out).save(path)
    print(f"{name}: re-propagated with skull-dome tracking")
