#!/usr/bin/env python3
"""Rebuild female rare boots (boots_rare1_f/2_f/3_f).

Fixes vs the previous generation:
  1. Size: silhouette = warrior_boots_f mask INTERSECTED with the female
     skin (skin_f1) foot silhouette per pixel -- removes the ~122 px that
     stuck out past the female foot.
  2. Detail: per-frame decorative accents matching the male rare boots:
       - 2-row cuff trim band at the boot top (1 row for set 2) in the set
         accent color, with black corner pixels at the cuff edges (male style)
       - toe cap: 2 accent pixels centered on the bottom row of each foot
       - set 2 only: short vertical teal accent line down the outer edge of
         each foot (rows +2..+4 from the cuff), matching the male accent-line
         distribution
     Base color via luminance-quantile transfer from the male boot palette
     (non-black, non-accent colors), same approach as the rare shirts.
Run scripts/sprite_shade.py afterwards, then sprite_qa.py --y-max 63.
"""
import numpy as np
from PIL import Image

CHAR = 'sprites/preview_assets/char/'
FW, FH = 80, 64

SETS = {
    1: dict(trim=(255, 215, 0),   toe=(255, 215, 0),   rows=2, line=False),
    2: dict(trim=(0, 254, 227),   toe=(0, 254, 227),   rows=1, line=True),
    3: dict(trim=(255, 251, 234), toe=(255, 251, 234), rows=2, line=False),
}

def load(p):
    return np.array(Image.open(CHAR + p).convert('RGBA'))

def lum(rgb):
    rgb = rgb.astype(np.float64)
    return (3 * rgb[..., 0] + 6 * rgb[..., 1] + rgb[..., 2]) / 10.0

def is_accent(rgb):
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    gold = (r >= 230) & (g >= 190)
    teal = (g >= 150) & (b >= 130) & (r <= g)
    ivory = (r >= 240) & (g >= 235) & (b >= 200)
    return gold | teal | ivory

def build_ramp(male_sheet):
    op = male_sheet[..., 3] > 10
    cols = male_sheet[op][:, :3]
    keep = ~is_accent(cols) & (cols.astype(int).sum(axis=1) >= 15)
    cols = cols[keep]
    order = np.argsort(lum(cols), kind='stable')
    return cols[order]

def components(P):
    """8-connected components of a small boolean frame mask."""
    seen = np.zeros_like(P)
    comps = []
    for sy, sx in zip(*np.where(P)):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        comp = []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < FH and 0 <= nx < FW and P[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        comps.append(comp)
    return comps

def main():
    skin = load('skin_f1.png')[..., 3] > 0
    base = load('warrior_boots_f.png')
    baseP = base[..., 3] > 0
    mask = baseP & skin                      # fix 1: clip to female foot silhouette
    removed = int((baseP & ~skin).sum())

    for n, cfg in SETS.items():
        male = load(f'boots_rare{n}.png')
        ramp = build_ramp(male)
        out = np.zeros_like(base)
        # quantile color transfer over the clipped silhouette
        src_l = lum(base[mask][:, :3])
        ref = np.sort(src_l)
        q = np.searchsorted(ref, src_l, side='left') / max(1, len(ref) - 1)
        idx = np.clip((q * (len(ramp) - 1)).round().astype(int), 0, len(ramp) - 1)
        out[mask, 0] = ramp[idx][:, 0]
        out[mask, 1] = ramp[idx][:, 1]
        out[mask, 2] = ramp[idx][:, 2]
        out[mask, 3] = 255

        for fi in range(70):
            r, c = fi // 10, fi % 10
            sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
            Pf = mask[sl].copy()
            of = out[sl]
            if not Pf.any():
                continue
            # drop isolated pixels created by the clip
            for y, x in zip(*np.where(Pf)):
                nb = Pf[max(0, y-1):y+2, max(0, x-1):x+2].sum() - 1
                if nb == 0:
                    of[y, x] = 0
                    Pf[y, x] = False
            for comp in components(Pf):
                if len(comp) < 4:
                    continue
                ys = [p[0] for p in comp]; xs = [p[1] for p in comp]
                y0, y1 = min(ys), max(ys)
                # cuff trim band (top `rows` rows), black corners on top row
                for rr in range(cfg['rows']):
                    rowx = sorted(x for (y, x) in comp if y == y0 + rr)
                    if not rowx:
                        continue
                    for x in rowx:
                        col = (0, 0, 0) if (rr == 0 and (x == rowx[0] or x == rowx[-1])) \
                              else cfg['trim']
                        of[y0 + rr, x, :3] = col
                # toe cap: 2 centered pixels on the bottom row
                rowx = sorted(x for (y, x) in comp if y == y1)
                if rowx:
                    mid = len(rowx) // 2
                    for x in rowx[max(0, mid-1):mid+1]:
                        of[y1, x, :3] = cfg['toe']
                # set-2 vertical accent line on the outer edge
                if cfg['line']:
                    fys, fxs = np.where(Pf)
                    outer_left = (sum(xs) / len(xs)) < fxs.mean()
                    for y in range(y0 + 2, min(y0 + 5, y1)):
                        rowx = sorted(x for (yy, x) in comp if yy == y)
                        if rowx:
                            of[y, rowx[0] if outer_left else rowx[-1], :3] = cfg['trim']
        Image.fromarray(out).save(CHAR + f'boots_rare{n}_f.png')
        print(f'boots_rare{n}_f.png written ({int((out[...,3]>0).sum())} px)')
    print(f'clipped {removed} px outside female foot silhouette (per sheet)')

if __name__ == '__main__':
    main()
