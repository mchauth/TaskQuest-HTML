#!/usr/bin/env python3
"""Generate female rare warrior chest armor + boots from male rare palettes.

Method per set (rare1 Crimson Sentinel / rare2 Shadow Warden / rare3 Solar
Paladin):
  shirts: female base silhouette = warrior_shirt_default_f.png
    - silhouette-edge pixels -> pure black outline (male rare style)
    - interior pixels -> luminance-quantile color transfer onto the male
      rare shirt's non-black, non-accent color distribution (exact same
      hues/sats as the male sheets)
    - inverted-triangle chest emblem stamped at the female chest centroid
      (frame 0 centroid from torso zone y=37-46 x=34-50; other frames offset
      by the per-frame shirt-mask centroid delta)
  boots: female base silhouette = warrior_boots_f.png
    - luminance-quantile transfer from male boots_rareN palette
    - top-edge trim in the set accent color (matches male rare boots)
    - fill any uncovered female skin pixels in the foot zone
Run scripts/sprite_shade.py afterwards for cosine shading.
"""
import numpy as np
from PIL import Image

CHAR = 'sprites/preview_assets/char/'
FW, FH = 80, 64

SETS = {
    1: dict(emblem_edge=(255, 215, 0), emblem_fill=(255, 236, 120),
            emblem_hi=(255, 255, 220), boot_trim=(255, 215, 0)),
    2: dict(emblem_edge=(0, 254, 227), emblem_fill=(120, 255, 236),
            emblem_hi=(220, 255, 248), boot_trim=(0, 254, 227)),
    3: dict(emblem_edge=(255, 215, 0), emblem_fill=(255, 236, 120),
            emblem_hi=(255, 255, 220), boot_trim=(255, 251, 234)),
}

def load(p):
    return np.array(Image.open(CHAR + p).convert('RGBA'))

def lum(rgb):
    rgb = rgb.astype(np.float64)
    return (3 * rgb[..., 0] + 6 * rgb[..., 1] + rgb[..., 2]) / 10.0

def is_accent(rgb):
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    gold = (r >= 230) & (g >= 190)
    teal = (g >= 190) & (b >= 160) & (r <= g) & (r <= b)
    return gold | teal

def build_ramp(male_sheet):
    """Sorted-by-luminance RGB list of male rare colors (no black, no accent)."""
    op = male_sheet[..., 3] > 10
    cols = male_sheet[op][:, :3]
    keep = ~is_accent(cols) & (cols.astype(int).sum(axis=1) >= 15)
    cols = cols[keep]
    order = np.argsort(lum(cols), kind='stable')
    return cols[order]

def edge_mask(P):
    pad = np.pad(P, 1)
    n4 = (pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    return P & ~n4   # any transparent 4-neighbor (or frame border)

def quantile_map(base_sheet, ramp, force_outline):
    """Recolor base sheet: edges black (if force_outline), interior via
    luminance quantile lookup into ramp."""
    out = np.zeros_like(base_sheet)
    P = base_sheet[..., 3] > 10
    edges = np.zeros_like(P)
    if force_outline:
        for r in range(7):
            for c in range(10):
                sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
                edges[sl] = edge_mask(P[sl])
    interior = P & ~edges
    src_l = lum(base_sheet[interior][:, :3])
    ref = np.sort(src_l)
    q = np.searchsorted(ref, src_l, side='left') / max(1, len(ref) - 1)
    idx = np.clip((q * (len(ramp) - 1)).round().astype(int), 0, len(ramp) - 1)
    out[interior, 0] = ramp[idx][:, 0]
    out[interior, 1] = ramp[idx][:, 1]
    out[interior, 2] = ramp[idx][:, 2]
    out[interior, 3] = 255
    out[edges] = (0, 0, 0, 255)
    return out

def stamp_emblem(out, base_P, cfg):
    """Inverted triangle at chest centroid, per frame."""
    # frame 0 chest centroid (torso zone y=37-46, x=34-50)
    f0 = base_P[:FH, :FW]
    zys, zxs = np.where(f0[37:47, 34:51])
    cx0, cy0 = 34 + zxs.mean(), 37 + zys.mean()
    fys, fxs = np.where(f0)
    fcx0, fcy0 = fxs.mean(), fys.mean()
    E, F, H = cfg['emblem_edge'], cfg['emblem_fill'], cfg['emblem_hi']
    shape = [(-1, -2, E), (-1, -1, F), (-1, 0, H), (-1, 1, F), (-1, 2, E),
             (0, -1, E), (0, 0, H), (0, 1, E),
             (1, 0, E)]
    stamped = 0
    for fi in range(70):
        r, c = fi // 10, fi % 10
        sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
        Pf = base_P[sl]
        if not Pf.any():
            continue
        ys, xs = np.where(Pf)
        cy = int(round(cy0 + ys.mean() - fcy0))
        cy = max(1, min(FH - 2, cy))
        of = out[sl]
        # center emblem on the widest torso run of interior (non-outline)
        # pixels at row cy (sleeve pixels would bias a plain centroid)
        inter = (of[cy, :, 3] > 0) & ~np.all(of[cy, :, :3] == 0, axis=-1)
        runs, x = [], 0
        while x < FW:
            if inter[x]:
                x0 = x
                while x + 1 < FW and inter[x + 1]:
                    x += 1
                runs.append((x0, x))
            x += 1
        if not runs:
            continue
        r0, r1 = max(runs, key=lambda t: t[1] - t[0])
        mid = (r0 + r1) / 2.0
        def fit(cxc):
            k = 0
            for dy, dx, _ in shape:
                yy, xx = cy + dy, cxc + dx
                if 0 <= yy < FH and 0 <= xx < FW and Pf[yy, xx] \
                        and out[sl][yy, xx, 3] > 0 \
                        and tuple(out[sl][yy, xx, :3]) != (0, 0, 0):
                    k += 1
            return k
        cands = range(max(1, r0), min(FW - 1, r1 + 1))
        cx = max(cands, key=lambda cxc: (fit(cxc), -abs(cxc - mid)))
        for dy, dx, col in shape:
            y, x = cy + dy, cx + dx
            if 0 <= y < FH and 0 <= x < FW and Pf[y, x] and of[y, x, 3] > 0 \
                    and tuple(of[y, x, :3]) != (0, 0, 0):
                of[y, x, :3] = col
                stamped += 1
    return stamped

def boot_trim(out, cfg):
    """Topmost opaque pixel per column -> accent trim (per frame)."""
    for fi in range(70):
        r, c = fi // 10, fi % 10
        of = out[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW]
        P = of[..., 3] > 0
        if not P.any():
            continue
        ymin = int(np.where(P.any(axis=1))[0].min())
        for x in range(FW):
            col = np.where(P[:, x])[0]
            if len(col) and col.min() <= ymin + 2:
                of[col.min(), x, :3] = cfg['boot_trim']

def fill_foot_gaps(out, skin):
    """Cover any female skin pixel in the foot zone left bare by the boots."""
    filled = 0
    for fi in range(70):
        r, c = fi // 10, fi % 10
        sl = (slice(r * FH, (r + 1) * FH), slice(c * FW, (c + 1) * FW))
        of, sk = out[sl], skin[sl]
        P = of[..., 3] > 0
        if not P.any():
            continue
        # per-column boot top: only holes inside/below the boot in that column
        gaps = np.zeros_like(P)
        for x in range(FW):
            col = np.where(P[:, x])[0]
            if len(col):
                gaps[col.min():, x] = sk[col.min():, x] & ~P[col.min():, x]
        gys, gxs = np.where(gaps)
        if not len(gys):
            continue
        oys, oxs = np.where(P)
        for gy, gx in zip(gys, gxs):
            d = np.abs(oxs - gx) + 3 * np.abs(oys - gy)
            k = d.argmin()
            of[gy, gx] = of[oys[k], oxs[k]]
            filled += 1
    return filled

def main():
    skin = load('skin_f1.png')[..., 3] > 0
    shirt_base = load('warrior_shirt_default_f.png')
    boots_base = load('warrior_boots_f.png')
    for n, cfg in SETS.items():
        # shirt
        ramp = build_ramp(load(f'shirt_rare{n}.png'))
        out = quantile_map(shirt_base, ramp, force_outline=True)
        ns = stamp_emblem(out, shirt_base[..., 3] > 10, cfg)
        Image.fromarray(out).save(CHAR + f'shirt_rare{n}_f.png')
        print(f'shirt_rare{n}_f.png written ({int((out[...,3]>0).sum())} px, emblem px stamped {ns})')
        # boots
        ramp = build_ramp(load(f'boots_rare{n}.png'))
        outb = quantile_map(boots_base, ramp, force_outline=False)
        boot_trim(outb, cfg)
        nf = fill_foot_gaps(outb, skin)
        Image.fromarray(outb).save(CHAR + f'boots_rare{n}_f.png')
        print(f'boots_rare{n}_f.png written ({int((outb[...,3]>0).sum())} px, foot gaps filled {nf})')

if __name__ == '__main__':
    main()
