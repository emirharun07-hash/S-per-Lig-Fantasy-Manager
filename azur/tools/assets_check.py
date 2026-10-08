"""Is a scene set complete enough to publish?

While the PC renders a rebuilt scene, the branch holds a half-filled set for hours (render_step.ps1 removes the old
outputs first). build_artifact.py and build_theme.py call `require_complete()` so a page built in that window is never
published with missing views: they stop with the list of what is missing. AZUR_ALLOW_PARTIAL=1 builds anyway.
"""
import json, os, sys

PASS_FILES = ('sky', 'sun_low', 'sun_high', 'neon', 'lamp', 'ceiling', 'street', 'spot')
MODELS = ('frankfurt', 'berlin', 'brasilien', 'deutschland', 'tuerkei')


def missing(set_dir):
    """What a scene3-style set lacks, as a list of short descriptions (empty: complete)."""
    out = []
    vdir = os.path.join(set_dir, 'views')
    try:
        views = [k for k, v in json.load(open(os.path.join(vdir, 'views.json'))).items() if isinstance(v, dict) and '@' not in k]
    except (OSError, ValueError):
        return ['views/views.json']
    try:
        passes = json.load(open(os.path.join(vdir, 'passes.json')))
    except (OSError, ValueError):
        return ['views/passes.json']
    for v in views:
        d = os.path.join(vdir, v)
        need = [p + '.webp' for p in PASS_FILES] + ['depth.png', 'masks.png', 'glow.png'] + ([] if v == 'bed' else ['ids.png', 'window.png'])
        gone = [f for f in need if not os.path.exists(os.path.join(d, f))]
        if gone: out.append(f'views/{v}: ' + ', '.join(gone))
        if set(PASS_FILES) - set((passes.get(v) or {}).keys()): out.append(f'passes.json: {v} incomplete')
    mdir = os.path.join(set_dir, 'models')
    gone = [m for m in MODELS if not os.path.exists(os.path.join(mdir, m + '.glb'))]
    if gone: out.append('models: ' + ', '.join(gone))
    return out


def require_complete(set_dir, what='publish'):
    m = missing(set_dir)
    if not m: return
    print(f'{os.path.basename(set_dir)} is not complete (the PC may still be rendering); not building the {what}:')
    for x in m: print('  -', x)
    if os.environ.get('AZUR_ALLOW_PARTIAL'):
        print('AZUR_ALLOW_PARTIAL is set: building anyway'); return
    sys.exit(2)


if __name__ == '__main__':
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    s = os.path.join(here, 'prototype', 'assets', os.environ.get('AZUR_SET', 'scene3'))
    m = missing(s); print('complete' if not m else '\n'.join(m)); sys.exit(1 if m else 0)
