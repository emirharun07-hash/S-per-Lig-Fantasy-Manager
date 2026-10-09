"""AZUR outside the window (round 4): one boy runs past on the lawn with his ball, now and then, and kicks it away.

The owner: "a boy, at most two, running past the window now and then, not a whole team; a kick sound once in a while;
the perspective was unnatural." So the outside is rendered from the room's own cameras: a lawn below the window (the
park HDRI stays the backdrop), a boy built from soft shapes with a procedural run cycle (seen from across the room,
blurred by the depth of field, which is all the detail the window shows) and a ball he dribbles and then kicks.

Only the window's rectangle is rendered (border render, half size: it is out of focus anyway) for each view with a
window (room, rail), as a short clip: the first frame has nobody in it, so the page can rest on it and play the clip
now and then. Output: prototype/assets/scene3/outside/<view>.mp4 + .webm and outside.json (box, fps, kick time).

Usage:  python3 azur/scene/outside.py [test] [view ...]      (test: three stills of the middle frames, small)
"""
import os, sys, json, math, time, subprocess, shutil
import bpy
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq

OUT = os.path.join(rq.OUT, '..', 'outside')
FPS, SECONDS = 25, 3.6
FRAMES = int(FPS * SECONDS)
GROUND_Z = -0.35                 # the garden a little below the room's floor (house plinth)
PATH_X = 8.6                     # how far out he runs (metres from the room's left wall)
Y0, Y1 = -3.5, 8.5               # where the run starts and ends (along the house)
SPEED = (Y1 - Y0) / SECONDS
KICK_T = 1.95                    # seconds into the clip
GROUND = os.environ.get('AZUR_OUT_GROUND', 'catcher')   # 'catcher': HDRI + shadow only; 'lawn': modelled lawn and hedge


def mat(name, rgb, rough=0.6, sheen=0.0, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    if sheen: b.inputs['Sheen Weight'].default_value = sheen
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (0.01, 0.004, 0.002)
    return m


def blob(name, size, mat_, parent, offset=(0, 0, 0)):
    """A soft limb or body part: an ellipsoid hanging from its joint (parent), offset in the joint's frame."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_smooth(); o.data.materials.append(mat_)
    o.parent = parent; o.location = offset
    return o


def joint(name, parent, loc):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    e.parent = parent; e.location = loc; e.rotation_mode = 'XYZ'
    return e


def build_lawn():
    if GROUND == 'catcher':
        # the park HDRI's own grass stays visible (the window looks exactly like the still room); the ground only
        # catches his shadow and the ball's
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(3.8 + 30, 5, GROUND_Z))
        g = bpy.context.object; g.name = 'out_ground'; g.scale = (60, 70, 1); bpy.ops.object.transform_apply(scale=True)
        g.is_shadow_catcher = True
        return [g]
    t = rq_tex('grass_ground')
    m = bpy.data.materials.new('lawn'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.5, 0.5, 0.5)
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    for key, inp, cs in (('Diffuse', 'Base Color', 'sRGB'), ('Rough', 'Roughness', 'Non-Color')):
        it = N.new('ShaderNodeTexImage'); it.image = bpy.data.images.load(t[key]); it.image.colorspace_settings.name = cs
        nt.links.new(mp.outputs[0], it.inputs[0])
        if key == 'Diffuse':                       # a mown summer lawn, greener than the photo's dry patch
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            mx.inputs[7].default_value = (0.30, 0.55, 0.18, 1)
            nt.links.new(it.outputs['Color'], mx.inputs[6]); nt.links.new(mx.outputs[2], b.inputs[inp])
        else:
            nt.links.new(it.outputs['Color'], b.inputs[inp])
    nn = N.new('ShaderNodeTexImage'); nn.image = bpy.data.images.load(t['nor_gl']); nn.image.colorspace_settings.name = 'Non-Color'
    nm = N.new('ShaderNodeNormalMap'); nt.links.new(mp.outputs[0], nn.inputs[0]); nt.links.new(nn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs[0], b.inputs['Normal'])
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(3.8 + 30, 5, GROUND_Z))
    g = bpy.context.object; g.name = 'out_lawn'; g.scale = (60, 70, 1); bpy.ops.object.transform_apply(scale=True)
    g.data.materials.append(m)
    # a low hedge at the far side of the garden: the eye reads the distance (the HDRI's trees stand behind it)
    hm = mat('out_hedge', (0.05, 0.11, 0.035), rough=0.9, sheen=0.3)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(17.0, 5, GROUND_Z + 0.55))
    h = bpy.context.object; h.name = 'out_hedge'; h.scale = (0.9, 60, 1.1); bpy.ops.object.transform_apply(scale=True)
    tx = bpy.data.textures.new('hedgenoise', 'CLOUDS'); tx.noise_scale = 0.35
    sub = h.modifiers.new('sub', 'SUBSURF'); sub.levels = 3; sub.render_levels = 3
    d = h.modifiers.new('disp', 'DISPLACE'); d.texture = tx; d.strength = 0.35
    h.data.materials.append(hm)
    return [g, h]


def rq_tex(key):
    import glob
    d = os.path.join(rq.ROOT, '.cache', 'ph', 'tex', key)
    f = {}
    for p in glob.glob(os.path.join(d, '*')):
        n = os.path.basename(p)
        for k in ('Diffuse', 'Rough', 'nor_gl'):
            if f'_{k}_' in n: f[k] = p
    return f


def build_boy():
    """About 1.45 m: an eleven-year-old in a sky-blue shirt, black shorts, white socks. Returns the joints to animate."""
    skin = mat('boy_skin', (0.46, 0.29, 0.20), rough=0.55, sss=0.2)
    shirt = mat('boy_shirt', (0.04, 0.24, 0.56), rough=0.8)
    shorts = mat('boy_shorts', (0.03, 0.03, 0.035), rough=0.8, sheen=0.3)
    socks = mat('boy_socks', (0.72, 0.72, 0.70), rough=0.85)
    shoe = mat('boy_shoes', (0.05, 0.05, 0.05), rough=0.5)
    hair = mat('boy_hair', (0.05, 0.03, 0.018), rough=0.55)
    J = {}
    root = joint('boy', None, (PATH_X, Y0, GROUND_Z)); J['root'] = root
    pelvis = joint('boy_pelvis', root, (0, 0, 0.74)); J['pelvis'] = pelvis
    blob('boy_hips', (0.13, 0.09, 0.09), shorts, pelvis, (0, 0, 0.0))
    chest = joint('boy_chest', pelvis, (0, 0, 0.02)); J['chest'] = chest
    blob('boy_torso', (0.15, 0.10, 0.24), shirt, chest, (0, 0, 0.22))
    neck = joint('boy_neck', chest, (0, 0, 0.45)); J['neck'] = neck
    blob('boy_neckpart', (0.045, 0.045, 0.05), skin, neck, (0, 0, 0.02))
    blob('boy_head', (0.092, 0.10, 0.108), skin, neck, (0, 0.01, 0.15))
    blob('boy_hair', (0.097, 0.105, 0.085), hair, neck, (0, -0.012, 0.185))
    for side, sx in (('l', -1), ('r', 1)):
        sh = joint(f'boy_shoulder_{side}', chest, (0.17 * sx, 0, 0.41)); J['shoulder_' + side] = sh
        blob(f'boy_sleeve_{side}', (0.052, 0.052, 0.09), shirt, sh, (0, 0, -0.06))
        blob(f'boy_upperarm_{side}', (0.04, 0.04, 0.12), skin, sh, (0, 0, -0.15))
        el = joint(f'boy_elbow_{side}', sh, (0, 0, -0.26)); J['elbow_' + side] = el
        blob(f'boy_forearm_{side}', (0.036, 0.036, 0.12), skin, el, (0, 0, -0.12))
        blob(f'boy_hand_{side}', (0.035, 0.03, 0.045), skin, el, (0, 0, -0.26))
        hp = joint(f'boy_hip_{side}', pelvis, (0.075 * sx, 0, -0.02)); J['hip_' + side] = hp
        blob(f'boy_thigh_{side}', (0.07, 0.075, 0.12), shorts, hp, (0, 0, -0.1))
        blob(f'boy_leg_{side}', (0.055, 0.058, 0.12), skin, hp, (0, 0, -0.25))
        kn = joint(f'boy_knee_{side}', hp, (0, 0, -0.36)); J['knee_' + side] = kn
        blob(f'boy_sock_{side}', (0.047, 0.05, 0.15), socks, kn, (0, 0, -0.18))
        an = joint(f'boy_ankle_{side}', kn, (0, 0, -0.35)); J['ankle_' + side] = an
        blob(f'boy_shoe_{side}', (0.045, 0.11, 0.04), shoe, an, (0, 0.045, -0.015))
    return J


def build_ball():
    bm = mat('boy_ball', (0.92, 0.92, 0.9), rough=0.45)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.11)
    b = bpy.context.object; b.name = 'boy_ball'; bpy.ops.object.shade_smooth(); b.data.materials.append(bm)
    # dark panels, so it reads as a football when it rolls
    pm = mat('boy_ball_panel', (0.03, 0.03, 0.03), rough=0.5)
    b.data.materials.append(pm)
    for p in b.data.polygons:
        c = p.center.normalized()
        if any(c.dot(Vector(v).normalized()) > 0.93 for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
                                                               (1, 1, 1), (-1, -1, 1), (1, -1, -1), (-1, 1, -1))):
            p.material_index = 1
    b.rotation_mode = 'XYZ'
    return b


def pose(J, ball, t):
    """Run cycle at time t (seconds): legs, arms, a little bounce, the ball dribbled ahead and kicked at KICK_T."""
    f = 1.45                                   # strides per second per leg
    ph = 2 * math.pi * f * t
    y = Y0 + SPEED * t
    J['root'].location = (PATH_X, y, GROUND_Z)
    J['pelvis'].location.z = 0.74 + 0.035 * math.cos(2 * ph)
    J['chest'].rotation_euler = (math.radians(11), 0, math.radians(6) * math.sin(ph))
    J['neck'].rotation_euler = (math.radians(-6), 0, -math.radians(5) * math.sin(ph))
    kick = max(0.0, 1 - abs(t - KICK_T) / 0.28)            # 0..1 around the kick
    for side, off in (('l', 0.0), ('r', math.pi)):
        p = ph + off
        th = math.radians(12 + 38 * math.sin(p))
        kn = -math.radians(12 + 62 * max(0.0, math.cos(p - 0.35)) ** 1.4)
        if side == 'r' and kick > 0:                       # wind up and swing through
            s = (t - KICK_T) / 0.28
            th = math.radians(-35 + 105 * min(1.0, max(0.0, (s + 1) / 1.4)))
            kn = -math.radians(70 * max(0.0, -s)) if s < 0 else -math.radians(8)
        J['hip_' + side].rotation_euler = (th, 0, 0)
        J['knee_' + side].rotation_euler = (kn, 0, 0)
        J['ankle_' + side].rotation_euler = (math.radians(10) * math.sin(p), 0, 0)
        arm = -math.radians(40) * math.sin(p) + (math.radians(25) * kick if side == 'l' else 0)
        J['shoulder_' + side].rotation_euler = (arm, 0, math.radians(8) * (-1 if side == 'l' else 1))
        J['elbow_' + side].rotation_euler = (math.radians(75), 0, 0)
    # ball: dribbled ahead, then kicked away (it flies on along the garden and up)
    r = 0.11
    if t < KICK_T:
        lead = 0.55 + 0.25 * math.sin(2 * math.pi * 0.7 * t)
        by, bz = y + lead, GROUND_Z + r
        dist = by - Y0
    else:
        ty = y if False else Y0 + SPEED * KICK_T
        k = t - KICK_T
        by = ty + 0.55 + 11.0 * k; bz = GROUND_Z + r + 4.2 * k - 4.9 * k * k
        if bz < GROUND_Z + r: bz = GROUND_Z + r
        dist = by - Y0
    ball.location = (PATH_X + 0.05, by, bz)
    ball.rotation_euler = (dist / r, 0, 0)


def window_box(key):
    from PIL import Image
    import numpy as np
    m = np.asarray(Image.open(os.path.join(rq.OUT, key, 'window.png')).convert('L')) > 100
    ys, xs = np.nonzero(m)
    if not len(xs): return None
    h, w = m.shape
    return [max(0, xs.min() / w - 0.01), max(0, ys.min() / h - 0.01), min(1, (xs.max() + 1) / w + 0.01), min(1, (ys.max() + 1) / h + 0.01)]


def setup(sc):
    objs = build_lawn(); J = build_boy(); ball = build_ball()
    rq.render_settings(sc, 'beauty'); rq.lights_off(sc)
    # the day look (azur-config.js daylight around noon), like render_moves.light_variant('day')
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 2.2; rq.world_tint(sc, (1.0, 1.0, 1.0))
    s = bpy.data.objects['sun']; s.hide_render = False; s.data.color = (1.0, 0.96, 0.88)
    s.data.energy = 3.0 * 0.75 * float(os.environ.get('AZUR_OUT_SUN', 0.3))   # the park HDRI is overcast: a soft sun only
    s.rotation_euler = Vector(rq.SUN['sun_high']).normalized().to_track_quat('-Z', 'Y').to_euler()
    sc.view_settings.exposure = float(os.environ.get('AZUR_OUT_EXPOSURE', 0.4))   # outdoors in daylight, not the dim room
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.render.fps = FPS; sc.render.use_persistent_data = True
    sc.cycles.samples = int(os.environ.get('AZUR_OUT_SAMPLES', 128 if os.environ.get('AZUR_GPU') else 48)); sc.cycles.adaptive_threshold = 0.03
    return J, ball


def plan(key):
    """Where the window shows the garden at his distance (y range at PATH_X): he enters 2 m before, kicks in the middle
    and runs on 3 m past it. Sets the run's start, speed, length and kick for this view."""
    global Y0, Y1, SECONDS, FRAMES, KICK_T, SPEED
    c = rq.VIEWS[key]['loc']; xw = 3.55
    ys = [c[1] + (yw - c[1]) * (PATH_X - c[0]) / (xw - c[0]) for yw in (rq_win()['y0'], rq_win()['y1'])]
    lo, hi = min(ys), max(ys)
    SPEED = 2.9                                  # a boy jogging with his ball, not a sprinter
    Y0, Y1 = lo - 2.0, hi + 3.0
    SECONDS = (Y1 - Y0) / SPEED; FRAMES = int(round(SECONDS * FPS))
    KICK_T = ((lo + hi) / 2 - Y0) / SPEED
    rq.log('outside plan', key, 'visible y', round(lo, 2), round(hi, 2), 'run', round(SECONDS, 2), 's', FRAMES, 'frames, kick at', round(KICK_T, 2), 's')


def rq_win():
    return dict(y0=2.30, y1=3.30)        # build_room.WIN (right wall opening)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    test = 'test' in args
    views = [a for a in args if a in ('room', 'rail')] or ['room', 'rail']
    rq.ensure_blend(); sc = rq.open_scene(); rq.restore_visibility(); rq.set_state('day')
    J, ball = setup(sc)
    os.makedirs(OUT, exist_ok=True)
    meta_p = os.path.join(OUT, 'outside.json')
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    for key in views:
        box = window_box(key)
        if not box: continue
        rq.set_view(sc, key); plan(key)
        sc.render.resolution_percentage = int(os.environ.get('AZUR_OUT_PCT', 25 if test else 50))
        r = sc.render; r.use_border = True; r.use_crop_to_border = True
        r.border_min_x, r.border_max_x = box[0], box[2]; r.border_min_y, r.border_max_y = 1 - box[3], 1 - box[1]
        fdir = os.path.join(rq.ROOT, '.cache', 'r4', 'outside', key); os.makedirs(fdir, exist_ok=True)
        frames = [int(KICK_T * FPS) + d for d in (-10, -2, 6)] if test else range(FRAMES)
        bg = background(sc, fdir, ball, test) if GROUND == 'catcher' else None
        t0 = time.time()
        for i in frames:
            png = os.path.join(fdir, f'{i:03d}.png')
            if os.path.exists(png) and not test: continue
            # motion blur needs the pose at neighbouring times: keyframe this frame and its neighbours
            for fr in (i - 1, i, i + 1):
                sc.frame_set(max(0, fr) + 1)
                pose(J, ball, fr / FPS)
                for o in list(J.values()) + [ball]:
                    o.keyframe_insert('location', frame=fr + 1); o.keyframe_insert('rotation_euler', frame=fr + 1)
            sc.frame_set(i + 1)
            if bg is None:
                sc.render.filepath = png; bpy.ops.render.render(write_still=True)
            else:
                tmp = png.replace('.png', '_rgba.png')
                sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
                over(tmp, bg, png)
                if not os.environ.get('AZUR_OUT_KEEP'): os.remove(tmp)
            rq.log('outside', key, i, round(time.time() - t0), 's')
        if test: continue
        enc(fdir, key)
        meta[key] = dict(box=box, fps=FPS, frames=FRAMES, kick=KICK_T, file=f'outside/{key}')
        json.dump(meta, open(meta_p, 'w'), indent=1)


def background(sc, fdir, ball, test):
    """The park through the window with nobody in it (the HDRI, as in the still room): rendered once per view. The
    frames then render the boy, the ball and their shadow on the ground alone (transparent film) and go over it."""
    path = os.path.join(fdir, 'bg.png')
    objs = [o for o in bpy.data.objects if o.name.startswith(('boy', 'out_'))] + [ball]
    # seen through the pane (a transmission ray) the shadow catcher is a white wall: no glass for the clip (the page
    # lays the clip over the window at 93 %, so the still room's own glass stays faintly on top)
    for o in bpy.data.objects:
        if o.name.startswith('glass'): o.hide_render = True
    if test or not os.path.exists(path):
        for o in objs: o.hide_render = True
        sc.render.film_transparent = False; sc.render.image_settings.color_mode = 'RGB'
        sc.render.filepath = path; bpy.ops.render.render(write_still=True)
        for o in objs: o.hide_render = False
    sc.render.film_transparent = True; sc.render.image_settings.color_mode = 'RGBA'
    return path


def over(fg_path, bg_path, out_path):
    from PIL import Image
    import numpy as np
    fg = np.asarray(Image.open(fg_path).convert('RGBA')).astype(np.float32) / 255
    bg = np.asarray(Image.open(bg_path).convert('RGB')).astype(np.float32) / 255
    a = fg[..., 3:4]
    out = fg[..., :3] * a + bg * (1 - a)
    Image.fromarray((out * 255 + 0.5).clip(0, 255).astype(np.uint8)).save(out_path)


def enc(fdir, key):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    src = os.path.join(fdir, '%03d.png')
    base = os.path.join(OUT, key)
    pad = 'scale=trunc(iw/2)*2:trunc(ih/2)*2'
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', src, '-vf', pad, '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '20', '-preset', 'slow', '-movflags', '+faststart', '-an', base + '.mp4'], check=True)
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', src, '-vf', pad, '-c:v', 'libvpx-vp9', '-b:v', '0',
                    '-crf', '34', '-an', base + '.webm'], check=True)
    rq.log('outside clip', key, os.path.getsize(base + '.mp4') // 1024, 'KB mp4', os.path.getsize(base + '.webm') // 1024, 'KB webm')


if __name__ == '__main__':
    main()
