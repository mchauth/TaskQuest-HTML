#!/usr/bin/env python3
"""Generate female legging sprites from male warrior pants tiers.

Per frame: intersect the row band of the male pants (ground-aligned) with the
female skin silhouette, then transfer colors by relative run mapping:
for each row, each pants run's position is expressed relative to the male skin
run containing it, and re-projected onto the paired female skin run. Run
endpoints map to run endpoints, preserving outlines.
"""
import numpy as np
from PIL import Image

CHAR = 'sprites/preview_assets/char/'
FW, FH = 80, 64

PAIRS = [
    ('leather_pants_1', 'leather_pants_1_f'),
    ('armor_pants_2', 'armor_pants_2_f'),
    ('armor_pants_3', 'armor_pants_3_f'),
    ('armor_pants_4', 'armor_pants_4_f'),
    ('armor_pants_5', 'armor_pants_5_f'),
    ('armor_pants_6', 'armor_pants_6_f'),
    ('pants_rare1', 'pants_rare1_f'),
    ('pants_rare2', 'pants_rare2_f'),
    ('pants_rare3', 'pants_rare3_f'),
]

def load(p):
    return np.array(Image.open(CHAR + p).convert('RGBA'))

def runs(mask_row):
    """List of (x0, x1) inclusive runs of True in a 1-D bool array."""
    out = []
    x = 0
    n = len(mask_row)
    while x < n:
        if mask_row[x]:
            x0 = x
            while x + 1 < n and mask_row[x + 1]:
                x += 1
            out.append((x0, x))
        x += 1
    return out

def gen_frame(mp, ms, fs, out):
    """mp: male pants frame RGBA, ms/fs: male/female skin alpha masks,
    out: output frame RGBA (written in place)."""
    pm = mp[..., 3] > 0
    if not pm.any() or not fs.any():
        return
    # ground alignment
    m_bot = np.max(np.where(ms.any(axis=1))[0])
    f_bot = np.max(np.where(fs.any(axis=1))[0])
    shift = int(f_bot - m_bot)
    p_rows = np.where(pm.any(axis=1))[0]
    Tm, Bm = int(p_rows.min()), int(p_rows.max())
    Tf, Bf = Tm + shift, Bm + shift

    nonempty_p_rows = set(int(r) for r in p_rows)

    for y in range(max(0, Tf), min(FH - 1, Bf) + 1):
        f_row = fs[y]
        if not f_row.any():
            continue
        ym = y - shift
        if ym not in nonempty_p_rows:
            ym = min(nonempty_p_rows, key=lambda r: abs(r - (y - shift)))
        m_skin_runs = runs(ms[ym])
        m_pants_runs = runs(pm[ym])
        f_skin_runs = runs(f_row)
        if not m_skin_runs or not f_skin_runs:
            continue
        # group pants runs under the male skin run containing their center
        def owner(pr):
            cx = (pr[0] + pr[1]) / 2.0
            best, bd = 0, 1e9
            for i, (s0, s1) in enumerate(m_skin_runs):
                d = 0 if s0 <= cx <= s1 else min(abs(cx - s0), abs(cx - s1))
                if d < bd:
                    bd, best = d, i
            return best
        grouped = {}
        for pr in m_pants_runs:
            grouped.setdefault(owner(pr), []).append(pr)
        if not grouped:
            continue
        # pair each female skin run with a male skin run (by relative center)
        m_ext0 = min(r[0] for r in m_skin_runs); m_ext1 = max(r[1] for r in m_skin_runs)
        f_ext0 = min(r[0] for r in f_skin_runs); f_ext1 = max(r[1] for r in f_skin_runs)
        m_span = max(1, m_ext1 - m_ext0); f_span = max(1, f_ext1 - f_ext0)

        def rel_center(run, e0, span):
            return ((run[0] + run[1]) / 2.0 - e0) / span

        for fr in f_skin_runs:
            fc = rel_center(fr, f_ext0, f_span)
            # nearest male skin run that owns pants
            cands = [i for i in grouped]
            mi = min(cands, key=lambda i: abs(rel_center(m_skin_runs[i], m_ext0, m_span) - fc))
            # require reasonable proximity unless counts match exactly
            if len(f_skin_runs) == len(m_skin_runs):
                # positional pairing by order instead
                mi_ord = f_skin_runs.index(fr)
                if mi_ord in grouped:
                    mi = mi_ord
                else:
                    continue  # this body part has no pants on the male (e.g. arm-only run)
            ms_run = m_skin_runs[mi]
            fs_run = fr
            mlen = max(1, ms_run[1] - ms_run[0])
            flen = max(1, fs_run[1] - fs_run[0])
            for pr in grouped[mi]:
                a = (pr[0] - ms_run[0]) / mlen
                b = (pr[1] - ms_run[0]) / mlen
                gx0 = fs_run[0] + int(round(a * flen))
                gx1 = fs_run[0] + int(round(b * flen))
                gx0 = max(fs_run[0], min(fs_run[1], gx0))
                gx1 = max(fs_run[0], min(fs_run[1], gx1))
                plen = max(1, pr[1] - pr[0])
                glen = max(1, gx1 - gx0)
                for x in range(gx0, gx1 + 1):
                    if not f_row[x]:
                        continue
                    u = (x - gx0) / glen
                    mx = pr[0] + int(round(u * plen))
                    out[y, x] = mp[ym, mx]



def fix_passes(mp, fs, out):
    """Post passes on one output frame: gap fill, hole fill, cuff extension."""
    pm = mp[..., 3] > 0
    if not pm.any():
        return
    # darkest pants color in this frame = seam/outline shade
    ys, xs = np.where(pm)
    cols = mp[ys, xs, :3].astype(int)
    lum = cols @ [3, 6, 1]
    seam = mp[ys[lum.argmin()], xs[lum.argmin()]]

    def covered(y, x):
        return out[y, x, 3] > 0

    # 1. horizontal interior gap fill: skin pixel with pants within 2px both sides
    #    (same skin run, no transparency crossed) -> seam color
    for y in range(FH):
        if not fs[y].any():
            continue
        for x in range(FW):
            if not fs[y, x] or covered(y, x):
                continue
            ok_l = ok_r = False
            for d in (1, 2):
                if x - d >= 0 and fs[y, x - d] and covered(y, x - d):
                    ok_l = True; break
                if x - d < 0 or not fs[y, x - d]:
                    break
            for d in (1, 2):
                if x + d < FW and fs[y, x + d] and covered(y, x + d):
                    ok_r = True; break
                if x + d >= FW or not fs[y, x + d]:
                    break
            if ok_l and ok_r:
                out[y, x] = seam

    # 2. vertical hole fill: skin pixel with pants directly above and below
    for y in range(1, FH - 1):
        for x in range(FW):
            if fs[y, x] and not covered(y, x) and covered(y - 1, x) and covered(y + 1, x):
                out[y, x] = out[y - 1, x]

    # 3. downward cuff extension: extend pants down each column over the shin,
    #    stopping 2px above that column's lowest skin pixel (the foot)
    col_low = {}
    for x in range(FW):
        col = np.where(fs[:, x])[0]
        if len(col):
            col_low[x] = int(col.max())
    for x in range(FW):
        if x not in col_low:
            continue
        limit = col_low[x] - 2
        for y in range(1, FH):
            if y <= limit and fs[y, x] and not covered(y, x) and covered(y - 1, x):
                out[y, x] = out[y - 1, x]

def main():
    skin_m = load('skin_m1.png')
    skin_f = load('skin_f1.png')
    am = skin_m[..., 3] > 0
    af = skin_f[..., 3] > 0
    for src, dst in PAIRS:
        mp = load(src + '.png')
        out = np.zeros_like(mp)
        for r in range(7):
            for c in range(10):
                sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
                gen_frame(mp[sl], am[sl], af[sl], out[sl])
                fix_passes(mp[sl], af[sl], out[sl])
        Image.fromarray(out).save(CHAR + dst + '.png')
        print(dst, 'written,', int((out[..., 3] > 0).sum()), 'px')

if __name__ == '__main__':
    main()
