#!/usr/bin/env python3
"""sprite_pipeline.py — full sprite shade → QA → auto-fix → re-QA loop.

Usage (from repo root):
  python3 scripts/sprite_pipeline.py sprites/preview_assets/char/helmet_mage1.png \
      [--type hat|chest|pants|boots] [--gender m|f]
  python3 scripts/sprite_pipeline.py --all          # all armor sprites in char/
  python3 scripts/sprite_pipeline.py --set mage     # all sprites whose name contains 'mage'
  ... [--no-shade]                                  # skip the shading pass (QA/fix only)

Pipeline per sprite:
  1. Shade   : sprite_shade.shade_sheet() in-process (same model as the CLI tool)
  2. QA      : sprite_qa.check_sprite() with type-appropriate --y-min/--y-max
  3. Auto-fix: stray isolated pixels -> transparent (all frames);
               background/bottom-row bleed in frame 0 -> transparent;
               luminance outlier vs set median -> uniform V-scale toward median
  4. Re-QA   : run QA again
  5. Report  : PASS / FIXED / FAIL summary table; FAIL list at the end

QA flag map (see SPRITE_SPEC.md §8):
  hat   : y_min=2,  y_max=52
  chest : y_min=16, y_max=52
  pants : y_min=16, y_max=62 (male) / 63 (female leggings)
  boots : y_min=16, y_max=63

No dependencies beyond PIL + numpy.
"""
import os
import sys
import argparse
import numpy as np
from PIL import Image

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import sprite_shade      # noqa: E402
import sprite_qa         # noqa: E402

CHAR_DIR = os.path.join(ROOT, 'sprites', 'preview_assets', 'char')
FW, FH, COLS, ROWS = 80, 64, 10, 7

# Non-armor sheets: never shade/fix these (skin/hair/sword are base layers the
# shader must not touch; previews/tests are scratch files).
SKIP_PREFIXES = ('skin', 'hair', 'sword')
SKIP_SUBSTR = ('_preview', '_test', 'leather_test')

# Luminance-outlier auto-fix thresholds
LUM_DEV = 0.25          # trigger when |median/set_median - 1| > 25%
LUM_SCALE_CLAMP = (0.70, 1.40)


# ── Classification ───────────────────────────────────────────────────────────

def classify_type(name):
    n = os.path.basename(name).lower()
    if 'helmet' in n:
        return 'hat'
    if 'pants' in n or 'legging' in n or n.startswith('warrior_pants'):
        return 'pants'
    if 'boot' in n or 'shoe' in n or 'sock' in n:
        return 'boots'
    return 'chest'


def infer_gender(name):
    base = os.path.basename(name).lower().rsplit('.', 1)[0]
    if base.endswith('_f') or '_f.' in os.path.basename(name).lower():
        return 'f'
    if base.endswith('_m') or '_default_f' in base or base.endswith('_f'):
        return 'f' if base.endswith('_f') else 'm'
    # warrior_* legacy files carry _m/_f before extension
    if base.endswith('_m'):
        return 'm'
    return 'm'


def qa_flags(stype, gender):
    """Return (y_min, y_max) for sprite_qa per SPRITE_SPEC.md."""
    if stype == 'hat':
        return 2, 52
    if stype == 'pants':
        return 16, (63 if gender == 'f' else 62)
    if stype == 'boots':
        return 16, 63
    return 16, 52   # chest


def should_skip(name):
    n = os.path.basename(name).lower()
    if any(n.startswith(p) for p in SKIP_PREFIXES):
        return True
    if any(s in n for s in SKIP_SUBSTR):
        return True
    return False


# ── Set grouping (for luminance median) ──────────────────────────────────────

def set_key(name):
    """Group sprites into visual sets = class family + tier number. An armor
    set (shirt/pants/boots/helmet, m+f) shares one palette, so luminance should
    be consistent WITHIN a set. Do NOT group across tiers — tier progression
    legitimately darkens (mage t1 bright purple -> t6 near-void), so a
    cross-tier median would 'correct' correct sprites.
    e.g. pants_mage3_f.png -> ('mage','3'); armor_chest_4.png -> ('armor','4')."""
    n = os.path.basename(name).lower().rsplit('.', 1)[0]
    if n.endswith('_f') or n.endswith('_m'):
        n = n[:-2]
    fam = None
    for f in ('mage', 'ranger', 'rare', 'armor', 'leather', 'warrior'):
        if f in n:
            fam = f
            break
    if fam is None:
        fam = 'misc'
    digits = ''.join(ch for ch in n if ch.isdigit())
    tier = digits[-1] if digits else None
    return (fam, tier)


def lum_eligible_mask(img):
    """Opaque, non-black, non-accent pixels (mirrors scripts/lum_stats.py)."""
    rgb = img[:, :, :3].astype(np.int16)
    a = img[:, :, 3]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    opaque = a > 10
    black = (r + g + b) < 15
    gold = (r >= 230) & (g >= 190) & (b < 100)
    teal = (g >= 170) & (b >= 150) & (r < g)
    return opaque & ~black & ~(gold | teal)


def median_lum(img):
    m = lum_eligible_mask(img)
    if not m.any():
        return None
    rgb = img[:, :, :3].astype(np.float32)
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    return float(np.median(lum[m]))


# ── Auto-fix passes ──────────────────────────────────────────────────────────

def fix_isolated(arr):
    """Clear stray pixel islands in EVERY frame: 8-connected components with
    fewer than 3 pixels (a lone pixel = 'isolated, <2 neighbors', plus detached
    2px pairs). Component-based on purpose — committed sprites contain ~1700
    LEGIT pixels with <2 neighbors (ranger feather tips, boot toe pixels,
    plate seam ends) that are attached to a large component and must survive.
    Returns number of pixels cleared."""
    fixed = 0
    for fi in range(COLS * ROWS):
        c, r = fi % COLS, fi // COLS
        fr = arr[r * FH:(r + 1) * FH, c * FW:(c + 1) * FW]
        alpha = fr[:, :, 3]
        seen = np.zeros_like(alpha, dtype=bool)
        for (y0, x0) in np.argwhere(alpha > 0):
            y0, x0 = int(y0), int(x0)
            if seen[y0, x0]:
                continue
            # BFS over the 8-connected opaque component
            comp = [(y0, x0)]
            seen[y0, x0] = True
            qi = 0
            while qi < len(comp) and len(comp) < 4:
                y, x = comp[qi]
                qi += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if (0 <= ny < FH and 0 <= nx < FW
                                and alpha[ny, nx] > 0 and not seen[ny, nx]):
                            seen[ny, nx] = True
                            comp.append((ny, nx))
            if len(comp) < 3:
                for (y, x) in comp:
                    fr[y, x] = 0
                    fixed += 1
            else:
                # big component: mark the rest without clearing
                while qi < len(comp):
                    y, x = comp[qi]
                    qi += 1
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = y + dy, x + dx
                            if (0 <= ny < FH and 0 <= nx < FW
                                    and alpha[ny, nx] > 0 and not seen[ny, nx]):
                                seen[ny, nx] = True
                                comp.append((ny, nx))
    return fixed


def fix_bleed_frame0(arr, y_min, y_max):
    """Clear frame-0 pixels outside the QA background box (incl. bottom-row
    bleed y > FH-2). Frame 0 only — animation frames legitimately move limbs
    outside the frame-0 box (slash cx reaches 45-46)."""
    fr = arr[:FH, :FW]
    fixed = 0
    for (y, x) in np.argwhere(fr[:, :, 3] > 0):
        y, x = int(y), int(x)
        if (x < sprite_qa.BG_X_MIN or x > sprite_qa.BG_X_MAX
                or y < y_min or y > y_max or y > FH - 2):
            fr[y, x] = 0
            fixed += 1
    return fixed


def fix_lone_black_frame0(arr):
    """Clear LONE INNER BLACK pixels flagged by the QA rule (frame 0)."""
    fr = arr[:FH, :FW]
    fixed = 0
    for (y, x) in np.argwhere(fr[:, :, 3] > 0):
        y, x = int(y), int(x)
        r, g, b = (int(v) for v in fr[y, x, :3])
        if (r, g, b) == (0, 0, 0):
            if (not sprite_qa.is_edge_pixel(fr, y, x)
                    and not sprite_qa.has_black_neighbor(fr, y, x)):
                fr[y, x] = 0
                fixed += 1
    return fixed


def fix_luminance(arr, set_median):
    """If this sheet's median luminance deviates >LUM_DEV from the set median,
    V-scale all eligible pixels toward the median. Returns scale or None."""
    if set_median is None:
        return None
    med = median_lum(arr)
    if med is None or med <= 0:
        return None
    dev = med / set_median - 1.0
    if abs(dev) <= LUM_DEV:
        return None
    scale = max(LUM_SCALE_CLAMP[0], min(LUM_SCALE_CLAMP[1], set_median / med))
    m = lum_eligible_mask(arr)
    rgb = arr[:, :, :3].astype(np.float32)
    rgb[m] = np.clip(rgb[m] * scale, 0, 255)
    arr[:, :, :3] = rgb.astype(np.uint8)
    return scale


# ── Per-sprite pipeline ──────────────────────────────────────────────────────

def run_qa(path, y_min, y_max):
    passed, issues = sprite_qa.check_sprite(path, None, bg_y_max=y_max, bg_y_min=y_min)
    return passed, issues


def process(path, stype, gender, set_median=None, do_shade=True):
    """Run the full loop on one sprite. Returns a result dict."""
    rel = os.path.relpath(path, ROOT)
    y_min, y_max = qa_flags(stype, gender)
    res = dict(path=rel, type=stype, gender=gender, status='PASS',
               fixes=[], issues_before=0, issues_after=0)

    img = Image.open(path).convert('RGBA')
    if img.size != (800, 448):
        res['status'] = 'FAIL'
        res['fixes'].append(f'bad sheet size {img.size}')
        return res
    arr = np.array(img, dtype=np.uint8)

    # 1. Shade
    if do_shade:
        arr, stats = sprite_shade.shade_sheet(arr)
        res['fixes'].append(f"shaded {stats['armor_pixels']}px/"
                            f"{stats['frames_shaded']}f")
        Image.fromarray(arr).save(path)

    # 2. QA
    passed, issues = run_qa(path, y_min, y_max)
    res['issues_before'] = 0 if passed else len(issues)
    if passed:
        # Auto-fixes (incl. the luminance correction) only apply to sprites
        # that FAILED QA — passing committed sprites are never rewritten.
        # Report luminance outliers informationally instead.
        med = median_lum(arr)
        if set_median and med and abs(med / set_median - 1.0) > LUM_DEV:
            res['fixes'].append(
                f'note: lum median {med:.0f} vs set {set_median:.0f} '
                '(not fixed — QA passed)')
        return res

    # 3. Auto-fix
    n_iso = fix_isolated(arr)
    n_bleed = fix_bleed_frame0(arr, y_min, y_max)
    n_black = fix_lone_black_frame0(arr)
    scale = fix_luminance(arr, set_median)
    if n_iso:
        res['fixes'].append(f'{n_iso} isolated')
    if n_bleed:
        res['fixes'].append(f'{n_bleed} bleed')
    if n_black:
        res['fixes'].append(f'{n_black} lone-black')
    if scale is not None:
        res['fixes'].append(f'lum x{scale:.2f}')
    Image.fromarray(arr).save(path)

    # 4. Re-QA
    passed2, issues2 = run_qa(path, y_min, y_max)
    res['issues_after'] = 0 if passed2 else len(issues2)
    if passed2:
        res['status'] = 'FIXED'
    else:
        res['status'] = 'FAIL'
        res['fail_issues'] = issues2[:8]
    return res


# ── Discovery / batch ────────────────────────────────────────────────────────

def discover(set_filter=None):
    files = []
    for f in sorted(os.listdir(CHAR_DIR)):
        if not f.lower().endswith('.png'):
            continue
        if should_skip(f):
            continue
        if set_filter and set_filter.lower() not in f.lower():
            continue
        files.append(os.path.join(CHAR_DIR, f))
    return files


def compute_set_medians(paths):
    """Median-of-medians luminance per set key."""
    per_set = {}
    for p in paths:
        k = set_key(p)
        if k[1] is None:
            continue   # no tier number -> no meaningful set
        try:
            m = median_lum(np.array(Image.open(p).convert('RGBA')))
        except Exception:
            m = None
        if m is not None:
            per_set.setdefault(k, []).append(m)
    # A median over <3 members isn't meaningful — skip those sets.
    return {k: float(np.median(v)) for k, v in per_set.items() if len(v) >= 3}


def print_report(results):
    print()
    print(f"{'STATUS':7} {'TYPE':6} {'G':2} {'QA0':>4} {'QA1':>4}  SPRITE / FIXES")
    print('-' * 90)
    counts = {'PASS': 0, 'FIXED': 0, 'FAIL': 0}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
        fx = ('  [' + ', '.join(r['fixes']) + ']') if r['fixes'] else ''
        print(f"{r['status']:7} {r['type']:6} {r['gender']:2} "
              f"{r['issues_before']:4} {r['issues_after']:4}  {r['path']}{fx}")
    print('-' * 90)
    print(f"TOTAL: {len(results)}   PASS: {counts['PASS']}   "
          f"FIXED: {counts['FIXED']}   FAIL: {counts['FAIL']}")

    fails = [r for r in results if r['status'] == 'FAIL']
    if fails:
        print()
        print('═══ STILL FAILING AFTER AUTO-FIX — needs manual/agent attention ═══')
        for r in fails:
            print(f"  {r['path']}")
            for iss in r.get('fail_issues', []):
                print(f"      {iss}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(
        description='Sprite shade -> QA -> auto-fix -> re-QA pipeline.')
    ap.add_argument('sprite', nargs='?', help='single sprite PNG path')
    ap.add_argument('--type', choices=['hat', 'chest', 'pants', 'boots'],
                    help='override type classification')
    ap.add_argument('--gender', choices=['m', 'f'],
                    help='override gender inference')
    ap.add_argument('--all', action='store_true',
                    help='run on all armor sprites in sprites/preview_assets/char/')
    ap.add_argument('--set', dest='set_name', metavar='NAME',
                    help='run on all sprites whose filename contains NAME '
                         '(e.g. mage, ranger, rare, armor)')
    ap.add_argument('--no-shade', action='store_true',
                    help='skip the shading pass (QA + auto-fix only)')
    args = ap.parse_args()

    if args.all:
        paths = discover()
    elif args.set_name:
        paths = discover(args.set_name)
        if not paths:
            print(f'no sprites match --set {args.set_name}', file=sys.stderr)
            sys.exit(2)
    elif args.sprite:
        p = args.sprite if os.path.isabs(args.sprite) else os.path.join(ROOT, args.sprite)
        if not os.path.exists(p):
            print(f'not found: {p}', file=sys.stderr)
            sys.exit(2)
        paths = [p]
    else:
        ap.print_help()
        sys.exit(2)

    # Set medians for the luminance fix: computed over the siblings of each
    # sprite's (slot, class-family) set, across everything discoverable —
    # so even single-sprite mode compares against the full set on disk.
    medians = compute_set_medians(discover())

    results = []
    for p in paths:
        stype = args.type or classify_type(p)
        gender = args.gender or infer_gender(p)
        sm = medians.get(set_key(p))
        print(f'>> {os.path.relpath(p, ROOT)} (type={stype}, gender={gender})')
        try:
            results.append(process(p, stype, gender, set_median=sm,
                                   do_shade=not args.no_shade))
        except Exception as e:
            results.append(dict(path=os.path.relpath(p, ROOT), type=stype,
                                gender=gender, status='FAIL',
                                fixes=[f'ERROR: {e}'], issues_before=-1,
                                issues_after=-1, fail_issues=[str(e)]))

    sys.exit(print_report(results))


if __name__ == '__main__':
    main()
