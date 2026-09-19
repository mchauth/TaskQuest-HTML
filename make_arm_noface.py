"""Build skin_arm_{g}{n}_noface.png: the arm layer WITHOUT its copy of the face/head.
The face copy exists so axes/staffs/bows pass behind the head; swords are allowed to cross the face,
weapons are held in the outer hand, so every class with an arm layer uses this variant
(see getCharLayers in index.html). Only the fist needs to draw over the weapon grip."""
import numpy as np, os
from PIL import Image
from collections import deque
CH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sprites/preview_assets/char')
RAISED = {51, 52, 53}        # raised-arm frames: layer = fist + a chunk of the back of the head -> keep the fist only
def comps(m):
    seen = np.zeros_like(m); res = []
    for y0, x0 in zip(*np.where(m)):
        if seen[y0, x0]: continue
        q = deque([(y0, x0)]); seen[y0, x0] = True; cc = []
        while q:
            y, x = q.popleft(); cc.append((y, x))
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                yy, xx = y+dy, x+dx
                if 0 <= yy < m.shape[0] and 0 <= xx < m.shape[1] and m[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True; q.append((yy, xx))
        res.append(cc)
    return res
import importlib.util
_spec = importlib.util.spec_from_file_location('v8', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fix_swords_v8.py'))
v8 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v8)
HAND_R = 4.5                  # keep only arm pieces touching this radius around the detected hand

for g in 'mf':
    H = v8.hands(g)           # per-frame hand centre (idle, walk, attack)
    for n in range(1, 6):
        a = np.array(Image.open(f'{CH}/skin_arm_{g}{n}.png').convert('RGBA'))
        removed = 0
        for idx in range((a.shape[0]//64) * (a.shape[1]//80)):
            r, c = idx // 10, idx % 10
            f = a[r*64:(r+1)*64, c*80:(c+1)*80]
            cs = comps(f[:,:,3] > 0)
            if idx in RAISED:
                fist = max(cs, key=lambda cc: np.mean([p[1] for p in cc]))   # right-most piece = the raised fist
                for cc in cs:
                    if cc is not fist:
                        for y, x in cc: f[y, x, 3] = 0
                        removed += len(cc)
                continue
            if idx in H:                                        # fist only: drop belt line, briefs, neck bits
                hx, hy = H[idx][0]
                for cc in cs:
                    near = min(np.hypot(x - hx, y - hy) for y, x in cc) <= HAND_R
                    rgb = np.array([f[y, x, :3] for y, x in cc], int)
                    cloth = int((rgb[:, 2] > rgb[:, 0] + 15).sum()) >= 3   # blue-grey waistband / briefs
                    if not near or cloth:
                        for y, x in cc: f[y, x, 3] = 0
                        removed += len(cc)
                continue
            for cc in cs:
                ys = [p[0] for p in cc]; xs = [p[1] for p in cc]
                if min(ys) <= 25 and max(xs) <= 46:            # head/face piece
                    for y, x in cc: f[y, x, 3] = 0
                    removed += len(cc)
        Image.fromarray(a).save(f'{CH}/skin_arm_{g}{n}_noface.png')
        print(g, n, 'face pixels removed', removed)
