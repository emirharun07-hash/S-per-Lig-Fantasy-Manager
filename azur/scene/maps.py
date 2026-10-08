"""AZUR helper maps (depth, window) kept small for the web.

Blender dithers 8-bit output, so a flat mask carries noise in every pixel and PNG cannot compress it: a window mask
of a few white shapes weighed ~0.5 MB and each depth map ~0.9 MB, loaded before the first picture. Here the window
mask loses the dither (values under 8 become 0) and the depth map is median-filtered and halved (it only drives a few
pixels of parallax; the browser samples it smoothly). Safe to run again on files already tidied.

Usage:  python3 azur/scene/maps.py [views dir]      (default prototype/assets/scene3/views: tidies every view)
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter


def tidy_window(path):
    a = np.asarray(Image.open(path).convert('L'))
    Image.fromarray(np.where(a < 8, 0, a).astype(np.uint8), 'L').save(path, optimize=True)


def tidy_depth(path, plate_w=None):
    im = Image.open(path).convert('L').filter(ImageFilter.MedianFilter(3))
    if plate_w is None or im.width >= plate_w:                     # full plate size: halve it (only once)
        im = im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.BILINEAR)
    im.save(path, optimize=True)


def tidy_views(views_dir):
    res = {}
    vj = os.path.join(views_dir, 'views.json')
    if os.path.exists(vj): res = {k: v.get('res') for k, v in json.load(open(vj)).items() if isinstance(v, dict)}
    out = []
    for key in sorted(os.listdir(views_dir)):
        d = os.path.join(views_dir, key)
        if not os.path.isdir(d): continue
        w, dp = os.path.join(d, 'window.png'), os.path.join(d, 'depth.png')
        if os.path.exists(w):
            b = os.path.getsize(w); tidy_window(w); out.append((w, b, os.path.getsize(w)))
        if os.path.exists(dp):
            pw = (res.get(key) or [None])[0]
            if pw is None or Image.open(dp).width >= pw:
                b = os.path.getsize(dp); tidy_depth(dp, pw); out.append((dp, b, os.path.getsize(dp)))
    return out


if __name__ == '__main__':
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vd = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'prototype', 'assets', 'scene3', 'views')
    for p, b, a in tidy_views(vd):
        print(f'{os.path.relpath(p, vd)}: {b // 1024} KB -> {a // 1024} KB')
