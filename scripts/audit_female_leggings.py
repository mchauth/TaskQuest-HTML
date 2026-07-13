#!/usr/bin/env python3
"""Full-sheet audit + fix for female legging sprites vs skin_f1 silhouette.

Checks per frame (70 frames):
  strays   : opaque legging px outside skin silhouette -> remove
  floaters : opaque legging px with no opaque 4-neighbor -> remove
  gaps     : skin px transparent in leggings but vertically enclosed by
             legging px in the same column (interior hole) -> fill with
             spatially nearest opaque legging px (dy weighted 3x)
  speckles : legging px whose luminance differs from 3x3 opaque-neighbor
             median by >60 AND has <2 similar-luminance neighbors
             (protects 1px coherent seam lines) -> neighborhood median color
"""
import sys
import numpy as np
from PIL import Image

CHAR = 'sprites/preview_assets/char/'
FW, FH = 80, 64
SPRITES = ['leather_pants_1_f', 'armor_pants_2_f', 'armor_pants_3_f',
           'armor_pants_4_f', 'armor_pants_5_f', 'armor_pants_6_f',
           'pants_rare1_f', 'pants_rare2_f', 'pants_rare3_f']

def lum(c):
    return (3 * int(c[0]) + 6 * int(c[1]) + int(c[2])) / 10.0

def audit_frame(pf, sf, fix):
    """pf: legging frame RGBA (modified in place if fix), sf: skin alpha mask.
    Returns dict of counts."""
    n = dict(stray=0, floater=0, detached=0, gap=0, speckle=0)
    P = pf[..., 3] > 0
    if not P.any():
        return n

    # 1. strays outside silhouette
    stray = P & ~sf
    n['stray'] = int(stray.sum())
    if fix:
        pf[stray] = 0
        P = pf[..., 3] > 0

    # 2. lone floaters (no opaque 4-neighbor)
    pad = np.pad(P, 1)
    n4 = (pad[:-2, 1:-1].astype(int) + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:])
    floater = P & (n4 == 0)
    n['floater'] = int(floater.sum())
    if fix:
        pf[floater] = 0
        P = pf[..., 3] > 0
    if not P.any():
        return n

    # 2b. small detached clusters (8-conn components far smaller than main)
    from collections import deque
    lab = np.zeros((FH, FW), int); sizes = {}; nl = 0
    for sy, sx in zip(*np.where(P)):
        if lab[sy, sx]: continue
        nl += 1; q = deque([(sy, sx)]); lab[sy, sx] = nl; cnt = 0
        while q:
            y, x = q.popleft(); cnt += 1
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    ny, nx = y+dy, x+dx
                    if 0<=ny<FH and 0<=nx<FW and P[ny,nx] and not lab[ny,nx]:
                        lab[ny,nx] = nl; q.append((ny,nx))
        sizes[nl] = cnt
    if sizes:
        big = max(sizes.values())
        kill = {k for k, v in sizes.items() if v < max(5, big * 0.1) and v != big}
        det = np.isin(lab, list(kill)) & P
        n['detached'] = int(det.sum())
        if fix and det.any():
            pf[det] = 0
            P = pf[..., 3] > 0
        if not P.any():
            return n
    else:
        n['detached'] = 0

    # 3. gaps: skin px, no legging, legging above AND below in same column
    above = np.zeros_like(P)
    below = np.zeros_like(P)
    for x in range(FW):
        col = np.where(P[:, x])[0]
        if len(col):
            above[col.min() + 1:, x] = True
            below[:col.max(), x] = True
    gap = sf & ~P & above & below
    gys, gxs = np.where(gap)
    n['gap'] = len(gys)
    if fix and len(gys):
        oys, oxs = np.where(P)
        for gy, gx in zip(gys, gxs):
            d = np.abs(oxs - gx) + 3 * np.abs(oys - gy)   # y-weighted 3x
            k = d.argmin()
            pf[gy, gx] = pf[oys[k], oxs[k]]
        P = pf[..., 3] > 0

    # 4. value speckles
    fixes = []
    ys, xs = np.where(P)
    for y, x in zip(ys, xs):
        nb = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < FH and 0 <= nx < FW and P[ny, nx]:
                    nb.append(pf[ny, nx, :3].astype(int))
        if len(nb) < 3:
            continue
        nb = np.array(nb)
        nlum = np.array([lum(c) for c in nb])
        med = float(np.median(nlum))
        pl = lum(pf[y, x, :3])
        if abs(pl - med) > 60 and (np.abs(nlum - pl) <= 40).sum() < 2:
            fixes.append((y, x, np.median(nb, axis=0).astype(np.uint8)))
    n['speckle'] = len(fixes)
    if fix:
        for y, x, c in fixes:
            pf[y, x, :3] = c
            pf[y, x, 3] = 255
    return n

def main():
    fix = '--fix' in sys.argv
    skin = np.array(Image.open(CHAR + 'skin_f1.png').convert('RGBA'))[..., 3] > 0
    grand = dict(stray=0, floater=0, detached=0, gap=0, speckle=0)
    for name in SPRITES:
        img = np.array(Image.open(CHAR + name + '.png').convert('RGBA'))
        tot = dict(stray=0, floater=0, detached=0, gap=0, speckle=0)
        per_frame = {}
        for fi in range(70):
            r, c = fi // 10, fi % 10
            sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
            res = audit_frame(img[sl], skin[sl], fix)
            if sum(res.values()):
                per_frame[fi] = res
            for k in tot:
                tot[k] += res.get(k, 0)
        if fix:
            Image.fromarray(img).save(CHAR + name + '.png')
        for k in grand:
            grand[k] += tot[k]
        bad_frames = len(per_frame)
        print(f"{name}: strays={tot['stray']} floaters={tot['floater']} "
              f"detached={tot['detached']} gaps={tot['gap']} "
              f"speckles={tot['speckle']}  ({bad_frames} frames affected)")
        if not fix and per_frame:
            worst = sorted(per_frame.items(), key=lambda kv: -sum(kv[1].values()))[:5]
            for fi, res in worst:
                print(f"    frame {fi}: {res}")
    print(f"\nTOTAL: {grand}  ({'FIXED' if fix else 'dry run'})")

if __name__ == '__main__':
    main()
