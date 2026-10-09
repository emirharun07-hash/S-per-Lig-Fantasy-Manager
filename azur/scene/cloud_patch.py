"""AZUR round 4 in the cloud: the owner's PC is off, and rendering the whole room again would take about 50 hours on
this 4-core machine. So only what changed is rendered, and merged into the round 3 plates the PC made:

  regions   compare the round 3 scene (.cache/azur_room_scene3_r3cloud.blend) with the new one, object by object
            (moved, added, gone, or a different time of day), and frame what changed in every view
  day       the day passes inside those frames, merged where they really differ (feathered, in code space, same scale)
  neon      the sign's own pass again with more samples (the grain the owner saw), merged over the old one
  state     the time-of-day patches (morning, evening, night) again, against the new day plates
  masks     hover outlines (cheap: flat colours), depth maps (cheap)

The jerseys are frozen (scene/frozen) and identical to the PC's, so they never count as changed. Every step writes into
prototype/assets/scene3 in place (originals backed up to .cache/r4/orig) and records itself in .cache/r4/done.json,
so a run that stops starts again where it was.

Usage:  python3 azur/scene/cloud_patch.py [step ...]      (default: all, in the order above)
Env:    AZUR_R4_SAMPLES=256  AZUR_R4_ONLY=room,bed (views)
"""
import os, sys, json, time, shutil
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq
from bpy_extras.object_utils import world_to_camera_view

R4 = os.path.join(rq.ROOT, '.cache', 'r4')
ORIG = os.path.join(R4, 'orig')
OLD_BLEND = os.path.join(rq.ROOT, '.cache', 'azur_room_scene3_r3cloud.blend')
SAMPLES = int(os.environ.get('AZUR_R4_SAMPLES', 128))      # with the denoiser; 4 cores, a night to finish
STATE_SAMPLES = {'morning': 64, 'evening': 64, 'night': 96}   # the night (the sleeper, the hall light) gets the most
SKIP_PASSES = ('ceiling',)       # azur-config.js daylight: the ceiling light is never on (its weight is 0 at every hour)
VIEWS = [v for v in ('room', 'bed', 'rail', 'rail_m') if not os.environ.get('AZUR_R4_ONLY') or v in os.environ['AZUR_R4_ONLY'].split(',')]
FROZEN = ('jersey_', 'hook', 'hanger', 'hall_light_area', 'sleeper_', 'L_')
DONE_PATH = os.path.join(R4, 'done.json')
os.makedirs(R4, exist_ok=True)


def log(*a):
    line = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(os.path.join(R4, 'patch.log'), 'a') as f: f.write(line + '\n')


def done(): return json.load(open(DONE_PATH)) if os.path.exists(DONE_PATH) else {}
def mark(k, v=True):
    d = done(); d[k] = v; json.dump(d, open(DONE_PATH, 'w'), indent=1)


def backup(path):
    rel = os.path.relpath(path, rq.OUT); dst = os.path.join(ORIG, rel)
    if os.path.exists(path) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(path, dst)


# ------------------------------------------------------------------------------------------------ what changed
def snapshot(blend):
    """Per object: day visibility and world bounding box corners; per view: its screen box (uv from the top-left)."""
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene; bpy.context.view_layer.update()
    objs = {}
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE', 'FONT', 'META') or o.name.startswith(FROZEN): continue
        if o.hide_render and not o.get('azur_state'): continue
        tags = str(o.get('azur_state', ''))
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        objs[o.name] = dict(tags=tags, day=rq.state_visible(o, 'day') and not o.hide_render,
                            corners=[tuple(round(x, 4) for x in c) for c in corners], screen={})
    for key in VIEWS:
        rq.set_view(sc, key); bpy.context.view_layer.update()
        for name, d in objs.items():
            pts = [world_to_camera_view(sc, sc.camera, Vector(c)) for c in d['corners']]
            pts = [p for p in pts if p.z > 0]
            if pts: d['screen'][key] = [min(p.x for p in pts), 1 - max(p.y for p in pts), max(p.x for p in pts), 1 - min(p.y for p in pts)]
    return objs


def step_regions():
    if 'regions' in done(): return
    old = snapshot(OLD_BLEND); new = snapshot(rq.BLEND)
    changed = []
    for n in set(old) | set(new):
        a, b = old.get(n), new.get(n)
        if a and b:
            moved = max(abs(x - y) for ca, cb in zip(a['corners'], b['corners']) for x, y in zip(ca, cb)) > 0.002
            if moved or a['day'] != b['day']: changed.append((n, a, b, 'moved' if moved else 'day'))
        elif (a or b)['day']:
            changed.append((n, a, b, 'gone' if a else 'new'))
    log('changed in the day plates:', ', '.join(f'{n} ({why})' for n, _, _, why in sorted(changed, key=lambda c: c[0])))
    regions = {}
    for key in VIEWS:
        boxes = []
        for n, a, b, why in changed:
            for d in (a, b):
                if d and d['day'] and key in d['screen']: boxes.append(d['screen'][key])
        boxes = [[max(0, u0 - 0.04), max(0, v0 - 0.05), min(1, u1 + 0.04), min(1, v1 + 0.08)] for u0, v0, u1, v1 in boxes
                 if u1 > 0 and v1 > 0 and u0 < 1 and v0 < 1]                 # margin: shadows and bounce light
        boxes = rq.merge_boxes(boxes, 0.02)
        regions[key] = boxes
        log('regions', key, [[round(x, 3) for x in b] for b in boxes], f'{sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes):.0%} of the picture')
    json.dump(dict(regions=regions, changed=[c[0] for c in changed]), open(os.path.join(R4, 'regions.json'), 'w'), indent=1)
    mark('regions')


# ------------------------------------------------------------------------------------------------ merging
def read_codes(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert('RGB')).copy()


def decode(codes, scale):
    y = np.minimum(np.power(codes.astype(np.float32) / 255.0, 2.2), 0.995)
    return (y / (1.0 - y)) / scale


def feather_mask(changed, box_px, edge=12, grow=6, soft=4.0):
    """0..1 weight for the new pixels: where they differ (grown, softened), fading out toward the region's inner edges
    (the denoiser saw less there, and outside the region there is nothing new). The frame's own border is no seam."""
    from scipy import ndimage as ndi
    X0, Y0, X1, Y1 = box_px; h, w = changed.shape
    m = ndi.gaussian_filter(ndi.binary_dilation(changed, iterations=grow).astype(np.float32), soft) if grow else changed.astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    big = 10 ** 6
    dist = np.minimum(np.minimum(xx - X0 if X0 > 0 else big, X1 - 1 - xx if X1 < w else big),
                      np.minimum(yy - Y0 if Y0 > 0 else big, Y1 - 1 - yy if Y1 < h else big))
    ramp = np.clip((dist - 2) / edge, 0, 1)
    inside = (xx >= X0) & (xx < X1) & (yy >= Y0) & (yy < Y1)
    return np.clip(m, 0, 1) * ramp * inside


def merge_into(dst, new_codes, box_px, threshold=2.5, whole=False):
    """Blend new codes into the plate at dst inside box_px; only where they differ by more than ~3 codes (whole: the
    entire region, faded at its edge). Returns the share of the region that changed."""
    from PIL import Image
    from scipy import ndimage as ndi
    backup(dst)
    old = read_codes(dst)
    X0, Y0, X1, Y1 = box_px
    d = np.abs(new_codes.astype(np.int16) - old.astype(np.int16)).max(-1).astype(np.float32)
    region = np.zeros(d.shape, bool); region[Y0:Y1, X0:X1] = True
    changed = (ndi.uniform_filter(d, 3) > threshold) & region if not whole else region
    w = feather_mask(changed, box_px, grow=0 if whole else 6)
    out = old.astype(np.float32) + w[..., None] * (new_codes.astype(np.float32) - old.astype(np.float32))
    return out, float(changed[Y0:Y1, X0:X1].mean())


def render_region(sc, box, path, samples):
    r = sc.render; r.use_border = True; r.use_crop_to_border = False
    r.border_min_x, r.border_max_x = box[0], box[2]; r.border_min_y, r.border_max_y = 1 - box[3], 1 - box[1]
    sc.cycles.samples = samples
    tmp = path.replace('.exr', '_tmp.exr'); secs = rq.render_to(sc, tmp); os.replace(tmp, path)
    r.use_border = False
    return secs


def px_box(box, rx, ry):
    return int(box[0] * rx), int(box[1] * ry), int(np.ceil(box[2] * rx)), int(np.ceil(box[3] * ry))


def step_day(sc, meta):
    regions = json.load(open(os.path.join(R4, 'regions.json')))['regions']
    for key in VIEWS:
        for p in [x for x in rq.PASSES if x not in SKIP_PASSES]:
            dst = os.path.join(rq.OUT, key, p + '.webp')
            if not os.path.exists(dst) or not regions.get(key): continue
            for i, box in enumerate(regions[key]):
                tag_ = f'day {key} {p} {i}'
                if tag_ in done(): continue
                rq.set_view(sc, key); rq.render_settings(sc, 'pass'); rq.restore_visibility(); rq.set_pass(sc, p)
                rx, ry = sc.render.resolution_x, sc.render.resolution_y
                exr = os.path.join(R4, 'exr', key, f'day_{p}_{i}.exr'); os.makedirs(os.path.dirname(exr), exist_ok=True)
                secs = render_region(sc, box, exr, SAMPLES)
                new = rq.encode_rgb(rq.read_exr(exr), meta[key][p])
                out, share = merge_into(dst, new, px_box(box, rx, ry))
                rq.save_webp((out + 0.5).astype(np.uint8), dst, rq.pass_quality(p))
                os.remove(exr)
                log('day', key, p, i, f'{secs}s', f'changed {share:.0%} of the region')
                mark(tag_)


def step_neon(sc, meta):
    """The sign again with more samples (512 against 128): its pass only, the sign's frame plus its glow on the wall."""
    for key in VIEWS:
        tag_ = f'neon {key}'
        if tag_ in done() or key == 'bed': continue
        rq.set_view(sc, key); bpy.context.view_layer.update()
        objs = [o for o in bpy.data.objects if o.name in ('neon', 'neon_plate')]
        box = rq.frame_box(sc, objs, 0.0)
        if box is None: mark(tag_); continue
        w, h = box[2] - box[0], box[3] - box[1]
        box = (max(0, box[0] - 0.6 * w), max(0, box[1] - 0.6 * h), min(1, box[2] + 0.6 * w), min(1, box[3] + 0.9 * h))
        rq.render_settings(sc, 'pass'); rq.restore_visibility(); rq.set_pass(sc, 'neon')
        sc.cycles.adaptive_threshold = 0.004
        rx, ry = sc.render.resolution_x, sc.render.resolution_y
        exr = os.path.join(R4, 'exr', key, 'neon.exr'); os.makedirs(os.path.dirname(exr), exist_ok=True)
        secs = render_region(sc, box, exr, int(os.environ.get('AZUR_R4_NEON_SAMPLES', 512)))
        dst = os.path.join(rq.OUT, key, 'neon.webp')
        new = rq.encode_rgb(rq.read_exr(exr), meta[key]['neon'])
        out, _ = merge_into(dst, new, px_box(box, rx, ry), whole=True)
        rq.save_webp((out + 0.5).astype(np.uint8), dst, rq.pass_quality('neon'))
        os.remove(exr)
        log('neon', key, f'{secs}s', [round(x, 3) for x in box])
        mark(tag_)


# passes worth patching per time of day (azur-config.js daylight: the lamp is off from 23:00, so not at night)
STATE_PASSES = {'morning': ['sky', 'sun_high', 'neon', 'spot', 'street'],
                'evening': ['sky', 'sun_low', 'sun_high', 'neon', 'lamp', 'spot', 'street'],
                'night': ['sky', 'neon', 'spot', 'street']}


def step_state(sc, meta, key, state):
    """Like render_queue.job_state, against the (new) day webp plates instead of linear day EXRs."""
    from scipy import ndimage as ndi
    tag_ = f'state {key} {state}'
    if tag_ in done(): return
    mpath = os.path.join(rq.OUT, 'passes.json')
    st = meta.setdefault('states', {}).setdefault(key, {})
    rq.set_view(sc, key); bpy.context.view_layer.update()
    rx, ry = sc.render.resolution_x, sc.render.resolution_y
    suns = [rq.SUN[p] for p in STATE_PASSES[state] if p in rq.SUN]
    objs = [o for o in rq.state_objects(state) if o.name != 'hall_light_area']
    hall = [o for o in rq.state_objects(state) if o.name == 'hall_light_area']
    box_o = rq.frame_box(sc, objs, 0.08, suns) if objs else None
    box_h = rq.frame_box(sc, objs + hall, 0.08, suns) if hall else box_o
    # old patches of this view and state go (their rectangles change)
    sdir = os.path.join(rq.OUT, key, state)
    if os.path.isdir(sdir):
        for f in os.listdir(sdir): backup(os.path.join(sdir, f)); os.remove(os.path.join(sdir, f))
    if box_h is None:
        st[state] = dict(rects=[], passes=[], res=[rx, ry], complete=True); json.dump(meta, open(mpath, 'w'), indent=1)
        log('state', key, state, 'nothing of it in the picture'); mark(tag_); return
    union = np.zeros((ry, rx), bool); renders = {}; secs_all = 0
    for p in STATE_PASSES[state]:
        box = box_h if p == 'street' else box_o
        if p == 'street' and hall: box = (0.0, 0.0, 1.0, 1.0)   # the hallway light reaches walls and floor everywhere
        if box is None: continue
        e = 10
        X0, X1 = int(box[0] * rx) + (e if box[0] > 0 else 0), int(np.ceil(box[2] * rx)) - (e if box[2] < 1 else 0)
        Y0, Y1 = int(box[1] * ry) + (e if box[1] > 0 else 0), int(np.ceil(box[3] * ry)) - (e if box[3] < 1 else 0)
        exr = os.path.join(R4, 'exr', key, f'{state}_{p}.exr'); os.makedirs(os.path.dirname(exr), exist_ok=True)
        if not os.path.exists(exr):
            rq.set_view(sc, key); rq.render_settings(sc, 'pass'); rq.restore_visibility(); rq.set_state(state); rq.set_pass(sc, p)
            secs_all += render_region(sc, box, exr, STATE_SAMPLES.get(state, SAMPLES))
        scale = meta[key][p]
        day = read_codes(os.path.join(rq.OUT, key, p + '.webp'))
        a = rq.encode_rgb(rq.read_exr(exr), scale)
        keep = np.ones((ry, rx), bool); keep[Y0:Y1, X0:X1] = False
        a[keep] = day[keep]
        d = np.abs(a.astype(np.int16) - day.astype(np.int16)).max(-1)
        d = ndi.uniform_filter(d.astype(np.float32), 3) > 2.5
        union |= d; renders[p] = (a, day)
    union = ndi.binary_opening(union, iterations=1)
    lab, n = ndi.label(ndi.binary_dilation(union, iterations=14))
    pad = 12
    boxes = [[max(0, s_[1].start - pad), max(0, s_[0].start - pad), min(rx, s_[1].stop + pad), min(ry, s_[0].stop + pad)]
             for s_ in ndi.find_objects(lab) if s_ is not None and (s_[1].stop - s_[1].start) * (s_[0].stop - s_[0].start) > 400]
    boxes = rq.merge_boxes(boxes, 24)
    while len(boxes) > 6: boxes = rq.merge_boxes(boxes, int(len(boxes) * 40))
    for p, (a, day) in renders.items():
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            rq.save_webp(a[y0:y1, x0:x1], os.path.join(sdir, f'{p}_{i}.webp'), rq.pass_quality(p))
    st[state] = dict(rects=boxes, passes=list(renders), res=[rx, ry], complete=True)
    json.dump(meta, open(mpath, 'w'), indent=1)
    for p in renders: os.remove(os.path.join(R4, 'exr', key, f'{state}_{p}.exr'))
    area = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes) / (rx * ry)
    log('state', key, state, len(boxes), f'patches, {area:.0%} of the picture,', round(secs_all), 's')
    mark(tag_)


def step_maps(sc):
    for key in VIEWS:
        for state in ('day', 'night'):
            tag_ = f'masks {key} {state}'
            if tag_ in done(): continue
            sfx = '' if state == 'day' else '_' + state
            for f in (f'masks{sfx}.png', f'glow{sfx}.png'):
                p_ = os.path.join(rq.OUT, key, f)
                if os.path.exists(p_): backup(p_); os.remove(p_)
            rq.job_masks(sc, key, state); log('masks', key, state); mark(tag_)
        tag_ = f'depth {key}'
        if tag_ not in done():
            p_ = os.path.join(rq.OUT, key, 'depth.png')
            if os.path.exists(p_): backup(p_); os.remove(p_)
            rq.job_depth(sc, key); log('depth', key); mark(tag_)          # (job_depth tidies it for the web)


def main():
    steps = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    steps = steps or ['regions', 'day', 'neon', 'state', 'maps']
    t0 = time.time()
    if 'regions' in steps: step_regions()
    sc = rq.open_scene()
    meta_path = os.path.join(rq.OUT, 'passes.json'); meta = json.load(open(meta_path))
    if 'day' in steps: step_day(sc, meta)
    if 'neon' in steps: step_neon(sc, meta)
    if 'state' in steps:
        for key in VIEWS:
            for state in ('morning', 'evening', 'night'): step_state(sc, meta, key, state)
    if 'maps' in steps: step_maps(sc)
    log('finished', steps, round(time.time() - t0), 's')


if __name__ == '__main__':
    main()
