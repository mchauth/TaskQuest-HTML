#!/usr/bin/env python3
"""Redesign mage chest tiers 2-3 (shirt_mage2/3 + _f) — v2 "clean robes".

The redesign_mage_ranger_tiers.py output for T2/T3 stamped a black-outlined
chest panel (34 pure-#000 px forming a rectangle across rows 35-39) that
renders as a giant black blob at game scale. This script rebuilds both tiers
from the shirt_mage1[.png/_f] silhouette (which tracks every pose) with the
same authoring philosophy as redesign_mage_hats.py:

  Tones   : T1's per-pixel V is quantized against the frame median into an
            authored 3-tone ramp (shadow / base / highlight) per tier, so
            sprite_shade's diffusion produces smooth fabric gradients, not
            noise, and NO interior black.
  T2      : royal purple #4A0080 ramp (matches t2 pants/boots/hat palette).
            Silver collar band at the neckline, dark fold column left of
            center, dark sleeve cuffs, hem crease + lavender under-robe hem
            band (#8A70D6), hem flared 1 px each side on the bottom 2 rows
            for the flowing-robe silhouette (wider at hem than shoulders).
  T3      : indigo #2A1555 ramp (matches t3 set). Silver collar with a
            V-point, bronze waist sash (#B87333) with a dark-bronze knot —
            from the wizard reference (IMG_8157: contrasting collar + waist
            sash) — silver cuffs, fold columns both sides of center below
            the sash (pleats), same flared under-robe hem.
  Accents : collar/cuff silver is (230,230,230) so it passes sprite_shade's
            accent test (r>=230 & g>=190) and stays crisp instead of being
            diffused into the purple. Bronze sash is fabric — it shades.
  Female  : same tones/collar/sash/folds on the off-shoulder silhouette;
            no hem flare (the _f garment tapers to a V front flap — flaring
            would break the hip line). Bottom edge of the flap gets the
            shadow tone so the taper reads as a draped fold.
  Sleep   : frames fi>=60 (lying poses) skip the flare + sash (a horizontal
            sash across a lying bbox is wrong); tones/collar still apply.

Run from repo root:
  python3 scripts/redesign_mage_chest_t23.py
Then QA (defaults, y 16..52):
  python3 scripts/sprite_qa.py sprites/preview_assets/char/shirt_mage2.png
Shading is applied in-script with the shirt override (ADJ_MIN=-0.20,
ADJ_MAX=+0.25, BELL_WIDTH=0.7) — do NOT run sprite_shade.py again on top.
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_mage_ranger_tiers import load, shade, CHAR

FW, FH, COLS, NFR = 80, 64, 10, 70
Q_LO, Q_HI = 0.85, 1.18            # v/vref quantization thresholds (house style)

TIERS = {
    2: dict(D=(46, 8, 82),   M=(76, 12, 130), L=(116, 40, 186),
            ACC=(230, 230, 230), UNDER=(138, 112, 214), sash=False, vpoint=False,
            cuff='D'),
    3: dict(D=(22, 12, 46),  M=(44, 24, 88),  L=(76, 52, 152),
            ACC=(230, 230, 230), UNDER=(120, 96, 196), sash=True, vpoint=True,
            cuff='ACC', SASH=(184, 115, 51), KNOT=(139, 69, 19)),
}


def put(fr, y, x, rgb):
    if 0 <= y < FH and 0 <= x < FW:
        fr[y, x, :3] = rgb
        fr[y, x, 3] = 255


def build_tier(base, tier, female):
    P = TIERS[tier]
    out = np.zeros_like(base)
    for fi in range(NFR):
        r, c = fi // COLS, fi % COLS
        sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
        src = base[sl]
        a = src[..., 3] > 0
        if not a.any():
            continue
        fr = out[sl]

        # ── 1. quantized 3-tone recolor of the T1 silhouette ────────────────
        v = src[..., :3].astype(np.float32).max(-1) / 255.0
        vref = float(np.median(v[a]))
        ratio = v / max(vref, 1e-3)
        for y, x in np.argwhere(a):
            q = ratio[y, x]
            tone = P['D'] if q < Q_LO else (P['L'] if q > Q_HI else P['M'])
            put(fr, y, x, tone)

        # ── 2. frame geometry ────────────────────────────────────────────────
        ys, xs = np.where(a)
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
        w = max(1, x1 - x0)
        hh = max(1, y1 - y0)
        xc = int(round(x0 + 0.5 * w))
        cols = np.unique(xs)
        top = {int(x): int(ys[xs == x].min()) for x in cols}
        bot = {int(x): int(ys[xs == x].max()) for x in cols}
        sleeping = fi >= 60

        # ── 3. collar: silver band anchored to the NECK, not the bbox top ────
        # (cheer/slash frames raise the arms above the neckline — a bbox-top
        # rule sprays collar px along the raised sleeves as white noise)
        neck = min(top[x] for x in (xc - 1, xc, xc + 1) if x in top)
        span = 3 if female else 2
        for x in cols:
            if abs(x - xc) <= span and abs(top[x] - neck) <= 1:
                put(fr, top[x], x, P['ACC'])
        if P['vpoint'] and xc in top:            # T3: V-point one row lower
            vy = top[xc] + 1
            if vy < FH and a[vy, xc]:
                put(fr, vy, xc, P['ACC'])

        # ── 4. sleeve cuffs: bottom px of short outer columns ────────────────
        # Idle/walk/run rows only (fi < 30): on cheer/jump/slash frames the
        # raised arms are the outer columns, and a per-column bottom rule
        # traces a stray accent diagonal up the sleeve.
        if fi < 30:
            cuff_rgb = P['D'] if P['cuff'] == 'D' else P['ACC']
            for x in cols:
                rel = (x - x0) / w
                if (rel <= 0.16 or rel >= 0.84) and bot[x] < y1 - 2:
                    put(fr, bot[x], x, cuff_rgb)

        # ── 5. waist sash (T3, upright frames) ───────────────────────────────
        # Anchored to the neck, not the bbox top — raised arms stretch the
        # bbox upward and a fractional-height sash rides up to the chest.
        if P['sash'] and not sleeping:
            y_s = min(neck + (5 if female else 7), y1 - 3)
            for x in cols:
                rel = (x - x0) / w
                if 0.12 <= rel <= 0.88 and a[y_s, x]:
                    put(fr, y_s, x, P['SASH'])
            for x in (xc, xc + 1):               # knot
                if a[y_s, x]:
                    put(fr, y_s, x, P['KNOT'])

        # ── 6. fold columns below the waist (pleats) ─────────────────────────
        y_mid = int(round(y0 + 0.55 * hh))
        folds = (xc - 2, xc + 2) if P['sash'] else (xc - 2,)
        for fx in folds:
            for y in range(y_mid + 1, y1 - 1):
                if a[y, fx]:
                    put(fr, y, fx, P['D'])

        # ── 7. hem ───────────────────────────────────────────────────────────
        if female:
            # front-flap taper: shadow the bottom edge of each column
            for x in cols:
                if bot[x] >= y1 - 2:
                    put(fr, bot[x], x, P['D'])
        else:
            hem_cols = [x for x in cols if bot[x] >= y1 - 1]
            hx0, hx1 = min(hem_cols), max(hem_cols)
            for x in range(hx0, hx1 + 1):
                if a[y1 - 1, x]:
                    put(fr, y1 - 1, x, P['D'])       # crease shadow row
                if a[y1, x]:
                    put(fr, y1, x, P['UNDER'])       # under-robe band
            if not sleeping:                          # robe flare, 1 px/side
                for y, rgb in ((y1 - 1, P['D']), (y1, P['UNDER'])):
                    for x in (hx0 - 1, hx1 + 1):
                        if 30 <= x <= 54 and fr[y, x, 3] == 0:
                            put(fr, y, x, rgb)
    return out


def main():
    for suffix, female in (('', False), ('_f', True)):
        base = load('shirt_mage1%s.png' % suffix)
        for tier in (2, 3):
            arr = build_tier(base, tier, female)
            arr = shade(arr, adj_min=-0.20, adj_max=0.25)
            dst = 'shirt_mage%d%s.png' % (tier, suffix)
            Image.fromarray(arr).save(CHAR + dst)
            print('wrote %s' % dst)


if __name__ == '__main__':
    main()
