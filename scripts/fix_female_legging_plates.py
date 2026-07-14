#!/usr/bin/env python3
"""fix_female_legging_plates.py — restore female pants/boots from the
pre-brightening baseline and apply real plate shading instead of a flat
brightness lift.

Pipeline per sprite (base = HEAD~1 pre-lift PNG):
  1. Cosine shading pass (sprite_shade.py) with deeper shadows:
       ADJ_MIN=-0.20, ADJ_MAX=0.25, METALLIC_PEAK=0.25 (moderate highlights)
  2. Plate seam lines: rows where >=50% of overlapping armor columns show a
     significant color shift (max channel diff > 35) in the AUTHORED base
     are treated as plate boundaries; both boundary rows get V*0.6.
  3. Silhouette edge darkening: armor pixels horizontally adjacent to the
     outline/background get V*0.75 (3D rounded leg look).
  4. Boots only: cuff separation — pixel 2 rows below the boot top (i.e.
     immediately below the 2-row trim) gets V*0.65.

Usage: python3 fix_female_legging_plates.py <base_dir> <out_dir>
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sprite_shade as ss

# Deeper shadows / moderate highlights per plate-shading spec
ss.ADJ_MIN = -0.20
ss.ADJ_MAX = 0.25
ss.METALLIC_PEAK = 0.25   # keep metal peak at the same moderate ceiling
ss.X_ADJ = ss._build_x_adj_lut()

FRAME_W, FRAME_H = ss.FRAME_W, ss.FRAME_H
COLS, ROWS = ss.COLS, ss.ROWS

PANTS = [
    "armor_pants_2_f", "armor_pants_3_f", "armor_pants_4_f",
    "armor_pants_5_f", "armor_pants_6_f", "leather_pants_1_f",
    "pants_mage1_f", "pants_ranger1_f", "pants_rare1_f",
    "pants_rare2_f", "pants_rare3_f", "warrior_pants_default_f",
]
BOOTS = ["boots_rare1_f", "boots_rare2_f", "boots_rare3_f"]

SEAM_DIFF = 35        # max-channel diff that counts as a plate color shift
SEAM_FRACTION = 0.5   # fraction of overlapping columns that must agree
SEAM_MIN_COLS = 3     # and at least this many columns
SEAM_DARK = 0.6       # V multiplier on both boundary rows
EDGE_DARK = 0.75      # V multiplier 1px inside the silhouette edge
CUFF_DARK = 0.65      # V multiplier just below the boot trim


def scale_v(frame, ys, xs, factor):
    """Uniform RGB scale (V-channel darken, hue/sat preserved)."""
    rgb = frame[ys, xs, :3].astype(np.float32) * factor
    frame[ys, xs, :3] = np.clip(rgb, 0, 255).astype(np.uint8)


def plate_boundaries(base_frame, armor):
    """Boundary rows (y, y+1 pairs) where the authored plate color shifts."""
    rgb = base_frame[:, :, :3].astype(np.int16)
    rows = []
    prev = -10
    for y in range(FRAME_H - 1):
        both = armor[y] & armor[y + 1]
        n = int(both.sum())
        if n < SEAM_MIN_COLS:
            continue
        diff = np.abs(rgb[y + 1] - rgb[y]).max(axis=-1)
        shifted = int((diff[both] > SEAM_DIFF).sum())
        if shifted >= max(SEAM_MIN_COLS, SEAM_FRACTION * n) and y > prev + 1:
            rows.append(y)
            prev = y
    return rows


def edge_mask(frame, armor, outline):
    """Armor pixels horizontally adjacent to outline or background."""
    solid = (frame[:, :, 3] > 10) & ~outline           # armor-ish body
    open_ = ~solid                                      # outline or bg
    left = np.pad(open_, ((0, 0), (1, 0)))[:, :-1]
    right = np.pad(open_, ((0, 0), (0, 1)))[:, 1:]
    return armor & (left | right)


def process(name, base_dir, out_dir, is_boot):
    path = os.path.join(base_dir, name + ".png")
    base = np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)

    shaded, stats = ss.shade_sheet(base)

    seam_px = edge_px = cuff_px = 0
    for fi in range(COLS * ROWS):
        gx = (fi % COLS) * FRAME_W
        gy = (fi // COLS) * FRAME_H
        bframe = base[gy:gy + FRAME_H, gx:gx + FRAME_W]
        sframe = shaded[gy:gy + FRAME_H, gx:gx + FRAME_W]
        armor, outline = ss.classify(bframe)
        if not armor.any():
            continue

        # plate seams (pants and boots both benefit; detected on base)
        for y in plate_boundaries(bframe, armor):
            cols = np.flatnonzero(armor[y] & armor[y + 1])
            scale_v(sframe, np.full_like(cols, y), cols, SEAM_DARK)
            scale_v(sframe, np.full_like(cols, y + 1), cols, SEAM_DARK)
            seam_px += 2 * len(cols)

        # silhouette edge darkening
        em = edge_mask(bframe, armor, outline)
        ys, xs = np.nonzero(em)
        scale_v(sframe, ys, xs, EDGE_DARK)
        edge_px += len(ys)

        # boot cuff separation line
        if is_boot:
            for x in range(FRAME_W):
                col = np.flatnonzero(armor[:, x])
                if len(col) == 0:
                    continue
                yc = col[0] + 2
                if yc < FRAME_H and armor[yc, x]:
                    scale_v(sframe, np.array([yc]), np.array([x]), CUFF_DARK)
                    cuff_px += 1

    out = os.path.join(out_dir, name + ".png")
    Image.fromarray(shaded).save(out)
    print(f"{name:26s} shaded={stats['armor_pixels']:6d} "
          f"seam_px={seam_px:5d} edge_px={edge_px:5d} cuff_px={cuff_px:4d}")


def main():
    base_dir, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    for n in PANTS:
        process(n, base_dir, out_dir, is_boot=False)
    for n in BOOTS:
        process(n, base_dir, out_dir, is_boot=True)


if __name__ == "__main__":
    main()
