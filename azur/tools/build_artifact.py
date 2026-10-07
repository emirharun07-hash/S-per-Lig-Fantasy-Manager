"""Assemble the prototype for publishing as a Claude Artifact: one page plus its files, within the file limits.

An artifact version holds at most 511 files, and camera moves are hundreds of frames. This packs each move's frames
into a few vertical strips (moves.json gets "atlas": {"per": n}; azur-app.js reads both layouts) and copies only
the scene set the page uses.

    python3 azur/tools/build_artifact.py            -> azur/.cache/publish/ (+ files.json: published path -> source)
Env: AZUR_SET=scene2 (default)
"""
import json, os, shutil, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'prototype')
OUT = os.path.join(ROOT, '.cache', 'publish')
SET = os.environ.get('AZUR_SET', 'scene2')
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
        frames = {v: [os.path.join(src, name, f"{'n' if v == 'night' else 'f'}{i:03d}.webp") for i in range(n)] for v in variants}
        if not all(os.path.exists(f) for fs in frames.values() for f in fs):
            print('skip (frames missing):', name); continue
        w, h = Image.open(frames[variants[0]][0]).size
        per = max(1, min(n, MAX_STRIP_PX // h))
        for v, fs in frames.items():
            pre = 'n' if v == 'night' else 'f'
            for s in range(0, n, per):
                chunk = fs[s:s + per]; strip = Image.new('RGB', (w, h * len(chunk)))
                for j, f in enumerate(chunk): strip.paste(Image.open(f).convert('RGB'), (0, j * h))
                dst = os.path.join(OUT, set_dir, 'moves', name, f'{pre}_s{s // per}.webp'); os.makedirs(os.path.dirname(dst), exist_ok=True)
                strip.save(dst, quality=QUALITY, method=5)
        out[name] = dict(m, atlas=dict(per=per))
    dst = os.path.join(OUT, set_dir, 'moves', 'moves.json'); os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, 'w'))


def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(OUT)
    copy('index.html')
    for d in ('js', 'css', 'assets/products', 'assets/brand', 'assets/mag', f'assets/{SET}/views', f'assets/{SET}/outside'):
        for dp, _, fs in os.walk(os.path.join(SRC, d)):
            for f in fs:
                if f.endswith(('.png', '.webp', '.jpg', '.json', '.js', '.css', '.mp4', '.webm')):
                    copy(os.path.relpath(os.path.join(dp, f), SRC))
    pack_moves(f'assets/{SET}')
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
