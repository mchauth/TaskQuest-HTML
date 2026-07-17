# sprites/reference/ — Pixel Art Quality Reference Library

Annotated references for judging quality and placement of TaskQuest character
sprites. Use these when generating or reviewing new armor/hat sprites so output
matches the established style.

All character sheets are 800x448 PNG: 10 columns x 7 rows of 80x64 frames.
Frame 0 is the top-left frame (idle, facing front). The character body occupies
roughly x=30..54 within a frame. Male base skin is `skin_m1.png` (head_top at
y=21); female is `skin_f1.png` (head_top at y=22).

## Files

### ref_hat_comparison.png / ref_chest_comparison.png / ref_pants_comparison.png / ref_boots_comparison.png

Side-by-side GOOD vs BAD composite for each armor slot, 160x128:

- Left 80px column = GOOD, right 80px = BAD (labels on the dark bottom band).
- Top row: full 80x64 frame 0 (armor composited over `skin_m1.png`).
- Bottom row: 2x zoom of the armor region so pixel-level flaws are visible.

Good sources: `helmet_mage4.png`, `armor_chest_4.png`, `armor_pants_4.png`,
`armor_boots_4.png` (frame 0 of each, from `sprites/preview_assets/char/`).

The BAD side was synthesized from the good sprite by:
1. **Flat shading** — every non-outline pixel replaced with the median color
   (no left-shadow / right-highlight gradient).
2. **3 stray pixels** — random opaque pixels 2-6px outside the silhouette.
3. **Wrong placement** — the piece is offset from its anchor (hat +3px down so
   it covers the eyes, chest +2px right, pants -2px up, boots -2px left).

When reviewing a new sprite, reject anything showing the BAD-side symptoms:
orphan pixels detached from the silhouette, a single flat tone across a face,
or the piece drifting off the body anchor rows/columns.

### ref_shading_gradients.png

400x200 chart of the horizontal cosine shading model from
`scripts/sprite_shade.py`.

- Top: `armor_chest_4.png` frame 0 at 4x with arrows marking the four tonal
  faces — shadow face (x0.80), neutral face, highlight face (x1.10), deep
  shadow (x0.65 near outlines).
- Bottom: the per-x HSV V-adjustment curve for x=0..79, computed with
  `ADJ_MIN=-0.20`, `ADJ_MAX=+0.25`, `BELL_WIDTH=0.7`, `PEAK=0.55`, normalized
  over the character span x=30..54. Light source reads as upper-left-ish with
  the highlight peak at ~55% across the body (yellow dot); the curve clamps
  flat outside the character span.

New armor must show this left-dark to right-of-center-bright gradient, not
flat fills or random dithering. Tier scripts apply it via
`sprite_shade.py` with `ADJ_MIN=-0.20, ADJ_MAX=0.25`.

### ref_hat_placement.png

320x128 head-zone guide (frame rows 8..40 at 4x): `skin_m1.png` frame 0 with
`helmet_mage3.png` frame 0 overlaid at 50% opacity, plus guide lines:

- **Red, y=21** — `head_top`: topmost skull row of the male base skin. Hat
  cone/dome is authored upward from `head_top - 1`.
- **Blue, y=23** — brim anchor: bottom edge of the brim/lining region
  (`head_top..head_top+2` is the covered skull zone).
- **Green, y=26** — eye row. A hat must NEVER reach this row; if it does, it
  is sitting too low (see the BAD hat comparison).
- **Yellow verticals, x=35 and x=45** — skull zone. Brim width equals skull
  width (~9-11px, no overhang except wide tier-6 hats at +2px).

Hats are placed per-frame by skull-dome tracking (see
`scripts/rebuild_class_hats.py`); frame 0 anchors are the canonical ones shown
here.

## How to use when prompting for new sprites

1. State the frame geometry: 80x64 frames, 10x7 sheet, character at x=30..54.
2. Point at the GOOD side of the relevant slot comparison as the style target:
   1px black outline, 3-4 tone shading per face, no stray pixels.
3. Require the cosine shading gradient (`ref_shading_gradients.png`): shadow
   left, highlight at ~55% across the body, deep shadow beside outlines.
4. For hats, enforce the anchors in `ref_hat_placement.png`: build from
   head_top y=21 (male) / y=22 (female), brim = skull width at x=35..45,
   nothing at or below eye_row y=26.
5. QA any generated result the way the BAD examples were built: scan for
   opaque pixels outside the intended silhouette, check per-face tonal range,
   and verify anchors against the guide lines.
