#!/usr/bin/env python3
"""Redesign mage & ranger armor tiers 2-6 with purposeful, structured art.

Replaces the flat palette-variant approach of gen_mage_ranger_tiers.py:

  helmets: no more recolored skullcaps. Each tier keeps the tier-1 hood
           (quantized to a clean 3-tone tier ramp) as the head-covering
           base, then gets a hand-authored hat stamped on top:
             mage   -> pointed wizard hat (brim + hatband + tapering cone),
                       taller/fancier per tier (stars, lean, gold rim)
             ranger -> Robin Hood hat (tilted brim, low domed crown with
                       center crease, feather plume in tier accent)
           The hood is a constant 52-px shape that only translates between
           frames, so the frame-0 hat design is propagated by per-frame
           hood offset (authored once, pixel-identical tracking).

  shirts/pants/boots: the old recolor preserved per-pixel V noise from the
           AI-generated tier-1 sources (30+ unique colors per garment),
           which sprite_shade then smeared into random splotches. Here the
           V ratio is QUANTIZED to three authored tone levels per material
           (shadow / base / highlight) before any detail or shading pass,
           so sprite_shade's diffusion produces smooth structured
           gradients instead of noise. Accents are placed at specific
           authored positions (collar, stripes, rune dots, stitching,
           shoulder patch, buckle, seams, cuff trim) before shading.

Run from repo root:  python3 scripts/redesign_mage_ranger_tiers.py
QA:  sprite_qa.py --y-min 2 (helmets), default (shirts),
     --y-max 62 (pants m), --y-max 63 (pants f, boots)
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_shade
from gen_mage_ranger_tiers import (MAGE, RANGER, hx, hsv1, to_hsv, from_hsv,
                                   frames, load, shade, OUTLINE_V,
                                   pants_details, boots_details, _setpx, CHAR)

FW, FH, COLS, NFR = 80, 64, 10, 70
HOOD_X0, HOOD_Y0 = 35, 22          # tier-1 hood bbox origin in frame 0

# ── Quantized tone levels (shadow / base / highlight) ────────────────────────

Q_LO, Q_HI = 0.85, 1.18            # v/vref thresholds
Q_LEVELS = (0.70, 1.00, 1.38)      # authored ratio per tone


def _quant(ratio):
    """Collapse a continuous v/vref ratio array to 3 authored levels."""
    return np.select([ratio < Q_LO, ratio > Q_HI],
                     [Q_LEVELS[0], Q_LEVELS[2]], Q_LEVELS[1])


def recolor_mage_q(arr, tier):
    """Mage remap with quantized tones (see gen_mage_ranger_tiers.recolor_mage)."""
    P = MAGE[tier]
    out = arr.copy()
    op = out[..., 3] > 10
    rgb = out[..., :3][op]
    h, s, v = to_hsv(rgb)
    touch = v > OUTLINE_V
    base = touch & (h >= 215) & (h <= 315)
    trim = touch & (h >= 35) & (h <= 70) & (s >= 0.40)

    nh, ns, nv = h.copy(), s.copy(), v.copy()
    if base.any():
        vref = float(np.median(v[base]))
        th, ts, tv = hsv1(P['base'])
        q = _quant(v / max(vref, 1e-3))
        nh[base] = th
        ns[base] = np.clip(0.85 * ts + 0.15 * s[base], 0.0, 1.0)
        nv[base] = np.clip(tv * q[base], 0.05, 1.0)
        if P.get('shimmer'):                       # t5 purple shimmer on highlights
            hi = base & (q > 1.2)
            nh[hi] = 268.0
            ns[hi] = ns[hi] * 0.85
            nv[hi] = np.clip(nv[hi] * 1.5, 0.0, 0.40)
        if 'purple' in P:                          # t6 purple highlight tone
            hi = base & (q > 1.2)
            ph, ps, pv = hsv1(P['purple'])
            nh[hi] = ph
            ns[hi] = ps
            nv[hi] = np.clip(pv * 0.85, 0.0, 0.62)
    if trim.any():
        vref = float(np.median(v[trim]))
        th, ts, tv = hsv1(P['trim'])
        q = _quant(v / max(vref, 1e-3))
        nh[trim] = th
        ns[trim] = ts
        nv[trim] = np.clip(tv * np.clip(q[trim], 0.75, 1.25), 0.10, 1.0)

    out[..., :3][op] = from_hsv(nh, ns, nv)
    return out


def recolor_ranger_q(arr, tier):
    """Ranger remap with quantized tones per material class."""
    P = RANGER[tier]
    out = arr.copy()
    op = out[..., 3] > 10
    rgb = out[..., :3][op]
    h, s, v = to_hsv(rgb)
    touch = v > OUTLINE_V
    green = touch & (h >= 70) & (h <= 165)
    leather = touch & (h >= 4) & (h < 48)
    strap = leather & (s > 0.72) & (v > 0.45)
    tan = leather & (s < 0.45) & ~strap
    brown = leather & ~strap & ~tan

    nh, ns, nv = h.copy(), s.copy(), v.copy()
    if green.any():
        vref = float(np.median(v[green]))
        th, ts, tv = hsv1(P['green'])
        q = _quant(v / max(vref, 1e-3))
        nh[green] = th
        ns[green] = np.clip(0.85 * ts + 0.15 * s[green], 0.0, 1.0)
        nv[green] = np.clip(tv * q[green], 0.05, 1.0)
    for mask, mode in ((brown, P['brown']), (strap, P['strap']), (tan, P['tan'])):
        if not mask.any():
            continue
        kind, val = mode
        vref = float(np.median(v[mask]))
        q = _quant(v[mask] / max(vref, 1e-3))
        if kind == 'scale':
            nv[mask] = np.clip(vref * val * q, 0.05, 1.0)
        else:
            th, ts, tv = hsv1(val)
            nh[mask] = th
            ns[mask] = ts
            nv[mask] = np.clip(tv * q, 0.05, 1.0)

    out[..., :3][op] = from_hsv(nh, ns, nv)
    return out


# ── Authored shirt details ───────────────────────────────────────────────────

def _dark(fr, y, x, k):
    fr[y, x, :3] = np.clip(fr[y, x, :3].astype(np.float32) * k, 0, 255).astype(np.uint8)


def shirt_details_v2(arr, cls, tier, P):
    acc = P['accent']
    for sy, sx in frames():
        fr = arr[sy, sx]
        a = fr[..., 3] > 10
        if not a.any():
            continue
        vmax = fr[..., :3].astype(np.float32).max(-1) / 255.0
        paint = a & (vmax > OUTLINE_V)
        ys, xs = np.where(a)
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        w = max(1, x1 - x0)
        hh = max(1, y1 - y0)
        xc = int(round(x0 + 0.5 * w))
        cols = np.unique(xs)
        top = {int(x): int(ys[xs == x].min()) for x in cols}
        bot = {int(x): int(ys[xs == x].max()) for x in cols}

        if cls == 'mage':
            # collar border: 1px accent along the neckline (all tiers)
            for x in top:
                rel = (x - x0) / w
                if 0.32 <= rel <= 0.68 and top[x] <= y0 + 1:
                    _setpx(fr, top[x], x, acc)
            # chest stripe (t3+): 1px at t3, 2px azure band at t4
            if tier >= 3:
                stripe = P.get('azure', P['trim'])
                rows = (1, 2)[tier == 4]
                yr = int(round(y0 + 0.42 * hh))
                for dy in range(rows):
                    for x in top:
                        rel = (x - x0) / w
                        if 0.28 <= rel <= 0.72 and paint[yr + dy, x]:
                            _setpx(fr, yr + dy, x, stripe)
            # rune dots (t4+): symmetric accent pixels on the upper chest
            if tier >= 4:
                yr = y0 + 2
                for x in (xc - 2, xc + 1):
                    if paint[yr, x]:
                        _setpx(fr, yr, x, acc)
            # center rune line (t6): pale gold column down the chest
            if tier == 6:
                for y in range(int(y0 + 0.30 * hh), int(y0 + 0.62 * hh) + 1):
                    if paint[y, xc]:
                        _setpx(fr, y, xc, P['trim'], 0.95)
            # cuff trim (t4+)
            if tier >= 4:
                for x in top:
                    rel = (x - x0) / w
                    if rel <= 0.18 or rel >= 0.82:
                        _setpx(fr, bot[x], x, acc, 0.9)
        else:  # ranger
            # stitching (t2+): alternating dark pixels down the center chest
            for y in range(y0 + 2, y1 - 1, 2):
                if paint[y, xc]:
                    _dark(fr, y, xc, 0.55)
            # shoulder patch outline (t3+): darker box on the receding shoulder
            if tier >= 3:
                px0 = x0 + max(1, int(round(0.10 * w)))
                for x in range(px0, px0 + 3):
                    for y in (y0 + 1, y0 + 3):
                        if paint[y, x]:
                            _dark(fr, y, x, 0.60)
                for y in (y0 + 2,):
                    for x in (px0, px0 + 2):
                        if paint[y, x]:
                            _dark(fr, y, x, 0.60)
            # buckle (t4+): 3x3 accent-bordered square at center chest
            if tier >= 4:
                ym = int(round(y0 + 0.50 * hh))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        y, x = ym + dy, xc + dx
                        if not paint[y, x]:
                            continue
                        if dy == 0 and dx == 0:
                            _dark(fr, y, x, 0.50)
                        else:
                            _setpx(fr, y, x, acc, 0.92)
            # cuff trim (t4+)
            if tier >= 4:
                for x in top:
                    rel = (x - x0) / w
                    if rel <= 0.18 or rel >= 0.82:
                        _setpx(fr, bot[x], x, acc, 0.9)


# ── Hat authoring (frame-0 coordinates) ──────────────────────────────────────
# Tones: D dark / M mid / L highlight / A accent band / S star / O outline

MAGE_HAT = {
    2: dict(D=(60, 16, 102), M=(90, 24, 154), L=(123, 47, 196), A=(192, 192, 192), cone=9),
    3: dict(D=(29, 17, 69),  M=(45, 27, 105), L=(70, 48, 155),  A=(192, 192, 192), cone=11),
    4: dict(D=(16, 16, 62),  M=(26, 26, 94),  L=(46, 46, 143),  A=(255, 215, 0),
            S=(255, 240, 160), cone=12, tip_star=True),
    5: dict(D=(8, 8, 28),    M=(13, 13, 43),  L=(58, 40, 110),  A=(255, 215, 0),
            S=(226, 226, 255), cone=13, lean=-1, stars=2),
    6: dict(D=(5, 5, 16),    M=(10, 10, 26),  L=(93, 58, 150),  A=(240, 230, 140),
            S=(255, 240, 160), cone=15, wide=True, gold_rim=True, tip_star=True),
}

RANGER_HAT = {
    2: dict(D=(36, 66, 31),  M=(58, 107, 53), L=(79, 143, 73),
            F=[(139, 105, 20)] * 3),
    3: dict(D=(18, 41, 14),  M=(31, 71, 24),  L=(50, 109, 40),
            F=[(184, 134, 11)] * 5),
    4: dict(D=(14, 33, 16),  M=(26, 58, 21),  L=(44, 92, 36),  A=(184, 115, 51),
            F=[(232, 232, 232)] * 3 + [(85, 85, 85)]),
    5: dict(D=(8, 26, 6),    M=(15, 46, 10),  L=(30, 74, 24),  A=(192, 192, 192),
            F=[(245, 245, 245)] * 5),
    6: dict(D=(5, 13, 5),    M=(10, 20, 10),  L=(28, 51, 24),  A=(218, 165, 32),
            F=[(45, 90, 39)] * 3 + [(240, 240, 240)] * 2 + [(255, 215, 0)]),
}


def _outline(fill):
    """Black outside-outline around a filled pixel set (4-neighbor)."""
    o = set()
    for (x, y) in fill:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in fill:
                o.add((x + dx, y + dy))
    return o


def build_mage_hat(tier):
    """Return {(x,y): (r,g,b)} for the tier's wizard hat, frame-0 coords."""
    P = MAGE_HAT[tier]
    fill = {}
    bw = 14 if P.get('wide') else 12
    bx0 = 40 - bw // 2
    for x in range(bx0, bx0 + bw):              # brim: top lit, underside dark
        fill[(x, 20)] = 'M'
        fill[(x, 21)] = 'D'
    if P.get('gold_rim'):                       # t6 glowing rim at brim edges
        fill[(bx0, 20)] = 'A'
        fill[(bx0 + bw - 1, 20)] = 'A'
    cw = 8
    c0 = 40 - cw // 2                           # cone base x36..43
    for x in range(c0, c0 + cw):                # hatband row
        fill[(x, 19)] = 'A'
    H = P['cone']                               # cone rows above the band
    lean = P.get('lean', 0)
    for i in range(H):
        y = 18 - i
        t = i / max(1, H - 1)
        wdt = max(2, int(round(cw * (1 - t) + 2 * t)))
        off = int(round(lean * t))
        rx0 = 40 - wdt // 2 + off
        for x in range(rx0, rx0 + wdt):
            rel = (x - rx0) / max(1, wdt - 1)
            fill[(x, y)] = 'D' if rel < 0.3 else ('L' if 0.55 <= rel <= 0.8 else 'M')
    # stars
    tip_y = 18 - (H - 1)
    tip_x = 40 - 1 + int(round(lean))
    if P.get('tip_star'):
        fill[(tip_x, tip_y)] = 'S'
    if P.get('stars'):
        fill[(41, tip_y + 4)] = 'S'
        fill[(38, tip_y + 8)] = 'S'
    out = {}
    for (x, y) in _outline(set(fill)):
        out[(x, y)] = (0, 0, 0)
    for (x, y), tone in fill.items():
        out[(x, y)] = P[tone] if isinstance(tone, str) else tone
    return out


def build_ranger_hat(tier):
    """Return {(x,y): (r,g,b)} for the tier's Robin Hood hat, frame-0 coords."""
    P = RANGER_HAT[tier]
    fill = {}
    for x in range(33, 46):                     # brim: lit top, dark underside
        fill[(x, 20)] = 'M'
        fill[(x, 21)] = 'D'
    fill[(33, 21)] = 'D'                        # left side dips...
    fill[(34, 21)] = 'D'
    fill[(44, 19)] = 'M'                        # ...right side tilts up
    fill[(45, 19)] = 'M'
    if 'A' in P:                                # t4+ metal rim at brim edges
        fill[(33, 20)] = 'A'
        fill[(45, 19)] = 'A'
    for x in range(36, 44):                     # crown: hatband + dome
        fill[(x, 19)] = 'D'
        fill[(x, 18)] = 'M'
    for x in range(37, 43):
        fill[(x, 17)] = 'M'
    for x in range(37, 43):
        fill[(x, 16)] = 'M'
    for x in range(38, 42):
        fill[(x, 15)] = 'L'
    for x in (42,):                             # right edge catches light
        fill[(x, 17)] = 'L'
        fill[(x, 16)] = 'L'
    for y in (16, 17, 18):                      # center crease
        fill[(39, y)] = 'D'
    out = {}
    for (x, y) in _outline(set(fill)):
        out[(x, y)] = (0, 0, 0)
    for (x, y), tone in fill.items():
        out[(x, y)] = P[tone]
    # feather: authored path up-right from the crown, drawn over the outline
    path = [(44, 16), (45, 15), (46, 14), (47, 13), (48, 12), (48, 11)]
    for (x, y), c in zip(path, P['F']):
        out[(x, y)] = c
    if len(P['F']) >= 4:                        # thicker plume base on long feathers
        out[(44, 17)] = P['F'][0]
    return out


# ── Helmet sheet composition ─────────────────────────────────────────────────

def hood_pixels(cls, ramp):
    """Tier-1 hood frame 0 quantized to the tier's 3-tone ramp (+ outline)."""
    src = load('helmet_%s1.png' % cls)[:FH, :FW]
    op = np.argwhere(src[..., 3] > 0)
    v = src[..., :3].astype(np.float32).max(-1) / 255.0
    vals = [v[y, x] for y, x in op if v[y, x] > OUTLINE_V]
    vmed = float(np.median(vals))
    px = {}
    for y, x in op:
        if v[y, x] <= OUTLINE_V:
            px[(int(x), int(y))] = (0, 0, 0)
        else:
            r = v[y, x] / vmed
            px[(int(x), int(y))] = ramp['D' if r < Q_LO else ('L' if r > Q_HI else 'M')]
    return px


def hood_offsets(cls):
    """Per-frame (dx, dy) of the tier-1 hood relative to frame 0."""
    a = load('helmet_%s1.png' % cls)
    offs = {}
    for fi in range(NFR):
        r, c = fi // COLS, fi % COLS
        f = a[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW]
        op = np.argwhere(f[..., 3] > 0)
        if len(op):
            offs[fi] = (int(op[:, 1].min()) - HOOD_X0, int(op[:, 0].min()) - HOOD_Y0)
    return offs


def compose_helmet(cls, tier):
    ramp = (MAGE_HAT if cls == 'mage' else RANGER_HAT)[tier]
    hat = build_mage_hat(tier) if cls == 'mage' else build_ranger_hat(tier)
    hood = hood_pixels(cls, ramp)
    sheet = np.zeros((FH * 7, FW * COLS, 4), np.uint8)
    for fi, (dx, dy) in hood_offsets(cls).items():
        r, c = fi // COLS, fi % COLS
        gx, gy = c * FW, r * FH
        for layer in (hood, hat):
            for (x, y), rgb in layer.items():
                px, py = x + dx, y + dy
                if 0 <= px < FW and 0 <= py < FH:
                    sheet[gy + py, gx + px] = (*rgb, 255)
    return sheet


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    made = []
    for cls, rec, pal in (('mage', recolor_mage_q, MAGE),
                          ('ranger', recolor_ranger_q, RANGER)):
        for tier in range(2, 7):
            P = pal[tier]
            jobs = [
                ('shirt', 'shirt_%s1.png' % cls,   'shirt_%s%d.png' % (cls, tier)),
                ('shirt', 'shirt_%s1_f.png' % cls, 'shirt_%s%d_f.png' % (cls, tier)),
                ('pants', 'pants_%s1.png' % cls,   'pants_%s%d.png' % (cls, tier)),
                ('pants', 'pants_%s1_f.png' % cls, 'pants_%s%d_f.png' % (cls, tier)),
                ('boots', 'boots_%s1.png' % cls,   'boots_%s%d.png' % (cls, tier)),
                ('boots', 'boots_%s1_f.png' % cls, 'boots_%s%d_f.png' % (cls, tier)),
            ]
            for slot, src, dst in jobs:
                arr = rec(load(src), tier)
                if slot == 'shirt':
                    shirt_details_v2(arr, cls, tier, P)
                    arr = shade(arr, adj_min=-0.20, adj_max=0.25)
                elif slot == 'pants':
                    pants_details(arr)
                    arr = shade(arr)
                else:
                    boots_details(arr, P['accent'])
                    arr = shade(arr)
                Image.fromarray(arr).save(CHAR + dst)
                made.append(dst)
                print('wrote %s' % dst)
            dst = 'helmet_%s%d.png' % (cls, tier)
            Image.fromarray(compose_helmet(cls, tier)).save(CHAR + dst)
            made.append(dst)
            print('wrote %s' % dst)
    print('%d sheets generated' % len(made))


if __name__ == '__main__':
    main()
