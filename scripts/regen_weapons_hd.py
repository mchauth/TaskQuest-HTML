#!/usr/bin/env python3
"""
regen_weapons_hd.py — High-density t7–t11 sword and staff sprites.

Copies build_sheet / extract_f0 logic from gen_weapons_v2.py without
running that script's module-level generation block.
"""
import os, sys, math
import numpy as np
from PIL import Image

# ── Constants ─────────────────────────────────────────────────────────────────
FW, FH, COLS, ROWS = 80, 64, 10, 7
SRC_PATH = 'sprites/preview_assets/char/sword.png'
OUT_DIR  = 'sprites/preview_assets/char/'

# ── Geometry helpers (from gen_weapons_v2) ────────────────────────────────────

def get_centroid(arr, fi):
    r, c = fi // COLS, fi % COLS
    sl = arr[r*FH:(r+1)*FH, c*FW:(c+1)*FW]
    op = np.argwhere(sl[..., 3] > 0)
    if len(op) == 0: return None, None
    return float(np.mean(op[:,1])), float(np.mean(op[:,0]))

def get_body_centroid(arr, fi, bright_thresh=400):
    r, c = fi // COLS, fi % COLS
    sl = arr[r*FH:(r+1)*FH, c*FW:(c+1)*FW]
    op = np.argwhere(sl[..., 3] > 0)
    if len(op) == 0: return None, None
    dark = [(y, x) for y, x in op
            if int(sl[y,x,0]) + int(sl[y,x,1]) + int(sl[y,x,2]) < bright_thresh]
    if not dark:
        return float(np.mean(op[:,1])), float(np.mean(op[:,0]))
    return float(np.mean([p[1] for p in dark])), float(np.mean([p[0] for p in dark]))

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

def _bresenham(x0, y0, x1, y1):
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

# ── Trail arcs (from gen_weapons_v2) ─────────────────────────────────────────

def make_trail_arc(trail_color_center, trail_color_edge):
    WHITE = trail_color_center; LAV = trail_color_edge
    pix = {}
    for y in range(0, 46):
        cx_line = 47.0 - 0.59 * y
        hw = 5.0 + 0.3 * y
        x0 = round(cx_line - hw); x1 = round(cx_line + hw)
        for x in range(max(0, x0), min(FW, x1+1)):
            dist = abs(x - cx_line)
            pix[(x, y)] = LAV if dist > hw - 1.5 else WHITE
    return pix

def make_trail_frame55(trail_color_center, trail_color_edge):
    WHITE = trail_color_center; LAV = trail_color_edge
    pix = {}
    for y in range(47, 55):
        cx_line = 16.0 + (y-47) * 2.0
        hw = 8.0 + (y-47)
        x0, x1 = round(cx_line - hw), round(cx_line + hw)
        for x in range(max(0, x0), min(FW, x1+1)):
            dist = abs(x - cx_line)
            pix[(x, y)] = LAV if dist > hw - 1.5 else WHITE
    for y in range(3, 7):
        cx_line = 36.0 - (y-3)*1.5
        for x in range(max(0, round(cx_line)-1), min(FW, round(cx_line)+2)):
            pix[(x, y)] = WHITE
    return pix

# ── Source sprite analysis ────────────────────────────────────────────────────
print("Loading sword.png reference...")
SRC = np.array(Image.open(SRC_PATH).convert('RGBA'))
src_cx0, src_cy0 = get_centroid(SRC, 0)
src_ang0 = get_angle(SRC, 0)

SLASH_ANGLES = {}
for fi in [51, 52, 53, 55]:
    SLASH_ANGLES[fi] = get_angle(SRC, fi) - src_ang0

SLASH_CX = {}; SLASH_CY = {}
for fi in range(COLS * ROWS):
    cx, cy = get_centroid(SRC, fi)
    if cx is not None: SLASH_CX[fi] = cx; SLASH_CY[fi] = cy

HAND_CX = {}; HAND_CY = {}
for fi in range(COLS * ROWS):
    cx, cy = get_body_centroid(SRC, fi)
    if cx is not None: HAND_CX[fi] = cx; HAND_CY[fi] = cy

print(f"  Slash angle deltas: {SLASH_ANGLES}")

# ── build_sheet (from gen_weapons_v2) ─────────────────────────────────────────

def build_sheet(f0, source_path, out_path, weapon_type='sword',
                trail_c=None, trail_e=None):
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
                dark_pix = {k: v for k, v in pix.items()
                            if int(v[0])+int(v[1])+int(v[2]) < 90}
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

        elif weapon_type == 'staff':
            if 50 <= fi <= 55:
                target_cx = HAND_CX.get(fi, cx_src)
                target_cy = HAND_CY.get(fi, cy_src)
            else:
                target_cx = cx_src
                target_cy = cy_src
            if fi <= 4 or 50 <= fi <= 55:
                rot_angle = -45
            else:
                rot_angle = 0
            if rot_angle:
                f0_rot = rotate_pixels(f0, rot_angle, cx0_f0, cy0_f0)
                rot_cx, rot_cy = centroid_of(f0_rot)
                actual_dx = round(target_cx - rot_cx)
                actual_dy = round(target_cy - rot_cy)
                pix = translate_pixels(f0_rot, actual_dx, actual_dy)
            else:
                actual_dx = round(target_cx - cx0_f0)
                actual_dy = round(target_cy - cy0_f0)
                pix = translate_pixels(f0, actual_dx, actual_dy)
            stamp(out, pix, gx, gy)
            # Energy orb on fr54
            if fi == 54:
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

# ── extract_f0 (from gen_weapons_v2) ─────────────────────────────────────────

def extract_f0(path):
    arr = np.array(Image.open(path).convert('RGBA'))
    sl = arr[0:FH, 0:FW]
    pix = {}
    for y in range(FH):
        for x in range(FW):
            if sl[y,x,3] > 0:
                pix[(x,y)] = tuple(sl[y,x])
    return pix

# ── HD pixel-art helpers ──────────────────────────────────────────────────────
# Perpendicular to the standard blade direction (28,43)→(45,15):
#   blade dir = (17,-28), perp = (28,17)/32.76 ≈ (0.854, 0.519)
_PERP_X = 0.8543
_PERP_Y = 0.5199

def put(pix, x, y, col, overwrite=True):
    if 0 <= x < FW and 0 <= y < FH:
        if overwrite or (x,y) not in pix:
            pix[(x, y)] = col

def draw_wide_blade(pix, pts, half_width, dark, shadow, base, hi, spec,
                    taper=True, taper_frac=0.65, reverse_light=False):
    """
    Draw a wide blade along `pts` (Bresenham / bezier list).
    Perpendicular offsets use the global _PERP_X/_PERP_Y direction.
    Shading columns: shadow-side outer=dark, inner=shadow,
                     center=base, highlight inner=hi, outer=spec.
    reverse_light: flips which side is highlight (for asymmetric blades).
    """
    n = len(pts)
    for i, (cx, cy) in enumerate(pts):
        t = i / max(n-1, 1)
        w = max(0.6, half_width * (1.0 - t * taper_frac)) if taper else float(half_width)
        # Write pixels from shadow side to highlight side
        for k in range(-int(w+1), int(w+2)):
            nx = round(cx + k * _PERP_X)
            ny = round(cy + k * _PERP_Y)
            if not (0 <= nx < FW and 0 <= ny < FH):
                continue
            frac = k / w if w > 0.5 else 0.0
            if reverse_light:
                frac = -frac
            # 5-level shading: dark | shadow | base | hi | spec
            if frac < -0.70:
                col = dark
            elif frac < -0.30:
                col = shadow
            elif frac < 0.30:
                col = base
            elif frac < 0.70:
                col = hi
            else:
                col = spec
            # Don't overwrite with darker shade if already bright
            existing = pix.get((nx, ny))
            if existing is None:
                pix[(nx, ny)] = col
            else:
                # overwrite only if new color is brighter
                if (int(col[0])+int(col[1])+int(col[2]) >
                        int(existing[0])+int(existing[1])+int(existing[2])):
                    pix[(nx, ny)] = col

def draw_circle(pix, cx, cy, r, col_inner, col_mid, col_outer,
                col_edge=None, spec_offset=(-1,-1)):
    """Draw a filled circle with 3-level shading + optional specular highlight."""
    for dy in range(-r-1, r+2):
        for dx in range(-r-1, r+2):
            dist = math.sqrt(dx*dx + dy*dy)
            nx, ny = round(cx+dx), round(cy+dy)
            if not (0 <= nx < FW and 0 <= ny < FH):
                continue
            if dist <= r - 1.8:
                put(pix, nx, ny, col_inner)
            elif dist <= r - 0.5:
                put(pix, nx, ny, col_mid)
            elif dist <= r + 0.5:
                put(pix, nx, ny, col_outer)
            elif dist <= r + 1.0:
                put(pix, nx, ny, col_edge or col_outer, overwrite=False)
    # Specular highlight
    sx, sy = round(cx+spec_offset[0]), round(cy+spec_offset[1])
    if 0 <= sx < FW and 0 <= sy < FH:
        put(pix, sx, sy, (255, 255, 255, 255))

def draw_gem(pix, cx, cy, size, col_dark, col_base, col_hi, col_spec):
    """Draw a faceted gem (diamond shape) with 4-level shading."""
    for dy in range(-size, size+1):
        for dx in range(-size, size+1):
            if abs(dx) + abs(dy) > size:
                continue
            nx, ny = cx+dx, cy+dy
            if not (0 <= nx < FW and 0 <= ny < FH):
                continue
            dist = abs(dx) + abs(dy)
            # Top-left quadrant: bright; bottom-right: dark
            if dy < 0 and dx < 0:
                col = col_spec if dist <= size//2 else col_hi
            elif dy > 0 and dx > 0:
                col = col_dark if dist <= size//2 else col_base
            else:
                col = col_base
            put(pix, nx, ny, col)
    # Outline
    for dy in range(-size, size+1):
        for dx in range(-size, size+1):
            if abs(dx) + abs(dy) == size:
                put(pix, cx+dx, cy+dy, col_dark)

def draw_grip(pix, x0, y0, x1, y1, grip_dark, grip_mid, grip_wrap):
    """Draw a 2px thick grip with leather-wrap texture."""
    pts = _bresenham(x0, y0, x1, y1)
    for i, (x, y) in enumerate(pts):
        col = grip_wrap if i % 3 == 1 else (grip_mid if i % 3 == 0 else grip_dark)
        put(pix, x, y, col)
        # Second pixel perpendicular
        nx2 = round(x + _PERP_X)
        ny2 = round(y + _PERP_Y)
        put(pix, nx2, ny2, grip_dark, overwrite=False)

def draw_crossguard(pix, cx, cy, width, height, col_dark, col_base, col_hi,
                    gems=None, end_style='flat'):
    """
    Draw a horizontal crossguard centered at (cx, cy).
    width = half-width each side, height = thickness (1-3px).
    gems = list of (x_offset_from_center, color) for gem pixels.
    end_style: 'flat', 'pointed', 'curved', 'winged'.
    """
    for yi in range(cy - height//2, cy + height//2 + 1):
        for xi in range(cx - width, cx + width + 1):
            if not (0 <= xi < FW and 0 <= yi < FH):
                continue
            # Edge darkening
            dx_frac = abs(xi - cx) / max(width, 1)
            dy_frac = abs(yi - cy) / max(height//2, 1) if height > 1 else 0
            if dx_frac > 0.85 or dy_frac > 0.7:
                col = col_dark
            elif dx_frac > 0.6:
                col = col_base
            elif dy_frac > 0.5:
                col = col_dark
            else:
                col = col_hi
            put(pix, xi, yi, col)
    if end_style == 'curved':
        # Add curved flares at ends
        for side in [-1, 1]:
            ex = cx + side * width
            for dy in [-1, 1]:
                put(pix, ex + side, cy + dy, col_dark, overwrite=False)
    elif end_style == 'winged':
        # Add upward/downward extensions at guard ends
        for side in [-1, 1]:
            ex = cx + side * (width - 1)
            for dy in range(1, 3):
                put(pix, ex, cy - dy, col_base, overwrite=False)
                put(pix, ex, cy + dy, col_base, overwrite=False)
            put(pix, ex, cy - 3, col_hi, overwrite=False)
            put(pix, ex, cy + 3, col_hi, overwrite=False)
    elif end_style == 'pointed':
        # Diamond-tipped ends
        for side in [-1, 1]:
            ex = cx + side * width
            put(pix, ex + side, cy, col_hi)
            put(pix, ex + side*2, cy, col_dark, overwrite=False)
    # Gems
    if gems:
        for (gx_off, gem_col) in gems:
            gx2 = cx + gx_off
            for dx2, dy2 in [(0,0),(1,0),(0,1),(1,1)]:
                put(pix, gx2+dx2, cy-1+dy2, gem_col)
            # Specular on gem
            put(pix, gx2, cy-1, (min(255, gem_col[0]+60),
                                   min(255, gem_col[1]+60),
                                   min(255, gem_col[2]+60), 255))

def draw_pommel(pix, cx, cy, size, col_dark, col_base, col_hi,
                gem_col=None, style='round'):
    """Draw pommel. style: 'round', 'octagon', 'crown'."""
    if style == 'round':
        draw_circle(pix, cx, cy, size, col_hi, col_base, col_dark,
                    spec_offset=(-1,-1))
    elif style == 'octagon':
        r = size
        for dy in range(-r, r+1):
            for dx in range(-r, r+1):
                if abs(dx) + abs(dy) <= r + r//2 and abs(dx) <= r and abs(dy) <= r:
                    dist = max(abs(dx), abs(dy))
                    if dist < r - 1:
                        col = col_hi if (dx < 0 and dy < 0) else col_base
                    else:
                        col = col_dark
                    put(pix, cx+dx, cy+dy, col)
    elif style == 'crown':
        # Base + spikes
        for dx in range(-size, size+1):
            put(pix, cx+dx, cy, col_base)
            put(pix, cx+dx, cy+1, col_dark)
        for spike_x in [cx-size+1, cx, cx+size-1]:
            put(pix, spike_x, cy-1, col_hi)
            put(pix, spike_x, cy-2, col_dark, overwrite=False)
    if gem_col and 0 <= cx < FW and 0 <= cy < FH:
        put(pix, cx, cy, gem_col)
        put(pix, cx-1, cy-1, (min(255,gem_col[0]+50),
                               min(255,gem_col[1]+50),
                               min(255,gem_col[2]+50), 255))

# ── SWORD DESIGNS ─────────────────────────────────────────────────────────────

def make_sword_t7():
    """Silver Knight Longsword — slim elegant blade, silver with blue tint, ornate cross guard."""
    pix = {}
    # Blade: from (28,43) to (50,11) — longer than t6, 3px half-width
    blade_pts = _bezier2((28,43), (37,28), (50,11))
    DARK   = (50, 58, 82, 255)
    SHADOW = (95, 108, 140, 255)
    BASE   = (148, 162, 198, 255)
    HI     = (200, 215, 242, 255)
    SPEC   = (232, 243, 255, 255)
    draw_wide_blade(pix, blade_pts, half_width=3,
                    dark=DARK, shadow=SHADOW, base=BASE, hi=HI, spec=SPEC,
                    taper=True, taper_frac=0.60)
    # Blue accent pixels every 4 steps along upper-highlight edge
    BLUE_ACC = (80, 140, 220, 255)
    for i, (x, y) in enumerate(blade_pts):
        if i % 4 == 2:
            nx = round(x + 2.5 * _PERP_X)
            ny = round(y + 2.5 * _PERP_Y)
            put(pix, nx, ny, BLUE_ACC)
    # Crossguard at ~y=37, centered at x=35
    # Ornate 16-wide with filigree wings
    GUARD_D = (55, 62, 88, 255)
    GUARD_B = (152, 165, 198, 255)
    GUARD_H = (208, 220, 245, 255)
    draw_crossguard(pix, 35, 37, width=8, height=2,
                    col_dark=GUARD_D, col_base=GUARD_B, col_hi=GUARD_H,
                    end_style='winged')
    # Blue gems at each end of crossguard
    GEM_D = (30, 60, 120, 255); GEM_B = (60, 115, 195, 255)
    GEM_H = (120, 180, 248, 255); GEM_S = (210, 238, 255, 255)
    draw_gem(pix, 27, 37, size=2, col_dark=GEM_D, col_base=GEM_B, col_hi=GEM_H, col_spec=GEM_S)
    draw_gem(pix, 43, 37, size=2, col_dark=GEM_D, col_base=GEM_B, col_hi=GEM_H, col_spec=GEM_S)
    # Grip: (28,43) to (33,37), brown leather
    GRIP_D = (55, 35, 15, 255); GRIP_M = (88, 58, 25, 255); GRIP_W = (120, 82, 35, 255)
    draw_grip(pix, 29, 42, 33, 38, GRIP_D, GRIP_M, GRIP_W)
    # Pommel: octagonal silver at (25, 45)
    POM_D = (62, 70, 92, 255); POM_B = (148, 162, 198, 255); POM_H = (210, 222, 248, 255)
    draw_pommel(pix, 25, 46, size=2, col_dark=POM_D, col_base=POM_B, col_hi=POM_H,
                gem_col=GEM_B, style='octagon')
    return pix

def make_sword_t8():
    """Stormcaller — wide blade with lightning rune engravings, dark steel with electric blue gems."""
    pix = {}
    blade_pts = _bezier2((28,43), (38,28), (50,12))
    DARK   = (16, 18, 26, 255)
    SHADOW = (40, 44, 58, 255)
    BASE   = (68, 74, 92, 255)
    HI     = (108, 115, 135, 255)
    SPEC   = (158, 165, 182, 255)
    draw_wide_blade(pix, blade_pts, half_width=4,
                    dark=DARK, shadow=SHADOW, base=BASE, hi=HI, spec=SPEC,
                    taper=True, taper_frac=0.60)
    # Lightning rune engravings: electric blue zigzag along blade center
    BLUE_BOLT = (28, 115, 255, 255)
    BLUE_GLOW = (80, 155, 255, 200)
    for i, (x, y) in enumerate(blade_pts):
        if i % 5 == 0 and i < len(blade_pts) - 3:
            nx1 = round(x + 0.5 * _PERP_X)
            ny1 = round(y + 0.5 * _PERP_Y)
            put(pix, nx1, ny1, BLUE_BOLT)
            # Glow around bolt pixel
            for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                put(pix, nx1+ox, ny1+oy, BLUE_GLOW, overwrite=False)
        elif i % 5 == 2:
            nx2 = round(x - 0.5 * _PERP_X)
            ny2 = round(y - 0.5 * _PERP_Y)
            put(pix, nx2, ny2, BLUE_BOLT)
    # Wide jagged crossguard: 18px, with storm-blue tips
    GUARD_D = (14, 18, 28, 255)
    GUARD_B = (32, 38, 56, 255)
    GUARD_H = (55, 65, 90, 255)
    draw_crossguard(pix, 34, 36, width=10, height=3,
                    col_dark=GUARD_D, col_base=GUARD_H, col_hi=GUARD_B,
                    end_style='pointed')
    # Electric blue gems at guard tips
    ELEC_GEM = (28, 115, 255, 255)
    ELEC_HI  = (120, 190, 255, 255)
    for gx2 in [24, 25, 26]:
        for gy2 in [35, 36, 37]:
            put(pix, gx2, gy2, ELEC_GEM)
    put(pix, 24, 35, ELEC_HI)
    for gx2 in [43, 44, 45]:
        for gy2 in [35, 36, 37]:
            put(pix, gx2, gy2, ELEC_GEM)
    put(pix, 43, 35, ELEC_HI)
    # Lightning bolt pixels on crossguard center
    for xi in [32, 33, 34, 35, 36]:
        put(pix, xi, 35, BLUE_GLOW, overwrite=False)
    # Grip
    GRIP_D = (18, 20, 28, 255); GRIP_M = (35, 38, 52, 255); GRIP_W = (55, 60, 80, 255)
    draw_grip(pix, 28, 43, 33, 37, GRIP_D, GRIP_M, GRIP_W)
    # Pommel: round with large electric blue gem
    POM_D = (16, 18, 26, 255); POM_B = (40, 44, 60, 255); POM_H = (68, 74, 95, 255)
    draw_pommel(pix, 24, 46, size=3, col_dark=POM_D, col_base=POM_B, col_hi=POM_H,
                gem_col=ELEC_GEM, style='round')
    put(pix, 23, 45, ELEC_HI)  # specular on gem
    return pix

def make_sword_t9():
    """Demonblade — curved asymmetric blade, crimson and black, jagged edge, red gem pommel."""
    pix = {}
    # Slightly curved blade using bezier: slight leftward curve
    blade_pts = _bezier2((28,43), (36,30), (44,15))
    DARK   = (32, 4, 4, 255)
    SHADOW = (80, 10, 10, 255)
    BASE   = (140, 18, 18, 255)
    HI     = (205, 48, 28, 255)
    SPEC   = (245, 95, 58, 255)
    draw_wide_blade(pix, blade_pts, half_width=4,
                    dark=DARK, shadow=SHADOW, base=BASE, hi=HI, spec=SPEC,
                    taper=True, taper_frac=0.58)
    # Left (shadow) side extra width — asymmetric
    for i, (x, y) in enumerate(blade_pts):
        t = i / max(len(blade_pts)-1, 1)
        w_extra = max(0, 2 - int(t * 3))
        for k in range(1, w_extra + 1):
            nx = round(x - (3 + k) * _PERP_X)
            ny = round(y - (3 + k) * _PERP_Y)
            put(pix, nx, ny, DARK, overwrite=False)
    # Jagged serrations on shadow (left/upper) edge every 3rd pixel
    SERR = (22, 3, 3, 255)
    for i, (x, y) in enumerate(blade_pts):
        if i % 3 == 0:
            nx = round(x - 4.5 * _PERP_X)
            ny = round(y - 4.5 * _PERP_Y)
            put(pix, nx, ny, SERR, overwrite=False)
    # Dark veining along blade
    VEIN = (65, 8, 8, 255)
    for i, (x, y) in enumerate(blade_pts):
        if i % 6 == 3:
            put(pix, x, y, VEIN)
    # Asymmetric crossguard — wider on shadow side
    GUARD_D = (28, 4, 4, 255)
    GUARD_B = (115, 14, 14, 255)
    GUARD_H = (180, 28, 28, 255)
    # Left side longer
    for xi in range(22, 43):
        t = abs(xi - 34) / 12.0
        col = GUARD_D if t > 0.80 else (GUARD_B if t > 0.45 else GUARD_H)
        put(pix, xi, 36, col)
        put(pix, xi, 37, GUARD_D)
        if t < 0.3:
            put(pix, xi, 35, GUARD_B, overwrite=False)
    # Red gems: crossguard center + small ones at ends
    GEM_D = (80, 5, 5, 255); GEM_B = (200, 20, 20, 255)
    GEM_H = (255, 60, 40, 255); GEM_S = (255, 140, 100, 255)
    draw_gem(pix, 33, 36, size=2, col_dark=GEM_D, col_base=GEM_B, col_hi=GEM_H, col_spec=GEM_S)
    # Smaller red pixel at guard ends
    for xi in [22, 23, 41, 42]:
        put(pix, xi, 36, GEM_B)
    put(pix, 22, 36, GEM_H)
    put(pix, 41, 36, GEM_H)
    # Grip: slightly longer for better hold feel
    GRIP_D = (22, 4, 4, 255); GRIP_M = (50, 8, 8, 255); GRIP_W = (80, 12, 12, 255)
    draw_grip(pix, 28, 43, 32, 38, GRIP_D, GRIP_M, GRIP_W)
    # Pommel: round with large red gem
    POM_D = (30, 4, 4, 255); POM_B = (100, 12, 12, 255); POM_H = (160, 22, 22, 255)
    draw_pommel(pix, 24, 46, size=3, col_dark=POM_D, col_base=POM_B, col_hi=POM_H,
                gem_col=GEM_B, style='round')
    put(pix, 23, 45, GEM_S)  # specular
    return pix

def make_sword_t10():
    """Crystal Greatsword — wide ice-blue crystal blade with internal facets, two-handed grip."""
    pix = {}
    # Very long, wide blade to (53,10)
    blade_pts = _bezier2((28,43), (40,26), (53,10))
    DARK   = (38, 62, 108, 255)
    SHADOW = (65, 105, 165, 255)
    BASE   = (88, 142, 215, 255)
    HI     = (158, 208, 255, 255)
    SPEC   = (215, 238, 255, 255)
    draw_wide_blade(pix, blade_pts, half_width=5,
                    dark=DARK, shadow=SHADOW, base=BASE, hi=HI, spec=SPEC,
                    taper=True, taper_frac=0.55)
    # Internal crystal facets: diagonal bright lines across the blade
    FACET_BRIGHT = (188, 228, 255, 255)
    FACET_DARK   = (52, 85, 138, 255)
    for i, (x, y) in enumerate(blade_pts):
        if i % 7 == 0:
            # Facet line perpendicular across blade
            for k in range(-2, 3):
                nx = round(x + k * _PERP_X)
                ny = round(y + k * _PERP_Y)
                col = FACET_BRIGHT if k >= 0 else FACET_DARK
                if (nx, ny) in pix:
                    put(pix, nx, ny, col)
    # Two-handed grip: longer (28,43)→(32,40)→(36,35)
    GRIP_D = (45, 32, 12, 255); GRIP_M = (75, 55, 22, 255); GRIP_W = (110, 82, 35, 255)
    for pt in _bresenham(28, 43, 36, 35):
        i2 = _bresenham(28,43,36,35).index(pt) if pt in _bresenham(28,43,36,35) else 0
        col = GRIP_W if i2 % 3 == 1 else (GRIP_M if i2 % 3 == 0 else GRIP_D)
        put(pix, pt[0], pt[1], col)
        put(pix, round(pt[0]+_PERP_X), round(pt[1]+_PERP_Y), GRIP_D, overwrite=False)
    # Metal band mid-grip
    BAND = (140, 178, 228, 255)
    for xi in range(30, 34):
        put(pix, xi, 39, BAND)
    # Crossguard: wide crystal with shards pointing up/down
    GUARD_D = (38, 62, 108, 255)
    GUARD_B = (88, 142, 215, 255)
    GUARD_H = (158, 208, 255, 255)
    draw_crossguard(pix, 33, 36, width=11, height=3,
                    col_dark=GUARD_D, col_base=GUARD_B, col_hi=GUARD_H,
                    end_style='winged')
    # Crystal shard upward/downward at guard ends
    for side, dx_off in [(-1, 22), (1, 45)]:
        for k in range(1, 4):
            put(pix, dx_off, 36 - k, GUARD_H if k == 1 else GUARD_B, overwrite=False)
            put(pix, dx_off, 36 + k, GUARD_D, overwrite=False)
    # Center crystal gem
    GEM_D = (38, 62, 108, 255); GEM_B = (88, 142, 215, 255)
    GEM_H = (180, 220, 255, 255); GEM_S = (228, 248, 255, 255)
    draw_gem(pix, 33, 36, size=2, col_dark=GEM_D, col_base=GEM_B, col_hi=GEM_H, col_spec=GEM_S)
    # Pommel: round crystal
    draw_pommel(pix, 25, 46, size=3, col_dark=DARK, col_base=BASE, col_hi=HI,
                gem_col=SPEC, style='round')
    return pix

def make_sword_t11():
    """Warlord's Axe — broad battle axe head, gold-trimmed, rune-etched, dual-gem pommel."""
    pix = {}
    # Handle from (28,43) down to (36,26) — short, thick
    HAFT_D = (45, 28, 8, 255)
    HAFT_M = (72, 48, 16, 255)
    HAFT_H = (105, 72, 28, 255)
    haft_pts = _bresenham(28, 43, 37, 24)
    for i, (x, y) in enumerate(haft_pts):
        col = HAFT_W = (135, 95, 38, 255) if i % 4 == 2 else (HAFT_M if i % 4 in (0,3) else HAFT_D)
        put(pix, x, y, col)
        put(pix, x+1, y, HAFT_D, overwrite=False)
        put(pix, x-1, y, HAFT_H, overwrite=False)
    # Metal bands on haft
    BAND_GOLD = (210, 170, 38, 255)
    for bx, by in _bresenham(29, 40, 31, 40):
        put(pix, bx, by, BAND_GOLD)
    for bx, by in _bresenham(30, 35, 33, 35):
        put(pix, bx, by, BAND_GOLD)
    # Axe head — large crescent blade
    # Outer arc of crescent: broad sweep from (29,23) → through (55,20) → (48,32)
    # Inner arc: from (29,23) → through (42,21) → (48,32)
    AXE_D   = (50, 33, 5, 255)
    AXE_SH  = (110, 80, 15, 255)
    AXE_B   = (162, 122, 25, 255)
    AXE_HI  = (218, 178, 45, 255)
    AXE_SP  = (255, 232, 78, 255)
    # Fill the axe head area: for each row, find span from inner to outer arc
    outer_arc = _bezier2((29,23), (60,16), (48,32))
    inner_arc = _bezier2((29,23), (42,20), (48,32))
    # Build sets for lookup
    outer_set = set(outer_arc)
    inner_set = set(inner_arc)
    # Fill using column-by-column approach
    outer_by_y = {}
    for (x, y) in outer_arc:
        outer_by_y.setdefault(y, []).append(x)
    inner_by_y = {}
    for (x, y) in inner_arc:
        inner_by_y.setdefault(y, []).append(x)
    for y in range(13, 35):
        if y not in outer_by_y:
            continue
        outer_xs = sorted(outer_by_y[y])
        inner_xs = sorted(inner_by_y.get(y, outer_xs[:1]))
        x_outer_max = max(outer_xs)
        x_inner_max = max(inner_xs)
        x_start = min(inner_xs + outer_xs)
        for x in range(x_start, x_outer_max + 1):
            t_horiz = (x - x_inner_max) / max(1, x_outer_max - x_inner_max)
            if t_horiz < 0:
                col = AXE_D
            elif t_horiz < 0.25:
                col = AXE_SH
            elif t_horiz < 0.55:
                col = AXE_B
            elif t_horiz < 0.80:
                col = AXE_HI
            else:
                col = AXE_SP
            put(pix, x, y, col, overwrite=False)
    # Draw the arcs explicitly for clean edges
    for (x, y) in outer_arc:
        put(pix, x, y, AXE_SP)  # outer = bright edge
        put(pix, x+1, y, AXE_D, overwrite=False)
    for (x, y) in inner_arc:
        put(pix, x, y, AXE_D)  # inner = shadow
    # Axe top spike
    SPIKE_pts = _bezier2((40, 17), (44, 10), (50, 14))
    for i, (x, y) in enumerate(SPIKE_pts):
        t = i / max(len(SPIKE_pts)-1, 1)
        col = AXE_SP if t > 0.6 else (AXE_HI if t > 0.3 else AXE_B)
        put(pix, x, y, col)
        put(pix, x, y+1, AXE_D, overwrite=False)
    # Rune etchings: slightly darker stripes across axe face
    RUNE = (100, 68, 10, 255)
    for i, (x, y) in enumerate(outer_arc):
        if i % 6 == 3:
            put(pix, x-1, y, RUNE, overwrite=False)
    # Dual gems on axe head
    GEM_R = (220, 45, 45, 255); GEM_RH = (255, 120, 80, 255)
    GEM_D  = (80, 8, 8, 255)
    # Upper gem
    draw_gem(pix, 50, 20, size=2, col_dark=GEM_D, col_base=GEM_R, col_hi=GEM_RH, col_spec=(255,180,140,255))
    # Lower gem
    draw_gem(pix, 45, 28, size=2, col_dark=GEM_D, col_base=GEM_R, col_hi=GEM_RH, col_spec=(255,180,140,255))
    # Gold trim around axe edge highlights
    TRIM = (238, 200, 55, 255)
    for (x, y) in outer_arc[::2]:
        put(pix, x, y, TRIM)
    # Pommel: dual-gem crown style at (24-26, 44-46)
    POM_D = (50, 33, 5, 255); POM_B = (162, 122, 25, 255); POM_H = (218, 178, 45, 255)
    draw_pommel(pix, 24, 45, size=2, col_dark=POM_D, col_base=POM_B, col_hi=POM_H,
                gem_col=GEM_R, style='octagon')
    put(pix, 24, 44, GEM_RH)  # upper gem specular
    return pix

# ── STAFF DESIGNS ─────────────────────────────────────────────────────────────

def _make_staff_shaft(pix, dark, mid, light, extra_px=0):
    """Draw the main shaft from (27,42) to (38,17). extra_px adds girth."""
    shaft_pts = _bezier2((27,42), (32,29), (38+extra_px,17))
    n_sh = max(1, len(shaft_pts)-1)
    for i, (x, y) in enumerate(shaft_pts):
        t_val = i / n_sh
        col = dark if t_val < 0.3 else (mid if t_val < 0.7 else light)
        put(pix, x, y, col)
        put(pix, x+1, y, dark, overwrite=False)
    return shaft_pts

def make_staff_t7():
    """Solar Crown Staff — staff topped with sunburst disc, golden, radiating spikes."""
    pix = {}
    DARK  = (128, 85, 10, 255)
    MID   = (198, 152, 28, 255)
    LIGHT = (235, 192, 52, 255)
    SPEC  = (255, 235, 90, 255)
    _make_staff_shaft(pix, DARK, MID, LIGHT)
    # Gold accent bands on shaft
    for xi in range(31, 37):
        put(pix, xi, 27, SPEC)
    # Solar disc: filled circle r=6 at (40,13)
    DX, DY = 40, 13
    draw_circle(pix, DX, DY, 6, col_inner=SPEC, col_mid=LIGHT, col_outer=MID,
                col_edge=DARK, spec_offset=(-2,-2))
    # 8 radiating spikes from disc
    SPIKE_LENS = [6, 4, 6, 4, 5, 4, 5, 4]  # N,NE,E,SE,S,SW,W,NW lengths
    ANGLES_DEG = [270, 315, 0, 45, 90, 135, 180, 225]
    for ang_deg, length in zip(ANGLES_DEG, SPIKE_LENS):
        rad = math.radians(ang_deg)
        for step in range(1, length+2):
            sx = round(DX + (6 + step) * math.cos(rad))
            sy = round(DY + (6 + step) * math.sin(rad))
            t_sp = step / (length+1)
            col = SPEC if t_sp < 0.4 else (LIGHT if t_sp < 0.7 else MID)
            if step == length+1:
                col = DARK
            put(pix, sx, sy, col, overwrite=False)
    return pix

def make_staff_t8():
    """Crescent Moon Staff — curved moon topper, silver with teal gem center."""
    pix = {}
    DARK  = (78, 88, 105, 255)
    MID   = (165, 178, 198, 255)
    LIGHT = (212, 225, 242, 255)
    SPEC  = (245, 248, 255, 255)
    TEAL  = (25, 198, 175, 255)
    TEAL_HI = (90, 240, 215, 255)
    _make_staff_shaft(pix, DARK, MID, LIGHT)
    # Shaft silver band
    for xi in range(33, 39):
        put(pix, xi, 28, SPEC)
    # Crescent moon: outer arc minus inner arc offset
    # Outer circle: r=7 at (40,13)
    # Inner circle: r=6 at (43,10) — offset creates the crescent opening
    CX, CY = 40, 13
    OCX, OCY, OR = 40, 13, 7
    ICX, ICY, IR = 43, 10, 6
    for dy in range(-OR-1, OR+2):
        for dx in range(-OR-1, OR+2):
            nx, ny = OCX+dx, OCY+dy
            if not (0 <= nx < FW and 0 <= ny < FH):
                continue
            outer_dist = math.sqrt((nx-OCX)**2 + (ny-OCY)**2)
            inner_dist = math.sqrt((nx-ICX)**2 + (ny-ICY)**2)
            if outer_dist <= OR and inner_dist > IR:
                # In crescent region
                t_d = outer_dist / OR
                if t_d < 0.4:
                    col = SPEC
                elif t_d < 0.7:
                    col = LIGHT
                elif t_d < 0.9:
                    col = MID
                else:
                    col = DARK
                # Highlight top-left
                if dx < 0 and dy < 0:
                    col = SPEC if t_d < 0.6 else LIGHT
                put(pix, nx, ny, col)
    # Outline the crescent
    for dy in range(-OR-2, OR+3):
        for dx in range(-OR-2, OR+3):
            nx, ny = OCX+dx, OCY+dy
            if not (0 <= nx < FW and 0 <= ny < FH):
                continue
            outer_dist = math.sqrt((nx-OCX)**2 + (ny-OCY)**2)
            inner_dist = math.sqrt((nx-ICX)**2 + (ny-ICY)**2)
            if (OR <= outer_dist <= OR+1 or (IR <= inner_dist <= IR+0.5 and outer_dist < OR)):
                put(pix, nx, ny, DARK, overwrite=False)
    # Teal gem at crescent center (2x2)
    GX, GY = 38, 14
    for ox, oy in [(0,0),(1,0),(0,1),(1,1)]:
        put(pix, GX+ox, GY+oy, TEAL)
    put(pix, GX, GY, TEAL_HI)
    return pix

def make_staff_t9():
    """Void Shard Staff — jagged obsidian crystal cluster on top, purple energy glow pixels."""
    pix = {}
    DARK  = (10, 7, 22, 255)
    MID   = (38, 25, 65, 255)
    LIGHT = (62, 42, 102, 255)
    SPEC  = (110, 65, 168, 255)
    GLOW  = (168, 78, 255, 180)
    GLOW_EDGE = (120, 50, 200, 140)
    # Dark shaft
    _make_staff_shaft(pix, DARK, MID, LIGHT)
    # Crystal cluster at top: 4 jagged spikes
    # Spike 1: central spike up-left
    def draw_crystal_spike(pix, base_x, base_y, tip_x, tip_y, w=2):
        pts = _bresenham(base_x, base_y, tip_x, tip_y)
        n = len(pts)
        for i, (x, y) in enumerate(pts):
            t = i / max(n-1,1)
            width = max(0, w - int(t * w * 1.5))
            col = SPEC if t < 0.2 else (LIGHT if t < 0.5 else (MID if t < 0.8 else DARK))
            put(pix, x, y, col)
            for k in range(1, width+1):
                nx = round(x + k * _PERP_X)
                ny = round(y + k * _PERP_Y)
                put(pix, nx, ny, MID, overwrite=False)
                nx2 = round(x - k * _PERP_X)
                ny2 = round(y - k * _PERP_Y)
                put(pix, nx2, ny2, DARK, overwrite=False)
            # Glow aura at lower part
            if t > 0.6:
                for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    put(pix, x+ox, y+oy, GLOW_EDGE, overwrite=False)
    # Base of crystal cluster
    BASE_X, BASE_Y = 38, 22
    # Spike 1: up-left (main)
    draw_crystal_spike(pix, BASE_X, BASE_Y, 34, 8, w=2)
    # Spike 2: straight up
    draw_crystal_spike(pix, BASE_X+1, BASE_Y, 40, 9, w=2)
    # Spike 3: up-right
    draw_crystal_spike(pix, BASE_X+2, BASE_Y, 46, 12, w=1)
    # Spike 4: far right, short
    draw_crystal_spike(pix, BASE_X+3, BASE_Y+2, 48, 18, w=1)
    # Glow pixels around cluster base
    for x in range(33, 50):
        for y in range(9, 25):
            if (x, y) in pix:
                for ox, oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    put(pix, x+ox, y+oy, GLOW_EDGE, overwrite=False)
    # Bright specular tips
    for tip_pt in [(34,8),(40,9),(46,12),(48,18)]:
        put(pix, tip_pt[0], tip_pt[1], (200, 130, 255, 255))
    return pix

def make_staff_t10():
    """Dragon Claw Staff — three curved claws clutching a red gem, dark wood shaft."""
    pix = {}
    DARK  = (20, 10, 3, 255)
    MID   = (58, 32, 8, 255)
    LIGHT = (95, 55, 18, 255)
    CLAW_D = (15, 8, 2, 255)
    CLAW_M = (50, 28, 6, 255)
    CLAW_H = (90, 52, 15, 255)
    CLAW_S = (135, 80, 28, 255)
    GEM_D  = (90, 8, 8, 255)
    GEM_B  = (215, 32, 32, 255)
    GEM_H  = (255, 75, 45, 255)
    GEM_S  = (255, 155, 110, 255)
    _make_staff_shaft(pix, DARK, MID, LIGHT)
    # Gold ring where claws meet shaft
    GOLD = (215, 172, 38, 255)
    for xi in range(35, 42):
        put(pix, xi, 25, GOLD)
        put(pix, xi, 26, (160, 120, 22, 255))
    # Three claws radiating from (38, 22), curling inward
    # Claw 1: left claw — arcs up-left then curls right
    claw1_pts = _bezier2((36, 22), (28, 12), (34, 8))
    # Claw 2: center claw — goes straight up
    claw2_pts = _bezier2((38, 22), (38, 10), (39, 6))
    # Claw 3: right claw — arcs up-right then curls left
    claw3_pts = _bezier2((40, 22), (48, 12), (44, 8))
    for claw_pts in [claw1_pts, claw2_pts, claw3_pts]:
        n_c = len(claw_pts)
        for i, (x, y) in enumerate(claw_pts):
            t = i / max(n_c-1,1)
            col = CLAW_D if t > 0.85 else (CLAW_M if t > 0.5 else (CLAW_H if t > 0.2 else CLAW_S))
            put(pix, x, y, col)
            # Claw thickness: 2px wide at base, 1px at tip
            if t < 0.7:
                put(pix, x+1, y, CLAW_D, overwrite=False)
        # Claw tip specular
        tx, ty = claw_pts[-1]
        put(pix, tx, ty, CLAW_S)
    # Central red gem between claws (3x3 diamond)
    draw_gem(pix, 38, 14, size=3, col_dark=GEM_D, col_base=GEM_B, col_hi=GEM_H, col_spec=GEM_S)
    # Claw shadow on gem
    for (x, y) in [(37,13),(38,12),(39,13)]:
        put(pix, x, y, CLAW_D)
    return pix

def make_staff_t11():
    """Celestial Prism Staff — large multifaceted gem prism atop ornate gold setting, rainbow tint."""
    pix = {}
    # Gold shaft
    GOLD_D = (118, 85, 10, 255)
    GOLD_M = (200, 158, 28, 255)
    GOLD_L = (238, 198, 52, 255)
    GOLD_S = (255, 240, 88, 255)
    _make_staff_shaft(pix, GOLD_D, GOLD_M, GOLD_L, extra_px=0)
    # Decorative gold accents on shaft
    for xi in range(31, 40):
        put(pix, xi, 25, GOLD_S)
        put(pix, xi, 26, GOLD_D)
    for xi in range(33, 38):
        put(pix, xi, 30, GOLD_M)
    # Gem-accent inlays on shaft
    for (gx2, gy2), col in [
        ((34,28),(130,200,255,255)),
        ((36,28),(200,130,255,255)),
        ((33,31),(255,200,130,255)),
    ]:
        put(pix, gx2, gy2, col)
    # Large prism gem — diamond shape 9-wide x 12-tall centered at (41,13)
    GCX, GCY = 41, 13
    GEM_W = (225, 225, 248, 255)  # white-crystal base
    GEM_HI = (242, 242, 255, 255)
    GEM_SP = (255, 255, 255, 255)
    # Each face of the prism gets a different rainbow tint
    FACE_TOP   = (215, 235, 255, 255)  # blue tint — top face
    FACE_LEFT  = (220, 255, 225, 255)  # green tint — left face
    FACE_RIGHT = (255, 215, 225, 255)  # pink/red tint — right face
    FACE_BOT   = (255, 248, 215, 255)  # gold tint — bottom face
    PRISM_DARK = (115, 112, 145, 255)
    GOLD_SETTING = (218, 178, 42, 255)
    for dy in range(-8, 9):
        for dx in range(-8, 9):
            # Diamond shape: |dx|*0.7 + |dy| <= 8
            if abs(dx)*0.65 + abs(dy) > 8:
                continue
            nx, ny = GCX+dx, GCY+dy
            if not (0 <= nx < FW and 0 <= ny < FH):
                continue
            dist = abs(dx)*0.65 + abs(dy)
            # Assign face color
            if dy < 0 and dx <= 0:
                face = FACE_TOP
            elif dy < 0 and dx > 0:
                face = FACE_RIGHT
            elif dy >= 0 and dx > 0:
                face = FACE_BOT
            else:
                face = FACE_LEFT
            # Shading within face
            if dist < 2:
                col = GEM_SP
            elif dist < 4:
                col = GEM_HI
            elif dist < 6:
                col = face
            elif dist < 7.5:
                col = GEM_W
            else:
                col = PRISM_DARK
            put(pix, nx, ny, col)
    # Gold ornate setting frame
    setting_pts = []
    for ang_i in range(360):
        a = math.radians(ang_i)
        r_outer = 9.5
        # Diamond-shaped setting
        rx = r_outer / (abs(math.cos(a))*0.65 + abs(math.sin(a)) + 0.001)
        sx = round(GCX + rx * math.cos(a))
        sy = round(GCY + rx * math.sin(a))
        setting_pts.append((sx, sy))
    seen_s = set()
    for (sx, sy) in setting_pts:
        if (sx,sy) not in seen_s:
            seen_s.add((sx,sy))
            put(pix, sx, sy, GOLD_SETTING)
            put(pix, sx+1, sy, GOLD_D, overwrite=False)
    # Specular points on prism facets
    put(pix, GCX-2, GCY-4, GEM_SP)
    put(pix, GCX+1, GCY-2, GEM_SP)
    put(pix, GCX-1, GCY+2, (200, 200, 220, 255))
    # Corner gems on setting
    CORNER_GEMS = [(GCX, GCY-9), (GCX+6, GCY), (GCX-6, GCY), (GCX, GCY+8)]
    GEM_COLS = [(255,200,200,255),(200,255,200,255),(200,200,255,255),(255,255,180,255)]
    for (cgx, cgy), gcol in zip(CORNER_GEMS, GEM_COLS):
        put(pix, cgx, cgy, gcol)
        put(pix, cgx-1, cgy-1, (min(255,gcol[0]+30),min(255,gcol[1]+30),min(255,gcol[2]+30),255))
    return pix

# ── TRAIL COLORS ──────────────────────────────────────────────────────────────
WHITE_TRAIL = (255, 255, 255, 255)
LAV_TRAIL   = (174, 161, 188, 255)

STAFF_TRAILS_HD = {
    't7': ((255, 220, 80, 255),  (255, 200, 120, 220)),  # gold solar
    't8': ((80, 230, 210, 255),  (140, 210, 200, 200)),  # teal moon
    't9': ((165, 72, 255, 255),  (120, 45, 200, 180)),   # void purple
    't10': ((255, 60, 40, 255),  (255, 120, 80, 180)),   # dragon fire
    't11': ((220, 200, 255, 255),(180, 255, 200, 180)),  # celestial rainbow
}

# ── GENERATE ALL SPRITES ──────────────────────────────────────────────────────

SWORD_DESIGNS = {
    't7':  (make_sword_t7,  'Silver Knight Longsword'),
    't8':  (make_sword_t8,  'Stormcaller'),
    't9':  (make_sword_t9,  'Demonblade'),
    't10': (make_sword_t10, 'Crystal Greatsword'),
    't11': (make_sword_t11, "Warlord's Axe"),
}

STAFF_DESIGNS = {
    't7':  (make_staff_t7,  'Solar Crown Staff'),
    't8':  (make_staff_t8,  'Crescent Moon Staff'),
    't9':  (make_staff_t9,  'Void Shard Staff'),
    't10': (make_staff_t10, 'Dragon Claw Staff'),
    't11': (make_staff_t11, 'Celestial Prism Staff'),
}

print("\n=== Generating HD swords t7–t11 ===")
for tier, (design_fn, name) in SWORD_DESIGNS.items():
    f0 = design_fn()
    for g in ['m', 'f']:
        out_path = f'{OUT_DIR}sword_warrior_{tier}_{g}.png'
        build_sheet(f0, SRC_PATH, out_path, weapon_type='sword',
                    trail_c=WHITE_TRAIL, trail_e=LAV_TRAIL)
    print(f"  {tier}: {name} — {len(f0)} pixels in frame 0")

print("\n=== Generating HD staffs t7–t11 ===")
for tier, (design_fn, name) in STAFF_DESIGNS.items():
    f0 = design_fn()
    tc, te = STAFF_TRAILS_HD[tier]
    for g in ['m', 'f']:
        out_path = f'{OUT_DIR}staff_mage_{tier}_{g}.png'
        build_sheet(f0, SRC_PATH, out_path, weapon_type='staff',
                    trail_c=tc, trail_e=te)
    print(f"  {tier}: {name} — {len(f0)} pixels in frame 0")

# ── VERIFY t1–t6 UNCHANGED ────────────────────────────────────────────────────
import hashlib

EXPECTED_MD5 = {
    'sword_warrior_t1_m.png': 'ba73b1a3744cf8268625db1fa298c286',
    'sword_warrior_t2_m.png': '0d921e4292fde42416de0a535c4a701c',
    'sword_warrior_t3_m.png': '8a5c4f9c7f78586b969946d4e76bb70e',
    'sword_warrior_t4_m.png': '937f2fc7f8de1f572e55d11ffc782faf',
    'sword_warrior_t5_m.png': '739b6653331a3a21a7bf774f108cfc2d',
    'sword_warrior_t6_m.png': '8af1a25dcf3d57711dedd9e7fa525fc8',
    'sword_warrior_t1_f.png': 'ba73b1a3744cf8268625db1fa298c286',
    'sword_warrior_t2_f.png': '0d921e4292fde42416de0a535c4a701c',
    'sword_warrior_t3_f.png': '8a5c4f9c7f78586b969946d4e76bb70e',
    'sword_warrior_t4_f.png': '937f2fc7f8de1f572e55d11ffc782faf',
    'sword_warrior_t5_f.png': '739b6653331a3a21a7bf774f108cfc2d',
    'sword_warrior_t6_f.png': '8af1a25dcf3d57711dedd9e7fa525fc8',
    'staff_mage_t1_m.png': 'b0b79ab9e0c70e51714a6390547e0f68',
    'staff_mage_t2_m.png': '8a01ab9701e59eeadda76d916ad6ebe3',
    'staff_mage_t3_m.png': '88f25c02719b6de939c3c81a2cb1958d',
    'staff_mage_t4_m.png': '0cdffe9e0682fa38685fccd1b60a237d',
    'staff_mage_t5_m.png': 'a409540783f502fc591ee1e25d82931b',
    'staff_mage_t6_m.png': 'e5a059191b69031d44f01bba9fdcbc50',
    'staff_mage_t1_f.png': 'b0b79ab9e0c70e51714a6390547e0f68',
    'staff_mage_t2_f.png': '8a01ab9701e59eeadda76d916ad6ebe3',
    'staff_mage_t3_f.png': '88f25c02719b6de939c3c81a2cb1958d',
    'staff_mage_t4_f.png': '0cdffe9e0682fa38685fccd1b60a237d',
    'staff_mage_t5_f.png': 'a409540783f502fc591ee1e25d82931b',
    'staff_mage_t6_f.png': 'e5a059191b69031d44f01bba9fdcbc50',
}

print("\n=== Verifying t1–t6 unchanged ===")
all_ok = True
for fname, expected in EXPECTED_MD5.items():
    full = os.path.join(OUT_DIR, fname)
    actual = hashlib.md5(open(full,'rb').read()).hexdigest()
    status = "OK" if actual == expected else f"CHANGED! expected {expected}, got {actual}"
    if actual != expected:
        all_ok = False
        print(f"  FAIL {fname}: {status}")

if all_ok:
    print("  All t1–t6 files unchanged ✓")
else:
    print("  WARNING: some t1–t6 files were modified!")

print("\nDone.")
