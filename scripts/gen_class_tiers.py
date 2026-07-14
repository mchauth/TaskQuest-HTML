#!/usr/bin/env python3
"""Generate mage & ranger armor tiers 2-6, male and female, in one batch.

Male sheets + female shirts/boots: hue-preserving palette remap of the tier 1
sheets (silhouettes stay pixel-identical -- female tier 1 shirts/boots share
the warrior female templates exactly: shirt 91px / boots 59px in frame 0).

Female pants: fitted leggings (NOT skirts). The finished male pants sheet for
each tier is run-remapped onto the female skin silhouette per frame, exactly
like gen_female_leggings.py did for the warrior armor_pants_N_f sheets.

Per slot:
  shirts : palette remap; tiers 4-6 get 1px collar + cuff trim in the tier
           accent; mage t3 shoulder rune dots, t4 azure chest stripe,
           t6 center rune line; shaded with ADJ_MIN=-0.20 ADJ_MAX=0.25.
  pants  : palette remap; seam lines at thigh/knee and knee/shin (V*0.60),
           edge darkening (V*0.75); default shading. Female = leggings remap
           of the finished male sheet (already shaded).
  boots  : palette remap + 1px cuff trim in the tier accent; default shading.
  helmets: palette remap (male only); default shading.

Run from repo root:  python3 scripts/gen_class_tiers.py
Then QA:  sprite_qa.py (shirts/helmets), --y-max 62 (pants), --y-max 63 (boots)
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_mage_ranger_tiers import (
    MAGE, RANGER, CHAR, recolor_mage, recolor_ranger,
    shirt_details, boots_details, pants_details, shade, load,
)
from gen_female_leggings import gen_frame, fix_passes

FW, FH = 80, 64


def female_leggings(male_pants, skin_m_a, skin_f_a):
    """Run-remap a finished male pants sheet onto the female skin silhouette."""
    out = np.zeros_like(male_pants)
    for r in range(7):
        for c in range(10):
            sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
            gen_frame(male_pants[sl], skin_m_a[sl], skin_f_a[sl], out[sl])
            fix_passes(male_pants[sl], skin_f_a[sl], out[sl])
    return out


def main():
    skin_m_a = load('skin_m1.png')[..., 3] > 0
    skin_f_a = load('skin_f1.png')[..., 3] > 0
    made = []

    def save(arr, dst):
        Image.fromarray(arr).save(CHAR + dst)
        made.append(dst)
        print('wrote %s' % dst)

    for cls, rec, pal in (('mage', recolor_mage, MAGE),
                          ('ranger', recolor_ranger, RANGER)):
        for tier in range(2, 7):
            P = pal[tier]

            # shirts (male + female): remap tier 1 in place
            for suf in ('', '_f'):
                arr = rec(load('shirt_%s1%s.png' % (cls, suf)), tier)
                shirt_details(arr, cls, tier, P)
                arr = shade(arr, adj_min=-0.20, adj_max=0.25)
                save(arr, 'shirt_%s%d%s.png' % (cls, tier, suf))

            # male pants: remap tier 1 + seams/edges + shade
            arr = rec(load('pants_%s1.png' % cls), tier)
            pants_details(arr)
            arr = shade(arr)
            save(arr, 'pants_%s%d.png' % (cls, tier))

            # female pants: fitted leggings remapped from the male sheet
            legg = female_leggings(arr, skin_m_a, skin_f_a)
            save(legg, 'pants_%s%d_f.png' % (cls, tier))

            # boots (male + female): remap tier 1 + cuff trim + shade
            for suf in ('', '_f'):
                arr = rec(load('boots_%s1%s.png' % (cls, suf)), tier)
                boots_details(arr, P['accent'])
                arr = shade(arr)
                save(arr, 'boots_%s%d%s.png' % (cls, tier, suf))

            # helmet (male only)
            arr = rec(load('helmet_%s1.png' % cls), tier)
            arr = shade(arr)
            save(arr, 'helmet_%s%d.png' % (cls, tier))

    print('%d sheets generated' % len(made))


if __name__ == '__main__':
    main()
