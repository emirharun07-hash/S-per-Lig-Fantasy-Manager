"""AZUR despeckle: the cloud renders (128 samples and fewer, round 4) leave coloured dots in bright sun patches that the
PC's 384 samples did not. They are chroma noise and single bright pixels, so this smooths the colour channels (YCbCr,
gaussian) and pulls lone pixels that stand far above their 3x3 median back to it, leaving luminance detail alone.

Runs inside the regions cloud_patch.py rendered (feathered at their edges) and on every time-of-day patch it wrote.
Each file once (recorded in .cache/r4/despeckle.json); time-of-day patches only once cloud_patch has rendered them.

Usage:  python3 azur/scene/despeckle.py
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VIEWS_DIR = os.path.join(ROOT, 'prototype', 'assets', 'scene3', 'views')
R4 = os.path.join(ROOT, '.cache', 'r4')
DONE = os.path.join(R4, 'despeckle.json')          # own record: cloud_patch.py writes done.json meanwhile
PATCHED = os.path.join(R4, 'done.json')
PASS_Q = {'neon': 97}


def clean(rgb):
    """rgb uint8 -> cleaned uint8 (same shape)."""
    a = rgb.astype(np.float32)
    # lone hot pixels: more than 18 codes above the 3x3 median in any channel
    med = np.stack([ndi.median_filter(a[..., c], 3) for c in range(3)], -1)
    hot = (a - med).max(-1) > 18
    a[hot] = med[hot]
    y = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    cb = a[..., 2] - y; cr = a[..., 0] - y
    cb = ndi.gaussian_filter(cb, 1.6); cr = ndi.gaussian_filter(cr, 1.6)
    r = y + cr; b = y + cb; g = (y - 0.299 * r - 0.114 * b) / 0.587
    return np.clip(np.stack([r, g, b], -1) + 0.5, 0, 255).astype(np.uint8)


def highlights(rgb, lo=228, hi=246, sigma=1.3):
    """Bright sun patches sit at the top of the pass encoding, where one code is a big step in light: decoded and
    tinted in the browser, single-code differences between channels show as coloured dots. Smooth only there."""
    a = rgb.astype(np.float32)
    w = np.clip((ndi.gaussian_filter(a.max(-1), 1.0) - lo) / (hi - lo), 0, 1)[..., None]
    b = np.stack([ndi.gaussian_filter(a[..., c], sigma) for c in range(3)], -1)
    return np.clip(a + w * (b - a) + 0.5, 0, 255).astype(np.uint8)


def feather(shape, box, edge=16):
    h, w = shape
    X0, Y0, X1, Y1 = int(box[0] * w), int(box[1] * h), int(np.ceil(box[2] * w)), int(np.ceil(box[3] * h))
    yy, xx = np.mgrid[0:h, 0:w]
    big = 10 ** 6
    dist = np.minimum(np.minimum(xx - X0 if X0 > 0 else big, X1 - 1 - xx if X1 < w else big),
                      np.minimum(yy - Y0 if Y0 > 0 else big, Y1 - 1 - yy if Y1 < h else big))
    inside = (xx >= X0) & (xx < X1) & (yy >= Y0) & (yy < Y1)
    return np.clip(dist / edge, 0, 1) * inside


def main():
    done = json.load(open(DONE)) if os.path.exists(DONE) else {}
    regions = json.load(open(os.path.join(R4, 'regions.json')))['regions']
    patched = json.load(open(PATCHED)) if os.path.exists(PATCHED) else {}
    n = 0
    for key, boxes in regions.items():
        for f in sorted(os.listdir(os.path.join(VIEWS_DIR, key))):
            if not f.endswith('.webp') or f == 'neon_glow.webp' or f == 'beauty.webp': continue
            path = os.path.join(VIEWS_DIR, key, f); tag = 'despeckle ' + os.path.relpath(path, VIEWS_DIR)
            if tag in done or not boxes or not any(k.startswith(f'day {key} {f[:-5]} ') for k in patched): continue
            a = np.asarray(Image.open(path).convert('RGB'))
            w = np.zeros(a.shape[:2], np.float32)
            for b in boxes: w = np.maximum(w, feather(a.shape[:2], b))
            c = clean(a)
            out = (a.astype(np.float32) + w[..., None] * (c.astype(np.float32) - a.astype(np.float32)) + 0.5).astype(np.uint8)
            Image.fromarray(out).save(path, 'WEBP', quality=PASS_Q.get(f[:-5], 94), method=6)
            done[tag] = True; n += 1
    for key in regions:
        for state in ('morning', 'evening', 'night'):
            sdir = os.path.join(VIEWS_DIR, key, state)
            if not os.path.isdir(sdir) or f'state {key} {state}' not in patched: continue
            for f in sorted(os.listdir(sdir)):
                path = os.path.join(sdir, f); tag = 'despeckle ' + os.path.relpath(path, VIEWS_DIR)
                if not f.endswith('.webp') or tag in done: continue
                a = np.asarray(Image.open(path).convert('RGB'))
                Image.fromarray(clean(a)).save(path, 'WEBP', quality=PASS_Q.get(f.split('_')[0], 94), method=6)
                done[tag] = True; n += 1
    # the sun passes' highlights, whole picture (the PC's plates had the dots too), and the patches of those passes
    for key in os.listdir(VIEWS_DIR):
        d = os.path.join(VIEWS_DIR, key)
        if not os.path.isdir(d): continue
        files = [os.path.join(d, p + '.webp') for p in ('sun_low', 'sun_high')]
        for state in ('morning', 'evening'):
            sd = os.path.join(d, state)
            if os.path.isdir(sd) and f'state {key} {state}' in patched:
                files += [os.path.join(sd, f) for f in sorted(os.listdir(sd)) if f.startswith('sun_')]
        for path in files:
            tag = 'highlights ' + os.path.relpath(path, VIEWS_DIR)
            if tag in done or not os.path.exists(path): continue
            a = np.asarray(Image.open(path).convert('RGB'))
            Image.fromarray(highlights(a)).save(path, 'WEBP', quality=94, method=6)
            done[tag] = True; n += 1
    json.dump(done, open(DONE, 'w'), indent=1)
    print('despeckled', n, 'files')


if __name__ == '__main__':
    main()
