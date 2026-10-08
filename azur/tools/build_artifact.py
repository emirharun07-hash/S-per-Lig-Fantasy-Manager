"""Assemble the prototype for publishing as a Claude Artifact: one page plus its files, within the file limits.

An artifact version holds at most 511 files, and camera moves are hundreds of frames. This packs each move's frames
into a few vertical strips (moves.json gets "atlas": {"per": n}; azur-app.js reads both layouts) and copies only
the scene set the page uses. scene3: every light pass also gets a half-size copy (views/<view>/lo/, passes.json
"_lo": true): the page starts on those and swaps in the full plates once it runs.

    python3 azur/tools/build_artifact.py            -> azur/.cache/publish/ (+ files.json: published path -> source)
Env: AZUR_SET=scene3 (default)
"""
import json, os, shutil, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'prototype')
OUT = os.path.join(ROOT, '.cache', 'publish')
SET = os.environ.get('AZUR_SET', 'scene3')
PRE = {'day': 'f', 'night': 'n', 'evening': 'e'}     # frame file prefix per light variant (render_moves.py)
PASS_FILES = ('sky', 'sun_low', 'sun_high', 'neon', 'lamp', 'ceiling', 'street', 'spot')
MAX_STRIP_PX = 6400          # tall enough for few files, small enough to decode on a phone
QUALITY = 86


def copy(rel):
    dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(SRC, rel), dst)


def pack_moves(set_dir):
    src = os.path.join(SRC, set_dir, 'moves'); mpath = os.path.join(src, 'moves.json')
    if not os.path.exists(mpath): return
    moves = json.load(open(mpath)); out = {}
    for name, m in moves.items():
        n = m['frames']; variants = m.get('variants', ['day'])
        frames = {v: [os.path.join(src, name, f"{PRE[v]}{i:03d}.webp") for i in range(n)] for v in variants}
        if not all(os.path.exists(f) for fs in frames.values() for f in fs):
            print('skip (frames missing):', name); continue
        w, h = Image.open(frames[variants[0]][0]).size
        per = max(1, min(n, MAX_STRIP_PX // h))
        for v, fs in frames.items():
            pre = PRE[v]
            for s in range(0, n, per):
                chunk = fs[s:s + per]; strip = Image.new('RGB', (w, h * len(chunk)))
                for j, f in enumerate(chunk): strip.paste(Image.open(f).convert('RGB'), (0, j * h))
                dst = os.path.join(OUT, set_dir, 'moves', name, f'{pre}_s{s // per}.webp'); os.makedirs(os.path.dirname(dst), exist_ok=True)
                strip.save(dst, quality=QUALITY, method=5)
        out[name] = dict(m, atlas=dict(per=per))
    dst = os.path.join(OUT, set_dir, 'moves', 'moves.json'); os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, 'w'))


def low_copies(views_rel, width=1200, q=88):
    """Half-size copies of the light passes (the first thing a visitor downloads) and the "_lo" flag in passes.json."""
    vdir = os.path.join(OUT, views_rel); mpath = os.path.join(vdir, 'passes.json')
    if not os.path.exists(mpath): return 0
    meta = json.load(open(mpath)); n = 0
    for key in os.listdir(vdir):
        d = os.path.join(vdir, key)
        if not os.path.isdir(d) or '@' in key: continue
        for p in PASS_FILES:
            f = os.path.join(d, p + '.webp')
            if not os.path.exists(f): continue
            im = Image.open(f)
            if im.width <= width: continue
            lo = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            os.makedirs(os.path.join(d, 'lo'), exist_ok=True); lo.save(os.path.join(d, 'lo', p + '.webp'), quality=q, method=6); n += 1
    if n: meta['_lo'] = True; json.dump(meta, open(mpath, 'w'))
    return n


def main():
    if SET not in ('scene1', 'scene2'):          # never package a set the PC is still filling in
        sys.path.insert(0, HERE); import assets_check
        assets_check.require_complete(os.path.join(SRC, 'assets', SET), 'artifact')
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    copy('index.html')
    for d in ('js', 'css', 'assets/products', 'assets/brand', 'assets/mag', f'assets/{SET}/views', f'assets/{SET}/models', 'assets/scene2/outside'):
        for dp, _, fs in os.walk(os.path.join(SRC, d)):
            for f in fs:
                if f.endswith(('.png', '.webp', '.jpg', '.json', '.js', '.css', '.mp4', '.webm', '.glb')):
                    copy(os.path.relpath(os.path.join(dp, f), SRC))
    pack_moves(f'assets/{SET}')
    # artifacts do not serve .glb: the models go base64-wrapped in JSON, the page is told so
    import base64
    mdir = os.path.join(OUT, f'assets/{SET}/models')
    if os.path.isdir(mdir):
        for f in [f for f in os.listdir(mdir) if f.endswith('.glb')]:
            src = os.path.join(mdir, f)
            json.dump({'glb': base64.b64encode(open(src, 'rb').read()).decode()}, open(src + '.json', 'w')); os.remove(src)
        cfg = os.path.join(OUT, 'js', 'azur-config.js'); t = open(cfg).read()
        assert "modelExt: 'glb'," in t
        open(cfg, 'w').write(t.replace("modelExt: 'glb',", "modelExt: 'glb.json',", 1))
    if SET not in ('scene1', 'scene2'): print('low-resolution copies:', low_copies(f'assets/{SET}/views'))
    files = {}
    for dp, _, fs in os.walk(OUT):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), OUT)
            if rel not in ('index.html', 'files.json'): files[rel] = os.path.join(OUT, rel)
    json.dump(files, open(os.path.join(OUT, 'files.json'), 'w'), indent=0)
    size = sum(os.path.getsize(p) for p in files.values())
    print(f'{len(files)} files, {size / 1e6:.1f} MB -> {OUT}')


if __name__ == '__main__':
    main()
