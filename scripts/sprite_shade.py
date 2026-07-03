#!/usr/bin/env python3
"""
sprite_shade.py — Per-pixel smooth shading for armor sprite sheets.

Replaces the old zone-based shader (discrete darken/lighten bands) with a
continuous cosine-falloff lighting model. Light source: upper-right,
slightly elevated.

Usage:
  python3 scripts/sprite_shade.py <input.png> [output.png] [--dry-run] [--frame N]

If output.png is omitted the input is overwritten in place.

Shading model
-------------
Horizontal (primary light direction):
  norm_x = (px_in_frame - 30) / 24            # character zone x=30..54 -> 0..1
  intensity = cos((norm_x - 0.55) * pi * 0.8) # wide bell, peak at 0.55
  base_adj  = map intensity [-1..1] -> [-0.28 .. +0.25]

Vertical (elevated light / plate bulge):
  Within each contiguous armor segment per column, a sine bulge:
  sin(pi * t) with t = position within segment. The middle of the plate
  reads as the most forward surface. Mapped to +/-8% brightness
  (-8% at segment ends, +8% at the middle).

Edge shadow (curvature falloff):
  Distance-from-outline falloff: armor pixels within 3px of any outline
  pixel get a quadratic shadow ramp, from 0% at 3px away to -12% right
  next to the outline. No hard adjacency line.

Material response:
  metallic (HSV sat > 0.35 and val > 0.55): positive adj smoothly rescaled
      so the cosine peak reaches +0.30 (continuous curve, no bands/streaks)
  matte (HSV sat < 0.35): positive adj capped at +0.15
  everything else: cap +0.25

Pixel classes
-------------
  outline    : alpha == 255 and R+G+B < 90     -> never shaded (defines form)
  background : alpha < 10                      -> skipped
  skin       : within +/-25 of #F4A460         -> skipped
  hair       : near brown/black/blonde/silver palette -> skipped
  armor      : alpha > 10, brightness > 30, not skin/hair/outline -> shaded

Brightness is adjusted on the HSV V channel only (uniform RGB scale), so
hue and saturation are preserved.
"""

import sys
import argparse
import numpy as np
from PIL import Image

FRAME_W, FRAME_H = 80, 64
COLS, ROWS = 10, 7

# Character occupies x=30..54 within each frame
CHAR_X0, CHAR_X1 = 30, 54

# Skin color and tolerance (per task spec: #F4A460 +/-25)
SKIN_RGB = np.array([244, 164, 96], dtype=np.float32)
SKIN_TOL = 25

# Hair palette — Dark / Auburn / Red / Blonde / Silver game variants
# (brown/black/blonde/silver ranges; see HANDOFF.md hair color labels)
HAIR_PALETTE = np.array([
    [40,  25,  12],   # Dark (very dark brown)
    [60,  30,  10],   # Dark variant 2
    [80,  40,  15],   # Auburn dark
    [110, 60,  20],   # Auburn mid
    [150, 90,  40],   # Brown mid
    [190, 130, 60],   # Warm blonde
    [200, 160, 80],   # Blonde
    [155, 155, 155],  # Silver dark
    [180, 180, 180],  # Silver mid
    [210, 210, 210],  # Silver light
], dtype=np.float32)
HAIR_TOL = 15   # tight Chebyshev tolerance — avoids eating gold armor tones

# Shading constants
PEAK = 0.55            # highlight peak position (norm_x)
BELL_WIDTH = 0.8       # cosine bell widening factor (spreads the highlight)
ADJ_MIN, ADJ_MAX = -0.28, 0.25
VERT_AMPL = 0.08       # +/-8% sine bulge within each contiguous segment
EDGE_DARK_MAX = 0.12   # max shadow right next to an outline pixel
EDGE_DIST = 3          # falloff radius in px (0 shadow at this distance)
METALLIC_PEAK = 0.30   # smooth cosine peak for metallic colors (was cap 0.25)
MATTE_CAP = 0.15
MET_SAT, MET_VAL = 0.35, 0.55  # metallic thresholds in HSV


# ── Horizontal cosine LUT ────────────────────────────────────────────────────

def _build_x_adj_lut() -> np.ndarray:
    """Per-x additive brightness adjustment from the cosine bell curve."""
    xs = np.arange(FRAME_W, dtype=np.float32)
    norm_x = np.clip((xs - CHAR_X0) / float(CHAR_X1 - CHAR_X0), 0.0, 1.0)
    intensity = np.cos((norm_x - PEAK) * np.pi * BELL_WIDTH)   # wide bell
    return ADJ_MIN + (intensity + 1.0) * 0.5 * (ADJ_MAX - ADJ_MIN)


X_ADJ = _build_x_adj_lut()


# ── Pixel classification ─────────────────────────────────────────────────────

def classify(frame: np.ndarray):
    """Return (armor_mask, outline_mask) boolean arrays for one RGBA frame."""
    rgb = frame[:, :, :3].astype(np.float32)
    alpha = frame[:, :, 3]

    brightness = rgb.mean(axis=-1)
    rgb_sum = rgb.sum(axis=-1)

    outline = (alpha == 255) & (rgb_sum < 90)
    background = alpha < 10

    skin = (np.abs(rgb - SKIN_RGB) <= SKIN_TOL).all(axis=-1)

    h, w = rgb.shape[:2]
    diffs = np.abs(rgb.reshape(-1, 1, 3) - HAIR_PALETTE[np.newaxis, :, :]).max(axis=-1)
    hair = (diffs.min(axis=-1) <= HAIR_TOL).reshape(h, w)

    armor = (~background) & (alpha > 10) & (brightness > 30) & ~outline & ~skin & ~hair
    return armor, outline


def dilate8(mask: np.ndarray) -> np.ndarray:
    """8-neighbor dilation via padded shifts (no scipy dependency)."""
    p = np.pad(mask, 1, mode='constant')
    out = np.zeros_like(mask)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            out |= p[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]]
    return out


def edge_falloff_adj(outline: np.ndarray) -> np.ndarray:
    """
    Curvature shadow: per-pixel negative adjustment that ramps quadratically
    from -EDGE_DARK_MAX right next to an outline pixel to 0 at EDGE_DIST px
    away. Chebyshev distance via iterated 8-neighbor dilation.
    """
    dist = np.full(outline.shape, EDGE_DIST + 1, dtype=np.float32)
    ring = outline.copy()
    for d in range(1, EDGE_DIST + 1):
        ring = dilate8(ring) | ring
        dist = np.where(ring & (dist > EDGE_DIST), d, dist)
    # quadratic ramp: t=1 right next to outline (dist 1), t=0 at EDGE_DIST
    t = np.clip((EDGE_DIST - dist) / float(EDGE_DIST - 1), 0.0, 1.0)
    return -EDGE_DARK_MAX * t * t


# ── Vertical segment gradient ────────────────────────────────────────────────

def vertical_adj(armor: np.ndarray) -> np.ndarray:
    """
    Per-pixel vertical adjustment: within each contiguous run of armor pixels
    in a column, a sine bulge sin(pi * t) mapped to [-VERT_AMPL, +VERT_AMPL].
    The middle of each segment is brightest (+VERT_AMPL), the ends darkest
    (-VERT_AMPL) — plates read as curved, not flat ramps. Single-pixel
    segments get 0.
    """
    h, w = armor.shape
    adj = np.zeros((h, w), dtype=np.float32)
    for x in range(w):
        col = armor[:, x]
        if not col.any():
            continue
        ys = np.flatnonzero(col)
        # split into contiguous runs
        splits = np.flatnonzero(np.diff(ys) > 1) + 1
        for run in np.split(ys, splits):
            top, bot = run[0], run[-1]
            if bot == top:
                continue
            t = (run - top) / float(bot - top)          # 0 at top, 1 at bottom
            adj[run, x] = VERT_AMPL * (2.0 * np.sin(np.pi * t) - 1.0)
    return adj


# ── HSV material classification ──────────────────────────────────────────────

def material_masks(rgb: np.ndarray):
    """Return (metallic, matte) masks from HSV saturation/value."""
    rf = rgb.astype(np.float32) / 255.0
    v = rf.max(axis=-1)
    mn = rf.min(axis=-1)
    sat = np.where(v > 0, (v - mn) / np.maximum(v, 1e-9), 0.0)
    metallic = (sat > MET_SAT) & (v > MET_VAL)
    matte = sat <= MET_SAT
    return metallic, matte


# ── Per-frame shading ────────────────────────────────────────────────────────

def shade_frame(frame: np.ndarray) -> tuple[np.ndarray, int]:
    """Shade one 64x80 RGBA frame. Returns (new_frame, n_armor_pixels)."""
    armor, outline = classify(frame)
    if not armor.any():
        return frame, 0

    rgb = frame[:, :, :3]

    # 1) horizontal cosine adjustment (broadcast per column)
    adj = np.broadcast_to(X_ADJ[np.newaxis, :], armor.shape).astype(np.float32).copy()

    # 2) vertical per-segment gradient
    adj += vertical_adj(armor)

    # 3) curvature shadow: quadratic distance-from-outline falloff
    adj += edge_falloff_adj(outline)

    # 4) material response: matte pixels capped; metallic pixels get their
    #    positive adjustment smoothly rescaled so the cosine peak reaches
    #    METALLIC_PEAK. Continuous curve — no discrete bands or streaks.
    metallic, matte = material_masks(rgb)
    pos = adj > 0
    adj = np.where(pos & matte, np.minimum(adj, MATTE_CAP), adj)
    adj = np.where(pos & metallic,
                   np.minimum(adj * (METALLIC_PEAK / ADJ_MAX), METALLIC_PEAK),
                   adj)

    # apply on V channel: scale RGB uniformly so hue/sat are preserved
    factor = 1.0 + adj
    rf = rgb.astype(np.float32)
    v = rf.max(axis=-1)
    v_new = np.clip(v * factor, 0.0, 255.0)
    scale = np.where(v > 0, v_new / np.maximum(v, 1e-9), 1.0)
    shaded = np.clip(rf * scale[:, :, np.newaxis], 0, 255).astype(np.uint8)

    out = frame.copy()
    out[:, :, :3] = np.where(armor[:, :, np.newaxis], shaded, rgb)
    return out, int(armor.sum())


def shade_sheet(arr: np.ndarray, only_frame: int | None = None):
    """Shade all frames (or a single frame). Returns (out, stats dict)."""
    out = arr.copy()
    total_armor = 0
    frames_touched = 0
    for fi in range(COLS * ROWS):
        if only_frame is not None and fi != only_frame:
            continue
        col, row = fi % COLS, fi // COLS
        gx, gy = col * FRAME_W, row * FRAME_H
        new_frame, n = shade_frame(arr[gy:gy + FRAME_H, gx:gx + FRAME_W])
        if n:
            out[gy:gy + FRAME_H, gx:gx + FRAME_W] = new_frame
            total_armor += n
            frames_touched += 1
    return out, {"armor_pixels": total_armor, "frames_shaded": frames_touched}


# ── CLI ──────────────────────────────────────────────────────────────────────

SAMPLE_XS = (35, 38, 41, 44)
SAMPLE_Y = 35


def print_samples(before: np.ndarray, after: np.ndarray):
    print(f"  frame 0 samples at y={SAMPLE_Y}:")
    for x in SAMPLE_XS:
        br, bg_, bb, ba = (int(v) for v in before[SAMPLE_Y, x])
        ar, ag, ab, aa = (int(v) for v in after[SAMPLE_Y, x])
        if ba <= 10:
            print(f"    x={x}: transparent")
        else:
            print(f"    x={x}: ({br:3},{bg_:3},{bb:3}) -> ({ar:3},{ag:3},{ab:3})")


def main():
    parser = argparse.ArgumentParser(
        description="Per-pixel cosine-falloff shading for armor sprite sheets.")
    parser.add_argument("input", help="Input PNG sprite sheet (800x448)")
    parser.add_argument("output", nargs="?", default=None,
                        help="Output PNG path (default: overwrite input)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats without saving")
    parser.add_argument("--frame", type=int, default=None, metavar="N",
                        help="Process only frame N (0-69), for testing")
    args = parser.parse_args()

    img = Image.open(args.input).convert("RGBA")
    if img.size != (800, 448):
        print(f"WARNING: expected 800x448, got {img.size}", file=sys.stderr)

    arr = np.array(img, dtype=np.uint8)
    shaded, stats = shade_sheet(arr, only_frame=args.frame)

    print(f"{args.input}: shaded {stats['armor_pixels']} armor pixels "
          f"across {stats['frames_shaded']} frames"
          f"{f' (frame {args.frame} only)' if args.frame is not None else ''}")
    print_samples(arr, shaded)

    if args.dry_run:
        print("  dry run — nothing saved")
        return

    out_path = args.output or args.input
    Image.fromarray(shaded).save(out_path)
    print(f"  saved: {out_path}")


if __name__ == "__main__":
    main()
