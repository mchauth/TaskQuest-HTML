#!/usr/bin/env python3
"""
sprite_qa.py — Rare armor sprite QA checker
Usage:
  python3 scripts/sprite_qa.py <sprite.png> [<sprite.png> ...] [--palette r,g,b r,g,b ...] [--y-max N]

For each sprite, reads frame 0 (top-left 80×64 crop of the 800×448 sheet) and checks:
  1. No stray isolated pixels outside the character bounds (8-neighbor isolated)
  2. No pure #000000 black EXCEPT on outline edges or adjacent to another black pixel
     (interior black regions forming plate lines/seams are allowed; only truly lone
      black islands in a field of colored armor are flagged)
  3. No armor pixels bleeding into the background zone
     (x<30 or x>55 or y<16 or y>--y-max, default 52 for helmets/shirts, use 62 for pants)
  4. Color palette consistent with declared set (if --palette supplied)

Exits 0 if all PASS, 1 if any FAIL.
"""

import sys
import argparse
import numpy as np
from PIL import Image


FRAME_W, FRAME_H = 80, 64

# Background zone defaults: armor must not bleed outside this box
BG_X_MIN, BG_X_MAX = 30, 55
BG_Y_MIN = 16
BG_Y_MAX_DEFAULT = 52   # use --y-max 62 for pants (legs extend to y≈61)


def load_frame0(path):
    img = np.array(Image.open(path).convert('RGBA'))
    assert img.shape == (448, 800, 4), f"Expected 800×448, got {img.shape[1]}×{img.shape[0]}"
    return img[:FRAME_H, :FRAME_W]   # top-left crop = frame 0


def is_edge_pixel(frame, y, x):
    """True if the pixel at (x,y) is adjacent to transparent or at the frame border."""
    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        ny, nx = y+dy, x+dx
        if not (0 <= ny < FRAME_H and 0 <= nx < FRAME_W):
            return True
        if frame[ny, nx, 3] == 0:
            return True
    return False


def is_isolated(frame, y, x):
    """True if this opaque pixel has NO opaque neighbors (8-directional)."""
    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        ny, nx = y+dy, x+dx
        if 0 <= ny < FRAME_H and 0 <= nx < FRAME_W and frame[ny, nx, 3] > 0:
            return False
    return True


def has_black_neighbor(frame, y, x):
    """True if any 4-directional neighbor is also pure black (part of a black region)."""
    for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
        ny, nx = y+dy, x+dx
        if 0 <= ny < FRAME_H and 0 <= nx < FRAME_W:
            r, g, b, a = (int(v) for v in frame[ny, nx])
            if a > 0 and (r, g, b) == (0, 0, 0):
                return True
    return False


def check_sprite(path, palette_rgba=None, bg_y_max=BG_Y_MAX_DEFAULT):
    issues = []

    try:
        frame = load_frame0(path)
    except Exception as e:
        return False, [f"LOAD ERROR: {e}"]

    opaque_yx = np.argwhere(frame[:,:,3] > 0)

    if len(opaque_yx) == 0:
        return True, ["(no opaque pixels in frame 0 — skipped)"]

    for (y, x) in opaque_yx:
        r, g, b, a = int(frame[y,x,0]), int(frame[y,x,1]), int(frame[y,x,2]), int(frame[y,x,3])

        # Check 1: stray isolated pixels (no opaque 8-neighbor)
        if is_isolated(frame, y, x):
            issues.append(f"ISOLATED pixel at ({x},{y}) color=({r},{g},{b})")

        # Check 2: lone interior black — pure #000000 not on an outline edge AND no adjacent
        #   black neighbor. This allows black seam lines / solid back-plates (which always have
        #   adjacent black pixels) while still catching lone stray black dots inside colored armor.
        if (r, g, b) == (0, 0, 0):
            if not is_edge_pixel(frame, y, x) and not has_black_neighbor(frame, y, x):
                issues.append(f"LONE INNER BLACK at ({x},{y}) — isolated #000 not on edge")

        # Check 3: armor bleed into background zone (x bounds; y uses per-call limit)
        in_bg = (x < BG_X_MIN or x > BG_X_MAX or y < BG_Y_MIN or y > bg_y_max)
        if in_bg:
            issues.append(f"BACKGROUND BLEED at ({x},{y}) color=({r},{g},{b})")

        # Check 4: palette consistency (if declared)
        if palette_rgba:
            pixel_rgb = (r, g, b)
            if pixel_rgb != (0, 0, 0):   # outline/seam black always allowed
                closest_dist = min(
                    (pr-r)**2 + (pg-g)**2 + (pb-b)**2
                    for pr, pg, pb in palette_rgba
                )
                if closest_dist > 400:    # tolerance ~20 per channel
                    issues.append(
                        f"PALETTE MISMATCH at ({x},{y}) color=({r},{g},{b}) "
                        f"— nearest palette color dist²={closest_dist}"
                    )

    return len(issues) == 0, issues


def parse_palette(args_palette):
    """Parse list of 'r,g,b' strings into list of (r,g,b) tuples."""
    result = []
    for s in args_palette:
        parts = s.strip().split(',')
        if len(parts) != 3:
            raise ValueError(f"Palette entry must be 'r,g,b', got: {s!r}")
        result.append(tuple(int(p) for p in parts))
    return result


def main():
    parser = argparse.ArgumentParser(description="QA check for rare armor sprites.")
    parser.add_argument("sprites", nargs="+", help="PNG sprite sheet paths")
    parser.add_argument("--palette", nargs="*", default=None,
                        metavar="R,G,B",
                        help="Allowed colors (besides black) e.g. --palette 235,60,60 215,168,18")
    parser.add_argument("--y-max", type=int, default=BG_Y_MAX_DEFAULT,
                        metavar="N",
                        help=f"Background zone lower y limit (default {BG_Y_MAX_DEFAULT}; use 62 for pants)")
    args = parser.parse_args()

    palette_rgb = None
    if args.palette:
        try:
            palette_rgb = parse_palette(args.palette)
        except ValueError as e:
            print(f"ERROR parsing palette: {e}", file=sys.stderr)
            sys.exit(2)

    overall_pass = True
    col_w = max(len(p) for p in args.sprites) + 2

    for path in args.sprites:
        passed, issues = check_sprite(path, palette_rgb, bg_y_max=args.y_max)
        status = "PASS" if passed else "FAIL"
        if not passed:
            overall_pass = False
        print(f"{status}  {path}")
        for issue in issues:
            print(f"      {issue}")

    print()
    print("═══ QA RESULT:", "ALL PASS ✓" if overall_pass else "FAILURES FOUND ✗", "═══")
    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
