"""AZUR neon glow: the soft halo a camera sees around a lit neon sign (round 4: "so grainy, it does not glow nicely").

Cycles renders the tubes and the light they throw on the wall, but no lens bloom, and the dim wall light carries
render noise. This takes the brightest part of each view's neon pass (the tubes), spreads it with a few gaussian
radii and stores the result small and smooth (quarter size): <view>/neon_glow.webp, with its decode scale in
passes.json as 'neon_glow'. The browser adds it to the neon light (same colour and dimmer), so it glows by day as
faintly as the sign does and fully at night. Safe to run again (it always starts from neon.webp).

Usage:  python3 azur/scene/glow.py [views dir]
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

RADII = ((1.5, 0.42), (4.0, 0.30), (10.0, 0.18), (24.0, 0.10))     # gaussian sigma (quarter-size px), weight
ENC_REF = 1.5


def decode(codes, scale):
    e = codes.astype(np.float32) / 255.0
    if scale < 0: return (np.exp(e * np.log1p(2000.0)) - 1.0) / (2000.0 * -scale)   # log curve (render_queue.LOG_K)
    y = np.minimum(np.power(e, 2.2), 0.995)
    return (y / (1.0 - y)) / scale


def encode(rgb, scale):
    x = np.clip(rgb * scale, 0, None)
    return np.clip(np.power(x / (1.0 + x), 1 / 2.2) * 255 + 0.5, 0, 255).astype(np.uint8)


def neon_glow(neon_path, scale, out_path):
    lin = decode(np.asarray(Image.open(neon_path).convert('RGB')), scale)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    top = float(np.percentile(lum, 99.97))
    if top <= 0 or top < 200 * float(np.percentile(lum, 50)): return None      # the sign is not in this view (bed)
    wgt = np.clip((lum - 0.3 * top) / np.maximum(lum, 1e-6), 0, 1)         # the tubes, not the wall they light
    src = lin * wgt[..., None]
    h, w = lum.shape; q = 4
    small = src[: h // q * q, : w // q * q].reshape(h // q, q, w // q, q, 3).mean((1, 3))   # energy kept
    glow = sum(wt * np.stack([ndi.gaussian_filter(small[..., c], s, mode='constant') for c in range(3)], -1) for s, wt in RADII)
    lg = glow @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    gscale = ENC_REF / max(float(np.percentile(lg, 99.9)), 1e-6)
    Image.fromarray(encode(glow, gscale)).save(out_path, 'WEBP', quality=92, method=6)
    return gscale


def run(views_dir):
    mpath = os.path.join(views_dir, 'passes.json'); meta = json.load(open(mpath))
    done = []
    for key, scales in meta.items():
        if not isinstance(scales, dict) or 'neon' not in scales: continue
        src = os.path.join(views_dir, key, 'neon.webp')
        if not os.path.exists(src): continue
        dst = os.path.join(views_dir, key, 'neon_glow.webp')
        g = neon_glow(src, scales['neon'], dst)
        if g: scales['neon_glow'] = g; done.append(key)
        else:
            scales.pop('neon_glow', None)
            if os.path.exists(dst): os.remove(dst)
    json.dump(meta, open(mpath, 'w'), indent=1)
    return done


if __name__ == '__main__':
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vd = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, 'prototype', 'assets', 'scene3', 'views')
    print('neon glow:', run(vd))
