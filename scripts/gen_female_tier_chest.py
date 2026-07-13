#!/usr/bin/env python3
"""Generate female warrior chest armor tiers 1-6 from the male tier sheets.

Method: per-frame proportional warp. For every opaque pixel of the female
base silhouette (warrior_shirt_default_f), map its bbox-relative position
into the male tier frame's bbox and sample the nearest opaque male pixel.
This preserves the male plate detail (chest-plate gradient, plate lines,
shoulder highlights) at proportionally equivalent positions on the female
silhouette -- both sheets share the same 45 active frames / poses, so the
warp is pose-consistent.

Outputs: leather_armor_1_f.png, armor_chest_2_f.png ... armor_chest_6_f.png
Run scripts/sprite_shade.py afterwards, then sprite_qa.py.
"""
import numpy as np
from PIL import Image

CHAR = 'sprites/preview_assets/char/'
FW, FH = 80, 64
TIERS = [
    ('leather_armor_1.png', 'leather_armor_1_f.png'),
    ('armor_chest_2.png',   'armor_chest_2_f.png'),
    ('armor_chest_3.png',   'armor_chest_3_f.png'),
    ('armor_chest_4.png',   'armor_chest_4_f.png'),
    ('armor_chest_5.png',   'armor_chest_5_f.png'),
    ('armor_chest_6.png',   'armor_chest_6_f.png'),
]

def load(p):
    return np.array(Image.open(CHAR + p).convert('RGBA'))

def main():
    base = load('warrior_shirt_default_f.png')
    baseP = base[..., 3] > 0
    for msrc, fdst in TIERS:
        male = load(msrc)
        maleP = male[..., 3] > 0
        out = np.zeros_like(base)
        for fi in range(70):
            r, c = fi // 10, fi % 10
            sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
            Pf, Pm = baseP[sl], maleP[sl]
            if not Pf.any():
                continue
            assert Pm.any(), f'{msrc} frame {fi} empty but female frame active'
            mf, of = male[sl], out[sl]
            fys, fxs = np.where(Pf)
            mys, mxs = np.where(Pm)
            fy0, fy1, fx0, fx1 = fys.min(), fys.max(), fxs.min(), fxs.max()
            my0, my1, mx0, mx1 = mys.min(), mys.max(), mxs.min(), mxs.max()
            fh = max(1, fy1 - fy0); fw = max(1, fx1 - fx0)
            mh = my1 - my0; mw = mx1 - mx0
            for y, x in zip(fys, fxs):
                ty = my0 + (y - fy0) / fh * mh
                tx = mx0 + (x - fx0) / fw * mw
                yy, xx = int(round(ty)), int(round(tx))
                if not (0 <= yy < FH and 0 <= xx < FW and Pm[yy, xx]):
                    d = np.abs(mys - ty) + np.abs(mxs - tx)
                    k = int(d.argmin())
                    yy, xx = mys[k], mxs[k]
                of[y, x] = mf[yy, xx]
        Image.fromarray(out).save(CHAR + fdst)
        print(f'{fdst} written ({int((out[...,3]>0).sum())} px)')

if __name__ == '__main__':
    main()
