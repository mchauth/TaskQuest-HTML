#!/usr/bin/env python3
"""
gen_weapons_v2.py — Rebuild all weapon sprites with:
  1. Per-frame rotation in slash frames 51-53 (matching source sword.png angles)
  2. Arc trail (white+lavender) for frame 54 on swords and staffs
  3. Redesigned bow shape (vertical bow, upper+lower limbs, string)
  4. Bow draw animation instead of slash (bow raises to vertical, arrow fires)
"""
import numpy as np
from PIL import Image

FW, FH, COLS, ROWS = 80, 64, 10, 7

# ── Source sprite analysis ───────────────────────────────────────────────────

def get_centroid(arr, fi):
    r, c = fi // COLS, fi % COLS
    sl = arr[r*FH:(r+1)*FH, c*FW:(c+1)*FW]
    op = np.argwhere(sl[..., 3] > 0)
    if len(op) == 0: return None, None
    return float(np.mean(op[:,1])), float(np.mean(op[:,0]))

def get_angle(arr, fi):
    r, c = fi // COLS, fi % COLS
    sl = arr[r*FH:(r+1)*FH, c*FW:(c+1)*FW]
    op = np.argwhere(sl[..., 3] > 0)
    if len(op) < 3: return 0.0
    ys, xs = op[:,0].astype(float), op[:,1].astype(float)
    cx, cy = np.mean(xs), np.mean(ys)
    pts = np.stack([xs-cx, ys-cy], axis=1)
    cov = pts.T @ pts / len(op)
    vals, vecs = np.linalg.eigh(cov)
    pv = vecs[:, np.argmax(vals)]
    return float(np.degrees(np.arctan2(pv[1], pv[0])))

SRC = np.array(Image.open('sprites/preview_assets/char/sword.png').convert('RGBA'))
src_cx0, src_cy0 = get_centroid(SRC, 0)
src_ang0 = get_angle(SRC, 0)

# Per-frame slash rotation deltas (relative to frame 0)
SLASH_ANGLES = {}
for fi in [51, 52, 53, 55]:
    SLASH_ANGLES[fi] = get_angle(SRC, fi) - src_ang0

# Slash centroids from source
SLASH_CX = {}; SLASH_CY = {}
for fi in range(COLS * ROWS):
    cx, cy = get_centroid(SRC, fi)
    if cx is not None: SLASH_CX[fi] = cx; SLASH_CY[fi] = cy

print("Slash angle deltas:", {k: f"{v:.1f}°" for k,v in SLASH_ANGLES.items()})

# Pre-compute extend positions: only use fr54 and fr55 (last 2 frames, reversed)
# fr54 = "extended/raised" position; fr55 = "idle/resting" position
DX_FR54 = round(SLASH_CX[54] - src_cx0)
DY_FR54 = round(SLASH_CY[54] - src_cy0)
DX_FR55 = round(SLASH_CX[55] - src_cx0)
DY_FR55 = round(SLASH_CY[55] - src_cy0)
print(f"Extend positions: fr54=({DX_FR54},{DY_FR54}), fr55=({DX_FR55},{DY_FR55})")

# ── Utility ──────────────────────────────────────────────────────────────────

def bezier_pts(p0, ctrl, p2, steps=14):
    """Quadratic Bezier curve from p0 to p2 with control point ctrl."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = round((1-t)**2 * p0[0] + 2*t*(1-t) * ctrl[0] + t**2 * p2[0])
        y = round((1-t)**2 * p0[1] + 2*t*(1-t) * ctrl[1] + t**2 * p2[1])
        pts.append((x, y))
    deduped = [pts[0]]
    for p in pts[1:]:
        if p != deduped[-1]:
            deduped.append(p)
    return deduped

def bresenham(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1-x0), abs(y1-y0)
    sx, sy = (1 if x1>x0 else -1), (1 if y1>y0 else -1)
    err = dx - dy
    x, y = x0, y0
    while True:
        pts.append((x, y))
        if x == x1 and y == y1: break
        e2 = 2 * err
        if e2 > -dy: err -= dy; x += sx
        if e2 < dx:  err += dx; y += sy
    return pts

def rotate_pixels(pix, angle_deg, around_cx, around_cy):
    if not pix: return {}
    rad = np.radians(angle_deg)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    result = {}
    for (x, y), color in pix.items():
        px, py = x - around_cx, y - around_cy
        nx = round(cos_a*px - sin_a*py + around_cx)
        ny = round(sin_a*px + cos_a*py + around_cy)
        if 0 <= nx < FW and 0 <= ny < FH and (nx,ny) not in result:
            result[(nx, ny)] = color
    return result

def translate_pixels(pix, dx, dy):
    result = {}
    for (x, y), color in pix.items():
        nx, ny = x+dx, y+dy
        if 0 <= nx < FW and 0 <= ny < FH and (nx,ny) not in result:
            result[(nx, ny)] = color
    return result

def centroid_of(pix):
    if not pix: return 0.0, 0.0
    xs = [p[0] for p in pix]; ys = [p[1] for p in pix]
    return float(np.mean(xs)), float(np.mean(ys))

def stamp(out, pix, gx, gy):
    for (x, y), color in pix.items():
        if 0 <= x < FW and 0 <= y < FH:
            out[gy+y, gx+x] = color

# ── Trail arc for frame 54 (swing trail) ─────────────────────────────────────

def make_trail_arc(trail_color_center, trail_color_edge):
    """Generate a diagonal sweep arc like the one in sword.png frame 54."""
    WHITE = trail_color_center
    LAV   = trail_color_edge
    pix = {}
    # Diagonal band: center line goes from upper-right to lower-left
    # y in [1,44], center_x = 47 - 0.59*y, half_width = 5 + 0.3*y
    for y in range(0, 46):
        cx_line = 47.0 - 0.59 * y
        hw = 5.0 + 0.3 * y
        x0 = round(cx_line - hw)
        x1 = round(cx_line + hw)
        for x in range(max(0, x0), min(FW, x1+1)):
            dist = abs(x - cx_line)
            if dist > hw - 1.5:
                color = LAV
            else:
                color = WHITE
            pix[(x, y)] = color
    return pix

def make_trail_frame55(trail_color_center, trail_color_edge):
    """Smaller fading trail for frame 55 (sword.png pattern)."""
    WHITE = trail_color_center
    LAV   = trail_color_edge
    pix = {}
    # Sword-like bottom arc: horizontal band around y=47-54
    for y in range(47, 55):
        cx_line = 16.0 + (y-47) * 2.0
        hw = 8.0 + (y-47)
        x0, x1 = round(cx_line - hw), round(cx_line + hw)
        for x in range(max(0, x0), min(FW, x1+1)):
            dist = abs(x - cx_line)
            if dist > hw - 1.5:
                color = LAV
            else:
                color = WHITE
            pix[(x, y)] = color
    # Small upper remnant
    for y in range(3, 7):
        cx_line = 36.0 - (y-3)*1.5
        for x in range(max(0, round(cx_line)-1), min(FW, round(cx_line)+2)):
            pix[(x, y)] = WHITE
    return pix

# ── Centroid-propagate pixels across all frames ───────────────────────────────

def build_sheet(f0, source_path, out_path, weapon_type='sword',
                trail_c=None, trail_e=None):
    """
    f0: dict of {(x,y): rgba_tuple} for frame 0
    source_path: reference sprite for centroid tracking (sword.png)
    weapon_type: 'sword', 'staff', or 'bow'
    trail_c/trail_e: trail center/edge colors for slash frame 54 (sword/staff only)
    """
    src_arr = np.array(Image.open(source_path).convert('RGBA'))
    out = np.zeros((ROWS*FH, COLS*FW, 4), dtype=np.uint8)

    cx0_src, cy0_src = get_centroid(src_arr, 0)
    cx0_f0, cy0_f0   = centroid_of(f0)

    for fi in range(COLS * ROWS):
        r, c = fi // COLS, fi % COLS
        gx, gy = c * FW, r * FH

        cx_src, cy_src = get_centroid(src_arr, fi)
        if cx_src is None: continue
        dx = round(cx_src - cx0_src)
        dy = round(cy_src - cy0_src)

        if weapon_type == 'sword':
            # Sword: full slash arc with rotation and trail.
            # +180° flips grip/blade so grip stays in hand during swing.
            if fi in [51, 52, 53]:
                angle_delta = SLASH_ANGLES.get(fi, 0.0) + 180.0
                pix2 = rotate_pixels(f0, angle_delta, cx0_f0, cy0_f0)
                pix2 = translate_pixels(pix2, dx, dy)
                stamp(out, pix2, gx, gy)
            elif fi == 54:
                if trail_c and trail_e:
                    trail = make_trail_arc(trail_c, trail_e)
                    stamp(out, trail, gx, gy)
                pix = translate_pixels(f0, dx, dy)
                dark_pix = {k: v for k, v in pix.items() if int(v[0])+int(v[1])+int(v[2]) < 90}
                stamp(out, dark_pix, gx, gy)
            elif fi == 55:
                if trail_c and trail_e:
                    trail = make_trail_frame55(trail_c, trail_e)
                    stamp(out, trail, gx, gy)
                pix = translate_pixels(f0, dx, dy)
                stamp(out, pix, gx, gy)
            else:
                pix = translate_pixels(f0, dx, dy)
                stamp(out, pix, gx, gy)

        elif weapon_type in ('staff', 'bow'):
            # Align weapon's OWN centroid to sword hand centroid for THIS frame.
            # Characters are displayed with scaleX(-1), so LEFT in PNG = RIGHT on screen.
            # For slash frames use the slash centroid table; for all other frames use
            # the sword's per-frame centroid directly (absolute, not delta).
            if 50 <= fi <= 55:
                target_cx = SLASH_CX.get(fi, cx_src)
                target_cy = SLASH_CY.get(fi, cy_src)
            else:
                target_cx = cx_src   # sword centroid at this frame (absolute)
                target_cy = cy_src
            actual_dx = round(target_cx - cx0_f0)
            actual_dy = round(target_cy - cy0_f0)
            # Bow grip sits ~5px above centroid; shift up to place grip in hand.
            if weapon_type == 'bow':
                actual_dy -= 5
            pix = translate_pixels(f0, actual_dx, actual_dy)
            stamp(out, pix, gx, gy)

            # Arrow on fr54 only — the frame shown when mage/ranger arm is fully raised.
            # Tip at far LEFT in PNG → far RIGHT on screen (toward enemy) after scaleX(-1).
            if weapon_type == 'bow' and fi == 54:
                SHAFT = (120, 80,  35, 255)
                TIP   = (180, 180, 190, 255)
                FEATH = (200, 60,  60, 255)
                arrow_y = max(2, min(FH-3, round(target_cy)))
                ax_r = max(14, round(target_cx) - 2)   # feather end (right of shaft, near bow in PNG)
                ax_l = max(0, ax_r - 16)               # tip end (far left in PNG = far right on screen)
                for ax in range(ax_l, ax_r):
                    if 0 <= gy + arrow_y < out.shape[0] and 0 <= gx + ax < out.shape[1]:
                        out[gy + arrow_y, gx + ax] = SHAFT
                # Tip (point) at far left → appears far right on screen toward enemy
                # Use ax_l-1 if space available, else ax_l (stay within this frame slot)
                tip_local = ax_l - 1 if ax_l > 0 else ax_l
                for ay in [-1, 0, 1]:
                    r2 = gy + arrow_y + ay
                    tip_x = gx + tip_local
                    if 0 <= r2 < out.shape[0] and gx <= tip_x < gx + FW:
                        out[r2, tip_x] = TIP
                # Feathers at right end (near bow on screen = behind the arrow)
                for ay in [-1, 1]:
                    r2 = gy + arrow_y + ay
                    feat_x = gx + ax_r
                    if 0 <= r2 < out.shape[0] and feat_x < out.shape[1]:
                        out[r2, feat_x] = FEATH

            # Energy orb on fr54 only — fires from staff tip toward enemy.
            # Orb placed LEFT of centroid in PNG → RIGHT on screen after scaleX(-1).
            elif weapon_type == 'staff' and fi == 54:
                orb_x = max(3, min(FW-4, round(target_cx) - 10))
                orb_y = max(3, min(FH-4, round(target_cy) - 6))
                orb_core = trail_c if trail_c else (180, 120, 255, 255)
                orb_glow = trail_e if trail_e else (220, 180, 255, 180)
                for dy2 in range(-4, 5):
                    for dx2 in range(-4, 5):
                        r2 = gy + orb_y + dy2
                        c2 = gx + orb_x + dx2
                        if 0 <= r2 < out.shape[0] and 0 <= c2 < out.shape[1]:
                            dist = abs(dx2) + abs(dy2)
                            if dist <= 2:
                                out[r2, c2] = orb_core
                            elif dist <= 5:
                                out[r2, c2] = orb_glow

        else:
            pix = translate_pixels(f0, dx, dy)
            stamp(out, pix, gx, gy)

    Image.fromarray(out).save(out_path)
    print(f"  Saved: {out_path}")

def _bow_slash_frame(out, fi, f0, cx0, cy0, dx, dy, gx, gy, trail_c, trail_e):
    """Bow draw animation: bow raises to vertical, arrow fires."""
    WHITE = (255, 255, 255, 255)
    ARROW_SHAFT = (120, 80, 35, 255)
    ARROW_TIP   = (180, 180, 190, 255)
    ARROW_FEATHER = (200, 60, 60, 255)

    if fi == 50:
        # Start: bow at normal position
        pix = translate_pixels(f0, dx, dy)
        stamp(out, pix, gx, gy)
    elif fi == 51:
        # Bow rotated ~30° toward vertical (arm raising)
        pix = rotate_pixels(f0, -30, cx0, cy0)
        pix = translate_pixels(pix, dx - 4, dy - 8)
        stamp(out, pix, gx, gy)
    elif fi in [52, 53]:
        # Bow at full "draw" position — near-vertical, arm stopped
        # Rotate ~55° from base
        pix = rotate_pixels(f0, -55, cx0, cy0)
        pix = translate_pixels(pix, dx - 8, dy - 16)
        stamp(out, pix, gx, gy)
    elif fi == 54:
        # FIRE: bow at draw position + arrow streak going right
        pix = rotate_pixels(f0, -55, cx0, cy0)
        pix = translate_pixels(pix, dx - 8, dy - 16)
        stamp(out, pix, gx, gy)
        # Arrow streak: from grip outward to the right
        arrow_y = gy + 44
        arrow_x0 = gx + 44
        # Shaft
        for ax in range(arrow_x0, min(gx + FW, arrow_x0 + 20)):
            if 0 <= arrow_y < out.shape[0] and 0 <= ax < out.shape[1]:
                out[arrow_y, ax] = ARROW_SHAFT
        # Tip (arrowhead)
        tip_x = arrow_x0 + 20
        for ay in range(-2, 3):
            if abs(ay) <= 1:
                if 0 <= arrow_y+ay < out.shape[0] and 0 <= tip_x < out.shape[1]:
                    out[arrow_y+ay, tip_x] = ARROW_TIP
        # Feathers (back end)
        for ay in [-2, -1, 0, 1, 2]:
            if 0 <= arrow_y+ay < out.shape[0] and 0 <= arrow_x0+1 < out.shape[1]:
                if abs(ay) >= 1:
                    out[arrow_y+ay, arrow_x0+1] = ARROW_FEATHER
    elif fi == 55:
        # Bow relaxing back, faint arrow trail
        pix = rotate_pixels(f0, -30, cx0, cy0)
        pix = translate_pixels(pix, dx - 2, dy - 5)
        stamp(out, pix, gx, gy)
        # Faint arrow trail
        arrow_y = gy + 44
        for ax in range(gx+44, min(gx+FW, gx+60)):
            if 0 <= arrow_y < out.shape[0] and 0 <= ax < out.shape[1]:
                out[arrow_y, ax] = (200, 180, 140, 160)

# ── New bow frame-0 design (proper bow shape) ────────────────────────────────

def make_bow_frame0(limb_dark, limb_mid, limb_light, limb_hi, grip_dark, str_color):
    """
    Bow held diagonally: grip at upper-right area, upper limb curves to upper-left tip,
    lower limb curves to lower-right tip.  Gentle Bezier curves — visible arc, not extreme.
    """
    pix = {}
    bd = limb_dark; gd = limb_mid; gl = limb_light; gh = limb_hi
    sk = grip_dark; sr = str_color

    # ── Grip (leather wrap) x=39-42, y=44-48 ──
    for x in range(39, 43):
        for y in range(44, 49):
            pix[(x,y)] = sk
    for pt in [(38,44),(38,45),(38,46),(38,47),(38,48),
               (43,44),(43,45),(43,46),(43,47),(43,48),
               (39,43),(40,43),(41,43),(42,43),
               (39,49),(40,49),(41,49),(42,49)]:
        pix[pt] = bd

    # ── Upper limb: grip top (39,43) → tip (27,20)
    # Control pulled left so x monotonically decreases — clean ")" arc, no S
    upper_path = bezier_pts((39,43), (28, 30), (27,20))
    for i, (x,y) in enumerate(upper_path):
        t = i / max(len(upper_path)-1, 1)
        col_main = gd if t < 0.5 else gl
        col_edge = gl if t < 0.5 else gh
        if 0 <= x < FW and 0 <= y < FH:
            pix[(x,y)] = col_main
        if 0 <= x+1 < FW and 0 <= y < FH:
            pix.setdefault((x+1,y), col_edge)
        if 0 <= x-1 < FW and 0 <= y < FH:
            pix.setdefault((x-1,y), bd)
        if 0 <= x < FW and 0 <= y-1 < FH:
            pix.setdefault((x,y-1), bd)

    # ── Lower limb: grip bottom (43,49) → tip (52,63)
    # Control inside the endpoint range so x monotonically increases — no S
    lower_path = bezier_pts((43,49), (50, 53), (52,63))
    for i, (x,y) in enumerate(lower_path):
        t = i / max(len(lower_path)-1, 1)
        col_main = gd if t < 0.3 else gl
        col_edge = gl if t < 0.3 else gd
        if 0 <= x < FW and 0 <= y < FH:
            pix[(x,y)] = col_main
        if 0 <= x-1 < FW and 0 <= y < FH:
            pix.setdefault((x-1,y), col_edge)
        if 0 <= x+1 < FW and 0 <= y < FH:
            pix.setdefault((x+1,y), bd)
        if 0 <= x < FW and 0 <= y+1 < FH:
            pix.setdefault((x,y+1), bd)

    # ── String: tip to tip, gentle inward bow (string tension)
    str_path = bezier_pts((29, 20), (40, 42), (53, 62))
    for (x,y) in str_path:
        if 0 <= x < FW and 0 <= y < FH and (x,y) not in pix:
            pix[(x,y)] = sr

    return pix

# ── Weapon frame-0 pixel dicts ────────────────────────────────────────────────
# (Read existing sprites and extract frame 0 as pixel dict)

def extract_f0(path):
    arr = np.array(Image.open(path).convert('RGBA'))
    sl = arr[0:FH, 0:FW]
    pix = {}
    for y in range(FH):
        for x in range(FW):
            if sl[y,x,3] > 0:
                pix[(x,y)] = tuple(sl[y,x])
    return pix

# ── Clean bow frame-0 generation (from gen_bows_v3 design) ───────────────────

def _bezier2(p0, p1, p2, n=80):
    pts = []
    for i in range(n+1):
        t = i / n
        x = (1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t**2*p2[0]
        y = (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t**2*p2[1]
        pts.append((round(x), round(y)))
    seen = set(); out = []
    for p in pts:
        if p not in seen: seen.add(p); out.append(p)
    return out

def _bresenham(x0,y0,x1,y1):
    pts=[]; dx,dy=abs(x1-x0),abs(y1-y0)
    sx,sy=(1 if x1>x0 else -1),(1 if y1>y0 else -1)
    err=dx-dy; x,y=x0,y0
    while True:
        pts.append((x,y))
        if x==x1 and y==y1: break
        e2=2*err
        if e2>-dy: err-=dy; x+=sx
        if e2<dx:  err+=dx; y+=sy
    return pts

def make_clean_bow_f0(dark, mid, light, hi, grip_col, str_col, recurve=False):
    """Diagonal bow: upper tip upper-right (52,17), lower tip lower-left (30,61).
    Single continuous arc; grip is an inline color band at the midpoint.
    Limbs curve LEFT in PNG → after game scaleX(-1) flip they face right (toward enemy).
    String on the RIGHT in PNG (facing character in game).
    `recurve` and `hi` are accepted for API compatibility but not used in this design.
    """
    pix = {}
    UPPER_TIP = (52, 17)
    LOWER_TIP = (30, 61)
    GRIP_MID  = (36, 39)

    upper_pts = _bezier2(UPPER_TIP, (43, 27), GRIP_MID)
    lower_pts = _bezier2(GRIP_MID,  (32, 51), LOWER_TIP)
    all_pts   = upper_pts + lower_pts[1:]   # single continuous arc

    n_total = max(1, len(all_pts) - 1)
    for i, (x, y) in enumerate(all_pts):
        t = i / n_total
        # Middle 15% of arc → grip color band
        if 0.43 < t < 0.57:
            col = grip_col
        elif t < 0.25:
            col = light
        elif t < 0.5:
            col = mid
        elif t < 0.75:
            col = mid
        else:
            col = light
        if 0 <= x < FW and 0 <= y < FH:
            pix[(x, y)] = col

    # 1px dark outline along the full arc
    limb_pts = set(all_pts)
    for (x, y) in list(limb_pts):
        for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + ox, y + oy
            if 0 <= nx < FW and 0 <= ny < FH and (nx, ny) not in limb_pts and (nx, ny) not in pix:
                pix[(nx, ny)] = dark

    # String: straight line tip-to-tip, +1px offset toward concave/inner side
    for (x, y) in _bresenham(UPPER_TIP[0] + 1, UPPER_TIP[1] + 1,
                              LOWER_TIP[0] + 1, LOWER_TIP[1] - 1):
        if 0 <= x < FW and 0 <= y < FH and (x, y) not in pix:
            pix[(x, y)] = str_col
    return pix

def scale_pixels(pix, scale, cx=None, cy=None):
    """Scale a pixel dict by `scale` around centroid (or provided cx,cy)."""
    if not pix: return pix
    if cx is None:
        xs=[p[0] for p in pix]; ys=[p[1] for p in pix]
        cx,cy = float(np.mean(xs)), float(np.mean(ys))
    result = {}
    for (x,y),color in pix.items():
        nx = round((x - cx)*scale + cx)
        ny = round((y - cy)*scale + cy)
        if 0<=nx<FW and 0<=ny<FH and (nx,ny) not in result:
            result[(nx,ny)] = color
    return result

_A = 255
def _c(*a): return (*a, _A)
BOW_PALETTES = {
    't1': dict(dark=_c(20,10,3),  mid=_c(90,55,20),   light=_c(135,90,38),  hi=_c(155,110,50), grip_col=_c(50,28,10),  str_col=_c(220,215,195), recurve=False),
    't2': dict(dark=_c(20,8,3),   mid=_c(110,65,22),  light=_c(155,105,40), hi=_c(175,130,55), grip_col=_c(55,30,10),  str_col=_c(215,218,205), recurve=True),
    't3': dict(dark=_c(10,20,8),  mid=_c(55,100,40),  light=_c(85,145,58),  hi=_c(110,175,75), grip_col=_c(30,55,18),  str_col=_c(180,235,200), recurve=True),
    't4': dict(dark=_c(25,8,3),   mid=_c(155,68,18),  light=_c(195,105,32), hi=_c(225,140,55), grip_col=_c(90,28,8),   str_col=_c(255,205,100), recurve=True),
    't5': dict(dark=_c(8,4,18),   mid=_c(55,22,100),  light=_c(90,48,145),  hi=_c(120,70,185), grip_col=_c(30,12,60),  str_col=_c(185,140,255), recurve=True),
    't6': dict(dark=_c(10,8,2),   mid=_c(190,160,18), light=_c(230,200,40), hi=_c(255,238,90), grip_col=_c(110,90,8),  str_col=_c(255,245,200), recurve=True),
}

# ── Trail colors per weapon type ──────────────────────────────────────────────

WHITE_TRAIL = (255,255,255,255)
LAV_TRAIL   = (174,161,188,255)

# Staff orb trail colors (per tier)
STAFF_TRAILS = {
    't1': ((180,120,255,255), (220,180,255,255)),   # purple
    't2': ((100,160,255,255), (160,200,255,255)),   # blue sapphire
    't3': ((80,220,120,255), (160,255,180,255)),    # emerald
    't4': ((255,200,60,255), (255,230,120,255)),    # topaz
    't5': ((255,80,80,255),  (255,160,120,255)),    # crimson
    't6': ((200,160,255,255),(160,200,255,255)),    # celestial
}

# ── Main generation ───────────────────────────────────────────────────────────

SRC_PATH = 'sprites/preview_assets/char/sword.png'
OUT_DIR  = 'sprites/preview_assets/char/'

# Female centroid source (use shirt_mage1 which we know exists)
import os
FEMALE_SRC = 'sprites/preview_assets/char/sword.png'  # same — flip is symmetric

# ── Generate all swords ───────────────────────────────────────────────────────
print("\n=== Swords ===")
for tier in ['t1','t2','t3','t4','t5','t6']:
    for g in ['m','f']:
        fname = f'{OUT_DIR}sword_warrior_{tier}_{g}.png'
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}"); continue
        f0 = extract_f0(fname)
        out_path = fname
        build_sheet(f0, SRC_PATH, out_path, weapon_type='sword',
                    trail_c=WHITE_TRAIL, trail_e=LAV_TRAIL)

# ── Generate all staffs ───────────────────────────────────────────────────────
print("\n=== Staffs ===")
for tier in ['t1','t2','t3','t4','t5','t6']:
    tc, te = STAFF_TRAILS.get(tier, (WHITE_TRAIL, LAV_TRAIL))
    for g in ['m','f']:
        fname = f'{OUT_DIR}staff_mage_{tier}_{g}.png'
        if not os.path.exists(fname):
            print(f"  SKIP: {fname}"); continue
        f0 = extract_f0(fname)
        build_sheet(f0, SRC_PATH, fname, weapon_type='staff',
                    trail_c=tc, trail_e=te)

# ── Generate all bows ─────────────────────────────────────────────────────────
# Generate from make_clean_bow_f0: compact C-curve, small grip, per-tier colors.
# To lock in a design: switch back to extract_f0(fname) after generating once.
print("\n=== Bows ===")

for tier in ['t1','t2','t3','t4','t5','t6']:
    palette = BOW_PALETTES.get(tier, BOW_PALETTES['t1'])
    f0 = make_clean_bow_f0(**palette)
    for g in ['m','f']:
        fname = f'{OUT_DIR}bow_ranger_{tier}_{g}.png'
        build_sheet(f0, SRC_PATH, fname, weapon_type='bow',
                    trail_c=(220,200,140,255), trail_e=(180,160,100,255))

print("\nDone.")
