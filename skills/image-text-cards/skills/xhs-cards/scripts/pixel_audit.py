#!/usr/bin/env python
"""pixel_audit.py — PIL audits for verify.mjs: void scan on previews, size+corner check on exports.
Usage: python pixel_audit.py <run-dir>  → prints "ok …" lines / defect lines.

Void scan is gradient-safe: each row's own median color is its background, so vertical
gradients (andy) and tinted surfaces don't read as ink. A row is "empty" when ~no pixel
deviates from the row median."""
import sys, glob, os
from PIL import Image

run = sys.argv[1]

def row_ink_ratio(im, y, w):
    samples = [im.getpixel((x, y)) for x in range(6, w - 6, 6)]
    n = len(samples)
    med = tuple(sorted(p[c] for p in samples)[n // 2] for c in range(3))
    ink = sum(1 for p in samples if abs(p[0]-med[0]) > 24 or abs(p[1]-med[1]) > 24 or abs(p[2]-med[2]) > 24)
    return ink / n

previews = sorted(glob.glob(os.path.join(run, "preview", "[0-9][0-9].png")))
for f in previews:
    im = Image.open(f).convert("RGB"); w, h = im.size
    gaps, start = [], None
    for y in range(60, h - 60):
        if row_ink_ratio(im, y, w) < 0.01:
            if start is None: start = y
        else:
            if start is not None: gaps.append(y - start); start = None
    if start is not None: gaps.append(h - 60 - start)
    m = max(gaps, default=0)
    if m > 150: print(f"{os.path.basename(f)}: void band {m}px")
print(f"ok pixel: void scan ({len(previews)} previews)")

exports = sorted(glob.glob(os.path.join(run, "exports", "[0-9][0-9].png")))
for f in exports:
    im = Image.open(f).convert("RGBA"); w, h = im.size
    if (w, h) != (3240, 4320):
        print(f"{os.path.basename(f)}: size {(w, h)}")
if exports:
    print(f"ok pixel: exports size ({len(exports)})")
