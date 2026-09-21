"""Mage staff sheets t7-t25 — zero resampling, same system as fix_swords_v8.py.

Art (sprites/staff_src/):  tN_vert.png  upright PixelLab staff     -> 0 / 90 / 180 / 270 deg
                           tN_diag.png  45-deg PixelLab redraw      -> 45 / 135 / 225 / 315 deg
Poses are GAME-view degrees (0 = forward, 90 = up). The mage hand is on the body layer
(no arm layer), so every held frame cuts the hand shape out of the staff.
Usage: python3 fix_staffs.py [outdir] [t7,t8,...]
"""
import os, sys, math, numpy as np, importlib.util
from PIL import Image, ImageOps
ROOT = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('v8', f'{ROOT}/fix_swords_v8.py'); v8 = importlib.util.module_from_spec(_s); _s.loader.exec_module(v8)
CH, BW, BH, PAD, FW, FH = v8.CH, v8.BW, v8.BH, v8.PAD, v8.FW, v8.FH
SRC = f'{ROOT}/sprites/staff_src'
GRIP = 0.46                                  # hand position up the shaft (higher = head sits lower, away from the face)
POSE = {'idle': 45, 50: 45, 51: 90, 52: 90, 53: 90, 54: 90, 55: 45}   # 54 = cast (staff raised upright)
SLEEP = {'frames': (68, 69), 'angle': 0, 'centre': (36, 59)}         # lying on the ground beside the sleeper

def prep(path, upright):
    img = ImageOps.mirror(Image.open(path).convert('RGBA'))
    a = np.array(img); a[a[:,:,3] < 128] = 0; img = Image.fromarray(a); img = img.crop(img.getbbox())
    a = np.array(img); ys, xs = np.where(a[:,:,3] > 0)
    if upright: by = ys.max(); butt = (float(np.median(xs[ys >= by - 1]).round()), float(by))
    else:       k = np.argmax(xs + ys); butt = (float(xs[k]), float(ys[k]))
    t = np.argmax((xs - butt[0])**2 + (ys - butt[1])**2)
    return img, butt, (float(xs[t]), float(ys[t]))

def pick(srcs, g):
    src = srcs['vert'] if g % 90 == 0 else srcs['diag']
    return src, round(v8.game_deg_to_cw(src, g) / 90.0) * 90

def place(f, src, hold_xy, cw):
    img, butt, tip = src
    ux, uy, L = v8.dir_of(butt, tip); r = math.radians(cw)
    rx, ry = ux*math.cos(r) - uy*math.sin(r), ux*math.sin(r) + uy*math.cos(r)
    rot, piv = v8.rotate_about(img, butt, cw)
    px, py = hold_xy[0] + PAD - GRIP*L*rx, hold_xy[1] + PAD - GRIP*L*ry
    f.alpha_composite(rot, (int(round(px - piv[0])), int(round(py - piv[1]))))

def fist_masks(g):
    arm = np.array(Image.open(f'{CH}/skin_arm_{g}1_noface.png').convert('RGBA'))[:,:,3] > 0
    return {i: arm[(i//10)*FH:(i//10+1)*FH, (i%10)*FW:(i%10+1)*FW] for i in (51, 52, 53, 54)}

def build(tier, g):
    srcs = {'vert': prep(f'{SRC}/{tier}_vert.png', True), 'diag': prep(f'{SRC}/{tier}_diag.png', False)}
    H, FM = v8.hands(g), fist_masks(g)
    out = Image.new('RGBA', (10*BW, 7*BH), (0,0,0,0))
    for idx in range(70):
        r, c = idx // 10, idx % 10
        f = Image.new('RGBA', (BW, BH), (0,0,0,0)); mask = None
        if idx in H and (r in (0, 1) or 50 <= idx <= 55):
            g_ang = POSE.get(idx, POSE['idle'])
            src, cw = pick(srcs, g_ang)
            place(f, src, H[idx][0], cw)
            mask = FM.get(idx, H[idx][1])
        elif idx in SLEEP['frames']:
            src, cw = pick(srcs, SLEEP['angle'])
            rot, _ = v8.rotate_about(src[0], src[1], cw); rot = rot.crop(rot.getbbox())
            cx, cy = SLEEP['centre']
            f.alpha_composite(rot, (int(cx + PAD - rot.size[0]/2), int(min(cy + PAD - rot.size[1]/2, FH + PAD - rot.size[1]))))
        if mask is not None:
            fa = np.array(f); fa[PAD:PAD+FH, PAD:PAD+FW, 3][mask] = 0; f = Image.fromarray(fa)
        out.paste(f, (c*BW, r*BH))
    return out

if __name__ == '__main__':
    outdir = sys.argv[1] if len(sys.argv) > 1 else CH
    tiers = sys.argv[2].split(',') if len(sys.argv) > 2 else [f't{i}' for i in range(7, 26)]
    os.makedirs(outdir, exist_ok=True)
    for t in tiers:
        for g in 'mf': build(t, g).save(f'{outdir}/staff_mage_{t}_{g}.png')
        print(t, 'ok')
