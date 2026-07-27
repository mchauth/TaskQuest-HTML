#!/usr/bin/env python3
"""Cowl + cape as HELMET slot items — v7 split.

v6 (redesign_hooded_capes.py) folded the hood cap into the shirt sprite
so it could sit under the hair. v7 moves the cowl to the HELMET slot
instead: full helmets hide the hair in-game (index.html applyLegLayerOrder
/ hatType check), so the cap can own the whole head, and the cape is
BAKED INTO the helmet sheet, extending down from the brim into the body
zone (brim_row .. y=55).

Helmet sheets (helmet_<cls>_legendary_cowl.png), per frame:
  1. Cape back panel + trapezoid (hooded_cape_cells) — brim_row down to
     y=55, carved by the BODY SILHOUETTE (skin_m1 alpha | T1 shirt
     alpha): in-game the helmet layer renders on top of everything, so
     carving the cape out wherever the body/garment is opaque is what
     makes it read as hanging BEHIND the character. No cape on sleep
     frames (house convention).
  2. Hood cap (cap_cells, unchanged v5 geometry) — crown dome +
     asymmetric side drape, face opening transparent. NOT carved: the
     hood covers the head. Drawn on every reference-helmet frame,
     including sleep.
  3. NO body recolor — the chest/torso stays transparent so whatever
     shirt the player equips shows through under the cape.

Shirt sheets (shirt_<cls>_legendary_hooded.png) are regenerated as
standalone capes: cape + body recolor only, NO hood cap (build_shirt
from redesign_hooded_capes with an empty hat_frames set).

Shading: one shade(adj_min=-0.20, adj_max=0.25) pass per sheet (the
shirt override — same modelling the v6 combined sheet used, so the
flat-authored hood fills keep their left-shadow / right-light look).

LOOT_TABLE: the two shirt entries stay slot:'shirt' (standalone capes);
two helmet entries are added (helmet_mage_legendary_cowl 'Arcane Cowl',
helmet_ranger_legendary_cowl 'Shadow Cowl') with no hatType, so the
game hides the hair under them.

Run from repo root:
  python3 scripts/redesign_cowl_helmets.py [preview_out.png]
Writes the 4 sheets to sprites/preview_assets/char/ and a 4x preview
strip (skin, T1 shirt, cowl helmet — no hair; frames 0/10/20, mage row
then ranger row) to preview_out.png (default _PREVIEW_helmet_cowl.png
in the repo root).
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_mage_ranger_tiers import load, shade, CHAR, ROOT
from rebuild_class_hats import make_head_dome_fn
from legendary_capes import (FW, FH, COLS, MID_RAMP, GRN_RAMP,
                             MAGE_CAPE, RGR_CAPE, put, stamp)
from redesign_hooded_capes import (CAP_PAL, hooded_cape_cells, cap_cells,
                                   build_shirt, get_active_frames)


def build_helmet(base, skin_sheet, dome, pal, cap_pal, rugged, hat_frames):
    """Helmet sheet: cape (body-carved) + hood cap. No body recolor."""
    out = np.zeros_like(base)
    skin_alpha = skin_sheet[..., 3] > 0
    for fi in sorted(set(hat_frames)):
        hp = dome(fi)
        if hp is None:
            continue
        r, c = fi // COLS, fi % COLS
        sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
        src = base[sl]
        a = src[..., 3] > 0
        fr = out[sl]
        ht, cx = hp
        # neck_top from the reference garment silhouette (cape anchor)
        ys, xs = np.where(a)
        if len(ys):
            top = {int(x): int(ys[xs == x].min()) for x in np.unique(xs)}
            tops = [top[x] for x in range(cx - 3, cx + 4) if x in top]
            nt = min(tops) if tops else int(ys.min())
        else:
            nt = ht + 11
        # whole body silhouette (skin + T1 garment) carves the cape:
        # the helmet layer draws on top in-game, so these px must be
        # transparent for the cape to appear behind the character
        hide = skin_alpha[sl] | a
        # 1. cape back panel + trapezoid, brim_row..55 (not on sleep)
        if fi < 60:
            stamp(fr, hooded_cape_cells(cx, ht, nt, pal),
                  hide, a, pal['outline'])
        # 2. hood cap — covers the head, never carved (incl. sleep).
        #    back_mask=False: clean hood silhouette only; long/medium/ponytail
        #    hair is hidden via hatType:'hood' game logic (index.html), not
        #    by opaque sprite pixels.
        for (x, y), rgb in cap_cells(cx, ht, cap_pal, rugged,
                                     back_mask=False).items():
            put(fr, y, x, rgb)
        # 3. NO body recolor: chest stays transparent
    return out


def preview_strip(jobs_layers, frames, path, zoom=4, gap=6):
    """Rows of composited frames (layers bottom->top per row) at zoom."""
    rows = []
    for layers in jobs_layers:
        bg = np.zeros((FH, len(frames) * (FW + gap) - gap, 4), np.uint8)
        bg[..., :3] = (40, 40, 48)
        bg[..., 3] = 255
        for i, fi in enumerate(frames):
            r, c = fi // COLS, fi % COLS
            sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
            tile = bg[:, i * (FW + gap):i * (FW + gap) + FW]
            for sheet in layers:
                m = sheet[sl][..., 3] > 0
                tile[m] = sheet[sl][m]
        rows.append(bg)
    strip = np.concatenate(rows, axis=0)
    big = np.kron(strip, np.ones((zoom, zoom, 1), dtype=np.uint8))
    Image.fromarray(big).save(path)


JOBS = [
    ('mage', 'shirt_mage1.png', MID_RAMP, MAGE_CAPE, False),
    ('ranger', 'shirt_ranger1.png', GRN_RAMP, RGR_CAPE, True),
]


def main():
    out_pv = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(ROOT, '_PREVIEW_helmet_cowl.png')
    skin_sheet = load('skin_m1.png')
    dome = make_head_dome_fn(skin_sheet)
    hat_frames = get_active_frames(CHAR + 'helmet_mage1.png')
    pv_rows = []
    for cls, src_name, ramp, pal, rugged in JOBS:
        base = load(src_name)
        # HELMET: cape + hood cap, transparent chest
        helm = build_helmet(base, skin_sheet, dome, pal,
                            CAP_PAL[cls], rugged, hat_frames)
        helm = shade(helm, adj_min=-0.20, adj_max=0.25)
        helm_name = 'helmet_%s_legendary_cowl.png' % cls
        Image.fromarray(helm).save(CHAR + helm_name)

        # SHIRT: standalone cape + body recolor, no hood cap
        shirt = build_shirt(base, skin_sheet, dome, ramp, pal,
                            CAP_PAL[cls], rugged, hat_frames=[])
        shirt = shade(shirt, adj_min=-0.20, adj_max=0.25)
        shirt_name = 'shirt_%s_legendary_hooded.png' % cls
        Image.fromarray(shirt).save(CHAR + shirt_name)

        # preview row: skin + T1 shirt + cowl helmet (no hair — hidden)
        pv_rows.append([skin_sheet, base, helm])
        print('wrote %s + %s' % (helm_name, shirt_name))

    preview_strip(pv_rows, [0, 10, 20], out_pv, zoom=4)
    print('preview -> %s' % out_pv)


if __name__ == '__main__':
    main()
