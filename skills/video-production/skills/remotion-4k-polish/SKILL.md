---
name: remotion-4k-polish
description: Fix and prevent jagged, thin, or hairy text and lines in 4K Remotion renders, and choose the right 4K rendering path. Use when a 4K video must be rendered (before choosing the scale/render path), when 4K text or lines look rough, thin, or worse than the 1080p draft (毛刺/线太细), or when a killed or segmented Remotion render leaves `moov atom not found` errors.
---

# remotion-4k-polish

Why 4K Remotion text goes rough, and the three ways out.

## Root cause

Rendering a 1920×1080 composition with `--scale=2` sets Chromium's deviceScaleFactor to 2. On that path Chromium **disables font hinting and drops to grayscale antialiasing** — glyphs rasterize from their true outlines, so thin strokes render truly thin and small/medium text gets hairy edges. 1080p drafts look better than the 4K master because scale=1 gets the full rasterization path (hinting + subpixel AA) that visually fattens and smooths strokes.

This is Chromium rendering-path behavior with no setting to flip — choose a path instead:

```
new project / theme carries size constants          → Path B
sizes hardcoded, deadline, platform re-encodes      → Path A
a scale=2 master already exists                     → Path C (know its ceiling), else A/B
```

(Inside a pipeline that reserves the upscale decision for the user, present Path A vs B rather than auto-routing.)

## Path B — 4K-native composition (quality path)

Design the composition at 3840×2160 with every size constant doubled, render with `--scale=1`. deviceScaleFactor stays 1, so Chromium's standard rasterization (hinting, proper AA) runs at 4K resolution: true 4K sharpness with smooth edges.

Feasibility: the project's theme must carry all sizes as constants (a single `SCALE` multiplier applied to layout, font, and spacing constants). Projects with literal pixel values scattered through components need a constants pass first — cheap if done at scaffold time, which the decision block routes new projects through.

## Path A — 1080p master + lanczos upscale (universal quick path)

Render at 1080p (hinting on, best possible text), then upscale:

```bash
ffmpeg -i main-1080p.mp4 -vf "scale=3840:2160:flags=lanczos" -c:v libx264 -crf 15 -c:a copy main-4k.mp4
```

Text renders at its best and the upscale is uniform — soft but clean, and platform re-encoding erases most of the difference against a native 4K master. Bonus: the 1080p render is ~4× faster than 4K-native. Use when the composition isn't size-parameterized, when time matters, or when the platform re-encodes everything anyway.

## Path C — scale=2 + compensation (mitigation only; know its ceiling)

When a scale=2 master already exists or is unavoidable:

- **Line-weight compensation**: hairlines nominally keep their relative thickness across resolutions, but the 2× downsample to typical 1080p viewing dilutes 1px-scale lines below perceptual weight (they shimmer or break after platform re-encode). Double hairline widths in the 4K master (a `LN(w) → SCALE>=2 ? w*2 : w` helper in the theme) so the 1080p viewing path sees the designed weight.
- **Same-color stroke for serif/thin faces**: a ~0.15px CSS-px same-color `WebkitTextStroke` restores the weight the no-hinting path loses — five measured rounds on a real 4K master: 0.5px reads too bold, 0.25px is visually identical to 0.15px (subpixel rounding), so 0.15px is the value. Pair with crf ≤14 so the encoder doesn't shave the restored weight; scale up only if your largest stroked face still reads thin.
- Ceiling: strokes are vector edges layered on an unhinted raster — they restore weight but do not restore smoothness. If the master still reads jagged at viewing size, move to Path A or B.

## Integrity checks (any path)

ffprobe every segment before concat — mandatory after any force-kill. `moov atom not found` marks a file killed mid-finalize; re-render it. "File exists" is not "file is complete".
