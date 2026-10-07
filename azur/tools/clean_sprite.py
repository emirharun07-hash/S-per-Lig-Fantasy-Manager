"""Drop sprites pick up specks (tape, dust-sized holdout leaks) that blow up their bounding box.
Keeps only large opaque regions, re-crops, and corrects the box in sprites.json.
Usage: python3 azur/tools/clean_sprite.py <view> [<view> ...]"""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prototype', 'assets', 'views')


def clean(view, out=OUT, min_frac=0.01):
    path = os.path.join(out, view, 'drop.webp'); meta = os.path.join(out, 'sprites.json')
    d = json.load(open(meta)); box = d[view]['drop']['box']
    im = Image.open(path).convert('RGBA'); a = np.array(im)
    mask = a[..., 3] > 6
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0: return
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.where(sizes >= max(sizes.max() * min_frac, 40))[0])
    a[..., 3] = np.where(keep, a[..., 3], 0)
    ys, xs = np.where(keep)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    w, h = im.size
    bw, bh = box[2] - box[0], box[3] - box[1]
    d[view]['drop']['box'] = [box[0] + bw * x0 / w, box[1] + bh * y0 / h, box[0] + bw * x1 / w, box[1] + bh * y1 / h]
    Image.fromarray(a[y0:y1, x0:x1]).save(path, 'WEBP', quality=88, method=6)
    json.dump(d, open(meta, 'w'), indent=1)
    print(view, 'components', n, 'kept', int(keep.any()), 'crop', (x0, y0, x1, y1), 'of', (w, h))


if __name__ == '__main__':
    for v in sys.argv[1:]: clean(v)
