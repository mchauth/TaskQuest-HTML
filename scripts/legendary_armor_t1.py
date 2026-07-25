#!/usr/bin/env python3
"""Generate "Divine Seraph Plate" — legendary winged warrior chest (m + f).

shirt_warrior_legendary1.png / shirt_warrior_legendary1_f.png

Goes beyond normal armor: large angelic wings extend ~13px to each side of
the body, giving a dramatic bigger-than-normal silhouette. Built the same
way as redesign_mage_chest_t2_sweater.py:

  Body    : shirt_rare1[_f] silhouette (full m+f coverage, tracks every pose).
            Per-frame edge px stay pure black outline; interior px (including
            the black plate-seam px — 44% of frame 0 is black in the source,
            which made a 3-tone V-quantize come out near-black) are mapped by
            luminance QUANTILE onto a 6-step gold ramp around the task tones
            D=(120,90,20) M=(200,160,40) L=(240,200,80), same technique as
            gen_warrior_legendary4.py. Seams land on the darkest gold, trim
            on the near-white glint.
  Wings   : hand-authored feathered wing, mirrored left/right, drawn UNDER
            the plate body. Anchored per frame: cx from the skull-dome
            tracker (skin sheet), vertical anchor from the garment neck row
            (min top alpha over cx±3 — immune to raised arms on cheer/
            slash). Wing rows span neck_top-12 .. neck_top+1: tips curve up
            above the shoulders (y≈21 male idle), base overlaps the garment
            top so the plate visually mounts the wings. Bottom edge is
            scalloped into hanging primary feathers.
            NOTE: the sheet is a single 3/4-facing animation sheet (idle/
            walk/run/jump/cheer/slash/sleep), so the full spread-wing
            profile is shown on every upright frame; sleep frames (fi>=60)
            get the gold plate only (character lies down — house convention,
            same as the sweater script's sleep handling).
  Wing    : every wing color passes sprite_shade's accent test
  colors    (r>=230 AND g>=190) so the cosine shader freezes them — the
            white/gold never gets crushed:
              FE=(252,250,255) bright white leading edge
              WW=(242,236,220) warm white vane
              PG=(238,214,152) pale gold trailing/outer edge
              DG=(230,196,116) dim gold feather detail lines (ribs)
            Exterior 1px outline OL=(112,82,28) is NOT accent — it takes
            the cosine light like the body, which grounds the wing edges.
  Pauldrons: gold joint caps drawn OVER the plate at the wing roots
            (L-tone cluster + 1 white rim px per side) so the wings read
            as shoulder-mounted, not floating.
  Shading : shade(adj_min=-0.20, adj_max=0.25) — the shirt override, same
            as gen_mage_ranger_tiers shirts. Do NOT run sprite_shade.py
            again on top.

Run from repo root:
  python3 scripts/legendary_armor_t1.py
Then QA (expected: the bg-zone check flags the wings — they intentionally
exceed the x=30..55 character zone; that IS the legendary silhouette):
  python3 scripts/sprite_qa.py sprites/preview_assets/char/shirt_warrior_legendary1.png
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_mage_ranger_tiers import load, shade, CHAR
from rebuild_class_hats import make_head_dome_fn

FW, FH, COLS, NFR = 80, 64, 10, 70

# gold plate ramp (task spec tones D/M/L inside a 6-step ramp, dark -> light)
D = (120, 90, 20)                  # shadow gold
M = (200, 160, 40)                 # midtone gold
L = (240, 200, 80)                 # highlight gold (accent-frozen by design)
RAMP = np.array([
    (80, 58, 14),                  # plate seam / deepest shadow
    D,
    (163, 125, 30),
    M,
    L,
    (252, 238, 180),               # near-white glint (accent-frozen)
], dtype=np.uint8)

# wing palette — ALL pass the accent test (r>=230 & g>=190)
FE = (252, 250, 255)               # bright white leading edge
WW = (242, 236, 220)               # warm white vane
PG = (238, 214, 152)               # pale gold trailing/outer edge
DG = (230, 196, 116)               # dim gold feather ribs
OL = (112, 82, 28)                 # exterior outline (shaded, not accent)

# Right-wing filled silhouette: dy (0=top tip row .. 13=base row) -> set of
# dx offsets from cx. Bottom two rows are scalloped into feather tips.
# Mirrored for the left wing (dx -> -dx). Max |dx|=19 -> span x=cx±19,
# ~13px beyond the body edge (body bbox x=34..46, cx=40).
WING_ROWS = {
    0:  [19],                      # single outer pixel — sharp tip
    1:  range(16, 20),             # fast expansion from tip
    2:  range(12, 20),
    3:  range(8, 20),
    4:  range(5, 20),              # full width
    5:  range(5, 20),
    6:  range(5, 19),
    7:  range(5, 17),
    8:  range(5, 15),
    9:  range(5, 13),
    10: [6, 7, 8, 10, 11, 12],     # scallop with 3 notch groups
    11: [7, 8, 11, 12],            # secondary feather tips
    12: [8, 11],                   # primary hanging feather tips (pointed)
}
WING_H = 13                        # rows 0..12


def edge_mask(P):
    pad = np.pad(P, 1)
    n4 = (pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    return P & ~n4


def put(fr, y, x, rgb):
    if 0 <= y < FH and 0 <= x < FW:
        fr[y, x, :3] = rgb
        fr[y, x, 3] = 255


def wing_pixels(cx, top_y):
    """Return {(x, y): rgb} for BOTH wings, anchored so row 0 sits at top_y.

    Coloring per column (per side): topmost px = FE leading edge, second = WW,
    bottommost px + outermost column = PG trailing edge, dashed DG rib line at
    dy=7 and vertical DG separators at |dx| in {9,12,15} for dy 9..11.
    """
    px = {}
    for sgn in (1, -1):
        cells = set()
        for dy, dxs in WING_ROWS.items():
            for dx in dxs:
                cells.add((sgn * dx, dy))
        col_rows = {}
        for (dx, dy) in cells:
            col_rows.setdefault(dx, []).append(dy)
        max_adx = max(abs(dx) for dx, _ in cells)
        for (dx, dy) in cells:
            rows = sorted(col_rows[dx])
            if dy == rows[0]:
                c = FE                          # leading (top) edge
            elif len(rows) > 1 and dy == rows[1]:
                c = WW
            elif dy == rows[-1] or abs(dx) == max_adx:
                c = PG                          # trailing / outer edge
            elif dy == 7 and abs(dx) >= 8 and abs(dx) % 2 == 0:
                c = DG                          # dashed covert/primary rib
            elif 9 <= dy <= 11 and abs(dx) in (9, 12, 15):
                c = DG                          # primary feather separators
            else:
                c = WW
            px[(cx + dx, top_y + dy)] = c
    return px


def build(base, dome, female):
    out = np.zeros_like(base)
    for fi in range(NFR):
        r, c = fi // COLS, fi % COLS
        sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
        src = base[sl]
        a = src[..., 3] > 0
        if not a.any():
            continue
        fr = out[sl]
        sleeping = fi >= 60

        # ── frame geometry ───────────────────────────────────────────────────
        ys, xs = np.where(a)
        x0, x1 = int(xs.min()), int(xs.max())
        hp = dome(fi)                       # (head_top, cx) from skin sheet
        cx = hp[1] if hp else (x0 + x1) // 2
        cols = np.unique(xs)
        top = {int(x): int(ys[xs == x].min()) for x in cols}
        tops = [top[x] for x in range(cx - 3, cx + 4) if x in top]
        neck_top = min(tops) if tops else int(ys.min())

        # ── 1. wings (under the body) — upright frames only ──────────────────
        if not sleeping:
            wpx = wing_pixels(cx, neck_top - 8)
            for (x, y), rgb in wpx.items():
                put(fr, y, x, rgb)
            # exterior 1px outline on transparent 4-neighbors
            for (x, y) in wpx:
                for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + ddx, y + ddy)
                    if n not in wpx and 0 <= n[0] < FW and 0 <= n[1] < FH \
                            and fr[n[1], n[0], 3] == 0:
                        put(fr, n[1], n[0], OL)

        # ── 2. gold plate recolor: black edge outline + quantile interior ────
        # Only px that were black IN THE SOURCE and sit on the silhouette
        # edge stay pure black — a blanket edge_mask blacked out the whole
        # 2px-wide sleeves. Colored edge px join the quantile mapping.
        src_black = a & (src[..., :3].astype(np.int32).sum(-1) < 90)
        edges = edge_mask(a) & src_black
        interior = a & ~edges
        if interior.any():
            rgbf = src[..., :3].astype(np.float64)
            lu = (3 * rgbf[..., 0] + 6 * rgbf[..., 1] + rgbf[..., 2]) / 10.0
            src_l = lu[interior]
            ref = np.sort(src_l)
            q = np.searchsorted(ref, src_l, side='left') / max(1, len(ref) - 1)
            idx = np.clip((q * (len(RAMP) - 1)).round().astype(int),
                          0, len(RAMP) - 1)
            fr[interior, :3] = RAMP[idx]
            fr[interior, 3] = 255
        fr[edges, :3] = 0
        fr[edges, 3] = 255

        # ── 3. pauldron wing-root caps over the plate shoulders ─────────────
        if not sleeping:
            for sgn in (1, -1):
                for dx, dy, col in ((3, 0, L), (4, 0, L), (5, 0, FE),
                                    (3, 1, M), (4, 1, L), (5, 1, M)):
                    x, y = cx + sgn * dx, neck_top + dy
                    if 0 <= x < FW and 0 <= y < FH and a[y, x]:
                        put(fr, y, x, col)
    return out


def main():
    for suffix, skin, female in (('', 'skin_m1.png', False),
                                 ('_f', 'skin_f1.png', True)):
        base = load('shirt_rare1%s.png' % suffix)
        dome = make_head_dome_fn(load(skin))
        arr = build(base, dome, female)
        arr = shade(arr, adj_min=-0.20, adj_max=0.25)
        dst = 'shirt_warrior_legendary1%s.png' % suffix
        Image.fromarray(arr).save(CHAR + dst)
        n = sum(1 for fi in range(NFR)
                if (arr[(fi // COLS) * FH:(fi // COLS + 1) * FH,
                        (fi % COLS) * FW:(fi % COLS + 1) * FW, 3] > 0).any())
        print('wrote %s (%d active frames)' % (dst, n))


if __name__ == '__main__':
    main()
