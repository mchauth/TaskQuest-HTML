"""Rotate pixel art without blur (RotSprite-style): 8x EPX upscale -> nearest rotate -> sample back down.
Every output pixel is an exact colour from the source; no new colours, no semi-transparency.
Usage: python3 rotate_pixelart.py <in.png> <out.png> <degrees clockwise> [canvas]"""
import sys, math, numpy as np
from PIL import Image

def epx(a):
    P = np.pad(a, ((1,1),(1,1),(0,0)), mode='edge')
    A, B, C, D, Pc = P[:-2,1:-1], P[1:-1,2:], P[1:-1,:-2], P[2:,1:-1], P[1:-1,1:-1]
    eq = lambda x, y: np.all(x == y, axis=2)
    h, w = a.shape[:2]; o = np.zeros((h*2, w*2, 4), a.dtype)
    o[0::2,0::2] = np.where((eq(C,A) & ~eq(C,D) & ~eq(A,B))[...,None], A, Pc)
    o[0::2,1::2] = np.where((eq(A,B) & ~eq(A,C) & ~eq(B,D))[...,None], B, Pc)
    o[1::2,0::2] = np.where((eq(D,C) & ~eq(D,B) & ~eq(C,A))[...,None], C, Pc)
    o[1::2,1::2] = np.where((eq(B,D) & ~eq(B,A) & ~eq(D,C))[...,None], D, Pc)
    return o

def strip_shadow(a):
    """PixelLab drops a dark ground shadow in the bottom rows - remove it."""
    h = a.shape[0]
    for y in range(h-1, max(h-12, 0), -1):
        s = a[y,:,:3].astype(int).sum(1)
        a[y,:,3][((a[y,:,3] < 220) & (s < 200)) | ((a[y,:,3] == 255) & (s <= 200))] = 0
    return a

def repair(a, passes=2):
    """Close 1-px gaps that a 45-degree turn opens in thin lines (handles, outlines):
    a transparent pixel with solid pixels on both opposite sides takes the colour of one of them."""
    a = a.copy()
    for _ in range(passes):
        op = a[:,:,3] > 0
        P = np.pad(a, ((1,1),(1,1),(0,0))); Po = np.pad(op, 1)
        L, R, U, Dn = Po[1:-1,:-2], Po[1:-1,2:], Po[:-2,1:-1], Po[2:,1:-1]
        UL, DR, UR, DL = Po[:-2,:-2], Po[2:,2:], Po[:-2,2:], Po[2:,:-2]
        cnt = (L+R+U+Dn+UL+DR+UR+DL)
        fill_h = ~op & L & R & (cnt <= 5)
        fill_v = ~op & U & Dn & (cnt <= 5) & ~fill_h
        a[fill_h] = P[1:-1,:-2][fill_h]          # take left neighbour
        a[fill_v] = P[:-2,1:-1][fill_v]          # take top neighbour
        # interior holes (surrounded on all 4 sides) -> left neighbour
        hole = ~op & L & R & U & Dn
        a[hole] = P[1:-1,:-2][hole]
    return a

def bridge_handle(a):
    """For a horizontal sword: the thin run of columns at the grip end is the handle.
    Make it one continuous row (fills the dashes a 45-degree turn leaves in 1-2px diagonal lines)."""
    a = a.copy(); op = a[:,:,3] > 0
    cols = np.where(op.any(0))[0]
    if len(cols) < 10: return a
    cnt = op.sum(0)
    for side in (cols[:len(cols)//3], cols[::-1][:len(cols)//3]):   # try both ends, use the thin one
        thin = [c for c in side if 0 < cnt[c] <= 3]
        run = []
        for c in side:                       # contiguous-ish thin run from the end inward
            if cnt[c] <= 3: run.append(c)
            elif len(run) > 4: break
        run = [c for c in run if cnt[c] > 0] or run
        if len(run) < 5: continue
        rows = np.concatenate([np.where(op[:, c])[0] for c in run if cnt[c] > 0])
        if not len(rows): continue
        r0 = int(np.bincount(rows).argmax())
        lo, hi = min(run), max(run)
        last = None
        for c in range(lo, hi+1):
            if op[r0, c]: last = a[r0, c].copy(); continue
            src = [rr for rr in (r0-1, r0+1) if 0 <= rr < a.shape[0] and op[rr, c]]
            if src: a[r0, c] = a[src[0], c]
            elif last is not None: a[r0, c] = last
        break
    return a

def rotate(img, deg_cw, canvas=None, shadow=True, repair_gaps=True):
    a = np.array(img.convert('RGBA'))
    if shadow: a = strip_shadow(a)
    a[a[:,:,3] < 128] = 0; a[a[:,:,3] >= 128, 3] = 255          # hard alpha
    h, w = a.shape[:2]
    D = int(math.ceil(math.hypot(w, h))) + 4
    can = np.zeros((D, D, 4), np.uint8)
    oy, ox = (D-h)//2, (D-w)//2; can[oy:oy+h, ox:ox+w] = a
    q = deg_cw / 90
    if abs(q - round(q)) < 1e-9:
        out = np.rot90(can, k=-int(round(q)))
    else:
        big = can
        for _ in range(3): big = epx(big)
        big = np.array(Image.fromarray(big).rotate(-deg_cw, resample=Image.NEAREST, center=(D*4, D*4)))
        out = big[4::8, 4::8]
    out = repair(np.ascontiguousarray(out)) if repair_gaps else np.ascontiguousarray(out)
    if repair_gaps and abs((deg_cw % 90) - 45) < 1: out = bridge_handle(out)
    out = Image.fromarray(out)
    bb = out.getbbox(); out = out.crop(bb)
    if canvas:
        c = Image.new('RGBA', (canvas, canvas), (0,0,0,0))
        c.paste(out, ((canvas-out.size[0])//2, (canvas-out.size[1])//2)); out = c
    return out

if __name__ == '__main__':
    src, dst, deg = sys.argv[1], sys.argv[2], float(sys.argv[3])
    canvas = int(sys.argv[4]) if len(sys.argv) > 4 else None
    rotate(Image.open(src), deg, canvas).save(dst)
