"""Broadsword sheets v8 — ZERO resampling. Every frame is the original art or an exact 90-degree turn of it.

Two art sets give 8 clean directions:
  sprites/sword_src_native/tN.png              original PixelLab diagonal art  -> 45 / 135 / 225 / 315 deg
  sprites/sword_src_native/horizontal_pl/tN.png PixelLab horizontal redraws     -> 0 / 90 / 180 / 270 deg
  (t19/t20 use *_strip.png animated versions of both)
Angles below are GAME-view degrees (0 = forward, 90 = up, 180 = behind) and must be multiples of 45.

Usage:  python3 fix_swords_v7.py [outdir] [t7,t8,...]      (default outdir = sprites/preview_assets/char)

Inputs
  sprites/sword_src_native/tN.png         original PixelLab exports (t7-t18)
  sprites/sword_src_native/t19_strip.png  animated strips, 48px frames (t19, t20)
  sprites/sword_src_80x64/                the old 80x64 sheets (used only for hand/bob positions + unused rows)
Output
  128x112 frames (80x64 box + 24px padding), sheet 1280x784.

Pixel rule: exact 90-degree turns are lossless; any other angle is resampled (RotSprite-style)
and will show some breakup on 48px art. Idle uses a lossless pose; only the fast attack frames rotate freely.
"""
import numpy as np, math, os, sys
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
CH   = f'{ROOT}/sprites/preview_assets/char'
NAT  = f'{ROOT}/sprites/sword_src_native'
OLD  = f'{ROOT}/sprites/sword_src_80x64'
FW, FH, PAD = 80, 64, 24
BW, BH = FW + 2*PAD, FH + 2*PAD
HOLD = 7                      # px from pommel to the fist, along the blade
HOR = f'{NAT}/horizontal_pl'
IDLE_ANGLE = 0                # idle + walk: blade level and forward (chest/armor visible)
# Tiers that keep ONLY the original diagonal art (the horizontal redraw lost too much detail).
# Their idle stays as drawn (45 deg); attack frames at 0/90/180 are rotated from the original (brief frames).
ORIGINAL_ONLY = {'t8', 't10', 't13'}
ORIGINAL_IDLE_ANGLE = 45      # as drawn: the original art, untouched

POSE_ROWS = (0, 1)            # row 0 idle, row 1 walk

# Fist centres (raw coords) in attack frames, read from skin_arm layers
FIST = {'m': {50:(43,49), 51:(50,23), 52:(54,22), 53:(54,22), 54:(29,42), 55:(37,50)},
        'f': {50:(44,49), 51:(49,23), 52:(54,22), 53:(54,22), 54:(29,42), 55:(38,50)}}
# Blade direction in GAME view (0 = forward, 90 = up, 180 = behind)
SWING = {50: 45, 51: 135, 52: 180, 53: 90, 54: 0, 55: 0}
SMEAR = {53: (180, 90), 54: (90, 0)}

# ── pixel helpers ──────────────────────────────────────────────────────────────
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

def rotate_about(img, pivot, deg_cw):
    """Rotate clockwise (screen) about pivot. Exact for multiples of 90, RotSprite-style otherwise.
    Returns (canvas_image, pivot_on_canvas)."""
    a = np.array(img); a[a[:,:,3] <= 50] = 0
    R = int(math.hypot(*img.size)) + 4; C = 2*R
    can = np.zeros((C, C, 4), np.uint8)
    ox, oy = R - int(pivot[0]), R - int(pivot[1])
    can[oy:oy+a.shape[0], ox:ox+a.shape[1]] = a
    q = deg_cw / 90.0
    if abs(q - round(q)) < 1e-6:                        # lossless path
        k = int(round(q)) % 4
        # np.rot90 k>0 is counter-clockwise; pivot sits at (R,R) on a CxC canvas -> rotation keeps it at (R-?,...)
        can2 = np.rot90(can, k=-k)                      # clockwise k times
        # centre of rotation for rot90 on an even canvas is (C-1)/2 -> shift so pivot stays at (R,R)
        piv = np.array([R, R], float); c0 = (C-1)/2
        v = piv - c0
        for _ in range(k): v = np.array([-v[1], v[0]])  # clockwise on screen (x right, y down)
        newp = v + c0
        return Image.fromarray(np.ascontiguousarray(can2)), (newp[0], newp[1])
    big = can
    for _ in range(3): big = epx(big)
    bi = Image.fromarray(big).rotate(-deg_cw, resample=Image.NEAREST, center=(R*8+4, R*8+4))
    return Image.fromarray(np.array(bi)[4::8, 4::8]), (R, R)

def remove_shadow(a):
    h = a.shape[0]
    for y in range(h-1, max(h-12, 0), -1):
        s = a[y,:,:3].astype(int).sum(1)
        a[y,:,3][((a[y,:,3] < 220) & (s < 200)) | ((a[y,:,3] == 255) & (s <= 200))] = 0
    return a

def prep(img, horizontal=False):
    """mirror (game flips back), strip shadow, crop. NO scaling."""
    a = remove_shadow(np.array(ImageOps.mirror(img.convert('RGBA'))))
    a[a[:,:,3] <= 50] = 0
    ys, xs = np.where(a[:,:,3] > 0)
    img = Image.fromarray(a).crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
    a = np.array(img); ys, xs = np.where(a[:,:,3] > 0)
    if horizontal:   # handle is the right-most end after mirroring
        rx = xs.max(); rr = ys[xs == rx]; pom = (float(rx), float(np.median(rr).round()))
    else:
        k = np.argmax(xs + ys); pom = (float(xs[k]), float(ys[k]))        # pommel: lower-right (raw)
    t = np.argmax((xs-pom[0])**2 + (ys-pom[1])**2); tip = (float(xs[t]), float(ys[t]))
    return img, pom, tip

def _load(folder, tier, horizontal):
    p = f'{folder}/{tier}.png'
    if os.path.exists(p): return [prep(Image.open(p), horizontal)]
    strip = Image.open(f'{folder}/{tier}_strip.png').convert('RGBA'); fw = strip.size[1]
    return [prep(strip.crop((i*fw, 0, i*fw+fw, fw)), horizontal) for i in range(strip.size[0] // fw)]

def sources(tier):
    horiz = None if tier in ORIGINAL_ONLY else _load(HOR, tier, True)
    return {'diag': _load(NAT, tier, False), 'horiz': horiz}

def pick(srcs, idx, g):
    """art + exact 90-degree rotation for game angle g (multiple of 45)"""
    assert g % 45 == 0, f'angle {g} is not a multiple of 45 -> would need resampling'
    if g % 90 == 0 and srcs['horiz'] is None:          # original-only tier: rotate the diagonal art
        src = srcs['diag'][idx % len(srcs['diag'])]
        return src, game_deg_to_cw(src, g)
    lst = srcs['horiz'] if g % 90 == 0 else srcs['diag']
    src = lst[idx % len(lst)]
    cw = game_deg_to_cw(src, g)
    return src, round(cw / 90.0) * 90

def dir_of(pom, tip):
    L = math.hypot(tip[0]-pom[0], tip[1]-pom[1]); return (tip[0]-pom[0])/L, (tip[1]-pom[1])/L, L

def place(frame, src, hold_xy, deg_cw):
    """Rotate sword by deg_cw (screen, raw coords) about its pommel, put its hold point at hold_xy (raw)."""
    img, pom, tip = src
    ux, uy, L = dir_of(pom, tip)
    r = math.radians(deg_cw)
    rx, ry = ux*math.cos(r) - uy*math.sin(r), ux*math.sin(r) + uy*math.cos(r)   # rotated blade dir
    rot, piv = rotate_about(img, pom, deg_cw)
    hold = grip_dist(src)
    px, py = hold_xy[0] + PAD - hold*rx, hold_xy[1] + PAD - hold*ry
    frame.alpha_composite(rot, (int(round(px - piv[0])), int(round(py - piv[1]))))
    return L

def game_deg_to_cw(src, g):
    """clockwise screen rotation (raw) that makes the blade point at game angle g"""
    img, pom, tip = src
    ux, uy, _ = dir_of(pom, tip)
    target = math.atan2(-math.sin(math.radians(g)), -math.cos(math.radians(g)))
    return math.degrees(target - math.atan2(uy, ux))

def smear(frame, src, fist, a0, a1, L):
    arr = np.array(src[0]); m = arr[:,:,3] > 50
    rgb = arr[m][:,:3].astype(float); lum = rgb.sum(1)
    col = rgb[lum >= np.percentile(lum, 80)].mean(0)*0.45 + 255*0.55
    cx, cy = fist[0] + PAD, fist[1] + PAD
    yy, xx = np.mgrid[0:BH, 0:BW]; dx, dy = xx + .5 - cx, yy + .5 - cy
    r = np.hypot(dx, dy); g = np.degrees(np.arctan2(-dy, -dx))
    lo, hi = min(a0, a1), max(a0, a1); g = np.where(g < lo - 90, g + 360, g)
    inside = (g >= lo) & (g <= hi) & (r >= L*.40) & (r <= L*.98)
    prog = np.clip(1 - np.abs(g - a1)/max(1e-6, hi-lo), 0, 1); rad = np.clip((r - L*.40)/(L*.58), 0, 1)
    a = np.round(prog**1.6*(0.35 + 0.65*rad)*3)/3*0.75
    out = np.zeros((BH, BW, 4), np.uint8); out[...,:3] = col.astype(np.uint8)
    out[...,3] = np.where(inside, a*255, 0).astype(np.uint8)
    frame.alpha_composite(Image.fromarray(out))

ARM_HAND_FRAMES = {51, 52, 53, 54}
HAND_ANCHOR = {55: (47, 37)}        # (y, x) search anchor; default (46, 44) = hand hanging at the hip   # fist is on the arm layer (draws over the sword already)
_HAND_CACHE = {}
def hands(g):
    """per frame: (fist_centre, mask) in raw 80x64 coords. mask = hand pixels the sword must NOT cover."""
    if g in _HAND_CACHE: return _HAND_CACHE[g]
    L = lambda n: np.array(Image.open(f'{CH}/{n}').convert('RGBA'))[:,:,3] > 50
    skin, shirt, pants = L(f'skin_{g}1.png'), L(f'warrior_shirt_default_{g}.png'), L(f'warrior_pants_default_{g}.png')
    arm = L(f'skin_arm_{g}1.png')
    skin_rgb = np.array(Image.open(f'{CH}/skin_{g}1.png').convert('RGBA'))[:,:,:3]
    out = {}
    for idx in list(range(0, 5)) + list(range(10, 18)) + list(range(50, 56)):
        r, c = idx//10, idx % 10
        sl = np.s_[r*FH:(r+1)*FH, c*FW:(c+1)*FW]
        if idx in ARM_HAND_FRAMES:
            a = arm[sl]; ys, xs = np.where(a)
            d = np.hypot(xs - 43.0, ys - 29.0); far = d >= d.max() - 3.5
            out[idx] = ((float(xs[far].mean()), float(ys[far].mean())), None)
            continue
        exposed = skin[sl] & ~shirt[sl] & ~pants[sl]
        win = np.zeros_like(exposed); win[38:57, 30:56] = True          # below the neck, around the hip
        rgb = skin_rgb[sl].astype(int)
        bright = exposed & win & (rgb.sum(2) > 330)                       # skin tone, not the dark outline
        blobs = [b for b in _blobs(bright) if len(b) >= 2]
        if not blobs: continue
        cy, cx = HAND_ANCHOR.get(idx, (46, 44))                            # where the hand hangs (y, x)
        core = min(blobs, key=lambda b: min(np.hypot(y - cy, x - cx) for y, x in b))
        m = np.zeros_like(bright)
        for y, x in core: m[y, x] = True
        grown = m.copy()                                                  # + the hand's own outline
        grown[1:] |= m[:-1]; grown[:-1] |= m[1:]; grown[:, 1:] |= m[:, :-1]; grown[:, :-1] |= m[:, 1:]
        m = (grown & exposed) | m
        ys, xs = np.array([p[0] for p in core]), np.array([p[1] for p in core])
        dd = np.hypot(xs - 43.0, ys - 29.0); far = dd >= dd.max() - 2.5        # hand = end farthest from shoulder
        ys, xs = ys[far], xs[far]
        out[idx] = ((float(xs.mean()), float(ys.mean())), m)
    _HAND_CACHE[g] = out
    return out

def _blobs(mask):
    from collections import deque
    seen = np.zeros_like(mask); res = []
    for y0, x0 in zip(*np.where(mask)):
        if seen[y0, x0]: continue
        q = deque([(y0, x0)]); seen[y0, x0] = True; comp = []
        while q:
            y, x = q.popleft(); comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y+dy, x+dx
                    if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True; q.append((yy, xx))
        res.append(comp)
    return res

def grip_dist(src):
    """distance (px) from pommel to where the fist should sit: just below the crossguard"""
    img, pom, tip = src
    ux, uy, L = dir_of(pom, tip)
    a = np.array(img); ys, xs = np.where(a[:,:,3] > 50)
    t = (xs - pom[0])*ux + (ys - pom[1])*uy
    sd = -(xs - pom[0])*uy + (ys - pom[1])*ux
    widths = []
    for k in range(int(L*0.4)):
        sel = (t >= k - 0.5) & (t < k + 0.5)
        widths.append(sd[sel].max() - sd[sel].min() + 1 if sel.any() else 0)
    widths = np.array(widths)
    handle_w = np.median(widths[2:6]) if len(widths) > 6 else 2
    guard = next((k for k in range(3, len(widths)) if widths[k] >= handle_w + 3), 8)
    return max(2.5, guard - 2.5)

def old_hold(old_sheet, idx):
    """hand position in the old 80x64 sheet frame: its (arm-masked) pommel sits at the fist"""
    r, c = idx//10, idx % 10
    a = np.array(old_sheet.crop((c*FW, r*FH, c*FW+FW, r*FH+FH)))
    ys, xs = np.where(a[:,:,3] > 50)
    if len(xs) < 5: return None
    k = np.argmax(xs + ys); return (float(xs[k]), float(ys[k]))

def build(tier, g):
    srcs = sources(tier)
    old = Image.open(f'{OLD}/sword_warrior_{tier}_{g}.png').convert('RGBA')
    out = Image.new('RGBA', (10*BW, 7*BH), (0,0,0,0))
    for idx in range(70):
        r, c = idx//10, idx % 10
        f = Image.new('RGBA', (BW, BH), (0,0,0,0))
        H = hands(g)
        if 50 <= idx <= 55:
            fist = H[idx][0] if idx in H else FIST[g][idx]
            src, cw = pick(srcs, idx, SWING[idx])
            L = dir_of(src[1], src[2])[2]
            if idx in SMEAR: smear(f, src, fist, *SMEAR[idx], L)
            place(f, src, fist, cw)
        elif r in POSE_ROWS:
            h = H[idx][0] if idx in H else old_hold(old, idx)
            if h is not None:
                src, cw = pick(srcs, idx, ORIGINAL_IDLE_ANGLE if srcs['horiz'] is None else IDLE_ANGLE)
                place(f, src, h, cw)
        else:
            f.paste(old.crop((c*FW, r*FH, c*FW+FW, r*FH+FH)), (PAD, PAD))
        if idx in H and H[idx][1] is not None:        # fist over the handle
            fa = np.array(f); m = H[idx][1]
            fa[PAD:PAD+FH, PAD:PAD+FW, 3][m] = 0
            f = Image.fromarray(fa)
        out.paste(f, (c*BW, r*BH))
    return out

if __name__ == '__main__':
    outdir = sys.argv[1] if len(sys.argv) > 1 else CH
    tiers = sys.argv[2].split(',') if len(sys.argv) > 2 else [f't{i}' for i in range(7, 21)]
    os.makedirs(outdir, exist_ok=True)
    for t in tiers:
        for g in 'mf': build(t, g).save(f'{outdir}/sword_warrior_{t}_{g}.png')
        print(t, 'ok')
