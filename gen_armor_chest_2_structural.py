#!/usr/bin/env python3
"""
armor_chest_2 rebuild — structural shirt-mask plate overlay.

For each active frame, plate pixels are derived directly from that frame's
shirt pixel structure — no offsets, no coordinate mapping, zero drift.

Zones (relative row index from top of shirt mask):
  Rows 0-1  : pauldrons  — left cluster → right pauldron (dark/receding)
                            rightmost 3 of right cluster → left pauldron (bright/facing)
  Row  2    : gap        — leather shows through
  Rows 3-9  : chest plate — main cluster, gradient dark-left → mid-right
                            skip leftmost 2 and rightmost 2 per row
  Rows 10+  : lower body — no plate
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np

CHAR = "/Users/matthauth/Projects/TaskQuest/sprites/preview_assets/char"
DESK = "/Users/matthauth/Desktop"
FRAME_W, FRAME_H = 80, 64
COLS, ROWS = 10, 7

# Iron plate palette
O = (26,  26,  26,  255)   # #1A1A1A outline/deepest
D = (58,  58,  58,  255)   # #3A3A3A dark shadow
S = (96,  96,  96,  255)   # #606060 shadow
M = (140, 140, 140, 255)   # #8C8C8C mid tone

def find_clusters(xs, gap=2):
    """Split sorted x-list into consecutive groups separated by gap > `gap`."""
    if not xs:
        return []
    result, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] > gap:
            result.append(cur)
            cur = [x]
        else:
            cur.append(x)
    result.append(cur)
    return result

def pauldron_colors_right(cluster):
    """Right pauldron (char's right = our left, receding): outline→dark→shadow."""
    palette = [O, D, S]
    return {x: palette[min(i, 2)] for i, x in enumerate(cluster)}

def pauldron_colors_left(cluster):
    """Left pauldron (char's left = our right, facing viewer): shadow→mid→outline."""
    tail = cluster[-3:] if len(cluster) >= 3 else cluster
    palette = [S, M, O]
    return {x: palette[i] for i, x in enumerate(tail)}

def chest_row_colors(xs):
    """
    Chest plate row. Skip leftmost 2 and rightmost 2 shirt pixels.
    Of the main (leftmost) cluster, apply gradient dark→mid left-to-right.
    """
    # Use only the main (leftmost) cluster for the plate
    clusters = find_clusters(xs)
    main = clusters[0]
    N = len(main)
    if N < 5:
        return {}
    center = main[2: N - 2]   # exclude leftmost 2 and rightmost 2
    if not center:
        return {}
    M_c = len(center)
    result = {}
    for i, x in enumerate(center):
        rel = i / (M_c - 1) if M_c > 1 else 0.5
        if i == 0:
            c = O          # hard left plate edge
        elif rel < 0.30:
            c = D
        elif rel < 0.55:
            c = S
        else:
            c = M
        result[x] = c
    return result

# ── Load sources ─────────────────────────────────────────────────────────
leather = np.array(Image.open(f"{CHAR}/leather_armor_1.png").convert('RGBA'))
shirt   = np.array(Image.open(f"{CHAR}/shirt.png").convert('RGBA'))

out = leather.copy()
total_painted = 0

for fi in range(COLS * ROWS):
    col_idx = fi % COLS
    row_idx = fi // COLS
    gx = col_idx * FRAME_W
    gy = row_idx * FRAME_H

    frame_shirt = shirt[gy:gy+FRAME_H, gx:gx+FRAME_W]
    op = np.argwhere(frame_shirt[:,:,3] > 0)
    if len(op) == 0:
        continue

    # Organise by row (sorted y values)
    ys = sorted(set(int(y) for y,x in op))

    for rel_row, y_abs in enumerate(ys):
        xs = sorted(int(x) for x in np.where(frame_shirt[y_abs,:,3] > 0)[0])
        plate_row = {}

        if rel_row < 2:
            # ── Pauldron rows ────────────────────────────────────────────
            clusters = find_clusters(xs)
            if len(clusters) >= 2:
                plate_row.update(pauldron_colors_right(clusters[0]))
                plate_row.update(pauldron_colors_left(clusters[-1]))
            elif len(clusters) == 1 and len(xs) >= 6:
                # Single-cluster frame (unusual) — treat outer edges as pauldrons
                plate_row.update(pauldron_colors_right(xs[:3]))
                plate_row.update(pauldron_colors_left(xs))

        elif rel_row == 2:
            pass  # gap row — leather visible, no plate

        elif 3 <= rel_row <= 9:
            # ── Chest plate rows ─────────────────────────────────────────
            plate_row.update(chest_row_colors(xs))

        # else: row >= 10 — lower body, no plate

        for lx, color in plate_row.items():
            out[gy + y_abs, gx + lx] = color
            total_painted += 1

print(f"Total plate pixels painted: {total_painted}")

# ── Save ─────────────────────────────────────────────────────────────────
OUT_PATH = f"{CHAR}/armor_chest_2.png"
Image.fromarray(out).save(OUT_PATH)
print(f"Saved → {OUT_PATH}")

# ── 3-frame preview: frames 0/1/2, 12x zoom, y:28-50 ────────────────────
ZOOM = 12
XA, XB = 25, 57
YA, YB = 28, 51
FW, FH = XB-XA, YB-YA
GAP = 10
LH  = 22

panel_w = FW * ZOOM
panel_h = FH * ZOOM
tw = panel_w * 3 + GAP * 4
th = panel_h + LH + GAP * 2

canvas = Image.new('RGB', (tw, th), (20, 20, 20))
draw   = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
except:
    font = ImageFont.load_default()

for pi, (fgx, label) in enumerate([(0,'Frame 0'),(80,'Frame 1'),(160,'Frame 2')]):
    px_off = GAP + pi * (panel_w + GAP)
    draw.text((px_off + panel_w//2, 4), label, fill=(200,200,200), font=font, anchor='mt')
    for ly in range(FH):
        for lx in range(FW):
            r,g,b,a = out[YA+ly, fgx+XA+lx]
            bx = px_off + lx*ZOOM
            by = LH + GAP + ly*ZOOM
            draw.rectangle([bx,by,bx+ZOOM-1,by+ZOOM-1], fill=(15,15,15) if a==0 else (r,g,b))
    for ly in range(FH+1):
        y = LH+GAP+ly*ZOOM
        draw.line([(px_off,y),(px_off+panel_w,y)], fill=(50,50,50))
    for lx in range(FW+1):
        x = px_off+lx*ZOOM
        draw.line([(x,LH+GAP),(x,LH+GAP+panel_h)], fill=(50,50,50))

PREV = f"{DESK}/armor_rebuild_preview.png"
canvas.save(PREV)
print(f"Saved preview → {PREV}  ({tw}×{th}px)")
