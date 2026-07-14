#!/usr/bin/env python3
"""
fix_female_shading_combat.py — one-shot fixer for female legging/boot shading
and combat-frame glitches (July 2026).

Task A (shading): female leggings measured too dark vs their corresponding
female chest piece; pre-lift V (hue-preserving) so the sheet median luminance
lands within +/-20 of the chest median, then sprite_shade.py is re-run by the
caller. Boots handled the same way (pre-dim if too bright, pre-lift if too
dark). Protected pixels: black/outline (R+G+B<15), gold accents
(R>=230,G>=190,B<100), teal accents (G>=170,B>=150,R<G), and pixels already
inside the target band [chest_median-20 .. chest_p90].

Task B (combat glitches, frames 50-55): all nine female leggings share an
identical run-remap arm contamination in frame 51 — a 7-px ledge covering the
hanging hand at (33-36,45)/(34-36,46). Cleared to transparent (skin shows
through). Stray/detached-cluster scan found zero pixels outside the dilated
skin_f1 silhouette. Value-speckle repair is done in a separate post-shade pass
(see --speckles) restricted to off-palette outliers so the sprites' intended
dither texture is not flattened.

Usage:
  python3 fix_female_shading_combat.py --prelift   # arm fix + pre-lift, prints plan
  python3 fix_female_shading_combat.py --speckles  # post-shade off-palette speckle repair
"""
import sys
import numpy as np
from PIL import Image

CHAR = 'sprites/preview_assets/char'
FRAME_W, FRAME_H = 80, 64

# legging/boot -> corresponding female chest piece
CHEST_MAP = {
    'leather_pants_1_f': 'leather_armor_1_f',
    'armor_pants_2_f': 'armor_chest_2_f',
    'armor_pants_3_f': 'armor_chest_3_f',
    'armor_pants_4_f': 'armor_chest_4_f',
    'armor_pants_5_f': 'armor_chest_5_f',
    'armor_pants_6_f': 'armor_chest_6_f',
    'pants_rare1_f': 'shirt_rare1_f',
    'pants_rare2_f': 'shirt_rare2_f',
    'pants_rare3_f': 'shirt_rare3_f',
    'boots_rare1_f': 'shirt_rare1_f',
    'boots_rare2_f': 'shirt_rare2_f',
    'boots_rare3_f': 'shirt_rare3_f',
}
LEGGINGS = [k for k in CHEST_MAP if 'pants' in k]

# frame 51 arm contamination (shared, verified identical across all 9 leggings)
ARM_LEDGE = [(33, 45), (34, 45), (35, 45), (36, 45), (34, 46), (35, 46), (36, 46)]
ARM_FRAME = 51
TOL = 20          # median must land within +/-TOL of chest median


def load(name):
    return np.array(Image.open(f'{CHAR}/{name}.png').convert('RGBA'))


def save(name, arr):
    Image.fromarray(arr).save(f'{CHAR}/{name}.png')


def eligible_mask(arr):
    rgb = arr[:, :, :3].astype(np.int16)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    opaque = arr[:, :, 3] > 10
    black = (r + g + b) < 15
    gold = (r >= 230) & (g >= 190) & (b < 100)
    teal = (g >= 170) & (b >= 150) & (r < g)
    return opaque & ~black & ~(gold | teal)


def lum_of(arr):
    rgb = arr[:, :, :3].astype(np.float32)
    return 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]


def stats(arr):
    v = lum_of(arr)[eligible_mask(arr)]
    return dict(median=float(np.median(v)), p10=float(np.percentile(v, 10)),
                p90=float(np.percentile(v, 90)), n=len(v))


def simulate_median(lum, adjust, F, vmax):
    per = np.ones_like(lum)
    per[adjust] = np.minimum(F, 255.0 / np.maximum(vmax[adjust], 1e-9))
    return float(np.median((lum * per)))


def prelift(arr, t_med, t_hi):
    """Hue-preserving V lift of dark pixels: minimal factor F that brings the
    sheet median to t_med-12 (comfortably inside the +/-20 acceptance band).
    A minimal-F forward scan is used instead of a binary search because the
    achievable median plateaus once dark pixels hit the V=255 ceiling."""
    elig = eligible_mask(arr)
    lum = lum_of(arr)
    vmax = arr[:, :, :3].astype(np.float32).max(axis=-1)
    adjust = elig & (lum < t_med - TOL)          # in-band/highlight pixels protected
    lum_e, adj_e, v_e = lum[elig], adjust[elig], vmax[elig]
    goal = t_med - 12
    F, best_F, best_m = 1.0, 1.0, simulate_median(lum_e, adj_e, 1.0, v_e)
    f = 1.0
    while f < 14.0:
        f += 0.05
        m = simulate_median(lum_e, adj_e, f, v_e)
        if m > best_m:
            best_m, best_F = m, f
        if m >= goal:
            F = f
            break
    else:
        F = best_F                                # plateau: take max reachable
    per = np.ones(arr.shape[:2], dtype=np.float32)
    per[adjust] = np.minimum(F, 255.0 / np.maximum(vmax[adjust], 1e-9))
    out = arr.copy()
    out[:, :, :3] = np.clip(
        np.round(arr[:, :, :3].astype(np.float32) * per[:, :, None]), 0, 255
    ).astype(np.uint8)
    return out, F


def fix_arm_ledge(arr):
    col, row = ARM_FRAME % 10, ARM_FRAME // 10
    gx, gy = col * FRAME_W, row * FRAME_H
    n = 0
    for x, y in ARM_LEDGE:
        if arr[gy + y, gx + x, 3] > 0:
            arr[gy + y, gx + x] = 0
            n += 1
    return n


def run_prelift():
    chest_stats = {c: stats(load(c)) for c in set(CHEST_MAP.values())}
    for name, chest in CHEST_MAP.items():
        arr = load(name)
        cleared = 0
        if name in LEGGINGS:
            cleared = fix_arm_ledge(arr)
        s = stats(arr)
        t = chest_stats[chest]
        delta = s['median'] - t['median']
        action = 'ok'
        F = 1.0
        if delta < -TOL:
            arr, F = prelift(arr, t['median'], t['p90'])
            action = f'PRELIFT F={F:.3f}'
        elif delta > TOL:
            arr, F = predim(arr, t['median'])
            action = f'PREDIM F={F:.3f}'
        save(name, arr)
        s2 = stats(arr)
        print(f"{name:20s} vs {chest:18s} med {s['median']:6.1f} -> {s2['median']:6.1f} "
              f"(target {t['median']:6.1f} delta {delta:+6.1f}) {action}"
              f"{f' armfix={cleared}px' if cleared else ''}")
        if action.startswith('PRELIFT'):
            print(f"NEEDS_SHADE {name}")


def predim(arr, t_med):
    elig = eligible_mask(arr)
    lum = lum_of(arr)
    vmax = arr[:, :, :3].astype(np.float32).max(axis=-1)
    adjust = elig & (lum > t_med + TOL)
    lo, hi = 0.05, 1.0
    lum_e, adj_e, v_e = lum[elig], adjust[elig], vmax[elig]
    for _ in range(40):
        F = 0.5 * (lo + hi)
        m = simulate_median(lum_e, adj_e, F, v_e)
        if m > t_med:
            hi = F
        else:
            lo = F
    F = 0.5 * (lo + hi)
    per = np.ones(arr.shape[:2], dtype=np.float32)
    per[adjust] = F
    out = arr.copy()
    out[:, :, :3] = np.clip(
        np.round(arr[:, :, :3].astype(np.float32) * per[:, :, None]), 0, 255
    ).astype(np.uint8)
    return out, F


def run_speckles():
    """Off-palette value-speckle repair in combat frames 50-55 (post-shade)."""
    for name in LEGGINGS:
        arr = load(name)
        pal = set()
        for fi in range(70):
            if 50 <= fi <= 55:
                continue
            c_, r_ = fi % 10, fi // 10
            fr = arr[r_ * 64:(r_ + 1) * 64, c_ * 80:(c_ + 1) * 80]
            op = fr[:, :, 3] > 0
            for y, x in zip(*np.nonzero(op)):
                pal.add(tuple(int(v) for v in fr[y, x, :3]))
        pal_arr = np.array(sorted(pal), dtype=np.int16)
        fixed = []
        for fi in range(50, 56):
            c_, r_ = fi % 10, fi // 10
            gy, gx = r_ * 64, c_ * 80
            fr = arr[gy:gy + 64, gx:gx + 80]
            op = fr[:, :, 3] > 0
            lum = lum_of(fr)
            rgb = fr[:, :, :3].astype(np.int16)
            r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
            accent = ((r >= 230) & (g >= 190) & (b < 100)) | \
                     ((g >= 170) & (b >= 150) & (r < g))
            black = (r + g + b) < 15
            for y, x in zip(*np.nonzero(op)):
                if accent[y, x] or black[y, x]:
                    continue
                c = rgb[y, x]
                if (np.abs(pal_arr - c).max(axis=1) <= 6).any():
                    continue
                nb = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < 64 and 0 <= nx < 80 and op[ny, nx]:
                            nb.append((lum[ny, nx], fr[ny, nx, :3]))
                if len(nb) >= 4 and abs(lum[y, x] - np.median([v for v, _ in nb])) > 50:
                    nb.sort(key=lambda t: t[0])
                    med_col = nb[len(nb) // 2][1]
                    arr[gy + y, gx + x, :3] = med_col
                    fixed.append((fi, int(x), int(y)))
        if fixed:
            save(name, arr)
            print(f"{name}: speckles fixed {len(fixed)}: {fixed}")
        else:
            print(f"{name}: speckles fixed 0")


if __name__ == '__main__':
    import os
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    if '--speckles' in sys.argv:
        run_speckles()
    else:
        run_prelift()
