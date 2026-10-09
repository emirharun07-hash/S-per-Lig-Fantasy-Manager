"""AZUR render queue: plates, light passes, depth maps, sprites and projections for the prototype.

Runs unattended and is safe to restart: every job is skipped when its output already exists,
and every finished output is committed and pushed so nothing is lost if the machine goes away.

Usage:  python3 azur/scene/render_queue.py            (all jobs)
        python3 azur/scene/render_queue.py rail       (only jobs for one view)

scene3 (round 3): the room changes through the day. Objects carry an 'azur_state' tag (build_room.py); 'day' is the
base and gets every light pass, 'morning', 'evening' and 'night' are stored as patches: only the rectangles where
they differ from day, for the light passes that state uses. masks.png per view (and state) gives the bed, the rail
and the magazine as white outlines for hover. A newer render request (azur/render_request.json on the branch)
stops the queue between jobs, so a fixed scene replaces a stale run.
Env:    AZUR_GPU=1            render on the graphics chip (e.g. on the owner's laptop), CPU otherwise
        AZUR_QUEUE_NO_GIT=1   skip commits (local testing)
        AZUR_QUEUE_FAST=1     tiny resolution and samples (pipeline test)
"""
import bpy, os, sys, json, math, time, subprocess
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import maps                                                         # depth/window maps kept small (maps.py)
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
SET = os.environ.get('AZUR_SET', 'scene3')    # scene2: jerseys in the renders; scene3: + times of day, masks, hi-res
OUT = os.path.join(ROOT, 'prototype', 'assets', SET, 'views')
BLEND = os.environ.get('AZUR_BLEND') or os.path.join(ROOT, '.cache', f"azur_room_{SET}.blend")   # rebuilt per scene set
LOG = os.path.join(ROOT, '.cache', 'queue.log')
FAST = bool(os.environ.get('AZUR_QUEUE_FAST'))
if FAST: OUT = os.path.join(ROOT, '.cache', 'queue_test')
NO_GIT = bool(os.environ.get('AZUR_QUEUE_NO_GIT'))
ONLY = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]

# ------------------------------------------------------------------ views (camera presets the prototype moves between)
HI = SET not in ('scene1', 'scene2')      # scene3: sharper plates (2400 wide: no upscaling on large and HiDPI screens)
RX = 0.24 if HI else 0.0                  # scene3 moved the rail 0.24 m right (it stood in the desk)
VIEWS = {
    # establishing shot: high in the front-left corner, the whole room
    'room':   dict(loc=(0.24, 0.22, 2.06), target=(1.85, 3.15, 0.78), lens=19, res=(2400, 1350) if HI else (1600, 900)),
    # the rail: centred, closer and a little higher than the first stills
    'rail':   dict(loc=(1.72 + RX, 0.70, 1.40), target=(1.85 + RX, 3.60, 1.18), lens=24, res=(2400, 1350) if HI else (1600, 900)),
    # the bed (easter egg, content decided later)
    'bed':    dict(loc=(1.55, 0.35, 1.35), target=(0.45, 1.50, 0.48), lens=26, res=(2400, 1350) if HI else (1600, 900)),
    # phones start at the rail; the plate is wider than a phone so the visitor can swipe along it
    'rail_m': dict(loc=(1.55 + RX, 1.15, 1.30), target=(1.55 + RX, 3.40, 1.12), lens=20, res=(1800, 2000) if HI else (1440, 1600), fit='VERTICAL', sensor=24),
}
FOCUS = Vector((1.55 + RX, 2.95, 1.2))   # depth of field: sharp on the jerseys
# light passes: each rendered alone, white light, mixed and tinted in the browser
PASSES = ['sky', 'sun_low', 'sun_high', 'neon', 'lamp', 'ceiling', 'street', 'spot']
SUN = {'sun_low': (-1.0, 0.22, -0.12), 'sun_high': (-1.0, 0.12, -0.78)}
DEPTH_NEAR, DEPTH_FAR = 0.4, 6.5   # metres; depth.png stores near=white, far=black (sRGB-encoded)
GARMENT_PREFIX = ('jersey_', 'drop_', 'hanger', 'hook', 'tag', 'tagtext', 'string', 'zip')
# times of day (scene3): which light passes each state needs (azur-config.js daylight weights over the state's hours)
STATES = ['day', 'morning', 'evening', 'night']
STATE_PASSES = {'morning': ['sky', 'sun_high', 'neon', 'spot', 'street'],
                'evening': ['sky', 'sun_low', 'sun_high', 'neon', 'lamp', 'spot', 'street'],
                'night':   ['sky', 'neon', 'spot', 'street']}       # the lamp is off from 23:00 (azur-config.js)
NEON_SAMPLES = 1024      # round 4: the sign looked grainy at 384; on a graphics card its pass takes about a minute
# hover outlines: the objects that make up the bed, the rail and the magazine (masks.png channels R, G, B)
# names are exact object names (Blender's .001 suffixes allowed); a trailing * makes a prefix
MASK_GROUPS = {
    'bed': ('mattress', 'duvet*', 'pillow', 'bed_*', 'leg', 'sock', 'phone'),
    'rail': ('bar', 'upright', 'foot', 'caster', 'hook', 'hanger', 'jersey_*', 'drop_*', 'tag', 'tagtext', 'string', 'zip*'),
    'mag': ('magazine*', 'masthead'),
}


def log(*a):
    msg = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
    print(msg, flush=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f: f.write(msg + '\n')


_last_push = [0.0]
BRANCH = 'claude/shopify-notification-signup-o5avym'
REQ_ID = os.environ.get('AZUR_REQUEST_ID')     # set by the PC's watch mode (tools/render_step.ps1)
_sup = [0.0]


def superseded():
    """True when the branch carries a newer render request than the one this run belongs to (checked once a minute)."""
    if not REQ_ID or NO_GIT or time.time() - _sup[0] < 60: return False
    _sup[0] = time.time()
    try:
        f = subprocess.run(['git', '-C', REPO, 'fetch', '-q', 'origin', BRANCH], capture_output=True, timeout=90)
        if f.returncode != 0:                      # offline (the owner's line is down at night): look again in 10 min
            _sup[0] = time.time() + 540; return False
        r = subprocess.run(['git', '-C', REPO, 'show', f'origin/{BRANCH}:azur/render_request.json'], capture_output=True, text=True, timeout=30)
        rid = json.loads(r.stdout).get('id')
        return bool(rid) and rid != REQ_ID
    except Exception:
        return False


def hand_over_to_watch_v2():
    """On the owner's PC: a script started by the old watch mode (or an old manual run) cannot report what it does.
    It opens watch mode v2 in a new PowerShell window (status reports, preview, newer requests stop stale runs),
    closes the old window and stops; v2 picks up the current render request and skips what is already rendered.
    Runs started by the current render_on_windows.ps1 set AZUR_NO_HANDOVER and are left alone."""
    if os.name != 'nt' or os.environ.get('AZUR_NO_HANDOVER') or NO_GIT or FAST: return
    ppid = os.getppid()
    try:
        out = subprocess.run(['tasklist', '/FI', f'PID eq {ppid}', '/FO', 'CSV', '/NH'], capture_output=True, text=True, timeout=30).stdout
        parent = out.strip().split(',')[0].strip().strip('"').lower()
    except Exception:
        return
    if parent not in ('powershell.exe', 'pwsh.exe'): return
    log('handing over to watch mode v2: a new window opens, this one closes')
    script = os.path.join(REPO, 'azur', 'tools', 'render_on_windows.ps1')
    subprocess.Popen(['powershell', '-ExecutionPolicy', 'Bypass', '-NoExit', '-File', script, 'watch'], cwd=REPO,
                     creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0x10))
    time.sleep(5)
    subprocess.run(['taskkill', '/PID', str(ppid), '/F'], capture_output=True)
    sys.exit(0)


def stop_if_superseded():
    if superseded():
        log('a newer render request is on the branch: stopping this run'); git_push(force=True); sys.exit(3)


OFFLINE_HINTS = ('Could not resolve host', 'unable to access', 'Failed to connect', 'Connection timed out',
                 'Could not read from remote', 'Network is unreachable', 'timed out')


def git_push(force=False):
    """Push at most every two minutes (a push per output costs more time than a fast GPU needs for the render).
    Offline (the owner's internet is off at night) it tries once and goes on rendering: the outputs stay committed and
    go up with the next push once the line is back (it used to wait about three minutes per output)."""
    if NO_GIT or (not force and time.time() - _last_push[0] < 120): return
    _last_push[0] = time.time()                    # a failed try also waits two minutes before the next one
    for attempt in range(3):
        try:
            r = subprocess.run(['git', '-C', REPO, 'pull', '--rebase', '--autostash', '-q', 'origin', BRANCH], capture_output=True, text=True, timeout=600)
            p = subprocess.run(['git', '-C', REPO, 'push', '-q', 'origin', 'HEAD:' + BRANCH], capture_output=True, text=True, timeout=600)
            if p.returncode == 0: return
            err = (r.stderr or '') + (p.stderr or '')
        except subprocess.TimeoutExpired as e:
            err = 'timed out: ' + str(e)
        if any(h in err for h in OFFLINE_HINTS):
            log('offline: the outputs stay committed and go up once the internet is back'); return
        log('git push retry', attempt, err.strip()[:300])
        time.sleep(5 * (attempt + 1))


def git_save(paths, message):
    """Commit the outputs right away (nothing is lost if the machine goes away), push in batches."""
    if NO_GIT: return
    rel = [os.path.relpath(p, REPO) for p in paths if os.path.exists(p)]
    for attempt in range(6):
        try:
            subprocess.run(['git', '-C', REPO, 'add', '--'] + rel, check=True, capture_output=True)
            r = subprocess.run(['git', '-C', REPO, 'commit', '-m', message + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01R3wWJYBEPWenzksQTM89FE', '--'] + rel,
                               capture_output=True, text=True)
            if r.returncode not in (0, 1): raise RuntimeError(r.stderr)
            break
        except Exception as e:
            log('git retry', attempt, e)
            time.sleep(2 ** attempt * 3)
    git_push()


# ------------------------------------------------------------------ scene
def ensure_assets():
    """The Poly Haven downloads, again when a newer scene needs one an earlier download lacks (round 4: the lawn)."""
    if not os.path.isdir(os.path.join(ROOT, '.cache', 'ph', 'tex', 'grass_ground')):
        subprocess.run([sys.executable, os.path.join(HERE, 'fetch_assets.py')], check=True)


def ensure_blend():
    ensure_assets()
    if os.path.exists(BLEND): return
    log('building scene (no saved .blend found)')
    env = dict(os.environ, AZUR_BUILD_ONLY='1')
    subprocess.run([sys.executable, os.path.join(HERE, 'build_room.py'), '--', 'preview', '/dev/null', BLEND], check=True, env=env)


def use_gpu(sc):
    """AZUR_GPU=1: render on the graphics chip if Cycles finds one (OptiX/CUDA on NVIDIA, Metal on Apple, HIP on AMD,
    oneAPI on Intel Arc). Falls back to the CPU. Returns the backend used."""
    if not os.environ.get('AZUR_GPU'): return 'CPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA', 'METAL', 'HIP', 'ONEAPI'):
        try: prefs.compute_device_type = kind
        except TypeError: continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices: d.use = d.type == kind
            sc.cycles.device = 'GPU'
            return kind + ': ' + ', '.join(d.name for d in gpus)
    return 'CPU (no supported graphics chip found)'


def open_scene():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    sc.cycles.device = 'CPU'
    dev = use_gpu(sc)
    if not getattr(open_scene, 'logged', False): log('render device', dev); open_scene.logged = True
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
    if 'L_spot' not in bpy.data.objects and 'spot_can' in bpy.data.objects:   # ceiling spot over the rail (scene2)
        L = bpy.data.lights.new('L_spot', 'SPOT'); L.energy = 60.0; L.spot_size = math.radians(72); L.spot_blend = 0.85; L.shadow_soft_size = 0.05
        o = bpy.data.objects.new('L_spot', L); sc.collection.objects.link(o)
        can = bpy.data.objects['spot_can']; c = sum((can.matrix_world @ Vector(v) for v in can.bound_box), Vector()) / 8
        aim = Vector((1.55 + RX, 2.95, 1.25)); o.location = c + (aim - c).normalized() * 0.1
        o.rotation_euler = (aim - c).to_track_quat('-Z', 'Y').to_euler()
    # opal ceiling light emits only in its own pass
    cm = bpy.data.objects['ceiling_light'].data.materials[0]
    cm.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1, 1, 1, 1)
    global BASE_HIDE, SAVED_HIDE
    SAVED_HIDE = {o.name: o.hide_render for o in bpy.data.objects}
    BASE_HIDE = {o.name: o.hide_render or not state_visible(o, 'day') for o in bpy.data.objects}
    restore_visibility()
    return sc


def state_visible(o, state):
    """build_room tags: 'night', 'evening night', '!night' (all but night); untagged objects are always there."""
    tags = str(o.get('azur_state', '')).split()
    if not tags: return True
    return state in tags or (any(t.startswith('!') for t in tags) and '!' + state not in tags)


STATE_NOW = ['day']
HALL_W = 25.0        # the hallway light (watts) in the street pass; the browser doses it with the street weight


def set_state(state):
    """Show what belongs to one time of day (on top of restore_visibility)."""
    STATE_NOW[0] = state
    for o in bpy.data.objects:
        if 'azur_state' in o and not SAVED_HIDE.get(o.name): o.hide_render = not state_visible(o, state)


def state_objects(state):
    """Objects whose visibility differs between day and `state`."""
    return [o for o in bpy.data.objects if 'azur_state' in o and o.type in ('MESH', 'CURVE', 'FONT', 'META')
            and state_visible(o, state) != state_visible(o, 'day')]


def restore_visibility():
    STATE_NOW[0] = 'day'
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
    cd.dof.focus_distance = (FOCUS - Vector(v['loc'])).length
    rx, ry = v['res']
    if FAST: rx, ry = rx // 5, ry // 5
    sc.render.resolution_x, sc.render.resolution_y = rx, ry
    sc.render.resolution_percentage = 100


def lights_off(sc):
    w = sc.world.node_tree.nodes
    w['Background'].inputs['Strength'].default_value = 0.0
    bpy.data.objects['sun'].hide_render = True
    for n in ('L_lamp', 'L_street', 'L_spot', 'L_hall'):
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
        hall = bpy.data.objects.get('L_hall')     # round 4: the hallway light through the door ajar, at night
        if hall:
            hall.hide_render = not state_visible(hall, STATE_NOW[0]); hall.data.energy = HALL_W; hall.data.color = (1, 1, 1)
    elif p == 'spot':
        bpy.data.objects['L_spot'].hide_render = False; bpy.data.objects['L_spot'].data.color = (1, 1, 1)


def neon_quality(sc, p):
    """The sign is the brand: its pass gets more samples and a finer noise threshold than the others."""
    if p == 'neon' and not FAST: sc.cycles.samples = NEON_SAMPLES; sc.cycles.adaptive_threshold = 0.004


def render_settings(sc, kind):
    cy = sc.cycles; r = sc.render
    r.film_transparent = False
    sc.view_layers[0].material_override = None
    cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'; cy.adaptive_threshold = 0.01 if HI else 0.02
    cy.samples = 8 if FAST else {'beauty': 256 if HI else 224, 'pass': 384 if HI else 192, 'depth': 4, 'sprite': 128}[kind]
    r.use_border = False
    r.dither_intensity = 0.0 if kind == 'depth' else 1.0     # maps (depth, window, ids, masks) without dither noise
    if kind == 'depth': cy.use_denoising = False
    if kind in ('pass', 'depth'):
        sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0
    else:
        sc.view_settings.view_transform = 'AgX'
        try: sc.view_settings.look = 'AgX - Medium High Contrast'
        except Exception: pass
        sc.view_settings.exposure = 2.65
    s = r.image_settings
    if kind == 'pass':   # colour mode must be set every time: the depth job leaves it at BW
        s.file_format = 'OPEN_EXR'; s.color_mode = 'RGB'; s.color_depth = '16'; s.exr_codec = 'ZIP'
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


EXR = os.path.join(ROOT, '.cache', 'exr', SET)     # scene3 keeps the linear day passes to find what a state changes
if FAST: EXR = os.path.join(OUT, 'exr')
ENC_REF = 1.5 if HI else 0.5     # where the 97th percentile lands before the curve: scene3 spends more codes on the dark


def read_exr(exr):
    img = bpy.data.images.load(exr); w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3].copy()


def pass_scale(rgb):
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return ENC_REF / max(float(np.percentile(lum, 97)), 1e-6)


def encode_rgb(rgb, scale):
    """Linear light -> 8-bit codes with a Reinhard curve; the browser undoes it: lin = (y / (1 - y)) / scale, y = enc^2.2."""
    x = np.clip(rgb * scale, 0, None)
    return np.clip(np.power(x / (1.0 + x), 1 / 2.2) * 255 + 0.5, 0, 255).astype(np.uint8)


def pass_quality(p):
    if not HI: return 90
    return 97 if p == 'neon' else 94           # the sign is the brand: least compression where it glows


def save_webp(codes, dst, q):
    from PIL import Image
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    Image.fromarray(codes).save(dst, 'WEBP', quality=q, method=6)


def encode_pass(exr, dst, p='', keep=None):
    """Linear EXR -> WebP (see encode_rgb); returns the scale for passes.json. keep: move the EXR there instead of deleting."""
    rgb = read_exr(exr); scale = pass_scale(rgb)
    save_webp(encode_rgb(rgb, scale), dst, pass_quality(p))
    if keep:
        os.makedirs(os.path.dirname(keep), exist_ok=True); os.replace(exr, keep)
    else:
        os.remove(exr)
    return scale


# ------------------------------------------------------------------ jobs
def project_slots(sc, cam):
    """Garment slots (one per hook, left to right) and the neon sign as seen by cam at the current resolution."""
    def uv(p):
        c = world_to_camera_view(sc, cam, Vector(p)); return [round(c.x, 4), round(1 - c.y, 4), round(c.z, 3)]
    hooks = sorted([o for o in bpy.data.objects if o.name.startswith('hook')], key=lambda o: o.matrix_world.translation.x)
    slots = []
    for h in hooks:
        top = h.matrix_world.translation + Vector((0, -0.018, 0.072))   # where the hook sits on the bar
        garment_top = h.matrix_world.translation + Vector((0, 0, -0.008))
        bottom = garment_top + Vector((0, 0, -0.74))
        a, b, t = uv(garment_top), uv(bottom), uv(top)
        left, right = uv(garment_top + Vector((-0.35, 0, 0))), uv(garment_top + Vector((0.35, 0, 0)))
        slots.append(dict(hook=t[:2], top=a[:2], bottom=b[:2], width=round(right[0] - left[0], 4), depth=a[2]))
    neon = bpy.data.objects['neon_plate']; npt = [neon.matrix_world @ Vector(c) for c in neon.bound_box]
    mag = bpy.data.objects.get('magazine')   # the ANSTOSS magazine on the duvet opens the brand story (bed view)
    return slots, uv((sum(p.x for p in npt) / 8, min(p.y for p in npt), sum(p.z for p in npt) / 8))[:2]


def magazine_corners(mag, uv):
    """The magazine's top face as four screen points (clockwise from the masthead's left)."""
    bb = [Vector(c) for c in mag.bound_box]; x0, x1 = min(c.x for c in bb), max(c.x for c in bb)
    y0, y1, z = min(c.y for c in bb), max(c.y for c in bb), max(c.z for c in bb)
    return [uv(mag.matrix_world @ Vector(p))[:2] for p in ((x0, y1, z), (x1, y1, z), (x1, y0, z), (x0, y0, z))]


def job_projections(sc):
    """Screen positions of the hangers, rail, window, bed and neon for every view (u, v from top-left, 0..1)."""
    path = os.path.join(OUT, 'views.json')
    data = json.load(open(path)) if os.path.exists(path) else {}
    hooks = sorted([o for o in bpy.data.objects if o.name.startswith('hook')], key=lambda o: o.matrix_world.translation.x)
    rail = bpy.data.objects['bar']; rp = [rail.matrix_world @ Vector(c) for c in rail.bound_box]
    glass = bpy.data.objects['glass']; gp = [glass.matrix_world @ Vector(c) for c in glass.bound_box]
    matt = bpy.data.objects['mattress']; mp = [matt.matrix_world @ Vector(c) for c in matt.bound_box]
    neon = bpy.data.objects['neon_plate']; npt = [neon.matrix_world @ Vector(c) for c in neon.bound_box]
    mag = bpy.data.objects.get('magazine')   # the ANSTOSS magazine on the duvet opens the brand story (bed view)
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
        if mag: data[key]['magazine'] = magazine_corners(mag, uv)
        magn = bpy.data.objects.get('magazine_night')     # scene3: at night it slid off the bed onto the floor
        if magn: data[key]['magazine_night'] = magazine_corners(magn, uv)
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
    secs = render_to(sc, dst.replace('.webp', '.png')); to_webp(dst.replace('.webp', '.png'), dst)
    log('beauty', key, secs, 's'); return [dst]


def job_depth(sc, key):
    dst = os.path.join(OUT, key, 'depth.png')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'depth'); lights_off(sc)
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
    maps.tidy_depth(dst, VIEWS[key]['res'][0])                       # small for the web (maps.py)
    log('depth', key, secs, 's'); return [dst]


def job_pass(sc, key, p, meta):
    dst = os.path.join(OUT, key, p + '.webp')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'pass'); set_pass(sc, p); neon_quality(sc, p)
    exr = dst.replace('.webp', '.exr'); secs = render_to(sc, exr)
    meta.setdefault(key, {})[p] = encode_pass(exr, dst, p, keep=os.path.join(EXR, key, p + '.exr') if HI else None)
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
    sys.path.insert(0, os.path.join(ROOT, 'tools')); import clean_sprite   # drop specks that blow up the box
    clean_sprite.clean(key, OUT)
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


# ------------------------------------------------------------------ garments as part of the room (scene2)
PULL = {'rail': 0.42, 'rail_m': 0.34}   # metres a chosen garment comes toward the camera


def garment_groups():
    """Per rail slot (left to right): (hook, objects that belong to that garment)."""
    hooks = sorted([o for o in bpy.data.objects if o.name.startswith('hook')], key=lambda o: o.matrix_world.translation.x)
    groups = []
    for i, h in enumerate(hooks):
        hx = h.matrix_world.translation.x
        objs = [o for o in bpy.data.objects if o.name.startswith(('hook', 'hanger')) and abs(o.matrix_world.translation.x - hx) < 0.03]
        if i == len(hooks) - 1:
            objs += [o for o in bpy.data.objects if o.name.startswith(('drop_', 'tag', 'tagtext', 'string', 'zip'))]
        else:
            objs += [o for o in bpy.data.objects if o.name.startswith('jersey_') and abs(o.matrix_world.translation.x - hx) < 0.03]
        groups.append((h, objs))
    return groups


def ease(t): return t * t * t * (t * (6 * t - 15) + 10)


def pose_garment(key, i, t):
    """Take garment i off the rail toward the camera of view `key` (t 0 = hanging, 1 = held out, facing the camera).
    Returns what unpose() needs."""
    h, objs = garment_groups()[i]
    saved = [(o, o.matrix_world.copy()) for o in objs]
    if t <= 0: return saved
    body = next((o for o in objs if not o.name.startswith(('hook', 'hanger'))), objs[0])
    piv = h.matrix_world.translation.copy()
    d = Vector(VIEWS[key]['loc']) - piv; d.z = 0; d.normalize()
    yaw_now = body.matrix_world.to_euler().z
    yaw_to = math.atan2(d.x, -d.y) + math.radians(7)        # front toward the camera, turned a touch
    dyaw = (yaw_to - yaw_now + math.pi) % (2 * math.pi) - math.pi
    new_piv = piv + d * (PULL.get(key, 0.4) * t) + Vector((0, 0, 0.03 * t + 0.03 * math.sin(math.pi * t)))
    M = Matrix.Translation(new_piv) @ Matrix.Rotation(dyaw * t, 4, 'Z') @ Matrix.Translation(-piv)
    for o, mw in saved: o.matrix_world = M @ mw
    return saved


def unpose(saved):
    for o, mw in saved: o.matrix_world = mw


def job_ids(sc, key):
    """Which garment is at each pixel (0 = none, slot i = (i + 1) * 32): exact hover and click areas."""
    dst = os.path.join(OUT, key, 'ids.png')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'depth'); lights_off(sc)
    sc.cycles.samples = 1 if FAST else 4; sc.cycles.filter_width = 0.01; sc.camera.data.dof.use_dof = False
    sc.render.film_transparent = True; sc.render.image_settings.color_mode = 'RGBA'
    groups = garment_groups(); member = {o.name: i for i, (_, objs) in enumerate(groups) for o in objs}
    saved_mats = {}
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE', 'FONT', 'META') or BASE_HIDE.get(o.name): continue
        if o.name in member:
            v = (member[o.name] + 1) * 32 / 255.0
            m = bpy.data.materials.get(f'azur_id{member[o.name]}') or bpy.data.materials.new(f'azur_id{member[o.name]}')
            m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
            em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (v, v, v, 1); out = nt.nodes.new('ShaderNodeOutputMaterial')
            nt.links.new(em.outputs[0], out.inputs['Surface'])
            if hasattr(o.data, 'materials'):
                saved_mats[o.name] = [s_.material for s_ in o.material_slots]
                for s_ in o.material_slots: s_.material = m
        else:
            o.is_holdout = True       # the rest of the room still hides what is behind it
    sc.view_settings.view_transform = 'Raw'      # exact values, no display curve
    png = dst.replace('.png', '_tmp.png'); secs = render_to(sc, png)
    for name, mats in saved_mats.items():
        for s_, m in zip(bpy.data.objects[name].material_slots, mats): s_.material = m
    sc.camera.data.dof.use_dof = True; sc.cycles.filter_width = 1.5
    from PIL import Image
    im = Image.open(png); a = np.asarray(im.convert('RGBA')).astype(np.int32)
    ids = np.where(a[..., 3] > 127, np.clip(np.round(a[..., 0] / 32.0), 0, 7) * 32, 0).astype(np.uint8)
    Image.fromarray(ids, 'L').save(dst, optimize=True); os.remove(png)
    log('ids', key, secs, 's'); return [dst]


def job_window(sc, key):
    """Where the outside is seen through the window (white): the prototype plays the real outdoor video there."""
    dst = os.path.join(OUT, key, 'window.png')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'depth'); lights_off(sc)
    sc.cycles.samples = 2 if FAST else 16
    black = bpy.data.materials.get('azur_black') or bpy.data.materials.new('azur_black')
    black.use_nodes = True; nt = black.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (0, 0, 0, 1); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    sc.view_layers[0].material_override = black
    glass = bpy.data.objects['glass']; glass.hide_render = True
    old_world = sc.world; w = bpy.data.worlds.get('azur_white') or bpy.data.worlds.new('azur_white'); w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    sc.world = w; sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.color_mode = 'BW'
    secs = render_to(sc, dst)
    sc.world = old_world; sc.view_layers[0].material_override = None
    maps.tidy_window(dst)
    log('window mask', key, secs, 's'); return [dst]


def job_selected(sc, key, i, what, meta):
    """View `key` with garment i taken off the rail toward the camera: 'beauty' or one light pass."""
    sel = f'{key}@{i}'
    dst = os.path.join(OUT, sel, what + '.webp')
    if os.path.exists(dst): return None
    if what == 'beauty':
        return job_beauty_at(sc, key, dst, lambda: pose_garment(key, i, 1.0))
    set_view(sc, key); render_settings(sc, 'pass'); set_pass(sc, what)
    saved = pose_garment(key, i, 1.0)
    try: exr = dst.replace('.webp', '.exr'); secs = render_to(sc, exr)
    finally: unpose(saved)
    meta.setdefault(sel, {})[what] = encode_pass(exr, dst)
    mpath = os.path.join(OUT, 'passes.json'); json.dump(meta, open(mpath, 'w'), indent=1)
    log('selected', sel, what, secs, 's'); return [dst, mpath]


def job_beauty_at(sc, key, dst, prepare):
    set_view(sc, key); render_settings(sc, 'beauty'); lights_off(sc)
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 2.2; world_tint(sc, (1.0, 0.86, 0.72))
    s = bpy.data.objects['sun']; s.hide_render = False; s.data.energy = 3.0; s.data.color = (1.0, 0.60, 0.33)
    s.rotation_euler = Vector(SUN['sun_low']).normalized().to_track_quat('-Z', 'Y').to_euler()
    b = bpy.data.materials['neon_tube'].node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (0.086, 0.722, 1.0, 1); b.inputs['Emission Strength'].default_value = 1.6
    saved = prepare()
    try: secs = render_to(sc, dst.replace('.webp', '.png')); to_webp(dst.replace('.webp', '.png'), dst)
    finally: unpose(saved)
    log('beauty', os.path.basename(os.path.dirname(dst)), secs, 's'); return [dst]


# ------------------------------------------------------------------ scene3: hover outlines and times of day
def name_in(name, names):
    base = name.split('.')[0]
    return any(name.startswith(n[:-1]) if n.endswith('*') else base == n for n in names)


def in_group(o, names):
    while o is not None:                     # children count for their parent (the magazine's masthead)
        if name_in(o.name, names): return True
        o = o.parent
    return False


def emission(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*rgb, 1); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def job_masks(sc, key, state='day'):
    """masks.png (half size, for hover tests: R bed, G rail, B magazine) and glow.png (full size: their outlines as a
    white glow outside the silhouette, added in the browser on hover). night: masks_night.png / glow_night.png."""
    sfx = '' if state == 'day' else '_' + state
    dst = os.path.join(OUT, key, f'masks{sfx}.png'); gdst = os.path.join(OUT, key, f'glow{sfx}.png')
    if os.path.exists(dst): return None
    set_view(sc, key); render_settings(sc, 'depth'); lights_off(sc); restore_visibility(); set_state(state)
    sc.cycles.samples = 1 if FAST else 8; sc.cycles.filter_width = 1.0; sc.camera.data.dof.use_dof = False
    sc.render.film_transparent = True; sc.render.image_settings.color_mode = 'RGBA'
    mats = {g: emission('azur_mask_' + g, c) for g, c in zip(MASK_GROUPS, ((1, 0, 0), (0, 1, 0), (0, 0, 1)))}
    saved = {}
    for o in bpy.data.objects:
        if o.type not in ('MESH', 'CURVE', 'FONT', 'META') or o.hide_render: continue
        g = next((g for g, pre in MASK_GROUPS.items() if in_group(o, pre)), None)
        if g and hasattr(o.data, 'materials') and len(o.material_slots):
            saved[o.name] = [s_.material for s_ in o.material_slots]
            for s_ in o.material_slots: s_.material = mats[g]
        elif g and hasattr(o.data, 'materials'):
            o.data.materials.append(mats[g]); saved[o.name] = []
        else:
            o.is_holdout = True
    sc.view_settings.view_transform = 'Raw'
    png = dst.replace('.png', '_tmp.png'); secs = render_to(sc, png)
    for name, ms in saved.items():
        o = bpy.data.objects[name]
        if not ms: o.data.materials.pop(); continue
        for s_, m in zip(o.material_slots, ms): s_.material = m
    sc.camera.data.dof.use_dof = True; sc.cycles.filter_width = 1.5
    from PIL import Image
    from scipy import ndimage as ndi
    a = np.asarray(Image.open(png).convert('RGBA')).astype(np.float32) / 255.0; os.remove(png)
    m = np.stack([a[..., 3] * (a[..., c] > 0.5) for c in range(3)], -1)          # coverage per group
    h, w = m.shape[:2]; k = w / 2400.0
    glow = np.zeros_like(m)
    for c in range(3):
        mc = m[..., c]
        if mc.max() < 0.5: continue
        line = np.clip(ndi.maximum_filter(mc, size=max(3, int(round(5 * k)))) - mc, 0, 1)           # ~2 px line around it
        halo = ndi.gaussian_filter(ndi.maximum_filter(mc, size=max(3, int(round(9 * k)))), sigma=7 * k)
        glow[..., c] = np.clip(line * 0.95 + halo * (1 - mc) * 0.55, 0, 1)
    Image.fromarray((m[::2, ::2] * 255 + 0.5).astype(np.uint8)).save(dst, optimize=True)
    Image.fromarray((glow * 255 + 0.5).astype(np.uint8)).save(gdst, optimize=True)
    log('masks', key, state, secs, 's'); return [dst, gdst]


def frame_box(sc, objs, margin, sun_dirs=()):
    """Screen box (u0, v0, u1, v1 from top-left) of objects' bounding boxes, grown by margin; None if out of the frame.
    sun_dirs: also cover the shadows those sun directions throw onto the floor."""
    cam = sc.camera; pts = []
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); ws = [w]
            for d in sun_dirs:
                d = Vector(d).normalized()
                if d.z < -1e-3 and w.z > 0: ws.append(w + d * (w.z / -d.z))
            for x in ws:
                q = world_to_camera_view(sc, cam, x)
                if q.z > 0: pts.append((min(max(q.x, -1), 2), min(max(1 - q.y, -1), 2)))
    if not pts: return None
    u0, u1 = min(p[0] for p in pts) - margin, max(p[0] for p in pts) + margin
    v0, v1 = min(p[1] for p in pts) - margin, max(p[1] for p in pts) + margin
    if u1 < 0 or v1 < 0 or u0 > 1 or v0 > 1: return None
    return max(0, u0), max(0, v0), min(1, u1), min(1, v1)


def day_exr(sc, key, p, meta):
    path = os.path.join(EXR, key, p + '.exr')
    if not os.path.exists(path):           # the webp exists from an earlier run but not the linear pass: render it again
        set_view(sc, key); render_settings(sc, 'pass'); restore_visibility(); set_pass(sc, p)
        tmp = path.replace('.exr', '_day_tmp.exr'); os.makedirs(os.path.dirname(path), exist_ok=True)
        render_to(sc, tmp); os.replace(tmp, path)
    return path


def merge_boxes(boxes, gap):
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]; del boxes[j]; changed = True; break
            if changed: break
    return boxes


def job_state(sc, key, state, meta):
    """Patches for one time of day. The state's passes are rendered only around what changes (its objects, plus the
    floor shadows of the sun passes it uses), compared with day, and the rectangles that differ are stored as
    <key>/<state>/<pass>_<n>.webp, encoded with the day pass's scale so the browser copies them into the day textures."""
    st = meta.setdefault('states', {}).setdefault(key, {})
    if st.get(state, {}).get('complete'): return None
    mpath = os.path.join(OUT, 'passes.json')
    set_view(sc, key); bpy.context.view_layer.update()
    rx, ry = sc.render.resolution_x, sc.render.resolution_y
    suns = [SUN[p] for p in STATE_PASSES[state] if p in SUN]
    box = frame_box(sc, state_objects(state), 0.12, suns)
    if any(o.name == 'hall_light_area' for o in state_objects(state)):
        box = (0.0, 0.0, 1.0, 1.0)       # round 4: the hallway light (night) reaches walls and floor everywhere
    if box is None:
        st[state] = dict(rects=[], passes=[], res=[rx, ry], complete=True); json.dump(meta, open(mpath, 'w'), indent=1)
        log('state', key, state, 'nothing of it in the picture'); return [mpath]
    from scipy import ndimage as ndi
    e = 10        # the denoiser sees less at the region's edge: patches stay this far inside
    X0, X1 = int(box[0] * rx) + (e if box[0] > 0 else 0), int(np.ceil(box[2] * rx)) - (e if box[2] < 1 else 0)
    Y0, Y1 = int(box[1] * ry) + (e if box[1] > 0 else 0), int(np.ceil(box[3] * ry)) - (e if box[3] < 1 else 0)
    union = np.zeros((ry, rx), bool); renders = {}; secs_all = 0; changed = {}
    for p in STATE_PASSES[state]:
        exr = os.path.join(EXR, key, f'{state}_{p}.exr')
        if not os.path.exists(exr):
            set_view(sc, key); render_settings(sc, 'pass'); restore_visibility(); set_state(state); set_pass(sc, p); neon_quality(sc, p)
            r = sc.render; r.use_border = True; r.use_crop_to_border = False
            r.border_min_x, r.border_max_x = box[0], box[2]; r.border_min_y, r.border_max_y = 1 - box[3], 1 - box[1]
            tmp = exr.replace('.exr', '_tmp.exr'); secs_all += render_to(sc, tmp); os.replace(tmp, exr)
            sc.render.use_border = False
            stop_if_superseded()
        a = read_exr(exr); b = read_exr(day_exr(sc, key, p, meta)); scale = meta[key][p]
        keep = np.ones((ry, rx), bool); keep[Y0:Y1, X0:X1] = False
        a[keep] = b[keep]                              # outside the region the state is day
        d = np.abs(encode_rgb(a, scale).astype(np.int16) - encode_rgb(b, scale).astype(np.int16)).max(-1)
        d = ndi.uniform_filter(d.astype(np.float32), 3) > 2.5          # more than ~3 codes: a real change, not noise
        union |= d; renders[p] = a; changed[p] = float(d.mean())
    union = ndi.binary_opening(union, iterations=1)
    lab, n = ndi.label(ndi.binary_dilation(union, iterations=14))
    pad = 12
    boxes = [[max(X0, s_[1].start - pad), max(Y0, s_[0].start - pad), min(X1, s_[1].stop + pad), min(Y1, s_[0].stop + pad)]
             for s_ in ndi.find_objects(lab) if s_ is not None and (s_[1].stop - s_[1].start) * (s_[0].stop - s_[0].start) > 400]
    boxes = merge_boxes(boxes, 24)
    while len(boxes) > 6: boxes = merge_boxes(boxes, int(len(boxes) * 40))
    out = []
    for p, a in renders.items():
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            dst = os.path.join(OUT, key, state, f'{p}_{i}.webp')
            save_webp(encode_rgb(a[y0:y1, x0:x1], meta[key][p]), dst, pass_quality(p)); out.append(dst)
    st[state] = dict(rects=boxes, passes=list(renders), res=[rx, ry], complete=True)
    json.dump(meta, open(mpath, 'w'), indent=1)
    for p in renders: os.remove(os.path.join(EXR, key, f'{state}_{p}.exr'))      # only the day passes are kept
    area = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes) / (rx * ry)
    log('state', key, state, len(boxes), f'patches, {area:.0%} of the picture (region {(X1 - X0) * (Y1 - Y0) / (rx * ry):.0%}),',
        'changed per pass', {k: round(v, 3) for k, v in changed.items()}, round(secs_all), 's')
    return out + [mpath]


def main():
    hand_over_to_watch_v2()
    ensure_blend()
    sc = open_scene()
    meta_path = os.path.join(OUT, 'passes.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    views = [v for v in VIEWS if not ONLY or v in ONLY]
    jobs = [('projections', lambda: job_projections(sc))]
    if HI:
        # quick ones first (hover and click areas), then the day passes, the fallback stills and the times of day
        for v in views:
            jobs += [(f'masks {v}', (lambda v=v: job_masks(sc, v))), (f'masks {v} night', (lambda v=v: job_masks(sc, v, 'night')))]
            if v != 'bed': jobs += [(f'ids {v}', (lambda v=v: job_ids(sc, v))), (f'window {v}', (lambda v=v: job_window(sc, v)))]
            jobs += [(f'depth {v}', (lambda v=v: job_depth(sc, v)))]
        for v in [x for x in ('room', 'rail', 'bed', 'rail_m') if x in views]:
            jobs += [(f'pass {v} {p}', (lambda v=v, p=p: job_pass(sc, v, p, meta))) for p in PASSES]
        jobs += [(f'beauty {v}', (lambda v=v: job_beauty(sc, v))) for v in views]
        for v in [x for x in ('room', 'bed', 'rail', 'rail_m') if x in views]:
            jobs += [(f'state {v} {st}', (lambda v=v, st=st: job_state(sc, v, st, meta))) for st in ('evening', 'night', 'morning')]
    else:
        jobs += [(f'beauty {v}', (lambda v=v: job_beauty(sc, v))) for v in views]
        jobs += [(f'depth {v}', (lambda v=v: job_depth(sc, v))) for v in views]
        jobs += [(f'ids {v}', (lambda v=v: job_ids(sc, v))) for v in views if v != 'bed']
        jobs += [(f'window {v}', (lambda v=v: job_window(sc, v))) for v in views if v != 'bed']
        for v in [x for x in ('rail', 'room', 'rail_m', 'bed') if x in views]:
            jobs += [(f'pass {v} {p}', (lambda v=v, p=p: job_pass(sc, v, p, meta))) for p in PASSES]
        # a chosen garment, taken off the rail toward the camera (desktop rail, then phone rail)
        for v in [x for x in ('rail', 'rail_m') if x in views]:
            for i in range(6):
                jobs += [(f'selected {v}@{i} {w}', (lambda v=v, i=i, w=w: job_selected(sc, v, i, w, meta))) for w in ['beauty'] + PASSES]
    failed = []
    for name, fn in jobs:
        stop_if_superseded()
        try:
            restore_visibility()
            out = fn()
            if out: git_save(out, f'AZUR render: {name}')
        except Exception as e:
            import traceback; log('FAILED', name, e); log(traceback.format_exc()); failed.append(name)
            sc = open_scene()
    git_push(force=True)
    log('queue finished' + (f' with {len(failed)} failed jobs: ' + ', '.join(failed) if failed else ''))
    if failed: sys.exit(1)


if __name__ == '__main__':
    main()
