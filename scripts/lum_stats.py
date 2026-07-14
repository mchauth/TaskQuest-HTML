#!/usr/bin/env python3
"""lum_stats.py — luminance distribution stats for sprite shading QA.

Measures median / p10 / p90 luminance over opaque, non-black, non-emblem
pixels across the whole sheet. Luminance = 0.299R + 0.587G + 0.114B.

Protected (excluded) pixels, per shading-fix spec:
  black/outline: R+G+B < 15
  gold accent  : R>=230, G>=190, B<100
  teal accent  : G>=170, B>=150, R<G
"""
import sys
import numpy as np
from PIL import Image


def masks(img):
    rgb = img[:, :, :3].astype(np.int16)
    a = img[:, :, 3]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    opaque = a > 10
    black = (r + g + b) < 15
    gold = (r >= 230) & (g >= 190) & (b < 100)
    teal = (g >= 170) & (b >= 150) & (r < g)
    eligible = opaque & ~black & ~(gold | teal)
    return eligible


def stats(path):
    img = np.array(Image.open(path).convert('RGBA'))
    eligible = masks(img)
    rgb = img[:, :, :3].astype(np.float32)
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    vals = lum[eligible]
    if len(vals) == 0:
        return None
    return {
        'n': len(vals),
        'median': float(np.median(vals)),
        'p10': float(np.percentile(vals, 10)),
        'p90': float(np.percentile(vals, 90)),
    }


if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = stats(p)
        name = p.split('/')[-1]
        if s is None:
            print(f"{name:28s}  (no eligible pixels)")
        else:
            print(f"{name:28s}  n={s['n']:6d}  median={s['median']:6.1f}  "
                  f"p10={s['p10']:6.1f}  p90={s['p90']:6.1f}")
