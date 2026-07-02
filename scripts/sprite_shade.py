#!/usr/bin/env python3
"""
sprite_shade.py — Add convex shading to flat-colored armor sprites.

Usage:
  python3 scripts/sprite_shade.py <input.png> <output.png> [--alpha-threshold 10]

Shading model (light from the right, 3/4 perspective):
  rel_x < 35   : deep shadow  → darken 35%
  rel_x 35–38  : shadow zone  → darken 25%
  rel_x 39–41  : highlight    → lighten 20%
  rel_x 42–44  : base zone    → no change
  rel_x 45+    : wrap shadow  → darken 15%

Plus vertical gradient: top of armor ≈ +10%, bottom ≈ –10%.

Armor pixels are defined as: opaque (alpha ≥ threshold), not outline
(brightness < 30), not skin (#F4A460 ±20), not hair colors.

RGB adjustments are made in HSV space (V channel only) to avoid hue shift.
"""

import sys
import argparse
import numpy as np
from PIL import Image

FRAME_W, FRAME_H = 80, 64
COLS, ROWS = 10, 7

# Skin color and tolerance
SKIN_RGB = np.array([244, 164, 96], dtype=np.float32)
SKIN_TOL = 20

# Hair color palette (dark → silver, covering all 5 game variants)
# These are approximate palette entries; actual sprite pixels may vary slightly.
HAIR_PALETTE = np.array([
    [40,  25,  12],   # Dark (very dark brown)
    [80,  40,  15],   # Auburn dark
    [110, 60,  20],   # Auburn mid
    [150, 90,  40],   # Brown mid
    [200, 160, 80],   # Blonde
    [210, 210, 210],  # Silver light
    [180, 180, 180],  # Silver mid
    [155, 155, 155],  # Silver dark
    [60,  30,  10],   # Dark variant 2
    [190, 130, 60],   # Warm blonde
], dtype=np.float32)
HAIR_TOL = 15   # tight tolerance — avoids false-positives on dark-gold armor colors


# ── LUTs ──────────────────────────────────────────────────────────────────────

def _build_x_factor_lut() -> np.ndarray:
    """Float32 array [0..FRAME_W): brightness multiplier by x position."""
    lut = np.ones(FRAME_W, dtype=np.float32)
    for x in range(FRAME_W):
        if x < 35:
            lut[x] = 0.65   # deep shadow: darken 35%
        elif x <= 38:
            lut[x] = 0.75   # shadow zone: darken 25%
        elif x <= 41:
            lut[x] = 1.20   # highlight:   lighten 20%
        elif x <= 44:
            lut[x] = 1.00   # base zone:   no change
        else:
            lut[x] = 0.85   # wrap shadow: darken 15%
    return lut


def _build_y_factor_lut() -> np.ndarray:
    """Float32 array [0..FRAME_H): brightness multiplier by y position."""
    lut = np.ones(FRAME_H, dtype=np.float32)
    Y_TOP, Y_BOT = 28, 45
    for y in range(FRAME_H):
        if y <= Y_TOP:
            lut[y] = 1.10
        elif y >= Y_BOT:
            lut[y] = 0.90
        else:
            t = (y - Y_TOP) / (Y_BOT - Y_TOP)
            lut[y] = 1.10 - t * 0.20   # linear 1.10 → 0.90
    return lut


X_FACTOR = _build_x_factor_lut()
Y_FACTOR = _build_y_factor_lut()

# Combined factor grid: shape (FRAME_H, FRAME_W)
COMBINED_FACTOR = (Y_FACTOR[:, np.newaxis] * X_FACTOR[np.newaxis, :])


# ── Pixel classification helpers ───────────────────────────────────────────────

def _brightness(rgb: np.ndarray) -> np.ndarray:
    """Mean brightness per pixel. rgb shape (..., 3), returns (...)."""
    return rgb.mean(axis=-1)


def _is_skin(rgb: np.ndarray) -> np.ndarray:
    """Boolean mask: True where pixel is within SKIN_TOL of skin color."""
    diff = np.abs(rgb.astype(np.float32) - SKIN_RGB)
    return (diff <= SKIN_TOL).all(axis=-1)


def _is_hair(rgb: np.ndarray) -> np.ndarray:
    """Boolean mask: True where pixel is within HAIR_TOL of any hair color."""
    # rgb: (H, W, 3), result: (H, W)
    h, w = rgb.shape[:2]
    rf = rgb.astype(np.float32).reshape(-1, 1, 3)     # (H*W, 1, 3)
    palette = HAIR_PALETTE[np.newaxis, :, :]           # (1, P, 3)
    diffs = np.abs(rf - palette).max(axis=-1)          # (H*W, P) — Chebyshev
    closest = diffs.min(axis=-1)                       # (H*W,)
    return (closest <= HAIR_TOL).reshape(h, w)


# ── HSV brightness adjustment (vectorised) ────────────────────────────────────

def _adjust_v(rgb: np.ndarray, factors: np.ndarray) -> np.ndarray:
    """
    Scale the V (value) channel of each pixel by factors[y,x] without
    shifting hue or saturation.

    Parameters
    ----------
    rgb     : uint8 (H, W, 3)
    factors : float32 (H, W)

    Returns
    -------
    uint8 (H, W, 3)
    """
    rf = rgb.astype(np.float32)
    v = rf.max(axis=-1)                          # V = max(R,G,B), shape (H,W)
    v_new = np.clip(v * factors, 0.0, 255.0)

    # Scale factor per pixel: avoid div-by-zero on pure black
    scale = np.where(v > 0, v_new / np.maximum(v, 1e-9), 1.0)  # (H,W)
    result = np.clip(rf * scale[:, :, np.newaxis], 0, 255)
    return result.astype(np.uint8)


# ── Main shading routine ───────────────────────────────────────────────────────

def shade_sprite(
    arr: np.ndarray,
    alpha_threshold: int = 10,
) -> np.ndarray:
    """
    Apply convex shading to all armor pixels in the sprite sheet.

    Parameters
    ----------
    arr              : uint8 RGBA array (448, 800, 4)
    alpha_threshold  : minimum alpha to consider a pixel opaque

    Returns
    -------
    uint8 RGBA (448, 800, 4) — alpha channel untouched
    """
    out = arr.copy()

    for row in range(ROWS):
        for col in range(COLS):
            gy = row * FRAME_H
            gx = col * FRAME_W

            frame = arr[gy:gy+FRAME_H, gx:gx+FRAME_W]   # (64, 80, 4)
            rgb   = frame[:, :, :3]
            alpha = frame[:, :,  3]

            # --- build armor mask ---
            opaque    = alpha >= alpha_threshold
            outline   = _brightness(rgb.astype(np.float32)) < 30
            skin_mask = _is_skin(rgb)
            hair_mask = _is_hair(rgb)

            armor_mask = opaque & ~outline & ~skin_mask & ~hair_mask

            if not armor_mask.any():
                continue

            # --- apply shading only within this frame ---
            rgb_shaded = _adjust_v(rgb, COMBINED_FACTOR)

            # Write back: only armor pixels change, alpha untouched
            new_rgb = rgb.copy()
            new_rgb[armor_mask] = rgb_shaded[armor_mask]
            out[gy:gy+FRAME_H, gx:gx+FRAME_W, :3] = new_rgb

    return out


# ── CLI ────────────────────────────────────────────────────────────────────────

def print_sample(arr: np.ndarray, label: str):
    """Print shading gradient samples from frame 0 for visual verification."""
    print(f"\n── {label} frame-0 samples (frame 0 = top-left 80×64 crop) ──")
    print(f"  {'y':>3}  {'x=36':>14}  {'x=40':>14}  {'x=43':>14}")
    for y in [30, 34, 38, 42, 46]:
        def fmt(x):
            r, g, b, a = arr[y, x]
            return f"({r:3},{g:3},{b:3})" if a > 10 else "    transp    "
        print(f"  {y:>3}  {fmt(36)}  {fmt(40)}  {fmt(43)}")


def main():
    parser = argparse.ArgumentParser(
        description="Add convex shading to flat-colored armor sprite sheets."
    )
    parser.add_argument("input",  help="Input PNG sprite sheet (800×448)")
    parser.add_argument("output", help="Output PNG path")
    parser.add_argument(
        "--alpha-threshold", type=int, default=10,
        help="Min alpha to treat pixel as opaque (default 10)"
    )
    parser.add_argument(
        "--samples", action="store_true",
        help="Print pixel value samples at x=36,40,43 for visual verification"
    )
    args = parser.parse_args()

    img = Image.open(args.input).convert("RGBA")
    if img.size != (800, 448):
        print(f"WARNING: expected 800×448, got {img.size}", file=sys.stderr)

    arr = np.array(img, dtype=np.uint8)

    if args.samples:
        print_sample(arr, f"BEFORE {args.input}")

    shaded = shade_sprite(arr, alpha_threshold=args.alpha_threshold)

    if args.samples:
        print_sample(shaded, f"AFTER  {args.output}")

    Image.fromarray(shaded).save(args.output)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
