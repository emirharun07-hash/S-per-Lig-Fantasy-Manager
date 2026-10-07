"""AZUR camera moves: pre-rendered flights between views, replacing the prototype's fake pans.

Renders room -> rail and room -> bed as image sequences (the way back plays them reversed).
The garments are part of the frames (scene2: they are real 3D garments in the room). Each frame's projected hanger
positions are stored in moves.json (track) for labels. Pull moves take one garment off the rail toward the camera.
Two light variants per move: 'day' (the approved golden-hour look, graded toward the clock in the browser)
and 'night' (the 22:30 mix of the light passes: night sky, neon, desk lamp, street light). The browser
crossfades them by how dark it is. Day frames of every move render first, so a usable set exists early.

Usage:  python3 azur/scene/render_moves.py              (all moves, resumable)
        python3 azur/scene/render_moves.py room-rail    (one move)
Env:    AZUR_MOVES_FRAMES=36  AZUR_MOVES_SAMPLES=48  AZUR_MOVES_RES=1280x720  AZUR_MOVES_OUT=<dir> (tests)
Rough cost on this 4-core CPU: ~1.5 min per frame, so 36 frames ~ 1 h per move and variant.

scene3: no pull moves (a click opens the product view right away); three variants that match the times of day, each
with that state's objects: 'day' (midday light, also used in the morning), 'evening' (golden hour) and 'night'.
"""
import os, sys, json, math, time
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq   # reuses scene loading, views, light setup and git saving

FRAMES = int(os.environ.get('AZUR_MOVES_FRAMES', 36))
SAMPLES = int(os.environ.get('AZUR_MOVES_SAMPLES', 48))
RES = tuple(int(x) for x in os.environ.get('AZUR_MOVES_RES', '1600x900' if rq.HI else '1280x720').split('x'))
VARIANTS = ('day', 'evening', 'night') if rq.HI else ('day', 'night')
STATE_OF = {'day': 'day', 'evening': 'evening', 'night': 'night'}
OUT = os.environ.get('AZUR_MOVES_OUT') or os.path.join(rq.ROOT, 'prototype', 'assets', rq.SET, 'moves')
PULL_FRAMES = int(os.environ.get('AZUR_PULL_FRAMES', 14))
MOVES = {
    'room-rail': dict(a='room', b='rail', lift=0.18),     # the camera rises a little mid-flight, like a person stepping in
    'room-bed':  dict(a='room', b='bed', lift=0.08),
}
# a chosen garment is taken off the rail toward the camera (camera stays): 'rail-rail@2' = view rail to view rail@2
PULL_RES = {'rail': (1280, 720), 'rail_m': (720, 800)}
for _v in ('rail', 'rail_m') if not rq.HI else ():
    for _i in range(6):
        MOVES[f'{_v}-{_v}@{_i}'] = dict(a=_v, b=f'{_v}@{_i}', pull=(_v, _i))


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
    if variant == 'day' and rq.HI:        # azur-config.js daylight key h 12.5
        bg.default_value = 2.2; rq.world_tint(sc, (1.0, 1.0, 1.0))
        s = bpy.data.objects['sun']; s.hide_render = False; s.data.energy = 3.0 * 0.75; s.data.color = (1.0, 0.96, 0.88)
        s.rotation_euler = Vector(rq.SUN['sun_high']).normalized().to_track_quat('-Z', 'Y').to_euler()
        nb.inputs['Emission Color'].default_value = (*[g * 0.08 for g in GLOW], 1); nb.inputs['Emission Strength'].default_value = 1.6
        sc.view_settings.exposure = 2.65
        if 'L_spot' in bpy.data.objects:
            P = bpy.data.objects['L_spot']; P.hide_render = False; P.data.energy = 60.0 * 0.3; P.data.color = (1.0, 0.82, 0.62)
    elif variant in ('day', 'evening'):   # golden hour, the approved stills
        bg.default_value = 2.2; rq.world_tint(sc, (1.0, 0.86, 0.72))
        s = bpy.data.objects['sun']; s.hide_render = False; s.data.energy = 3.0; s.data.color = (1.0, 0.60, 0.33)
        s.rotation_euler = Vector(rq.SUN['sun_low']).normalized().to_track_quat('-Z', 'Y').to_euler()
        nb.inputs['Emission Color'].default_value = (0.086, 0.722, 1.0, 1); nb.inputs['Emission Strength'].default_value = 1.6
        sc.view_settings.exposure = 2.65
        if 'L_spot' in bpy.data.objects:
            P = bpy.data.objects['L_spot']; P.hide_render = False; P.data.energy = 60.0 * 0.35; P.data.color = (1.0, 0.82, 0.62)
    else:                         # azur-config.js daylight key h 22.3 (scene3: h 0, he is asleep, the desk lamp is off)
        bg.default_value = 2.2; rq.world_tint(sc, (0.012, 0.016, 0.034) if rq.HI else (0.04, 0.055, 0.11))
        nb.inputs['Emission Color'].default_value = (*[g * 1.05 for g in GLOW], 1); nb.inputs['Emission Strength'].default_value = 1.6
        L = bpy.data.objects['L_lamp']; L.hide_render = rq.HI; L.data.energy = 18.0 * 0.85; L.data.color = (1.0, 0.62, 0.32)
        S = bpy.data.objects['L_street']; S.hide_render = False; S.data.energy = 2600.0 * 0.3; S.data.color = (0.95, 0.84, 0.7)
        sc.view_settings.exposure = 3.0
        if 'L_spot' in bpy.data.objects:
            P = bpy.data.objects['L_spot']; P.hide_render = False; P.data.energy = 60.0 * (0.5 if rq.HI else 0.7); P.data.color = (1.0, 0.82, 0.62)


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
    prefix = {'day': 'f', 'night': 'n', 'evening': 'e'}[variant]
    light_variant(sc, variant)
    if rq.HI: rq.restore_visibility(); rq.set_state(STATE_OF[variant])
    drops = [o for o in drop_objects() if not rq.BASE_HIDE.get(o.name)]
    pull = spec.get('pull')
    frames = PULL_FRAMES if pull else FRAMES
    if pull:
        rq.set_view(sc, pull[0]); res = PULL_RES[pull[0]]
    else:
        res = RES
    sc.render.resolution_x, sc.render.resolution_y = res
    cam = sc.camera; cd = cam.data
    if not pull: cd.sensor_fit = 'AUTO'; cd.sensor_width = 36
    saved = []; track = []
    for i in range(frames):
        dst = os.path.join(d, f'{prefix}{i:03d}.webp')
        t = i / (frames - 1)
        posed = None
        if pull:
            posed = rq.pose_garment(pull[0], pull[1], rq.ease(t))
        else:
            loc, tgt, lens = camera_at(spec['a'], spec['b'], t, spec['lift'])
            cam.location = loc; cd.lens = lens
            cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
            cd.dof.focus_distance = (rq.FOCUS - loc).length
        bpy.context.view_layer.update()
        slots, neon = rq.project_slots(sc, cam); track.append(dict(slots=slots, neon=neon, drop=drop_box(sc, cam, drops)))
        if os.path.exists(dst):
            if posed: rq.unpose(posed)
            continue
        png = dst.replace('.webp', '.png')
        try: secs = rq.render_to(sc, png)
        finally:
            if posed: rq.unpose(posed)
        rq.to_webp(png, dst, q=86 if rq.HI else 80)
        rq.stop_if_superseded()
        rq.log('move', name, variant, i, secs, 's'); saved.append(dst)
        if len(saved) >= 6:                     # commit in small batches
            rq.git_save(saved, f'AZUR move {name} ({variant}): frames up to {i}'); saved = []
    meta = os.path.join(OUT, 'moves.json')
    m = json.load(open(meta)) if os.path.exists(meta) else {}
    e = m.setdefault(name, {})
    e.update(from_=spec['a'], to=spec['b'], frames=frames, fps=30, res=list(res), track=track)
    if pull: e['kind'] = 'pull'
    e['variants'] = sorted(set(e.get('variants', [])) | {variant})
    json.dump(m, open(meta, 'w'), indent=1)
    rq.git_save(saved + [meta], f'AZUR move {name} ({variant}): complete')


def main():
    rq.hand_over_to_watch_v2()
    rq.ensure_blend()
    sc = rq.open_scene()
    names = [n for n in MOVES if not rq.ONLY or n in rq.ONLY]
    for variant in VARIANTS:
        for n in names:
            rq.restore_visibility()
            render_move(sc, n, MOVES[n], variant)
    rq.git_push(force=True)
    rq.log('moves finished')


if __name__ == '__main__':
    main()
