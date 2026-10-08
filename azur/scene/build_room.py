# AZUR bedroom — scene builder.
# Usage: python3 scene/build_room.py -- <preview|final> <out.png> [save.blend]
# Needs: pip install bpy==5.0.1 (Python 3.11) and the Poly Haven assets from scene/fetch_assets.py
import bpy, bmesh, math, json, random, os, sys
from mathutils import Vector, Euler, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garment          # jerseys: cloth-simulated shells on wooden hangers (round 3)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
A = ROOT + '/assets'
PH = os.environ.get('AZUR_CACHE', ROOT + '/.cache/ph')      # Poly Haven downloads (scene/fetch_assets.py)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['preview', ROOT + '/renders/out.png']
MODE, OUT = argv[0], argv[1]
BLEND = argv[2] if len(argv) > 2 else None
random.seed(11)

# ---------------------------------------------------------------- scene config (metres, Z up)
ROOM = dict(w=3.4, d=4.0, h=2.5)
WIN = dict(y0=2.30, y1=3.30, z0=0.92, z1=2.20, reveal=0.30)       # right wall opening
RAIL = dict(x0=0.76, x1=2.76, y=2.95, z=1.66, r=0.0125)      # starts right of the desk (desk ends at x 0.60)
CAM = dict(loc=(1.25, 0.22, 0.86), target=(2.0, 3.40, 1.02), lens=24, fstop=2.8)
SUN = dict(dir=(-1.0, 0.22, -0.12), strength=3.0, color=(1.0, 0.60, 0.33), angle=0.8)
NEON = dict(x=1.76, z=2.22, color=(0.086, 0.722, 1.0), strength=1.6)   # Azur Electric #16B8FF
JERSEYS = ['frankfurt', 'berlin', 'brasilien', 'deutschland', 'tuerkei']
JERSEY_H = 0.74
FAN = math.radians(25)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection

# ---------------------------------------------------------------- helpers
def link(o):
    col.objects.link(o); return o

def apply_tf(o, loc=True, rot=True, scale=True):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=loc, rotation=rot, scale=scale)

def box(name, x0, x1, y0, y1, z0, z1, mat=None, bevel=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.scale = (x1 - x0, y1 - y0, z1 - z0); o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    apply_tf(o)
    if bevel:
        m = o.modifiers.new('bev', 'BEVEL'); m.width = bevel; m.segments = 3; m.limit_method = 'NONE'
    if mat: o.data.materials.append(mat)
    return o

def cyl(name, p0, p1, r, mat=None, verts=24):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object; o.name = name
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    return o

def img(path, cs='sRGB'):
    i = bpy.data.images.load(path, check_existing=True); i.colorspace_settings.name = cs; return i

def tex_paths(key):
    d = f'{PH}/tex/{key}'
    return {m: f'{d}/{key}_{m}_2k.jpg' for m in ('Diffuse', 'nor_gl', 'Rough')}

def pbr(name, key, tile=1.0, tint=(1, 1, 1), rough=(0.0, 1.0), nstr=1.0, coords='Object', box_blend=0.25, sheen=0.0, spec=0.5):
    t = tex_paths(key)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / tile,) * 3
    L.new(tc.outputs[coords], mp.inputs[0])
    def tn(path, cs):
        n = N.new('ShaderNodeTexImage'); n.image = img(path, cs)
        if coords == 'Object': n.projection = 'BOX'; n.projection_blend = box_blend
        L.new(mp.outputs[0], n.inputs[0]); return n
    dn = tn(t['Diffuse'], 'sRGB')
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
    L.new(dn.outputs[0], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
    L.new(mix.outputs[2], b.inputs['Base Color'])
    rn = tn(t['Rough'], 'Non-Color')
    mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = rough[0]; mr.inputs['To Max'].default_value = rough[1]
    L.new(rn.outputs[0], mr.inputs[0]); L.new(mr.outputs[0], b.inputs['Roughness'])
    nn = tn(t['nor_gl'], 'Non-Color'); nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
    L.new(nn.outputs[0], nm.inputs['Color']); L.new(nm.outputs[0], b.inputs['Normal'])
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Specular IOR Level'].default_value = spec
    return m

def flat(name, color, rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    for k, v in kw.items(): b.inputs[k].default_value = v
    return m

def import_gltf(name, loc=(0, 0, 0), rot_z=0.0, scale=1.0, keep=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f'{PH}/models/{name}/{name}_1k.gltf')
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    if keep is not None:
        for i, o in enumerate(meshes):
            if i not in keep: bpy.data.objects.remove(o, do_unlink=True)
        meshes = [o for i, o in enumerate(meshes) if i in keep]
    root = bpy.data.objects.new(name + '_root', None); link(root)
    for o in new:
        if o.name in bpy.data.objects and o.parent is None: o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, rot_z); root.scale = (scale,) * 3
    return root, meshes

# ---------------------------------------------------------------- render settings
sc.render.engine = 'CYCLES'
cy = sc.cycles; cy.device = 'CPU'
if MODE == 'final':
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080; cy.samples = 256; cy.adaptive_threshold = 0.02
else:
    sc.render.resolution_x, sc.render.resolution_y = 960, 540; cy.samples = 48
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 10; cy.diffuse_bounces = 5; cy.glossy_bounces = 4; cy.transmission_bounces = 8; cy.transparent_max_bounces = 24
cy.caustics_reflective = False; cy.caustics_refractive = False; cy.blur_glossy = 0.6
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.view_settings.exposure = 2.65
sc.render.image_settings.file_format = 'PNG'

# ---------------------------------------------------------------- world (park HDRI, seen through the window)
w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True; N = w.node_tree.nodes; L = w.node_tree.links
env = N.new('ShaderNodeTexEnvironment'); env.image = img(f'{PH}/hdri/eilenriede_park_4k.hdr', 'Linear Rec.709')
tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(200))
L.new(tc.outputs['Generated'], mp.inputs[0]); L.new(mp.outputs[0], env.inputs[0])
bg = N['Background']; bg.inputs['Strength'].default_value = 2.2
warm = N.new('ShaderNodeMix'); warm.data_type = 'RGBA'; warm.blend_type = 'MULTIPLY'; warm.inputs['Factor'].default_value = 1.0
warm.inputs[7].default_value = (1.0, 0.86, 0.72, 1)
L.new(env.outputs[0], warm.inputs[6]); L.new(warm.outputs[2], bg.inputs['Color'])

# ---------------------------------------------------------------- materials
M = {}
M['wall'] = pbr('wall', 'white_plaster_02', tile=1.6, tint=(0.93, 0.91, 0.86), rough=(0.75, 0.95), nstr=0.35)
M['ceil'] = pbr('ceil', 'white_plaster_02', tile=1.6, tint=(0.95, 0.94, 0.91), rough=(0.85, 0.95), nstr=0.2)
M['floor'] = pbr('floor', 'laminate_floor_02', tile=1.8, tint=(0.92, 0.86, 0.80), rough=(0.32, 0.6), nstr=0.6)
M['oak'] = pbr('oak', 'oak_veneer_01', tile=0.9, tint=(0.98, 0.9, 0.78), rough=(0.4, 0.7), nstr=0.4)
M['duvet'] = pbr('duvet', 'cotton_jersey', tile=0.12, tint=(1.0, 0.99, 0.97), rough=(0.85, 1.0), nstr=0.5, coords='UV', sheen=0.4)
_db = M['duvet'].node_tree.nodes['Principled BSDF']   # keep the cotton weave in the normal map, plain coloured cover
for l in list(M['duvet'].node_tree.links):
    if l.to_socket == _db.inputs['Base Color']: M['duvet'].node_tree.links.remove(l)
_db.inputs['Base Color'].default_value = (0.14, 0.24, 0.40, 1)   # washed sky-blue cover (pillow stays white)
M['rug'] = pbr('rug', 'dirty_carpet', tile=0.9, tint=(0.62, 0.66, 0.70), rough=(0.85, 1.0), nstr=0.8, sheen=0.3)
M['paint'] = flat('white_paint', (0.88, 0.87, 0.84), rough=0.35)
M['pvc'] = flat('pvc', (0.90, 0.90, 0.88), rough=0.3)
M['sill'] = flat('sill', (0.80, 0.79, 0.76), rough=0.18, **{'Coat Weight': 0.3})
M['chrome'] = flat('chrome', (0.86, 0.86, 0.86), rough=0.16, metal=1.0)
M['wire'] = flat('wire', (0.75, 0.75, 0.74), rough=0.25, metal=1.0)
M['hanger'] = pbr('hanger', 'oak_veneer_01', tile=0.3, tint=(0.72, 0.52, 0.32), rough=(0.25, 0.4), nstr=0.2)
M['rubber'] = flat('rubber', (0.03, 0.03, 0.03), rough=0.6)
M['gold'] = flat('gold', (1.0, 0.72, 0.32), rough=0.28, metal=1.0)
M['silver'] = flat('silver', (0.88, 0.88, 0.9), rough=0.22, metal=1.0)
M['marble'] = flat('base', (0.06, 0.06, 0.07), rough=0.25)
M['ink'] = flat('ink', (0.04, 0.04, 0.05), rough=0.7)
M['paper'] = flat('paper', (0.86, 0.82, 0.72), rough=0.8, **{'Sheen Weight': 0.1})
M['tape'] = flat('tape', (0.95, 0.93, 0.86), rough=0.4, **{'Transmission Weight': 0.6, 'Alpha': 0.55})
glass = flat('glass', (1, 1, 1), rough=0.0, **{'Transmission Weight': 1.0, 'IOR': 1.5})
M['glass'] = glass

# ---------------------------------------------------------------- room shell
W, D, H = ROOM['w'], ROOM['d'], ROOM['h']
box('floor', -0.3, W + 0.4, -0.3, D + 0.3, -0.05, 0.0, M['floor'])
box('ceiling', -0.3, W + 0.4, -0.3, D + 0.3, H, H + 0.05, M['ceil'])
box('wall_back', -0.3, W + 0.4, D, D + 0.2, 0, H, M['wall'])
box('wall_left', -0.2, 0.0, -0.3, D, 0, H, M['wall'])
box('wall_front', -0.3, W + 0.4, -0.3, -0.1, 0, H, M['wall'])
R = WIN['reveal']
box('wall_right_low', W, W + R, -0.3, D, 0, WIN['z0'], M['wall'])
box('wall_right_high', W, W + R, -0.3, D, WIN['z1'], H, M['wall'])
box('wall_right_front', W, W + R, -0.3, WIN['y0'], WIN['z0'], WIN['z1'], M['wall'])
box('wall_right_back', W, W + R, WIN['y1'], D, WIN['z0'], WIN['z1'], M['wall'])
# skirting
for nm, args in {'sk_back': (0, W, D - 0.014, D, 0, 0.06), 'sk_left': (0, 0.014, 0, D, 0, 0.06), 'sk_right': (W - 0.014, W, 0, D, 0, 0.06)}.items():
    box(nm, *args, M['paint'])

# ---------------------------------------------------------------- window: PVC frame, glass, sill, radiator
fx0, fx1 = W + 0.17, W + 0.24     # frame sits in the outer part of the reveal
y0, y1, z0, z1 = WIN['y0'], WIN['y1'], WIN['z0'], WIN['z1']
fw = 0.075
box('frame_b', fx0, fx1, y0, y1, z0, z0 + fw, M['pvc'], 0.004)
box('frame_t', fx0, fx1, y0, y1, z1 - fw, z1, M['pvc'], 0.004)
box('frame_l', fx0, fx1, y0, y0 + fw, z0, z1, M['pvc'], 0.004)
box('frame_r', fx0, fx1, y1 - fw, y1, z0, z1, M['pvc'], 0.004)
sw = 0.055   # sash
ym = (y0 + y1) / 2; mw = 0.045   # mullion: a double window (Dreh-Kipp), the most common German kind
box('mullion', fx0, fx1, ym - mw, ym + mw, z0 + fw, z1 - fw, M['pvc'], 0.003)
gasket = flat('gasket', (0.025, 0.025, 0.028), rough=0.55)
M['alu'] = flat('alu', (0.82, 0.82, 0.83), rough=0.32, metal=1.0)
for side, (sy0, sy1) in (('l', (y0 + fw, ym - mw)), ('r', (ym + mw, y1 - fw))):
    box('sash_b' + side, fx0 - 0.02, fx1 - 0.03, sy0, sy1, z0 + fw, z0 + fw + sw, M['pvc'], 0.003)
    box('sash_t' + side, fx0 - 0.02, fx1 - 0.03, sy0, sy1, z1 - fw - sw, z1 - fw, M['pvc'], 0.003)
    box('sash_l' + side, fx0 - 0.02, fx1 - 0.03, sy0, sy0 + sw, z0 + fw, z1 - fw, M['pvc'], 0.003)
    box('sash_r' + side, fx0 - 0.02, fx1 - 0.03, sy1 - sw, sy1, z0 + fw, z1 - fw, M['pvc'], 0.003)
    gx = fx0 - 0.005    # black glazing gasket where the sash meets the glass
    box('gasket_b' + side, gx - 0.004, gx, sy0 + sw, sy1 - sw, z0 + fw + sw, z0 + fw + sw + 0.004, gasket)
    box('gasket_t' + side, gx - 0.004, gx, sy0 + sw, sy1 - sw, z1 - fw - sw - 0.004, z1 - fw - sw, gasket)
    box('gasket_l' + side, gx - 0.004, gx, sy0 + sw, sy0 + sw + 0.004, z0 + fw + sw, z1 - fw - sw, gasket)
    box('gasket_r' + side, gx - 0.004, gx, sy1 - sw - 0.004, sy1 - sw, z0 + fw + sw, z1 - fw - sw, gasket)
    # aluminium handle on the side that opens (next to the mullion), lever pointing down = closed
    hy = (sy1 - sw / 2) if side == 'l' else (sy0 + sw / 2); hz = (z0 + z1) / 2 + 0.02
    box('handle_plate' + side, fx0 - 0.032, fx0 - 0.02, hy - 0.016, hy + 0.016, hz - 0.035, hz + 0.035, M['alu'], 0.004)
    cyl('handle_neck' + side, (fx0 - 0.032, hy, hz), (fx0 - 0.05, hy, hz), 0.011, M['alu'], verts=20)
    cyl('handle_lever' + side, (fx0 - 0.05, hy, hz + 0.005), (fx0 - 0.055, hy, hz - 0.115), 0.0085, M['alu'], verts=16)
# roller-shutter box behind a white cover above the window, belt winder on the wall beside it (very German)
box('shutter_cover', W - 0.012, W, y0 - 0.06, y1 + 0.06, z1 + 0.03, z1 + 0.24, M['paint'], 0.003)
box('shutter_cover_seam', W - 0.014, W - 0.012, y0 - 0.06, y1 + 0.06, z1 + 0.135, z1 + 0.137, gasket)
box('belt_winder', W - 0.032, W, y1 + 0.11, y1 + 0.175, 0.93, 1.14, M['paint'], 0.006)
box('belt_slot', W - 0.034, W - 0.032, y1 + 0.135, y1 + 0.15, 1.11, 1.135, gasket)
box('belt', W - 0.008, W - 0.004, y1 + 0.132, y1 + 0.153, 1.13, z1 + 0.03, flat('belt', (0.78, 0.74, 0.66), rough=0.8))
g = box('glass', fx0 + 0.008, fx0 + 0.016, y0 + fw + sw, y1 - fw - sw, z0 + fw + sw, z1 - fw - sw, M['glass'])
g.visible_shadow = False
box('sill', W - 0.16, W + 0.17, y0 - 0.03, y1 + 0.03, z0 - 0.025, z0, M['sill'], 0.003)
# panel radiator (Plattenheizkörper) under the window
rx0, rx1 = W - 0.12, W - 0.04
rad = box('radiator', rx0, rx1, y0 + 0.06, y1 - 0.06, 0.16, 0.74, M['paint'], 0.006)
rad.data.materials[0] = flat('radiator', (0.92, 0.91, 0.88), rough=0.28)
for i in range(int((y1 - y0 - 0.14) / 0.033)):
    yy = y0 + 0.08 + i * 0.033
    box(f'rib{i}', rx0 - 0.006, rx0, yy, yy + 0.014, 0.19, 0.71, rad.data.materials[0])
cyl('rad_pipe', (rx1 - 0.02, y1 - 0.09, 0.0), (rx1 - 0.02, y1 - 0.09, 0.17), 0.009, M['paint'])
# window portal for cleaner sky sampling
pl = bpy.data.lights.new('portal', 'AREA'); pl.shape = 'RECTANGLE'; pl.size = (y1 - y0); pl.size_y = (z1 - z0)
for tgt in (pl, getattr(pl, 'cycles', None)):
    try:
        if tgt is not None and hasattr(tgt, 'is_portal'): tgt.is_portal = True; print('PORTAL_ON'); break
    except Exception as ex: print('portal', ex)
po = link(bpy.data.objects.new('portal', pl)); po.location = (W + R - 0.01, (y0 + y1) / 2, (z0 + z1) / 2)
po.rotation_euler = Vector((-1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()

# curtain: one linen panel pulled to the side of the window, gathered on a black rod
rod_x, rod_z = W - 0.075, z1 + 0.3
M['rod'] = flat('rod', (0.03, 0.03, 0.03), rough=0.35, metal=0.6)
cyl('curtain_rod', (rod_x, y0 - 0.3, rod_z), (rod_x, y1 + 0.5, rod_z), 0.011, M['rod'], verts=20)
for yy in (y0 - 0.25, y1 + 0.45):
    cyl('rod_bracket', (W, yy, rod_z), (rod_x, yy, rod_z), 0.006, M['rod'], verts=12)
cy0, cy1, cz1, cz0 = y1 - 0.04, y1 + 0.42, rod_z - 0.03, 0.04   # on the far side of the window: it frames it without hiding it
bpy.ops.mesh.primitive_grid_add(x_subdivisions=90, y_subdivisions=70, size=1.0)
cur = bpy.context.object; cur.name = 'curtain'
crnd = random.Random(7)
ph = [crnd.uniform(0, 6.28) for _ in range(4)]
for v in cur.data.vertices:
    u, t = v.co.x + 0.5, v.co.y + 0.5          # u along the rod 0..1, t bottom 0 .. top 1
    yy = cy0 + u * (cy1 - cy0) + (1 - t) * 0.05 * (u - 0.5)       # hem flares a little
    lam = 0.105 + 0.02 * (1 - t)
    amp = 0.028 + 0.012 * (1 - t) + 0.006 * math.sin(u * 9 + ph[0])
    xx = rod_x - 0.012 - amp * (1 + math.sin((yy - cy0) / lam * 2 * math.pi + 0.3 * math.sin(t * 5 + ph[1]))) \
         - 0.035 * (1 - t) ** 2 * (0.6 + 0.4 * math.sin(u * 4 + ph[2]))   # the hem swings a little into the room
    zz = cz0 + t * (cz1 - cz0) - 0.01 * math.sin(u * 13 + ph[3]) * (1 - t) ** 3
    v.co = (xx, yy, zz)
cur.modifiers.new('sol', 'SOLIDIFY').thickness = 0.003
cur.modifiers.new('sub', 'SUBSURF').levels = 1
bpy.ops.object.shade_smooth()
lin = pbr('curtain', 'rough_linen', tile=0.35, tint=(0.80, 0.70, 0.56), rough=(0.85, 1.0), nstr=0.6, coords='UV', sheen=0.3)
lb = lin.node_tree.nodes['Principled BSDF']
try: lb.inputs['Subsurface Weight'].default_value = 0.25; lb.inputs['Subsurface Radius'].default_value = (0.02, 0.015, 0.01)
except Exception: pass
cur.data.materials.append(lin)
for i in range(14):   # rings on the rod
    ry = cy0 + 0.02 + i * (cy1 - cy0 - 0.04) / 13
    bpy.ops.mesh.primitive_torus_add(major_radius=0.016, minor_radius=0.0025, location=(rod_x, ry, rod_z), rotation=(0, math.radians(90), 0))
    rg = bpy.context.object; rg.name = 'curtain_ring'; rg.data.materials.append(M['rod'])

# ceiling spot aimed at the rail (lights the jerseys; its light is its own pass, so the prototype can dose it)
SPOT = dict(loc=(2.05, 2.1, ROOM['h'] - 0.08), aim=(1.55, 2.95, 1.25))
cyl('spot_base', (SPOT['loc'][0], SPOT['loc'][1], ROOM['h']), (SPOT['loc'][0], SPOT['loc'][1], ROOM['h'] - 0.012), 0.04, M['rod'], verts=24)
_d = (Vector(SPOT['aim']) - Vector(SPOT['loc'])).normalized()
cyl('spot_arm', (SPOT['loc'][0], SPOT['loc'][1], ROOM['h'] - 0.012), SPOT['loc'], 0.006, M['rod'], verts=10)
cyl('spot_can', Vector(SPOT['loc']) - _d * 0.02, Vector(SPOT['loc']) + _d * 0.09, 0.032, M['rod'], verts=24)

# ---------------------------------------------------------------- sun
sl = bpy.data.lights.new('sun', 'SUN'); sl.energy = SUN['strength']; sl.color = SUN['color']; sl.angle = math.radians(SUN['angle'])
so = link(bpy.data.objects.new('sun', sl)); so.rotation_euler = Vector(SUN['dir']).normalized().to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- bed
bx0, bx1, by0, by1 = 0.02, 0.98, -0.25, 2.0
box('bed_side', bx1 - 0.04, bx1, by0, by1, 0.12, 0.32, M['oak'], 0.004)
box('bed_side_l', bx0, bx0 + 0.04, by0, by1, 0.12, 0.32, M['oak'], 0.004)
box('bed_foot', bx0, bx1, by1 - 0.03, by1 + 0.01, 0.0, 0.52, M['oak'], 0.005)
for yy in (by1 - 0.06,):
    for xx in (bx0 + 0.02, bx1 - 0.06):
        box('leg', xx, xx + 0.05, yy, yy + 0.05, 0.0, 0.14, M['oak'], 0.003)
matt = box('mattress', bx0 + 0.04, bx1 - 0.04, by0, by1 - 0.035, 0.24, 0.42, flat('mattress', (0.93, 0.92, 0.9), rough=0.8, **{'Sheen Weight': 0.3}), 0.035)
matt.modifiers.new('sub', 'SUBSURF').levels = 1
bpy.ops.object.select_all(action='DESELECT'); matt.select_set(True); bpy.context.view_layer.objects.active = matt; bpy.ops.object.shade_smooth()

# pillow at the head end (collides with the duvet)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.5, 0.16, 0.5))
pil = bpy.context.object; pil.name = 'pillow'; pil.scale = (0.66, 0.44, 0.15); apply_tf(pil)
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
pil.rotation_euler = (0, math.radians(9), math.radians(-24)); pil.location += Vector((-0.03, 0.06, 0.02))   # slept on, pushed crooked
pil.modifiers.new('sub', 'SUBSURF').levels = 3
ptx = bpy.data.textures.new('pillownoise', 'CLOUDS'); ptx.noise_scale = 0.6
pd = pil.modifiers.new('disp', 'DISPLACE'); pd.texture = ptx; pd.strength = 0.01
bpy.ops.object.shade_smooth()
pil.data.materials.append(flat('pillow', (0.86, 0.855, 0.83), rough=0.85, **{'Sheen Weight': 0.4}))
pil.modifiers.new('col', 'COLLISION')

# duvet: thrown back the way a kid leaves it in the morning. Simulated like it happens: the duvet lies over the
# bed, its head edge is pulled back toward the foot end in an arc (pinned to a moving hook), then let go to settle.
# A filled duvet makes few, broad folds: coarse cloth grid, soft rumples, light smoothing.
DUVET = dict(grid=(36, 64), cx=0.60, z=0.52, amp=0.05, fx=9.0, fy=6.5, push=0.06, mass=0.5, bend=0.6,
             pull_mid=(0.70, 0.70, 0.95), pull_to=(1.05, 1.30, 0.50), pull_rz=52, pull_f=52, frames=60, settle=50)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=56, y_subdivisions=92, size=1.0)   # the old grid, only to keep the
_tmp = bpy.context.object; _n = len(_tmp.data.vertices); bpy.data.objects.remove(_tmp, do_unlink=True)
for _ in range(_n): random.uniform(-0.006, 0.006)   # seeded sequence identical for everything built after the bed
rnd = random.Random(23); DV = DUVET
bpy.ops.mesh.primitive_grid_add(x_subdivisions=DV['grid'][0], y_subdivisions=DV['grid'][1], size=1.0, location=(DV['cx'], 1.02, DV['z']))
duv = bpy.context.object; duv.name = 'duvet'; duv.scale = (1.04, 1.90, 1); apply_tf(duv)   # must not start inside the wall
bm = bmesh.new(); bm.from_mesh(duv.data)
for v in bm.verts:
    x, y = v.co.x, v.co.y
    v.co.z += DV['amp'] * math.sin(x * DV['fx'] + y * 1.4 + 0.8) * math.sin(y * DV['fy'] + 0.4) + rnd.uniform(-0.002, 0.002)
    v.co.z += 0.025 * math.sin(x * 17.0 + y * 6.0) * math.sin(y * 13.0 - x * 4.0)     # teen bed: crumples, not waves
    v.co.x += DV['push'] * math.sin(y * 3.1)       # the cover is pushed together a little across the bed
bm.to_mesh(duv.data); bm.free()
for o in (matt,):
    c = o.modifiers.new('col', 'COLLISION'); o.collision.thickness_outer = 0.01; o.collision.cloth_friction = 80   # holds the overhanging duvet
floor_c = bpy.data.objects['floor']; floor_c.modifiers.new('col', 'COLLISION')
for nm in ('bed_foot', 'bed_side', 'bed_side_l', 'wall_left'):
    bpy.data.objects[nm].modifiers.new('col', 'COLLISION')

def cloth_on(o, mass, bend, pin=None):
    cl = o.modifiers.new('cloth', 'CLOTH'); cs = cl.settings
    cs.quality = 8; cs.mass = mass; cs.tension_stiffness = 15; cs.compression_stiffness = 15; cs.shear_stiffness = 8; cs.bending_stiffness = bend
    cs.air_damping = 1.5
    if pin: cs.vertex_group_mass = pin
    cl.collision_settings.use_self_collision = True; cl.collision_settings.self_distance_min = 0.012; cl.collision_settings.distance_min = 0.01
    return cl

def bake_cloth(o, frames):
    """Run the simulation and copy the result into the mesh (applying a cloth modifier keeps frame 1)."""
    pc = o.modifiers['cloth'].point_cache; pc.frame_start = 1; pc.frame_end = frames
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1): sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get(); coords = [v.co.copy() for v in o.evaluated_get(dg).data.vertices]
    for m in [m for m in o.modifiers if m.type in ('CLOTH', 'HOOK')]: o.modifiers.remove(m)
    for v, c in zip(o.data.vertices, coords): v.co = c
    sc.frame_set(1)

# stage 1: the head edge is pulled back on a hook
ymin = min(v.co.y for v in duv.data.vertices)
vg = duv.vertex_groups.new(name='pin'); vg.add([v.index for v in duv.data.vertices if v.co.y < ymin + 0.04], 1.0, 'REPLACE')
pull = link(bpy.data.objects.new('duvet_pull', None)); pull.location = (DV['cx'], ymin, DV['z']); bpy.context.view_layer.update()
hk = duv.modifiers.new('hook', 'HOOK'); hk.object = pull; hk.vertex_group = 'pin'; hk.center = pull.location; hk.matrix_inverse = pull.matrix_world.inverted()
pull.keyframe_insert('location', frame=1); pull.keyframe_insert('rotation_euler', frame=1)
pull.location = DV['pull_mid']; pull.keyframe_insert('location', frame=DV['pull_f'] // 2)
pull.location = DV['pull_to']; pull.rotation_euler = (0, 0, math.radians(DV['pull_rz']))
pull.keyframe_insert('location', frame=DV['pull_f']); pull.keyframe_insert('rotation_euler', frame=DV['pull_f'])
cloth_on(duv, DV['mass'], DV['bend'], pin='pin'); bake_cloth(duv, DV['frames'])
# stage 2: let go, the pulled edge drops onto the duvet
duv.vertex_groups.remove(vg); bpy.data.objects.remove(pull, do_unlink=True)
cloth_on(duv, DV['mass'], DV['bend']); bake_cloth(duv, DV['settle'])

# scarf over the foot board (invented club colours: navy / sky / white)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=70, size=1.0, location=(0.62, by1 + 0.02, 0.78))
scarf = bpy.context.object; scarf.name = 'scarf'; scarf.scale = (0.17, 1.35, 1); scarf.rotation_euler = (0, 0, math.radians(88)); apply_tf(scarf)
sc2 = scarf.modifiers.new('cloth', 'CLOTH'); sc2.settings.quality = 6; sc2.settings.mass = 0.25; sc2.settings.bending_stiffness = 0.3
bake_cloth(scarf, 90)
for o, th, lv, sf, si in ((duv, 0.05, 2, 0.45, 2), (scarf, 0.01, 1, 0.6, 6)):
    sm_ = o.modifiers.new('smooth', 'SMOOTH'); sm_.factor = sf; sm_.iterations = si   # calm the collision jitter
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = th; s.offset = 1
    sb_ = o.modifiers.new('sub', 'SUBSURF'); sb_.levels = lv; sb_.render_levels = lv
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o; bpy.ops.object.shade_smooth()
duv.data.materials.append(M['duvet'])
sm = bpy.data.materials.new('scarf'); sm.use_nodes = True; nt = sm.node_tree
wave = nt.nodes.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'X'; wave.inputs['Scale'].default_value = 2.2; wave.wave_profile = 'SAW'
cr = nt.nodes.new('ShaderNodeValToRGB'); e = cr.color_ramp; e.interpolation = 'CONSTANT'
e.elements[0].color = (0.02, 0.05, 0.16, 1); e.elements[1].position = 0.55; e.elements[1].color = (0.92, 0.92, 0.9, 1)
e.elements.new(0.75).color = (0.25, 0.55, 0.85, 1)
uv = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(uv.outputs['UV'], wave.inputs[0])
nt.links.new(wave.outputs['Fac'], cr.inputs[0]); nt.links.new(cr.outputs[0], nt.nodes['Principled BSDF'].inputs['Base Color'])
nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9; nt.nodes['Principled BSDF'].inputs['Sheen Weight'].default_value = 0.8
scarf.data.materials.append(sm)

# ---------------------------------------------------------------- garment rail (chrome, freestanding)
rz, ry, r = RAIL['z'], RAIL['y'], RAIL['r']
for x in (RAIL['x0'], RAIL['x1']):
    cyl('upright', (x, ry, 0.075), (x, ry, rz), r, M['chrome'])
    cyl('foot', (x, ry - 0.28, 0.05), (x, ry + 0.28, 0.05), 0.012, M['chrome'])
    for yy in (ry - 0.27, ry + 0.27):
        cyl('caster', (x - 0.012, yy, 0.025), (x + 0.012, yy, 0.025), 0.024, M['rubber'])
cyl('bar', (RAIL['x0'] - 0.03, ry, rz), (RAIL['x1'] + 0.03, ry, rz), r, M['chrome'])

def hanger(x, yaw):
    """Wooden hanger with a swivel hook; returns the attach matrix for the garment (top centre)."""
    org = Vector((x, ry + 0.018, rz - 0.072))
    # hook (in the YZ plane, around the bar)
    pts = [(0, 0, -0.065), (0, 0, 0), (0, 0, 0.045), (0, 0.004, 0.064), (0, -0.006, 0.084), (0, -0.024, 0.091), (0, -0.04, 0.08), (0, -0.043, 0.064), (0, -0.036, 0.055)]
    cu = bpy.data.curves.new('hook', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0022; cu.bevel_resolution = 3
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
    hk = link(bpy.data.objects.new('hook', cu)); hk.location = org; hk.data.materials.append(M['wire'])
    sm2 = hk.modifiers.new('sub', 'SUBSURF')
    # body: shallow V, rotated by the swivel
    cu2 = bpy.data.curves.new('hbody', 'CURVE'); cu2.dimensions = '3D'; cu2.bevel_depth = 0.009; cu2.bevel_resolution = 4
    sp2 = cu2.splines.new('BEZIER'); sp2.bezier_points.add(2)
    for i, p in enumerate([(-0.215, 0, -0.06), (0, 0, -0.012), (0.215, 0, -0.06)]):
        bp = sp2.bezier_points[i]; bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    hb = link(bpy.data.objects.new('hanger', cu2)); hb.location = org; hb.rotation_euler = (0, 0, yaw); hb.data.materials.append(M['hanger'])
    hb.scale = (1, 1.0, 1.0); hanger.body = hb
    return Matrix.Translation(org + Vector((0, 0, -0.008))) @ Matrix.Rotation(yaw, 4, 'Z')

def garment_plane(name, image_path, aspect, mtx, h=JERSEY_H, push=0.012, tint=(1, 1, 1)):
    w = h * aspect
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=28, y_subdivisions=28, size=1.0)
    o = bpy.context.object; o.name = name
    o.scale = (w, h, 1); o.rotation_euler = (math.radians(90), 0, 0); o.location = (0, 0, -h / 2); apply_tf(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        x, z = v.co.x / w, (v.co.z + h) / h          # x -0.5..0.5, z 0..1 (bottom..top)
        # body volume: chest bows toward the viewer, hem hangs slightly back, soft vertical folds
        v.co.y -= push * 2.4 * (1 - (2 * x) ** 2) * (0.35 + 0.65 * math.sin(z * math.pi * 0.9))
        v.co.y += 0.006 * math.sin(x * 19 + z * 3) * (1 - z) + 0.004 * math.sin(x * 37 + 1.3)
    bm.to_mesh(o.data); bm.free()
    o.matrix_world = mtx @ Matrix.Translation((0, -0.004, 0))
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new(name + '_m'); m.use_nodes = True; nt = m.node_tree; N2 = nt.nodes; b = N2['Principled BSDF']
    it = N2.new('ShaderNodeTexImage'); it.image = img(image_path); it.extension = 'CLIP'
    mix = N2.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0; mix.inputs[7].default_value = (*tint, 1)
    nt.links.new(it.outputs['Color'], mix.inputs[6]); nt.links.new(mix.outputs[2], b.inputs['Base Color']); nt.links.new(it.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.72; b.inputs['Sheen Weight'].default_value = 0.5; b.inputs['Sheen Roughness'].default_value = 0.4
    t = tex_paths('cotton_jersey'); tc2 = N2.new('ShaderNodeTexCoord'); mp2 = N2.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (14, 14, 14)
    nn = N2.new('ShaderNodeTexImage'); nn.image = img(t['nor_gl'], 'Non-Color'); nm = N2.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.35
    nt.links.new(tc2.outputs['UV'], mp2.inputs[0]); nt.links.new(mp2.outputs[0], nn.inputs[0]); nt.links.new(nn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    o.data.materials.append(m)
    return o

# Jerseys as real garments: a thin fabric shell built from the shop's own front and back photos.
# The photos' outline becomes the mesh, the space between front and back is inflated (fuller at the shoulders,
# where the hanger spreads the shirt, thinner toward the hem), soft gravity folds run down the body.
# The photos' alpha draws the exact silhouette; front and back meet at the outline, so the shell is closed.
JERSEY_PHOTOS = {k: (f'{A}/jerseys/back/{k}-vorne{v}.webp', f'{A}/jerseys/back/{k}-hinten{v}.webp')
                 for k, v in (('frankfurt', '-v2'), ('berlin', ''), ('brasilien', '-v2'), ('deutschland', '-v2'), ('tuerkei', '-v2'))}

def jersey_mesh(name, front_path, back_path, h=JERSEY_H, cell=0.011, depth=0.055):
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    fr = Image.open(front_path).convert('RGBA'); bk = Image.open(back_path).convert('RGBA')
    frc = fr.crop(fr.getchannel('A').getbbox())
    bkc = bk.crop(bk.getchannel('A').getbbox()).transpose(Image.FLIP_LEFT_RIGHT).resize(frc.size, Image.LANCZOS)  # seen from behind
    tdir = os.path.join(ROOT, '.cache', 'jersey_tex'); os.makedirs(tdir, exist_ok=True)
    fpath, bpath = os.path.join(tdir, name + '_front.png'), os.path.join(tdir, name + '_back.png')
    frc.save(fpath); bkc.save(bpath)
    W, H = frc.size; w = h * W / H
    rows, cols = int(round(h / cell)), int(round(w / cell))
    af = np.asarray(frc.getchannel('A').resize((cols, rows), Image.BOX), dtype=np.float32) / 255
    ab = np.asarray(bkc.getchannel('A').resize((cols, rows), Image.BOX), dtype=np.float32) / 255
    cells = ndimage.binary_dilation(np.maximum(af, ab) > 0.35, iterations=1)   # one cell of margin: the alpha cuts the edge
    dist = ndimage.distance_transform_edt(cells) * cell
    k = depth / math.sqrt(max(dist.max(), 1e-6))
    # per-vertex thickness: mean over the cells around it, zero on the outline (front and back meet there)
    pad = np.pad(cells, 1); dpad = np.pad(dist, 1)
    used = {}; verts = []; uvs = []
    def vid(r, c, layer):
        key = (r, c, layer)
        if key in used: return used[key]
        around = [(r - 1, c - 1), (r - 1, c), (r, c - 1), (r, c)]
        ins = [pad[rr + 1, cc + 1] for rr, cc in around]
        boundary = not all(ins)
        if boundary and layer == 1 and (r, c, 0) in used:      # share the outline vertex with the front layer
            used[key] = used[(r, c, 0)]; return used[key]
        d = 0.0 if boundary else float(np.mean([dpad[rr + 1, cc + 1] for rr, cc in around]))
        zz = r / rows; x = (c / cols - 0.5) * w; z = -zz * h
        t = k * math.sqrt(d) * (1.0 if zz < 0.32 else 1.0 - 0.5 * (zz - 0.32) / 0.68)
        fold = 0.010 * zz ** 1.6 * (0.6 * math.sin(x * 23 + 1.1) + 0.4 * math.sin(x * 41 + 2.3)) + 0.02 * zz ** 2
        y = (-t / 2 if layer == 0 else t / 2) + fold
        verts.append((x, y, z)); used[key] = len(verts) - 1
        return used[key]
    faces = []; fmat = []; fuv = []
    for r in range(rows):
        for c in range(cols):
            if not cells[r, c]: continue
            q = [(r, c), (r + 1, c), (r + 1, c + 1), (r, c + 1)]
            uv = [(cc / cols, 1 - rr / rows) for rr, cc in q]
            faces.append([vid(rr, cc, 0) for rr, cc in q]); fmat.append(0); fuv.append(uv)
    for r in range(rows):
        for c in range(cols):
            if not cells[r, c]: continue
            q = [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]     # reversed winding: normals point backwards
            uv = [(cc / cols, 1 - rr / rows) for rr, cc in q]
            faces.append([vid(rr, cc, 1) for rr, cc in q]); fmat.append(1); fuv.append(uv)
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    ul = me.uv_layers.new(name='UVMap')
    li = 0
    for fi, poly in enumerate(me.polygons):
        poly.material_index = fmat[fi]
        for j, loop in enumerate(poly.loop_indices): ul.data[loop].uv = fuv[fi][j]
    o = link(bpy.data.objects.new(name, me))
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    for p_ in me.polygons: p_.use_smooth = True
    knit = tex_paths('cotton_jersey')
    for path in (fpath, bpath):
        m = bpy.data.materials.new(name + ('_front' if path == fpath else '_back')); m.use_nodes = True
        nt = m.node_tree; N2 = nt.nodes; b = N2['Principled BSDF']
        it = N2.new('ShaderNodeTexImage'); it.image = img(path); it.extension = 'CLIP'; it.interpolation = 'Cubic'
        nt.links.new(it.outputs['Color'], b.inputs['Base Color']); nt.links.new(it.outputs['Alpha'], b.inputs['Alpha'])
        b.inputs['Roughness'].default_value = 0.58; b.inputs['Sheen Weight'].default_value = 0.35; b.inputs['Sheen Roughness'].default_value = 0.35
        tc2 = N2.new('ShaderNodeTexCoord'); mp2 = N2.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (38, 38, 38)
        nn = N2.new('ShaderNodeTexImage'); nn.image = img(knit['nor_gl'], 'Non-Color'); nm = N2.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.22
        nt.links.new(tc2.outputs['UV'], mp2.inputs[0]); nt.links.new(mp2.outputs[0], nn.inputs[0]); nt.links.new(nn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
        o.data.materials.append(m)
    return o

meta = json.load(open(A + '/jerseys/meta.json'))
n = len(JERSEYS) + 1
xs = [RAIL['x0'] + 0.20 + i * (RAIL['x1'] - RAIL['x0'] - 0.40) / (n - 1) for i in range(n)]
KNIT = tex_paths('cotton_jersey')['nor_gl']
for i, k in enumerate(JERSEYS):
    mt = hanger(xs[i], FAN + random.uniform(-0.04, 0.04))
    bpy.data.objects.remove(hanger.body, do_unlink=True)          # the wooden hanger now sits inside the jersey
    jo, hg = garment.jersey('jersey_' + k, *JERSEY_PHOTOS[k], knit_normal=KNIT, hanger_mat=M['hanger'])
    jo.matrix_world = mt; hg.matrix_world = mt

# 6th hanger: the covered "Nächster Drop" garment bag
mt = hanger(xs[-1], FAN * 0.6)
inner = garment_plane('drop_inner', f'{A}/jerseys/deutschland.png', meta['deutschland']['w'] / meta['deutschland']['h'], mt, tint=(0.32, 0.33, 0.35))
bpy.ops.mesh.primitive_cube_add(size=1.0)
bag = bpy.context.object; bag.name = 'drop_bag'; bag.scale = (0.64, 0.075, 0.98); bag.location = (0, 0.0, -0.49); apply_tf(bag)
bm = bmesh.new(); bm.from_mesh(bag.data)
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=10, use_grid_fill=True)
for v in bm.verts:   # shoulders follow the hanger, the bag bellies out and narrows at the hem
    x, z = v.co.x, v.co.z
    v.co.z -= 0.10 * min(1.0, abs(x) / 0.32) * max(0.0, (z + 0.2) / 0.2)
    v.co.y *= 1.0 + 0.9 * math.sin(max(0.0, min(1.0, (z + 0.98) / 0.98)) * math.pi)
    v.co.x *= 1.0 - 0.06 * max(0.0, (-z - 0.6) / 0.38)
bm.to_mesh(bag.data); bm.free()
bag.matrix_world = mt @ Matrix.Translation((0, -0.004, 0))
bv = bag.modifiers.new('bev', 'BEVEL'); bv.width = 0.03; bv.segments = 3
bag.modifiers.new('sub', 'SUBSURF').levels = 2
tx = bpy.data.textures.new('bagnoise', 'CLOUDS'); tx.noise_scale = 0.12
dm = bag.modifiers.new('disp', 'DISPLACE'); dm.texture = tx; dm.strength = 0.028
bpy.ops.object.shade_smooth()
# matte black non-woven garment bag with a small cream AZUR print and a centre zip
bmat = bpy.data.materials.new('bag'); bmat.use_nodes = True; nt = bmat.node_tree; N2 = nt.nodes; L2 = nt.links; bb = N2['Principled BSDF']
bb.inputs['Roughness'].default_value = 0.88; bb.inputs['Sheen Weight'].default_value = 0.12; bb.inputs['Sheen Roughness'].default_value = 0.6
tco = N2.new('ShaderNodeTexCoord'); sep = N2.new('ShaderNodeSeparateXYZ'); L2.new(tco.outputs['Object'], sep.inputs[0])
LOGO_W, LOGO_Z = 0.20, -0.27
mu = N2.new('ShaderNodeMapRange'); mu.clamp = False; mu.inputs['From Min'].default_value = -LOGO_W / 2; mu.inputs['From Max'].default_value = LOGO_W / 2
mv = N2.new('ShaderNodeMapRange'); mv.clamp = False; lh = LOGO_W * 227 / 480; mv.inputs['From Min'].default_value = LOGO_Z - lh / 2; mv.inputs['From Max'].default_value = LOGO_Z + lh / 2
L2.new(sep.outputs['X'], mu.inputs['Value']); L2.new(sep.outputs['Z'], mv.inputs['Value'])
cmb = N2.new('ShaderNodeCombineXYZ'); L2.new(mu.outputs[0], cmb.inputs['X']); L2.new(mv.outputs[0], cmb.inputs['Y'])
lt = N2.new('ShaderNodeTexImage'); lt.image = img(A + '/logo/azur-logo-paper.webp'); lt.extension = 'CLIP'; L2.new(cmb.outputs[0], lt.inputs[0])
front = N2.new('ShaderNodeMath'); front.operation = 'LESS_THAN'; front.inputs[1].default_value = 0.0; L2.new(sep.outputs['Y'], front.inputs[0])
fac = N2.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; L2.new(lt.outputs['Alpha'], fac.inputs[0]); L2.new(front.outputs[0], fac.inputs[1])
mixb = N2.new('ShaderNodeMix'); mixb.data_type = 'RGBA'; mixb.inputs[6].default_value = (0.012, 0.013, 0.015, 1); mixb.inputs[7].default_value = (0.78, 0.74, 0.66, 1)
L2.new(fac.outputs[0], mixb.inputs['Factor']); L2.new(mixb.outputs[2], bb.inputs['Base Color'])
bag.data.materials.append(bmat)
# zip: a thin strip shrink-wrapped onto the bag front
bpy.ops.mesh.primitive_grid_add(x_subdivisions=1, y_subdivisions=60, size=1.0)
zp = bpy.context.object; zp.name = 'zip'; zp.scale = (0.009, 0.86, 1); zp.rotation_euler = (math.radians(90), 0, 0); zp.location = (0.0, -0.25, -0.52); apply_tf(zp)
zp.matrix_world = bag.matrix_world @ Matrix.Translation((0, 0, 0))
sw = zp.modifiers.new('wrap', 'SHRINKWRAP'); sw.target = bag; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.0015
zs = zp.modifiers.new('sol', 'SOLIDIFY'); zs.thickness = 0.002
zp.data.materials.append(flat('zip', (0.05, 0.05, 0.055), rough=0.35, metal=0.6))
pull = box('zip_pull', -0.007, 0.007, -0.004, 0.004, -0.03, 0.0, M['silver'], 0.002)
pull.matrix_world = bag.matrix_world @ Matrix.Translation((0.0, -0.075, -0.07))
# handwritten paper tag on a string from the hook: "Nächster Drop"
tagm = mt @ Matrix.Translation((0.09, -0.12, -0.19)) @ Matrix.Rotation(math.radians(-10), 4, 'Y') @ Matrix.Rotation(math.radians(-12), 4, 'Z')
tag = box('tag', -0.05, 0.05, -0.0008, 0.0008, -0.07, 0.07, M['paper'], 0.001); tag.matrix_world = tagm
ft = bpy.data.fonts.load(A + '/fonts/Caveat.ttf')
tcu = bpy.data.curves.new('tagtext', 'FONT'); tcu.body = 'Nächster\nDrop'; tcu.font = ft; tcu.size = 0.03; tcu.align_x = 'CENTER'; tcu.align_y = 'CENTER'; tcu.space_line = 0.8
tto = link(bpy.data.objects.new('tagtext', tcu)); tto.matrix_world = tagm @ Matrix.Translation((0, -0.0012, 0.0)) @ Matrix.Rotation(math.radians(90), 4, 'X')
tto.data.materials.append(M['ink'])
cyl('string', (tagm @ Vector((0, 0, 0.07))), (mt @ Vector((0.0, -0.02, 0.05))), 0.0008, M['paper'], verts=6)

# ---------------------------------------------------------------- posters (Mbappé reference: the wall nearly becomes wallpaper)
plist = sorted(f for f in os.listdir(A + '/posters') if f.endswith('.jpg'))
random.shuffle(plist)
pq = list(plist)
def next_poster():
    global pq
    if not pq: pq = list(plist); random.shuffle(pq)
    return pq.pop()

def poster(path, w, h, mtx, gloss=True, border=0.0, tape=True):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=6, y_subdivisions=6, size=1.0)
    o = bpy.context.object; o.scale = (w, h, 1); apply_tf(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    lift = random.uniform(0.0, 0.012)
    corner = random.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
    for v in bm.verts:   # one corner peels slightly off the wall
        u, t = v.co.x / w * 2, v.co.y / h * 2
        d = max(0.0, (u * corner[0] + t * corner[1]) - 1.2)
        v.co.z += lift * d * d * 2.5
    bm.to_mesh(o.data); bm.free()
    o.matrix_world = mtx
    im = img(path); iw, ih = im.size
    m = bpy.data.materials.new('poster'); m.use_nodes = True; nt = m.node_tree; N2 = nt.nodes; b = N2['Principled BSDF']
    tc2 = N2.new('ShaderNodeTexCoord'); mp2 = N2.new('ShaderNodeMapping')
    # centre-crop the photo to the poster's aspect, keep a paper border if asked
    pa, ia = w / h, iw / ih
    sx, sy = (pa / ia, 1.0) if ia > pa else (1.0, ia / pa)
    sx /= (1 - 2 * border); sy /= (1 - 2 * border)
    mp2.inputs['Scale'].default_value = (sx, sy, 1); mp2.inputs['Location'].default_value = ((1 - sx) / 2, (1 - sy) / 2, 0)
    it = N2.new('ShaderNodeTexImage'); it.image = im; it.extension = 'CLIP'
    nt.links.new(tc2.outputs['UV'], mp2.inputs[0]); nt.links.new(mp2.outputs[0], it.inputs[0])
    fade = N2.new('ShaderNodeHueSaturation'); fade.inputs['Saturation'].default_value = random.uniform(0.82, 0.97); fade.inputs['Value'].default_value = random.uniform(0.9, 1.0)
    nt.links.new(it.outputs['Color'], fade.inputs['Color'])
    mx = N2.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (0.9, 0.89, 0.85, 1)
    nt.links.new(it.outputs['Alpha'], mx.inputs['Factor']); nt.links.new(fade.outputs[0], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = random.uniform(0.18, 0.3) if gloss else random.uniform(0.55, 0.75)
    b.inputs['Coat Weight'].default_value = 0.15 if gloss else 0.0
    o.data.materials.append(m)
    if tape:
        for cx in (-1, 1):
            if random.random() < 0.85:
                t = box('tape', -0.022, 0.022, -0.0005, 0.0005, -0.009, 0.009, M['tape'])
                t.matrix_world = mtx @ Matrix.Translation((cx * (w / 2 - 0.005), h / 2 - 0.004, 0.0015)) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Rotation(math.radians(cx * 40 + random.uniform(-10, 10)), 4, 'Y')
    return o

def fill_wall(wall, u0, u1, z0, z1, holes=(), seed=0):
    """Pack posters in loose rows; wall='back' (u=x, normal -Y) or 'left' (u=y, normal +X)."""
    rnd = random.Random(seed); z = z1; layer = 0
    while z > z0 + 0.2:
        rh = rnd.choice([0.42, 0.42, 0.594, 0.30, 0.594])
        u = u0 + rnd.uniform(-0.02, 0.03)
        while u < u1 - 0.12:
            path = A + '/posters/' + next_poster()
            iw, ih = img(path).size
            land = iw > ih
            w = rh * (1.414 if land else 0.707) if rh != 0.30 else (0.42 if land else 0.21)
            h = rh if rh != 0.30 else (0.297 if land else 0.297)
            w = min(w, u1 - u + 0.05)
            cu, cz = u + w / 2, z - h / 2 + rnd.uniform(-0.015, 0.015)
            if any(hx0 < cu + w / 2 and cu - w / 2 < hx1 and hz0 < cz + h / 2 and cz - h / 2 < hz1 for hx0, hx1, hz0, hz1 in holes):
                u += w * 0.5; continue
            if cz - h / 2 < z0 - 0.05: u += w; continue
            rot = math.radians(rnd.uniform(-1.8, 1.8)); layer += 1; off = 0.0015 + (layer % 7) * 0.0009
            if wall == 'back':
                mt = Matrix.Translation((cu, D - off, cz)) @ Euler((math.radians(90), rot, 0)).to_matrix().to_4x4()
            else:
                mt = Matrix.Translation((off, cu, cz)) @ Euler((math.radians(90), rot, math.radians(90))).to_matrix().to_4x4()
            poster(path, w, h, mt, gloss=rnd.random() < 0.7, border=rnd.choice([0, 0, 0.03, 0.05]), tape=rnd.random() < 0.8)
            u += w - rnd.uniform(0.0, 0.04)
        z -= rh - rnd.uniform(0.0, 0.035)

neon_hole = (NEON['x'] - 0.37, NEON['x'] + 0.37, NEON['z'] - 0.17, H)
fill_wall('back', 0.03, 2.56, 0.50, H - 0.03, holes=[neon_hole], seed=3)
fill_wall('left', 2.05, D - 0.03, 0.86, H - 0.03, seed=5)

# ---------------------------------------------------------------- AZUR neon (LED neon flex traced from the real signature)
nj = json.load(open(HERE + '/neon_paths.json'))
ncu = bpy.data.curves.new('neon', 'CURVE'); ncu.dimensions = '3D'; ncu.bevel_depth = 0.0048; ncu.bevel_resolution = 6; ncu.resolution_u = 24
for p in nj['paths']:
    sp = ncu.splines.new('NURBS'); sp.points.add(len(p) - 1); sp.use_endpoint_u = True; sp.order_u = 3
    for i, (x, y) in enumerate(p): sp.points[i].co = (x, 0, y, 1)
neon = link(bpy.data.objects.new('neon', ncu)); neon.location = (NEON['x'], D - 0.035, NEON['z']); 
nm_ = bpy.data.materials.new('neon_tube'); nm_.use_nodes = True; b = nm_.node_tree.nodes['Principled BSDF']
b.inputs['Base Color'].default_value = (0.86, 0.94, 0.98, 1); b.inputs['Emission Color'].default_value = (*NEON['color'], 1)
b.inputs['Emission Strength'].default_value = NEON['strength']; b.inputs['Roughness'].default_value = 0.42; b.inputs['Coat Weight'].default_value = 0.3
b.inputs['Subsurface Weight'].default_value = 0.5; b.inputs['Subsurface Radius'].default_value = (0.004, 0.006, 0.008)   # milky LED silicone
neon.data.materials.append(nm_)
plate = box('neon_plate', NEON['x'] - nj['width'] / 2 - 0.03, NEON['x'] + nj['width'] / 2 + 0.03, D - 0.03, D - 0.024, NEON['z'] - nj['height'] / 2 - 0.03, NEON['z'] + nj['height'] / 2 + 0.03,
            flat('acrylic', (1, 1, 1), rough=0.05, **{'Transmission Weight': 1.0, 'IOR': 1.49}), 0.006)
plate.visible_shadow = False
for dx in (-1, 1):
    for dz in (-1, 1):
        cyl('standoff', (NEON['x'] + dx * (nj['width'] / 2), D - 0.003, NEON['z'] + dz * (nj['height'] / 2)), (NEON['x'] + dx * (nj['width'] / 2), D - 0.03, NEON['z'] + dz * (nj['height'] / 2)), 0.006, M['silver'])
cable = bpy.data.curves.new('cable', 'CURVE'); cable.dimensions = '3D'; cable.bevel_depth = 0.0025
sp = cable.splines.new('BEZIER'); sp.bezier_points.add(2)
for i, p in enumerate([(NEON['x'] + 0.28, D - 0.03, NEON['z'] - 0.14), (NEON['x'] + 0.55, D - 0.012, NEON['z'] - 0.5), (NEON['x'] + 0.95, D - 0.006, 0.3)]):
    bp = sp.bezier_points[i]; bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
co_ = link(bpy.data.objects.new('cable', cable)); co_.data.materials.append(flat('cable', (0.9, 0.9, 0.88), rough=0.5))

# ---------------------------------------------------------------- shelf with books, trophies, boombox (back-right corner)
root, meshes = import_gltf('Shelf_01', loc=(2.98, D - 0.005, 0), rot_z=0.0, scale=1.0)
root.scale = (0.7, 1, 0.92)
bpy.context.view_layer.update()
def up_levels(objs, min_area=0.02):
    zs = []
    for o in objs:
        mw = o.matrix_world; r3 = mw.to_3x3()
        for p in o.data.polygons:
            nrm = (r3 @ p.normal).normalized()
            if nrm.z > 0.95 and p.area * 0.8 > min_area: zs.append(round((mw @ p.center).z, 3))
    out = []
    for z in sorted(set(zs)):
        if not out or z - out[-1] > 0.05: out.append(z)
        else: out[-1] = max(out[-1], z)
    return out
LV = up_levels(meshes); print('SHELF_LEVELS', LV)
def lv(i): return LV[min(i, len(LV) - 1)]
r2, _ = import_gltf('book_encyclopedia_set_01', loc=(2.62, D - 0.16, lv(3)), rot_z=0.0, scale=0.95)
r3, _ = import_gltf('boombox', loc=(2.98, D - 0.13, lv(len(LV) - 1)), rot_z=math.radians(-3), scale=0.82)
r4, _ = import_gltf('alarm_clock_01', loc=(3.23, D - 0.15, lv(3)), rot_z=math.radians(-20))

def lathe(name, prof, loc, mat, seg=40):
    bm = bmesh.new(); rings = []
    for r_, z_ in prof:
        rings.append([bm.verts.new((r_ * math.cos(a), r_ * math.sin(a), z_)) for a in [2 * math.pi * k / seg for k in range(seg)]])
    for a_, b_ in zip(rings, rings[1:]):
        for k in range(seg): bm.faces.new((a_[k], a_[(k + 1) % seg], b_[(k + 1) % seg], b_[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.data.materials.append(mat)
    o.modifiers.new('sol', 'SOLIDIFY').thickness = 0.002
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    for p in o.data.polygons: p.use_smooth = True
    return o

def trophy(x, y, z, s=1.0, metal='gold'):
    box('t_base', x - 0.035 * s, x + 0.035 * s, y - 0.035 * s, y + 0.035 * s, z, z + 0.035 * s, M['marble'], 0.002)
    box('t_base2', x - 0.026 * s, x + 0.026 * s, y - 0.026 * s, y + 0.026 * s, z + 0.035 * s, z + 0.06 * s, M['marble'], 0.002)
    prof = [(0.0, 0.0), (0.016, 0.0), (0.008, 0.01), (0.006, 0.045), (0.012, 0.055), (0.024, 0.07), (0.036, 0.1), (0.042, 0.13), (0.043, 0.14), (0.04, 0.142)]
    lathe('t_cup', [(r_ * s, z_ * s) for r_, z_ in prof], (x, y, z + 0.06 * s), M[metal])
    for sd in (-1, 1):
        cu = bpy.data.curves.new('handle', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.003 * s
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(2)
        for i, p in enumerate([(sd * 0.03, 0, 0.12), (sd * 0.062, 0, 0.11), (sd * 0.032, 0, 0.075)]):
            bp = sp.bezier_points[i]; bp.co = (p[0] * s, 0, p[2] * s); bp.handle_left_type = bp.handle_right_type = 'AUTO'
        h_ = link(bpy.data.objects.new('t_handle', cu)); h_.location = (x, y, z + 0.06 * s); h_.data.materials.append(M[metal])

trophy(2.76, D - 0.13, lv(5), 1.25, 'gold')
trophy(2.96, D - 0.12, lv(5), 0.9, 'silver')
trophy(3.16, D - 0.14, lv(5), 1.05, 'gold')
for i, (dx, s_) in enumerate([(-0.25, 0.8), (0.05, 1.0)]):
    trophy(2.98 + dx, D - 0.13, lv(4), s_, 'gold' if i else 'silver')
# little cup on the window sill
trophy(W - 0.06, y0 + 0.22, z0, 0.8, 'gold')

# ---------------------------------------------------------------- floor: rug, worn football, gamepad, box
rug = box('rug', 0.75, 2.35, 2.15, 3.35, 0.0, 0.008, M['rug'], 0.004)
rug.rotation_euler = (0, 0, math.radians(-4))
rb, ms = import_gltf('football', loc=(0.92, 2.2, 0.0), rot_z=math.radians(30))
bpy.context.view_layer.update()
# keep only the round ball (the model ships a cut-away half next to it)
cx = [sum((o.matrix_world @ Vector(c)).x for c in o.bound_box) / 8 for o in ms]
for o, c in zip(ms, cx):
    if c < max(cx) - 0.05: o.hide_render = True; o.hide_viewport = True
rg, _ = import_gltf('gamepad', loc=(0.62, 2.38, 0.004), rot_z=math.radians(-25))
rc, _ = import_gltf('cardboard_box_01', loc=(0.30, 3.72, 0.0), rot_z=math.radians(8), scale=0.9)
# flush opal ceiling light (the light source for the night passes)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0, location=(1.7, 1.9, H))
cl_ = bpy.context.object; cl_.name = 'ceiling_light'; cl_.scale = (0.19, 0.19, 0.075); bpy.ops.object.shade_smooth()
cl_.data.materials.append(flat('opal', (0.95, 0.94, 0.92), rough=0.25, **{'Subsurface Weight': 0.6, 'Coat Weight': 0.3}))
cyl('ceiling_ring', (1.7, 1.9, H - 0.002), (1.7, 1.9, H - 0.012), 0.2, M['paint'], verts=48)

# ---------------------------------------------------------------- storytelling props
def surface_z(x, y, z0=2.2):
    """Height of whatever is below (x, y): used to lay things on the crumpled duvet."""
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, _, _, _ = sc.ray_cast(dg, Vector((x, y, z0)), Vector((0, 0, -1)))
    return (loc.z, nrm) if hit else (0.0, Vector((0, 0, 1)))

def group(name, objs, loc=(0, 0, 0), rot_z=0.0):
    root = link(bpy.data.objects.new(name, None))
    for o in objs: o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, rot_z)
    return root

# desk against the left wall behind the bed: the pine desk the kid has had for years
pine = pbr('pine', 'oak_veneer_01', tile=0.7, tint=(1.0, 0.84, 0.62), rough=(0.35, 0.6), nstr=0.3)
DX1, DY0, DY1, DZ = 0.60, 2.30, 3.40, 0.74
box('desk_top', 0.0, DX1, DY0, DY1, DZ - 0.028, DZ, pine, 0.003)
for lx, ly in ((DX1 - 0.05, DY0 + 0.02), (DX1 - 0.05, DY1 - 0.055), (0.015, DY0 + 0.02), (0.015, DY1 - 0.055)):
    box('desk_leg', lx, lx + 0.035, ly, ly + 0.035, 0, DZ - 0.028, pine, 0.002)
box('desk_drawer', 0.04, DX1 - 0.02, DY1 - 0.44, DY1 - 0.07, DZ - 0.17, DZ - 0.03, pine, 0.003)
box('drawer_knob', DX1 - 0.02, DX1 + 0.006, DY1 - 0.265, DY1 - 0.245, DZ - 0.11, DZ - 0.09, M['silver'], 0.002)
def rest_on(root, z):
    """Put an imported model down so its lowest point touches z (models come with their own origins)."""
    bpy.context.view_layer.update()
    lo = min((o.matrix_world @ Vector(c)).z for o in root.children_recursive if o.type == 'MESH' for c in o.bound_box)
    root.location.z += z - lo
rest_on(import_gltf('desk_lamp_arm_01', loc=(0.16, DY1 - 0.16, DZ), rot_z=math.radians(-120))[0], DZ)
rest_on(import_gltf('binder_notebook', loc=(0.30, DY0 + 0.38, DZ + 0.001), rot_z=math.radians(78))[0], DZ)
rest_on(import_gltf('stationery_supplies', loc=(0.14, DY0 + 0.14, DZ + 0.074), rot_z=math.radians(80))[0], DZ)
def wbox(o):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])
def world_move(o, M): o.matrix_world = M @ o.matrix_world
cup = bpy.data.objects.get('stationery_supplies_pencilcup')
if cup:
    clo, chi = wbox(cup); cc = (clo + chi) / 2
    for k, n in enumerate(['stationery_supplies_pen_blue', 'stationery_supplies_pencil_new_a', 'stationery_supplies_pen_fancy']):
        o = bpy.data.objects.get(n)
        if not o: continue
        lo, hi = wbox(o); c = (lo + hi) / 2
        world_move(o, Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation(-c))   # stand it up
        lo, hi = wbox(o); c = (lo + hi) / 2; a_ = k * 2.1
        to = Vector((cc.x + 0.015 * math.cos(a_), cc.y + 0.015 * math.sin(a_), clo.z + 0.006))
        world_move(o, Matrix.Translation(Vector((to.x - c.x, to.y - c.y, to.z - lo.z))))
        lean = Vector((math.cos(a_), math.sin(a_), 0)).cross(Vector((0, 0, 1)))                 # lean outward a little
        world_move(o, Matrix.Translation(to) @ Matrix.Rotation(math.radians(-8), 4, lean) @ Matrix.Translation(-to))
    for n, (x, y, z, rz) in {'stationery_supplies_pen_red': (0.38, DY0 + 0.10, DZ, 28),
                             'stationery_supplies_pencil_used': (0.30, DY0 + 0.40, DZ + 0.019, -35),   # on the open notebook
                             'stationery_supplies_eraser': (0.46, DY0 + 0.15, DZ, 12)}.items():
        o = bpy.data.objects.get(n)
        if not o: continue
        lo, hi = wbox(o); c = (lo + hi) / 2
        world_move(o, Matrix.Translation(c) @ Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Translation(-c))
        lo, hi = wbox(o); c = (lo + hi) / 2
        world_move(o, Matrix.Translation(Vector((x - c.x, y - c.y, z + 0.0005 - lo.z))))
# exercise books, stacked a bit crooked
for i, (c_, rz) in enumerate([((0.15, 0.32, 0.55), 6), ((0.75, 0.2, 0.15), -4), ((0.9, 0.85, 0.25), 11)]):
    bk = box('heft', -0.105, 0.105, -0.148, 0.148, 0, 0.006, flat('heft', c_, rough=0.6), 0.001)
    bk.location = (0.33, DY0 + 0.78, DZ + i * 0.0065); bk.rotation_euler = (0, 0, math.radians(90 + rz))
# simple wooden chair, pulled out and turned
ch = []
ch.append(box('seat', -0.2, 0.2, -0.2, 0.2, 0.43, 0.455, pine, 0.004))
for lx, ly in ((-0.18, -0.18), (0.16, -0.18), (-0.18, 0.16), (0.16, 0.16)):
    ch.append(box('cleg', lx, lx + 0.025, ly, ly + 0.025, 0.0, 0.43, pine, 0.002))
for lx in (0.16,):
    for ly in (-0.18, 0.16):
        ch.append(box('cpost', lx, lx + 0.025, ly, ly + 0.025, 0.455, 0.86, pine, 0.002))
    ch.append(box('cback', lx - 0.004, lx + 0.03, -0.18, 0.185, 0.72, 0.84, pine, 0.003))
group('chair', ch, loc=(0.74, 2.47, 0), rot_z=math.radians(9))        # pulled out from the desk, facing it

# football boots: dropped by the bed, one on its side (metaball upper, rubber soleplate, studs)
def boot(name, loc, rot, tilt=0.0):
    """Football boot, lofted from cross-sections heel to toe: black synthetic upper with an azure side stripe,
    white laces over the instep, a dark collar opening, grey sole plate with conical studs (no real brand)."""
    L, N = 0.27, 28                      # length (kid's size), points per ring
    secs = [  # t (heel 0 .. toe 1), half width, height of the upper
        (0.00, 0.026, 0.085), (0.04, 0.033, 0.098), (0.12, 0.036, 0.100), (0.24, 0.038, 0.088), (0.36, 0.041, 0.078),
        (0.50, 0.045, 0.068), (0.64, 0.047, 0.056), (0.76, 0.046, 0.045), (0.86, 0.041, 0.036), (0.94, 0.031, 0.027),
        (0.985, 0.017, 0.018), (1.0, 0.004, 0.010)]
    bm = bmesh.new(); rings = []
    for t, hw, hh in secs:
        ring = []
        for j in range(N):
            a = 2 * math.pi * j / N
            ca, sa = math.cos(a), math.sin(a)
            x = hw * math.copysign(abs(ca) ** 0.7, ca)
            z = hh * math.copysign(abs(sa) ** 0.8, sa) if sa > 0 else 0.004 * sa     # flat bottom
            ring.append(bm.verts.new((x, -0.12 + t * L, 0.016 + z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(N):
            bm.faces.new((r0[j], r0[(j + 1) % N], r1[(j + 1) % N], r1[j]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    up = link(bpy.data.objects.new(name, me))
    up.modifiers.new('sub', 'SUBSURF').levels = 2
    for p_ in me.polygons: p_.use_smooth = True
    # upper material: black synthetic with clear coat, azure stripe along the side (object coordinates)
    m = bpy.data.materials.new(name + '_upper'); m.use_nodes = True; nt = m.node_tree; Nn = nt.nodes; b = Nn['Principled BSDF']
    tc = Nn.new('ShaderNodeTexCoord'); sep = Nn.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
    def band(src, lo, hi, soft=0.004):
        g1 = Nn.new('ShaderNodeMapRange'); g1.inputs['From Min'].default_value = lo - soft; g1.inputs['From Max'].default_value = lo + soft
        g2 = Nn.new('ShaderNodeMapRange'); g2.inputs['From Min'].default_value = hi + soft; g2.inputs['From Max'].default_value = hi - soft
        nt.links.new(src, g1.inputs['Value']); nt.links.new(src, g2.inputs['Value'])
        mm = Nn.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; nt.links.new(g1.outputs[0], mm.inputs[0]); nt.links.new(g2.outputs[0], mm.inputs[1]); return mm.outputs[0]
    zb = band(sep.outputs['Z'], 0.038, 0.050); yb = band(sep.outputs['Y'], -0.02, 0.07, 0.02)
    mk = Nn.new('ShaderNodeMath'); mk.operation = 'MULTIPLY'; nt.links.new(zb, mk.inputs[0]); nt.links.new(yb, mk.inputs[1])
    mix = Nn.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs[6].default_value = (0.012, 0.012, 0.015, 1); mix.inputs[7].default_value = (0.0, 0.42, 0.85, 1)
    nt.links.new(mk.outputs[0], mix.inputs['Factor']); nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.38; b.inputs['Coat Weight'].default_value = 0.45; b.inputs['Coat Roughness'].default_value = 0.2
    up.data.materials.append(m)
    parts = [up]
    # collar opening (dark, slightly sunken) and a padded rim
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0, location=(0, -0.075, 0.016 + 0.099))
    op = bpy.context.object; op.name = name + '_opening'; op.scale = (0.024, 0.042, 0.006); bpy.ops.object.shade_smooth()
    op.data.materials.append(flat('boot_inside', (0.006, 0.006, 0.007), rough=0.9)); parts.append(op)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.12, location=(0, -0.075, 0.016 + 0.1))
    rim = bpy.context.object; rim.name = name + '_collar'; rim.scale = (0.027, 0.046, 0.06); bpy.ops.object.shade_smooth()
    rim.data.materials.append(m); parts.append(rim)
    # sole plate and studs
    sole = box(name + '_sole', -0.044, 0.044, -0.122, 0.148, 0.004, 0.018, flat('sole', (0.55, 0.56, 0.58), rough=0.4), 0.008)
    parts.append(sole)
    for sx, sy in [(-0.026, -0.095), (0.026, -0.095), (-0.022, -0.055), (0.022, -0.055), (-0.03, 0.03), (0.03, 0.035),
                   (-0.03, 0.075), (0.03, 0.08), (-0.02, 0.115), (0.02, 0.118), (0.0, 0.135)]:
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.0075, radius2=0.004, depth=0.013, location=(sx, sy, -0.0025))
        st = bpy.context.object; st.name = name + '_stud'; st.rotation_euler = (math.pi, 0, 0); st.data.materials.append(M['rubber']); parts.append(st)
    lace_m = flat('lace', (0.92, 0.92, 0.9), rough=0.7)
    for i in range(6):   # laces across the instep, following the top of the upper
        t = 0.36 + i * 0.07; yy = -0.12 + t * L
        hh = 0.078 - (t - 0.36) * 0.16
        parts.append(cyl(name + '_lace', (-0.022, yy, 0.016 + hh - 0.002), (0.022, yy + 0.004, 0.016 + hh - 0.002), 0.0028, lace_m, verts=8))
    r = group(name + '_root', parts, loc=loc, rot_z=rot)
    r.rotation_euler = (0, tilt, rot)
    return r
boot('boot_l', (1.18, 1.62, 0.012), math.radians(-35))
boot('boot_r', (1.38, 1.5, 0.05), math.radians(60), tilt=math.radians(-80))

# training bag on the floor at the foot of the bed
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.15, depth=0.42, location=(0, 0, 0))
tb = bpy.context.object; tb.name = 'trainingbag'; tb.rotation_euler = (0, math.radians(90), 0); apply_tf(tb)
tb.scale = (1, 1, 0.82); apply_tf(tb)
bv2 = tb.modifiers.new('bev', 'BEVEL'); bv2.width = 0.07; bv2.segments = 6; bv2.limit_method = 'NONE'
tb.modifiers.new('sub', 'SUBSURF').levels = 2
tbt = bpy.data.textures.new('bagslump', 'CLOUDS'); tbt.noise_scale = 0.2
dd = tb.modifiers.new('disp', 'DISPLACE'); dd.texture = tbt; dd.strength = 0.03
bpy.ops.object.shade_smooth()
bagm = bpy.data.materials.new('trainingbag'); bagm.use_nodes = True; nt = bagm.node_tree; bp = nt.nodes['Principled BSDF']
tco = nt.nodes.new('ShaderNodeTexCoord'); sx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tco.outputs['Object'], sx.inputs[0])
band = nt.nodes.new('ShaderNodeMapRange'); band.interpolation_type = 'STEPPED'; band.inputs['From Min'].default_value = -0.03; band.inputs['From Max'].default_value = 0.03; band.inputs['Steps'].default_value = 1
nt.links.new(sx.outputs['Z'], band.inputs['Value'])
mb2 = nt.nodes.new('ShaderNodeMix'); mb2.data_type = 'RGBA'; mb2.inputs[6].default_value = (0.02, 0.04, 0.12, 1); mb2.inputs[7].default_value = (0.02, 0.04, 0.12, 1)
stripe = nt.nodes.new('ShaderNodeMath'); stripe.operation = 'COMPARE'; stripe.inputs[1].default_value = 0.045; stripe.inputs[2].default_value = 0.012
nt.links.new(sx.outputs['Z'], stripe.inputs[0])
mb2.inputs[7].default_value = (0.85, 0.85, 0.82, 1); nt.links.new(stripe.outputs[0], mb2.inputs['Factor']); nt.links.new(mb2.outputs[2], bp.inputs['Base Color'])
bp.inputs['Roughness'].default_value = 0.7; bp.inputs['Sheen Weight'].default_value = 0.2
tb.data.materials.append(bagm)
hd = bpy.data.curves.new('strap', 'CURVE'); hd.dimensions = '3D'; hd.bevel_depth = 0.008; hd.bevel_resolution = 2
for sxx in (-0.06, 0.06):
    spx = hd.splines.new('BEZIER'); spx.bezier_points.add(2)
    for i, pt in enumerate([(sxx, -0.04, 0.1), (sxx + 0.01, 0.0, 0.2), (sxx, 0.04, 0.1)]):
        bpt = spx.bezier_points[i]; bpt.co = pt; bpt.handle_left_type = bpt.handle_right_type = 'AUTO'
hdo = link(bpy.data.objects.new('strap', hd)); hdo.data.materials.append(bagm)
group('trainingbag_root', [tb, hdo], loc=(1.55, 1.82, 0.13), rot_z=math.radians(-18))

# medals hanging off the rail upright: the first small wins
def medal(x, y, z, drop, col, metal):
    rib = bpy.data.meshes.new('ribbon'); bm = bmesh.new()
    w = 0.012
    vs = [bm.verts.new(v) for v in [(-0.02 - w, 0, 0), (-0.02 + w, 0, 0), (w, 0, -drop), (-w, 0, -drop),
                                    (0.02 - w, -0.002, 0), (0.02 + w, -0.002, 0), (w, -0.002, -drop), (-w, -0.002, -drop)]]
    bm.faces.new(vs[0:4]); bm.faces.new(vs[4:8]); bm.to_mesh(rib); bm.free()
    ro = link(bpy.data.objects.new('ribbon', rib)); ro.location = (x, y, z); ro.data.materials.append(flat('ribbon', col, rough=0.6, **{'Sheen Weight': 0.5}))
    d = cyl('medal', (x, y - 0.002, z - drop - 0.026), (x, y - 0.006, z - drop - 0.026), 0.026, M[metal], verts=32)
    d.rotation_euler = (math.radians(90), 0, 0)
medal(RAIL['x0'], RAIL['y'] - 0.016, RAIL['z'] - 0.03, 0.21, (0.06, 0.12, 0.45), 'gold')
medal(RAIL['x0'] + 0.008, RAIL['y'] - 0.02, RAIL['z'] - 0.035, 0.26, (0.7, 0.05, 0.08), 'silver')

# felt pennant on the free wall by the window (invented club colours)
pn = bpy.data.meshes.new('pennant'); bm = bmesh.new()
pv = [bm.verts.new(v) for v in [(0, -0.14, 0), (0, 0.14, 0), (0, 0.0, -0.46)]]
bm.faces.new(pv); bm.to_mesh(pn); bm.free()
pno = link(bpy.data.objects.new('pennant', pn)); pno.location = (W - 0.004, 3.56, 2.12); pno.rotation_euler = (0, math.radians(2), math.radians(180))
pnm = bpy.data.materials.new('pennant'); pnm.use_nodes = True; nt = pnm.node_tree; pb = nt.nodes['Principled BSDF']
tco = nt.nodes.new('ShaderNodeTexCoord'); sz_ = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tco.outputs['Object'], sz_.inputs[0])
st = nt.nodes.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = -0.09; nt.links.new(sz_.outputs['Z'], st.inputs[0])
mp_ = nt.nodes.new('ShaderNodeMix'); mp_.data_type = 'RGBA'; mp_.inputs[6].default_value = (0.03, 0.07, 0.25, 1); mp_.inputs[7].default_value = (0.92, 0.9, 0.86, 1)
nt.links.new(st.outputs[0], mp_.inputs['Factor']); nt.links.new(mp_.outputs[2], pb.inputs['Base Color'])
pb.inputs['Roughness'].default_value = 0.95; pb.inputs['Sheen Weight'].default_value = 0.6
pno.data.materials.append(pnm)
cyl('pennant_pin', (W, 3.56, 2.12), (W - 0.012, 3.56, 2.12), 0.004, M['silver'], verts=8)

# football magazine left open on the duvet (invented title "ANSTOSS")
mz, _ = surface_z(0.62, 1.42)
mag = box('magazine', -0.105, 0.105, -0.14, 0.14, 0.0, 0.004, M['paper'], 0.001)
mag.location = (0.62, 1.42, mz + 0.002); mag.rotation_euler = (math.radians(4), math.radians(-3), math.radians(28))
cov = poster(A + '/posters/hero_a.jpg', 0.205, 0.275, Matrix.Translation((0, 0, 0.0042)), gloss=True, border=0.0, tape=False)
for v in cov.data.vertices: v.co.z = 0.0   # a magazine cover lies flat (poster() peels a corner, which hid the masthead)
cov.parent = mag
mtc = bpy.data.curves.new('masthead', 'FONT'); mtc.body = 'ANSTOSS'; mtc.size = 0.034; mtc.align_x = 'CENTER'
mto = link(bpy.data.objects.new('masthead', mtc)); mto.parent = mag; mto.location = (0, 0.1, 0.0046)
mto.data.materials.append(flat('masthead', (0.95, 0.95, 0.93), rough=0.4))

# ---------------------------------------------------------------- the room through the day (round 3)
# Objects tagged 'azur_state' appear only in the named states (render_queue.set_state): 'night' (the teen asleep),
# 'morning' (just got up), 'evening' (back from school); '!night' = all states but night. Untagged = always.
# Day is the base: only untagged and '!night' objects. Each state is rendered as patches over the day plates.
def tag(o, states):
    for x in [o] + list(o.children_recursive): x['azur_state'] = states
    return o

def fabric(name, col, sheen=0.5, rough=0.9, scale=40):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = 0.4
    t = tex_paths('cotton_jersey'); tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale,) * 3
    nn = nt.nodes.new('ShaderNodeTexImage'); nn.image = img(t['nor_gl'], 'Non-Color'); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.4
    nt.links.new(tc.outputs['UV'], mp.inputs[0]); nt.links.new(mp.outputs[0], nn.inputs[0]); nt.links.new(nn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
    return m

def cloth_drop(name, size, loc, mat, rot_z=0.0, frames=60, crumple=0.04, seed=1, grid=(20, 24), thick=0.008, collide=()):
    """A piece of clothing dropped onto something and left there."""
    r = random.Random(seed)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=grid[0], y_subdivisions=grid[1], size=1.0, location=loc)
    o = bpy.context.object; o.name = name; o.scale = (size[0], size[1], 1); o.rotation_euler = (0, 0, rot_z); apply_tf(o)
    ph = [r.random() * 6 for _ in range(4)]
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        v.co.z += crumple * math.sin(v.co.x * 21 + ph[0]) * math.sin(v.co.y * 17 + ph[1]) + 0.5 * crumple * math.sin(v.co.x * 9 + v.co.y * 11 + ph[2])
    bm.to_mesh(o.data); bm.free()
    added = [c.modifiers.new('col', 'COLLISION') for c in collide if not any(m.type == 'COLLISION' for m in c.modifiers)]
    cloth_on(o, 0.25, 0.15); bake_cloth(o, frames)
    for c in collide:
        for m in [m for m in c.modifiers if m in added]: c.modifiers.remove(m)
    sm_ = o.modifiers.new('smooth', 'SMOOTH'); sm_.factor = 0.5; sm_.iterations = 2
    so_ = o.modifiers.new('sol', 'SOLIDIFY'); so_.thickness = thick; so_.offset = 1
    o.modifiers.new('sub', 'SUBSURF').levels = 1
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o; bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o

# hoodie hung over the chair back (every state): shaped directly (a simulated one slid off or bunched up on the
# posts): over the back's top edge, both halves hanging down with soft folds, the hem a little away from the wood
bpy.context.view_layer.update()
cbp = [bpy.data.objects['cback'].matrix_world @ Vector(c) for c in bpy.data.objects['cback'].bound_box]
cb_c = sum(cbp, Vector()) / 8; cb_top = max(p.z for p in cbp)
cyaw = bpy.data.objects['chair'].rotation_euler.z
across, along = Vector((math.cos(cyaw), math.sin(cyaw), 0)), Vector((-math.sin(cyaw), math.cos(cyaw), 0))
R, HALF, LEN = 0.024, 0.36, 0.30          # wrap radius over the edge, cloth from the top to each hem, width along the back
nu, nv = 48, 20
rh = random.Random(4); ph = [rh.uniform(0, 6.3) for _ in range(4)]
verts, faces = [], []
for i in range(nu):
    u = -HALF + 2 * HALF * i / (nu - 1); sgn = 1 if u >= 0 else -1; s_ = abs(u)
    for j in range(nv):
        v = -LEN / 2 + LEN * j / (nv - 1)
        arc = math.pi * R / 2
        if s_ <= arc:
            th = s_ / R; a_ = sgn * R * math.sin(th); z = cb_top - 0.004 + R * math.cos(th)
        else:
            d = s_ - arc; k = min(1.0, d / 0.12)
            fold = 0.011 * math.sin(v * 31 + ph[0] + sgn) * k + 0.006 * math.sin(v * 13 + d * 9 + ph[1]) * k
            a_ = sgn * (R + 0.004 + 0.05 * (d / 0.33) ** 2 + fold)
            z = cb_top - 0.004 - d + 0.012 * math.sin(v * 17 + ph[2] + sgn) * (d / 0.33) ** 2   # uneven hem
        p_ = Vector((cb_c.x, cb_c.y, 0)) + across * a_ + along * v; p_.z = z
        verts.append(p_)
for i in range(nu - 1):
    for j in range(nv - 1):
        faces.append([i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1])
hme = bpy.data.meshes.new('hoodie'); hme.from_pydata([tuple(v) for v in verts], [], faces); hme.update()
hood = link(bpy.data.objects.new('hoodie', hme))
sm_ = hood.modifiers.new('smooth', 'SMOOTH'); sm_.factor = 0.4; sm_.iterations = 2
so_ = hood.modifiers.new('sol', 'SOLIDIFY'); so_.thickness = 0.009; so_.offset = 1
hood.modifiers.new('sub', 'SUBSURF').levels = 1
bpy.ops.object.select_all(action='DESELECT'); hood.select_set(True); bpy.context.view_layer.objects.active = hood; bpy.ops.object.shade_smooth()
hood.data.materials.append(fabric('hoodie', (0.21, 0.22, 0.24)))

# morning: the pyjama shirt dropped by the bed, the phone left on the duvet
tag(cloth_drop('pyjama', (0.50, 0.44), (1.18, 0.55, 0.12), fabric('pyjama', (0.30, 0.38, 0.50)), rot_z=math.radians(-20), frames=50, seed=7), 'morning')
pz, _ = surface_z(0.55, 0.62)
phone = box('phone', -0.036, 0.036, -0.075, 0.075, 0.0, 0.008, flat('phone', (0.02, 0.02, 0.025), rough=0.12, **{'Coat Weight': 0.8}), 0.006)
phone.location = (0.55, 0.62, pz + 0.002); phone.rotation_euler = (math.radians(3), math.radians(-4), math.radians(35)); tag(phone, 'morning')

# evening (and still there at night): the school backpack dropped by the desk, exercise books slid out of it
def backpack(loc, rot_z):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    bp = bpy.context.object; bp.name = 'backpack'; bp.scale = (0.30, 0.15, 0.40); bp.location = (0, 0, 0.20); apply_tf(bp)
    bv = bp.modifiers.new('bev', 'BEVEL'); bv.width = 0.05; bv.segments = 5
    bp.modifiers.new('sub', 'SUBSURF').levels = 2
    tx = bpy.data.textures.new('packslump', 'CLOUDS'); tx.noise_scale = 0.15
    dm = bp.modifiers.new('disp', 'DISPLACE'); dm.texture = tx; dm.strength = 0.02
    bpy.ops.object.shade_smooth()
    mat = fabric('backpack', (0.035, 0.09, 0.07), sheen=0.2, rough=0.7, scale=60)
    bp.data.materials.append(mat)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    pk = bpy.context.object; pk.name = 'backpack_pocket'; pk.scale = (0.22, 0.06, 0.18); pk.location = (0, -0.09, 0.14); apply_tf(pk)
    pk.modifiers.new('bev', 'BEVEL').width = 0.03; pk.modifiers.new('sub', 'SUBSURF').levels = 2; bpy.ops.object.shade_smooth()
    pk.data.materials.append(mat)
    hd = bpy.data.curves.new('pack_handle', 'CURVE'); hd.dimensions = '3D'; hd.bevel_depth = 0.008
    spx = hd.splines.new('BEZIER'); spx.bezier_points.add(2)
    for i, pt in enumerate([(-0.04, 0.02, 0.39), (0.0, 0.03, 0.44), (0.04, 0.02, 0.39)]):
        bpt = spx.bezier_points[i]; bpt.co = pt; bpt.handle_left_type = bpt.handle_right_type = 'AUTO'
    ho = link(bpy.data.objects.new('pack_handle', hd)); ho.data.materials.append(flat('webbing', (0.02, 0.02, 0.02), rough=0.8))
    root = group('backpack_root', [bp, pk, ho], loc=loc, rot_z=rot_z)
    root.rotation_euler = (math.radians(-14), 0, rot_z)          # leaning back against nothing, half tipped
    return root
tag(backpack((1.20, 2.12, 0.0), math.radians(32)), 'evening night')
for i, (x, y, rz, hcol) in enumerate([(1.02, 2.30, 18, (0.75, 0.2, 0.15)), (0.98, 2.16, -30, (0.15, 0.32, 0.55)), (1.10, 2.42, 64, (0.9, 0.85, 0.25))]):
    hb = box('floor_heft', -0.105, 0.105, -0.148, 0.148, 0.0, 0.006, flat('heft', hcol, rough=0.6), 0.001)
    hb.location = (x, y, 0.001 + i * 0.0002); hb.rotation_euler = (0, 0, math.radians(rz)); tag(hb, 'evening night')
pc_ = cyl('pencil_case', (0.86, 2.05, 0.035), (1.06, 2.0, 0.035), 0.033, fabric('pencil_case', (0.04, 0.05, 0.12), sheen=0.2), verts=20)
tag(pc_, 'evening night')

# night: the teen asleep on his side under the duvet, one socked foot out at the foot end
sleeper = []
for nm, c, r_ in (('torso', (0.50, 0.78, 0.53), (0.17, 0.33, 0.15)), ('hips', (0.52, 1.18, 0.51), (0.18, 0.17, 0.13)),
                  ('thighs', (0.62, 1.42, 0.49), (0.14, 0.2, 0.09)), ('shins', (0.58, 1.72, 0.47), (0.11, 0.2, 0.07)),
                  ('shoulder', (0.53, 0.42, 0.58), (0.16, 0.12, 0.14))):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0, location=c)
    so = bpy.context.object; so.name = 'sleeper_' + nm; so.scale = r_; apply_tf(so); so.hide_render = True
    so.modifiers.new('col', 'COLLISION'); so.collision.thickness_outer = 0.01; sleeper.append(so)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=34, y_subdivisions=54, size=1.0, location=(0.58, 1.10, 0.95))
nd = bpy.context.object; nd.name = 'duvet_night'; nd.scale = (1.06, 1.56, 1); nd.rotation_euler = (0, 0, math.radians(-4)); apply_tf(nd)
rn = random.Random(5); bm = bmesh.new(); bm.from_mesh(nd.data)
for v in bm.verts: v.co.z += 0.015 * math.sin(v.co.x * 11 + v.co.y * 3) * math.sin(v.co.y * 9) + rn.uniform(-0.002, 0.002)
bm.to_mesh(nd.data); bm.free()
cloth_on(nd, DV['mass'], DV['bend']); bake_cloth(nd, 60)
for o in sleeper: o.modifiers.remove(o.modifiers['col'])
for o_, th, lv_, sf, si in ((nd, 0.05, 2, 0.45, 2),):
    sm_ = o_.modifiers.new('smooth', 'SMOOTH'); sm_.factor = sf; sm_.iterations = si
    s_ = o_.modifiers.new('sol', 'SOLIDIFY'); s_.thickness = th; s_.offset = 1
    sb_ = o_.modifiers.new('sub', 'SUBSURF'); sb_.levels = lv_; sb_.render_levels = lv_
    bpy.ops.object.select_all(action='DESELECT'); o_.select_set(True); bpy.context.view_layer.objects.active = o_; bpy.ops.object.shade_smooth()
nd.data.materials.append(M['duvet']); tag(nd, 'night')
tag(bpy.data.objects['duvet'], '!night')
# the socked foot sticking out under the duvet's foot end, resting on the mattress
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0, location=(0, 0, 0))
ft = bpy.context.object; ft.name = 'sock'; ft.scale = (0.045, 0.125, 0.04); apply_tf(ft)
bm = bmesh.new(); bm.from_mesh(ft.data)
for v in bm.verts:            # heel rounder, toes flatter, a little arch
    if v.co.y > 0.05: v.co.z *= 0.75
    v.co.z += 0.012 * math.exp(-((v.co.y + 0.02) / 0.05) ** 2) * (1 if v.co.z > 0 else 0)
bm.to_mesh(ft.data); bm.free(); ft.modifiers.new('sub', 'SUBSURF').levels = 1; bpy.ops.object.shade_smooth()
ft.location = (0.60, 1.90, 0.44); ft.rotation_euler = (math.radians(8), math.radians(-70), math.radians(-14))
ft.data.materials.append(fabric('sock', (0.82, 0.82, 0.8), sheen=0.6)); tag(ft, 'night')
# the magazine slid off the bed onto the floor in the night
mn = box('magazine_night', -0.105, 0.105, -0.14, 0.14, 0.0, 0.004, M['paper'], 0.001)
mn.location = (1.13, 1.76, 0.001); mn.rotation_euler = (0, 0, math.radians(-17))   # in the bed view's frame
for ch_ in list(bpy.data.objects['magazine'].children):
    cp = ch_.copy(); cp.data = ch_.data.copy() if ch_.data else None; link(cp); cp.parent = mn; cp.matrix_parent_inverse = ch_.matrix_parent_inverse.copy()
tag(mn, 'night'); tag(bpy.data.objects['magazine'], '!night')

# ---------------------------------------------------------------- cameras (the owner may still change the angle; all presets render from one build)
CAMS = {
    'A': dict(loc=(1.25, 0.22, 0.86), target=(2.0, 3.40, 1.02), lens=24),    # first still: low, beside the bed
    'B': dict(loc=(0.24, 0.22, 2.06), target=(1.85, 3.15, 0.78), lens=19),   # high in the front-left corner
    'C': dict(loc=(1.72, 0.30, 1.15), target=(1.70, 3.95, 1.08), lens=22),   # centred on the rail
    'D': dict(loc=(0.70, 1.28, 0.98), target=(1.80, 3.00, 1.10), lens=26),   # sitting on the bed, closer to the jerseys
    'E': dict(loc=(0.55, 1.55, 1.12), target=(1.90, 3.10, 0.98), lens=22),   # bed's foot end in front, jerseys close
    'F': dict(loc=(0.30, 0.95, 1.95), target=(1.95, 3.20, 0.92), lens=20),   # high above the bed, closer to the rail
    'G': dict(loc=(1.65, 0.55, 1.45), target=(0.55, 1.45, 0.42), lens=28),   # detail: the bed
}
cd = bpy.data.cameras.new('cam'); cd.sensor_width = 36
cd.dof.use_dof = True; cd.dof.aperture_fstop = CAM['fstop']
cam = link(bpy.data.objects.new('cam', cd)); sc.camera = cam
def use_cam(k):
    c = CAMS[k]; cam.location = c['loc']; cd.lens = c['lens']
    cam.rotation_euler = (Vector(c['target']) - Vector(c['loc'])).to_track_quat('-Z', 'Y').to_euler()
    cd.dof.focus_distance = (Vector((1.55, RAIL['y'], 1.2)) - Vector(c['loc'])).length
CAM_KEYS = (argv[3] if len(argv) > 3 else 'A').split(',')
use_cam(CAM_KEYS[0])

if BLEND: bpy.ops.wm.save_as_mainfile(filepath=BLEND)
if os.environ.get('AZUR_BUILD_ONLY'):   # render_queue.py only needs the saved scene
    sys.exit(0)
import time
for k in CAM_KEYS:
    use_cam(k)
    sc.render.filepath = OUT.replace('{cam}', k) if '{cam}' in OUT else (OUT if len(CAM_KEYS) == 1 else OUT.replace('.png', f'_{k}.png'))
    t0 = time.time(); bpy.ops.render.render(write_still=True)
    print('RENDER_SECONDS', k, round(time.time() - t0, 1))
