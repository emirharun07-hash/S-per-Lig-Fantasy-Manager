"""AZUR render queue: plates, light passes, depth maps, sprites and projections for the prototype.

Runs unattended and is safe to restart: every job is skipped when its output already exists,
and every finished output is committed and pushed so nothing is lost if the machine goes away.

Usage:  python3 azur/scene/render_queue.py            (all jobs)
        python3 azur/scene/render_queue.py rail       (only jobs for one view)
Env:    AZUR_QUEUE_NO_GIT=1   skip commits (local testing)
        AZUR_QUEUE_FAST=1     tiny resolution and samples (pipeline test)
"""
import bpy, os, sys, json, math, time, subprocess
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
OUT = os.path.join(ROOT, 'prototype', 'assets', 'views')
BLEND = os.path.join(ROOT, '.cache', 'azur_room.blend')
LOG = os.path.join(ROOT, '.cache', 'queue.log')
FAST = bool(os.environ.get('AZUR_QUEUE_FAST'))
if FAST: OUT = os.path.join(ROOT, '.cache', 'queue_test')
NO_GIT = bool(os.environ.get('AZUR_QUEUE_NO_GIT'))
ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

# ------------------------------------------------------------------ views (camera presets the prototype moves between)
VIEWS = {
    # establishing shot: high in the front-left corner, the whole room
    'room':   dict(loc=(0.24, 0.22, 2.06), target=(1.85, 3.15, 0.78), lens=19, res=(1600, 900)),
    # the rail: centred, closer and a little higher than the first stills
    'rail':   dict(loc=(1.72, 0.70, 1.40), target=(1.85, 3.60, 1.18), lens=24, res=(1600, 900)),
    # the bed (easter egg, content decided later)
    'bed':    dict(loc=(1.55, 0.35, 1.35), target=(0.45, 1.50, 0.48), lens=26, res=(1600, 900)),
    # phones start at the rail; the plate is wider than a phone so the visitor can swipe along it
    'rail_m': dict(loc=(1.55, 1.15, 1.30), target=(1.55, 3.40, 1.12), lens=20, res=(1440, 1600), fit='VERTICAL', sensor=24),
}
# light passes: each rendered alone, white light, mixed and tinted in the browser
PASSES = ['sky', 'sun_low', 'sun_high', 'neon', 'lamp', 'ceiling', 'street']
SUN = {'sun_low': (-1.0, 0.22, -0.12), 'sun_high': (-1.0, 0.12, -0.78)}
DEPTH_NEAR, DEPTH_FAR = 0.4, 6.5   # metres; depth.png stores near=white, far=black (sRGB-encoded)
GARMENT_PREFIX = ('jersey_', 'drop_', 'hanger', 'hook', 'tag', 'tagtext', 'string', 'zip')


def log(*a):
    msg = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
    print(msg, flush=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f: f.write(msg + '\n')


def git_save(paths, message):
    if NO_GIT: return
    rel = [os.path.relpath(p, REPO) for p in paths if os.path.exists(p)]
    for attempt in range(6):
        try:
            subprocess.run(['git', '-C', REPO, 'add', '--'] + rel, check=True, capture_output=True)
            r = subprocess.run(['git', '-C', REPO, 'commit', '-m', message + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01R3wWJYBEPWenzksQTM89FE', '--'] + rel,
                               capture_output=True, text=True)
            if r.returncode not in (0, 1): raise RuntimeError(r.stderr)
            subprocess.run(['git', '-C', REPO, 'pull', '--rebase', '-q', 'origin', 'claude/shopify-notification-signup-o5avym'], capture_output=True)
            subprocess.run(['git', '-C', REPO, 'push', '-q', 'origin', 'HEAD:claude/shopify-notification-signup-o5avym'], check=True, capture_output=True)
            return
        except Exception as e:
            log('git retry', attempt, e)
            time.sleep(2 ** attempt * 3)


# ------------------------------------------------------------------ scene
def ensure_blend():
    if os.path.exists(BLEND): return
    log('building scene (no saved .blend found)')
    if not os.path.isdir(os.path.join(ROOT, '.cache', 'ph')):
        subprocess.run([sys.executable, os.path.join(HERE, 'fetch_assets.py')], check=True)
    env = dict(os.environ, AZUR_BUILD_ONLY='1')
    subprocess.run([sys.executable, os.path.join(HERE, 'build_room.py'), '--', 'preview', '/dev/null', BLEND], check=True, env=env)


def open_scene():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    sc.cycles.device = 'CPU'
    W = 3.4; H = 2.5
    # extra light sources for the night passes (kept out of the geometry builder)
    def point(name, loc, power, radius):
        if name in bpy.data.objects: return bpy.data.objects[name]
        L = bpy.data.lights.new(name, 'POINT'); L.energy = power; L.shadow_soft_size = radius
        o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = loc; return o
    lamp_pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' and 'desk_lamp' in o.name for c in o.bound_box]
    if lamp_pts:
        top = max(lamp_pts, key=lambda p: p.z)
        point('L_lamp', (top.x, top.y, top.z - 0.09), 18.0, 0.02)
    point('L_street', (W + 3.2, 2.75, 3.3), 2600.0, 0.25)
    # opal ceiling light emits only in its own pass
    cm = bpy.data.objects['ceiling_light'].data.materials[0]
    cm.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1, 1, 1, 1)
    global BASE_HIDE
    BASE_HIDE = {o.name: o.hide_render for o in bpy.data.objects}
    return sc


def restore_visibility():
    for o in bpy.data.objects:
        if o.name in BASE_HIDE: o.hide_render = BASE_HIDE[o.name]
        o.is_holdout = False


def garments(): return [o for o in bpy.data.objects if o.name.startswith(GARMENT_PREFIX)]


def set_view(sc, key):
    v = VIEWS[key]; cam = sc.camera; cd = cam.data
    cam.location = v['loc']; cd.lens = v['lens']
    cam.rotation_euler = (Vector(v['target']) - Vector(v['loc'])).to_track_quat('-Z', 'Y').to_euler()
    cd.sensor_fit = v.get('fit', 'AUTO')
    if 'sensor' in v: cd.sensor_height = v['sensor']
    else: cd.sensor_width = 36
    cd.dof.focus_distance = (Vector((1.55, 2.95, 1.2)) - Vector(v['loc'])).length
    rx, ry = v['res']
    if FAST: rx, ry = rx // 5, ry // 5
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100


def lights_off(sc):
    w = sc.world.node_tree.nodes
    w['Background'].inputs['Strength'].default_value = 0.0
    bpy.data.objects['sun'].hide_render = True
    for n in ('L_lamp', 'L_street'):
        if n in bpy.data.objects: bpy.data.objects[n].hide_render = True
    bpy.data.materials['neon_tube'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0
    bpy.data.objects['ceiling_light'].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.0


def world_tint(sc, rgb):
    for n in sc.world.node_tree.nodes:
        if n.type == 'MIX': n.inputs[7].default_value = (*rgb, 1)


def set_pass(sc, p):
    lights_off(sc)
    if p == 'sky':
        sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 2.2; world_tint(sc, (1, 1, 1))
    elif p in SUN:
        s = bpy.data.objects['sun']; s.hide_render = False; s.data.color = (1, 1, 1); s.data.energy = 3.0
        s.rotation_euler = Vector(SUN[p]).normalized().to_track_quat('-Z', 'Y').to_euler()
    elif p == 'neon':
        b = bpy.data.materials['neon_tube'].node_tree.nodes['Principled BSDF']
        b.inputs['Emission Color'].default_value = (1, 1, 1, 1); b.inputs['Emission Strength'].default_value = 1.6
    elif p == 'lamp':
        bpy.data.objects['L_lamp'].hide_render = False
    elif p == 'ceiling':
        bpy.data.objects['ceiling_light'].data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 30.0
    elif p == 'street':
        bpy.data.objects['L_street'].hide_render = False; bpy.data.objects['L_street'].data.color = (1, 1, 1)


def render_settings(sc, kind):
    cy = sc.cycles; r = sc.render
    r.film_transparent = False
    sc.view_layers[0].material_override = None
    cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.adaptive_threshold = 0.02
    cy.samples = 8 if FAST else {'beauty': 224, 'pass': 192, 'depth': 4, 'sprite': 128}[kind]
    if kind == 'depth': cy.use_denoising = False
    if kind in ('pass', 'depth'):
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0
    else:
        sc.view_settings.view_transform = 'AgX'
        try: sc.view_settings.look = 'AgX - Medium High Contrast'
        except Exception: pass
        sc.view_settings.exposure = 2.65
    s = r.image_settings
    if kind == 'pass':
        s.file_format = 'OPEN_EXR'; s.color_depth = '16'; s.exr_codec = 'ZIP'
    else:
        s.file_format = 'PNG'; s.color_mode = 'RGBA' if kind == 'sprite' else 'RGB'; s.color_depth = '8'


def render_to(sc, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    t = time.time(); bpy.ops.render.render(write_still=True)
    return round(time.time() - t, 1)


def to_webp(src_png, dst, q=86):
    from PIL import Image
    im = Image.open(src_png); im.save(dst, 'WEBP', quality=q, method=6); os.remove(src_png)


def encode_pass(exr, dst):
    """Linear EXR -> 8-bit WebP with a Reinhard curve; the browser undoes it: lin = (y / (1 - y)) / scale, y = enc^2.2."""
    from PIL import Image
    img = bpy.data.images.load(exr); w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    rgb = px.reshape(h, w, 4)[::-1, :, :3]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    ref = float(np.percentile(lum, 97))
    scale = 0.5 / max(ref, 1e-6)
    x = np.clip(rgb * scale, 0, None)
    enc = np.power(x / (1.0 + x), 1 / 2.2)
    Image.fromarray(np.clip(enc * 255 + 0.5, 0, 255).astype(np.uint8)).save(dst, 'WEBP', quality=90, method=6)
    os.remove(exr)
    return scale


# ------------------------------------------------------------------ jobs
def job_projections(sc):
    """Screen positions of the hangers, rail, window, bed and neon for every view (u, v from top-left, 0..1)."""
    path = os.path.join(OUT, 'views.json')
    data = json.load(open(path)) if os.path.exists(path) else {}
    hooks = sorted([o for o in bpy.data.objects if o.name.startswith('hook')], key=lambda o: o.matrix_world.translation.x)
    rail = bpy.data.objects['bar']; rp = [rail.matrix_world @ Vector(c) for c in rail.bound_box]
    glass = bpy.data.objects['glass']; gp = [glass.matrix_world @ Vector(c) for c in glass.bound_box]
    matt = bpy.data.objects['mattress']; mp = [matt.matrix_world @ Vector(c) for c in matt.bound_box]
    neon = bpy.data.objects['neon_plate']; npt = [neon.matrix_world @ Vector(c) for c in neon.bound_box]
    for key in VIEWS:
        set_view(sc, key); bpy.context.view_layer.update(); cam = sc.camera
        def uv(p):
            c = world_to_camera_view(sc, cam, Vector(p)); return [round(c.x, 4), round(1 - c.y, 4), round(c.z, 3)]
        slots = []
        for h in hooks:
            top = h.matrix_world.translation + Vector((0, -0.018, 0.072))   # where the hook sits on the bar
            garment_top = h.matrix_world.translation + Vector((0, 0, -0.008))
            bottom = garment_top + Vector((0, 0, -0.74))
            a, b, t = uv(garment_top), uv(bottom), uv(top)
            left, right = uv(garment_top + Vector((-0.35, 0, 0))), uv(garment_top + Vector((0.35, 0, 0)))
            slots.append(dict(hook=t[:2], top=a[:2], bottom=b[:2], width=round(right[0] - left[0], 4), depth=a[2]))
        xs = [p.x for p in rp]; ys = [p.y for p in rp]; zs = [p.z for p in rp]
        cy, cz = sum(ys) / 8, sum(zs) / 8
        bed = [uv((x, y, 0.55)) for x, y in ((0.02, -0.25), (0.98, -0.25), (0.98, 2.03), (0.02, 2.03))]
        data[key] = dict(
            res=list(VIEWS[key]['res']), slots=slots,
            rail=[uv((min(xs), cy, cz))[:2], uv((max(xs), cy, cz))[:2]],
            window=[uv((min(p.x for p in gp), y, z))[:2] for y, z in ((min(p.y for p in gp), max(p.z for p in gp)), (max(p.y for p in gp), max(p.z for p in gp)),
                                                                      (max(p.y for p in gp), min(p.z for p in gp)), (min(p.y for p in gp), min(p.z for p in gp)))],
            bed=[b[:2] for b in bed],
            neon=uv((sum(p.x for p in npt) / 8, min(p.y for p in npt), sum(p.z for p in npt) / 8))[:2],
            floor_under_rail=uv(((min(xs) + max(xs)) / 2, cy, 0.0))[:2],
        )
    os.makedirs(OUT, exist_ok=True)
    json.dump(data, open(path, 'w'), indent=1)
    return [path]


def job_beauty(sc, key):
    dst = os.path.join(OUT, key, 'beauty.webp')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'beauty'); lights_off(sc)
    # the golden-hour look of the approved stills
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 2.2; world_tint(sc, (1.0, 0.86, 0.72))
    s = bpy.data.objects['sun']; s.hide_render = False; s.data.energy = 3.0; s.data.color = (1.0, 0.60, 0.33)
    s.rotation_euler = Vector(SUN['sun_low']).normalized().to_track_quat('-Z', 'Y').to_euler()
    b = bpy.data.materials['neon_tube'].node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (0.086, 0.722, 1.0, 1); b.inputs['Emission Strength'].default_value = 1.6
    for o in garments(): o.hide_render = True
    secs = render_to(sc, dst.replace('.webp', '.png')); to_webp(dst.replace('.webp', '.png'), dst)
    log('beauty', key, secs, 's'); return [dst]


def job_depth(sc, key):
    dst = os.path.join(OUT, key, 'depth.png')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'depth'); lights_off(sc)
    for o in garments(): o.hide_render = True
    m = bpy.data.materials.get('azur_depth') or bpy.data.materials.new('azur_depth')
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    cdn = nt.nodes.new('ShaderNodeCameraData'); mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = DEPTH_NEAR; mr.inputs['From Max'].default_value = DEPTH_FAR
    mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0
    em = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(cdn.outputs['View Z Depth'], mr.inputs['Value']); nt.links.new(mr.outputs[0], em.inputs['Color']); nt.links.new(em.outputs[0], out.inputs['Surface'])
    sc.view_layers[0].material_override = m
    sc.render.image_settings.color_mode = 'BW'
    secs = render_to(sc, dst); sc.view_layers[0].material_override = None
    log('depth', key, secs, 's'); return [dst]


def job_pass(sc, key, p, meta):
    dst = os.path.join(OUT, key, p + '.webp')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'pass'); set_pass(sc, p)
    for o in garments(): o.hide_render = True
    exr = dst.replace('.webp', '.exr'); secs = render_to(sc, exr)
    meta.setdefault(key, {})[p] = encode_pass(exr, dst)
    mpath = os.path.join(OUT, 'passes.json'); json.dump(meta, open(mpath, 'w'), indent=1)
    log('pass', key, p, secs, 's'); return [dst, mpath]


def job_bag_sprite(sc, key):
    """The covered drop garment as its own layer, lit by the room's daylight (other objects are holdouts)."""
    dst = os.path.join(OUT, key, 'drop.webp')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'sprite'); set_pass(sc, 'sky')
    sc.render.film_transparent = True
    keep = ('drop_', 'tag', 'tagtext', 'string', 'zip')
    bag_x = bpy.data.objects['drop_bag'].matrix_world.translation.x
    held = []
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE', 'FONT', 'META'): continue
        is_drop = o.name.startswith(keep) or (o.name.startswith(('hanger', 'hook')) and abs(o.matrix_world.translation.x - bag_x) < 0.05)
        if BASE_HIDE.get(o.name): continue
        o.hide_render = False
        if not is_drop and not o.is_holdout: o.is_holdout = True; held.append(o)
        if o.name.startswith(('jersey_', 'hanger', 'hook')) and not is_drop: o.hide_render = True
    png = dst.replace('.webp', '.png'); secs = render_to(sc, png)
    for o in held: o.is_holdout = False
    from PIL import Image
    im = Image.open(png); bb = im.getchannel('A').point(lambda a: 255 if a > 6 else 0).getbbox()
    crop = im.crop(bb); crop.save(dst, 'WEBP', quality=88, method=6); os.remove(png)
    W_, H_ = im.size
    meta = os.path.join(OUT, 'sprites.json'); d = json.load(open(meta)) if os.path.exists(meta) else {}
    d.setdefault(key, {})['drop'] = dict(box=[bb[0] / W_, bb[1] / H_, bb[2] / W_, bb[3] / H_])
    json.dump(d, open(meta, 'w'), indent=1)
    log('drop sprite', key, secs, 's'); return [dst, meta]


def job_hanger_sprite(sc):
    dst = os.path.join(OUT, 'hanger.webp')
    if os.path.exists(dst): return None
    render_settings(sc, 'sprite'); set_pass(sc, 'sky'); sc.render.film_transparent = True
    hooks = sorted([o for o in bpy.data.objects if o.name.startswith('hook')], key=lambda o: o.matrix_world.translation.x)
    h0 = hooks[0]; x = h0.matrix_world.translation.x
    body = min([o for o in bpy.data.objects if o.name.startswith('hanger')], key=lambda o: abs(o.matrix_world.translation.x - x))
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE', 'FONT', 'META'): o.hide_render = o not in (h0, body)
    yaw = body.rotation_euler.z; body.rotation_euler.z = 0
    cam = sc.camera; cd = cam.data; cd.type = 'ORTHO'; cd.ortho_scale = 0.5; cd.dof.use_dof = False
    org = h0.matrix_world.translation
    cam.location = org + Vector((0, -1.5, 0.0)); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.render.resolution_x, sc.render.resolution_y = 800, 800
    png = dst.replace('.webp', '.png'); secs = render_to(sc, png)
    body.rotation_euler.z = yaw; cd.type = 'PERSP'; cd.dof.use_dof = True; restore_visibility()
    from PIL import Image
    im = Image.open(png); bb = im.getchannel('A').point(lambda a: 255 if a > 6 else 0).getbbox()
    # anchor: where the garment hangs (hook origin) in the cropped sprite, plus metres per pixel
    W_, H_ = im.size; mpp = 0.5 / W_
    ax, ay = W_ / 2 - bb[0], H_ / 2 - bb[1]
    im.crop(bb).save(dst, 'WEBP', quality=90, method=6); os.remove(png)
    meta = os.path.join(OUT, 'sprites.json'); d = json.load(open(meta)) if os.path.exists(meta) else {}
    d['hanger'] = dict(anchor=[ax, ay], size=[bb[2] - bb[0], bb[3] - bb[1]], metres_per_px=mpp)
    json.dump(d, open(meta, 'w'), indent=1)
    log('hanger sprite', secs, 's'); return [dst, meta]


def main():
    ensure_blend()
    sc = open_scene()
    meta_path = os.path.join(OUT, 'passes.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    views = [v for v in VIEWS if not ONLY or v in ONLY]
    jobs = [('projections', lambda: job_projections(sc))]
    jobs += [(f'beauty {v}', (lambda v=v: job_beauty(sc, v))) for v in views]
    jobs += [(f'depth {v}', (lambda v=v: job_depth(sc, v))) for v in views]
    jobs += [('hanger sprite', lambda: job_hanger_sprite(sc))]
    jobs += [(f'drop sprite {v}', (lambda v=v: job_bag_sprite(sc, v))) for v in views if v != 'bed']
    for v in [x for x in ('rail', 'room', 'rail_m', 'bed') if x in views]:
        jobs += [(f'pass {v} {p}', (lambda v=v, p=p: job_pass(sc, v, p, meta))) for p in PASSES]
    for name, fn in jobs:
        try:
            restore_visibility()
            out = fn()
            if out: git_save(out, f'AZUR render: {name}')
        except Exception as e:
            import traceback; log('FAILED', name, e); log(traceback.format_exc())
            sc = open_scene()
    log('queue finished')


if __name__ == '__main__':
    main()
