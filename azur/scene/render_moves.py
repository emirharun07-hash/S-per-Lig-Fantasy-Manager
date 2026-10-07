"""AZUR camera moves: pre-rendered flights between views, replacing the prototype's fake pans.

Renders room -> rail and room -> bed as image sequences (the way back plays them reversed).
The garments are left out of the frames: the prototype's own garment layer flies along, placed per frame from the
projected hanger positions and the drop bag's box stored in moves.json (so they look the same before, during and
after the move).
Two light variants per move: 'day' (the approved golden-hour look, graded toward the clock in the browser)
and 'night' (the 22:30 mix of the light passes: night sky, neon, desk lamp, street light). The browser
crossfades them by how dark it is. Day frames of every move render first, so a usable set exists early.

Usage:  python3 azur/scene/render_moves.py              (all moves, resumable)
        python3 azur/scene/render_moves.py room-rail    (one move)
Env:    AZUR_MOVES_FRAMES=36  AZUR_MOVES_SAMPLES=48  AZUR_MOVES_RES=1280x720  AZUR_MOVES_OUT=<dir> (tests)
Rough cost on this 4-core CPU: ~1.5 min per frame, so 36 frames ~ 1 h per move and variant.
"""
import os, sys, json, math, time
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq   # reuses scene loading, views, light setup and git saving

FRAMES = int(os.environ.get('AZUR_MOVES_FRAMES', 36))
SAMPLES = int(os.environ.get('AZUR_MOVES_SAMPLES', 48))
RES = tuple(int(x) for x in os.environ.get('AZUR_MOVES_RES', '1280x720').split('x'))
OUT = os.environ.get('AZUR_MOVES_OUT') or os.path.join(rq.ROOT, 'prototype', 'assets', 'moves')
MOVES = {
    'room-rail': dict(a='room', b='rail', lift=0.18),     # the camera rises a little mid-flight, like a person stepping in
    'room-bed':  dict(a='room', b='bed', lift=0.08),
}


def ease(t):          # smooth start and stop
    return t * t * t * (t * (6 * t - 15) + 10)


def camera_at(a, b, t, lift):
    A, B = rq.VIEWS[a], rq.VIEWS[b]
    e = ease(t)
    loc = Vector(A['loc']).lerp(Vector(B['loc']), e) + Vector((0, 0, lift * math.sin(math.pi * e)))
    tgt = Vector(A['target']).lerp(Vector(B['target']), ease(min(1, t * 1.15)))   # the eye leads the body slightly
    lens = A['lens'] + (B['lens'] - A['lens']) * e
    return loc, tgt, lens


def srgb2lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


GLOW = [srgb2lin(int('16B8FF'[i:i + 2], 16) / 255) for i in (0, 2, 4)]   # palette A glow, as the browser mixes the neon pass


def light_variant(sc, variant):
    """Same light rig as render_queue's passes, mixed with the prototype's daylight weights."""
    rq.render_settings(sc, 'beauty'); rq.lights_off(sc)
    sc.cycles.samples = SAMPLES; sc.cycles.adaptive_threshold = 0.04
    bg = sc.world.node_tree.nodes['Background'].inputs['Strength']
    nb = bpy.data.materials['neon_tube'].node_tree.nodes['Principled BSDF']
    if variant == 'day':          # golden hour, the approved stills
        bg.default_value = 2.2; rq.world_tint(sc, (1.0, 0.86, 0.72))
        s = bpy.data.objects['sun']; s.hide_render = False; s.data.energy = 3.0; s.data.color = (1.0, 0.60, 0.33)
        s.rotation_euler = Vector(rq.SUN['sun_low']).normalized().to_track_quat('-Z', 'Y').to_euler()
        nb.inputs['Emission Color'].default_value = (0.086, 0.722, 1.0, 1); nb.inputs['Emission Strength'].default_value = 1.6
        sc.view_settings.exposure = 2.65
    else:                         # azur-config.js daylight key h 22.3
        bg.default_value = 2.2; rq.world_tint(sc, (0.04, 0.055, 0.11))
        nb.inputs['Emission Color'].default_value = (*[g * 1.05 for g in GLOW], 1); nb.inputs['Emission Strength'].default_value = 1.6
        L = bpy.data.objects['L_lamp']; L.hide_render = False; L.data.energy = 18.0 * 0.85; L.data.color = (1.0, 0.62, 0.32)
        S = bpy.data.objects['L_street']; S.hide_render = False; S.data.energy = 2600.0 * 0.7; S.data.color = (1.0, 0.7, 0.38)
        sc.view_settings.exposure = 3.2


def drop_objects():
    """The covered drop garment: bag, tag, string, zip and its own hanger and hook."""
    bag_x = bpy.data.objects['drop_bag'].matrix_world.translation.x
    keep = ('drop_', 'tag', 'tagtext', 'string', 'zip')
    return [o for o in rq.garments() if o.name.startswith(keep) or (o.name.startswith(('hanger', 'hook')) and abs(o.matrix_world.translation.x - bag_x) < 0.05)]


def drop_box(sc, cam, objs):
    from bpy_extras.object_utils import world_to_camera_view
    pts = [world_to_camera_view(sc, cam, o.matrix_world @ Vector(c)) for o in objs for c in o.bound_box]
    xs = [p.x for p in pts]; ys = [1 - p.y for p in pts]
    return [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]


def render_move(sc, name, spec, variant):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    prefix = 'f' if variant == 'day' else 'n'
    light_variant(sc, variant)
    drops = [o for o in drop_objects() if not rq.BASE_HIDE.get(o.name)]
    for o in rq.garments(): o.hide_render = True
    sc.render.resolution_x, sc.render.resolution_y = RES
    cam = sc.camera; cd = cam.data; cd.sensor_fit = 'AUTO'; cd.sensor_width = 36
    saved = []; track = []
    for i in range(FRAMES):
        dst = os.path.join(d, f'{prefix}{i:03d}.webp')
        t = i / (FRAMES - 1)
        loc, tgt, lens = camera_at(spec['a'], spec['b'], t, spec['lift'])
        cam.location = loc; cd.lens = lens
        cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
        cd.dof.focus_distance = (Vector((1.55, 2.95, 1.2)) - loc).length
        bpy.context.view_layer.update()
        slots, neon = rq.project_slots(sc, cam); track.append(dict(slots=slots, neon=neon, drop=drop_box(sc, cam, drops)))
        if os.path.exists(dst): continue
        png = dst.replace('.webp', '.png'); secs = rq.render_to(sc, png); rq.to_webp(png, dst, q=80)
        rq.log('move', name, variant, i, secs, 's'); saved.append(dst)
        if len(saved) >= 6:                     # commit in small batches
            rq.git_save(saved, f'AZUR move {name} ({variant}): frames up to {i}'); saved = []
    meta = os.path.join(OUT, 'moves.json')
    m = json.load(open(meta)) if os.path.exists(meta) else {}
    e = m.setdefault(name, {})
    e.update(from_=spec['a'], to=spec['b'], frames=FRAMES, fps=30, res=list(RES), track=track)
    e['variants'] = sorted(set(e.get('variants', [])) | {variant})
    json.dump(m, open(meta, 'w'), indent=1)
    rq.git_save(saved + [meta], f'AZUR move {name} ({variant}): complete')


def main():
    rq.ensure_blend()
    sc = rq.open_scene()
    names = [n for n in MOVES if not rq.ONLY or n in rq.ONLY]
    for variant in ('day', 'night'):
        for n in names:
            rq.restore_visibility()
            render_move(sc, n, MOVES[n], variant)
    rq.log('moves finished')


if __name__ == '__main__':
    main()
