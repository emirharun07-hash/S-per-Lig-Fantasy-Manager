"""AZUR jerseys on wooden hangers: cloth-simulated shells built from the shop's front and back photos.

The photo outline is the sewing pattern: a front and a back panel that meet along the outline (a closed shell). A
wooden hanger sits inside at the shoulders, its hook leaves through the collar. Gravity does the rest in Blender's cloth
solver: the shoulders rest on the hanger, the sleeves drop, front and back fall together below the arms, and a little
inner pressure keeps the shirt from looking flat. Textures stay the photos (UVs from the flat pattern).

Swappable: when real 3D scans of the jerseys exist, `jersey()` can load them instead and keep the same contract
(an object whose local origin is the hook point, front facing -Y).
Kept light for render time: about 2-3k vertices per panel before subdivision.
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix


def _img(path, cs='sRGB'):
    im = bpy.data.images.load(path, check_existing=True); im.colorspace_settings.name = cs; return im


def wood_hanger(name, width=0.43, slope_deg=13.0, thick=0.012, depth=0.034, mat=None):
    """Contoured wooden hanger as a mesh (also the collision body for the cloth). Origin: where the hook enters."""
    bm = bmesh.new()
    half = width / 2; n = 24
    prof = []
    for i in range(n + 1):                          # centre line from left tip to right tip
        x = -half + width * i / n
        drop = math.tan(math.radians(slope_deg)) * abs(x) + 0.010 * (abs(x) / half) ** 3
        prof.append((x, -drop))
    rings = []
    for i, (x, z) in enumerate(prof):
        t = abs(x) / half
        d = depth * (1.0 - 0.25 * t) ; h = thick * (1.0 + 0.6 * (1 - t))        # fuller in the middle
        ring = [bm.verts.new((x, y, z + dz)) for y, dz in ((-d / 2, -h / 2), (d / 2, -h / 2), (d / 2, h / 2), (-d / 2, h / 2))]
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.modifiers.new('bev', 'BEVEL').width = 0.003
    for p in me.polygons: p.use_smooth = True
    if mat: me.materials.append(mat)
    return o


def panels(name, front_path, back_path, h=0.74, cell=0.014, depth=0.07, tex_dir=None):
    """Closed shell from the photo outline. Returns (object, info) with the shoulder line for the hanger."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    fr = Image.open(front_path).convert('RGBA'); bk = Image.open(back_path).convert('RGBA')
    frc = fr.crop(fr.getchannel('A').getbbox())
    bkc = bk.crop(bk.getchannel('A').getbbox()).transpose(Image.FLIP_LEFT_RIGHT).resize(frc.size, Image.LANCZOS)
    tex_dir = tex_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.cache', 'jersey_tex')
    os.makedirs(tex_dir, exist_ok=True)
    fpath, bpath = os.path.join(tex_dir, name + '_front.png'), os.path.join(tex_dir, name + '_back.png')
    def bleed(im):                    # every transparent pixel takes the colour of the nearest garment pixel
        a = np.asarray(im)
        _, idx = ndimage.distance_transform_edt(a[..., 3] < 128, return_indices=True)
        rgb = a[..., :3][idx[0], idx[1]]
        return Image.fromarray(np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)]).astype(np.uint8), 'RGBA')
    bleed(frc).save(fpath); bleed(bkc).save(bpath)
    W, H = frc.size; w = h * W / H
    rows, cols = int(round(h / cell)), int(round(w / cell))
    af = np.asarray(frc.getchannel('A').resize((cols, rows), Image.BOX), dtype=np.float32) / 255
    ab = np.asarray(bkc.getchannel('A').resize((cols, rows), Image.BOX), dtype=np.float32) / 255
    cells = ndimage.binary_fill_holes(np.maximum(af, ab) > 0.5)
    lab, nlab = ndimage.label(cells)                     # keep the garment, drop stray specks
    if nlab > 1: cells = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    dist = ndimage.distance_transform_edt(cells) * cell
    k = depth / math.sqrt(max(dist.max(), 1e-6))
    pad = np.pad(cells, 1); dpad = np.pad(dist, 1)
    used = {}; verts = []
    def vid(r, c, layer):
        key = (r, c, layer)
        if key in used: return used[key]
        around = [(r - 1, c - 1), (r - 1, c), (r, c - 1), (r, c)]
        boundary = not all(pad[rr + 1, cc + 1] for rr, cc in around)
        if boundary and layer == 1 and (r, c, 0) in used:
            used[key] = used[(r, c, 0)]; return used[key]
        d = 0.0 if boundary else float(np.mean([dpad[rr + 1, cc + 1] for rr, cc in around]))
        t = k * math.sqrt(d)
        x = (c / cols - 0.5) * w; z = -(r / rows) * h
        verts.append((x, -t / 2 if layer == 0 else t / 2, z)); used[key] = len(verts) - 1
        return used[key]
    faces, fmat, fuv = [], [], []
    for layer in (0, 1):
        for r in range(rows):
            for c in range(cols):
                if not cells[r, c]: continue
                q = [(r, c), (r + 1, c), (r + 1, c + 1), (r, c + 1)] if layer == 0 else [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]
                faces.append([vid(rr, cc, layer) for rr, cc in q]); fmat.append(layer)
                fuv.append([(cc / cols, 1 - rr / rows) for rr, cc in q])
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    # the cell grid leaves a staircase outline: relax the outline vertices along the outline (x/z only, UVs follow)
    bm = bmesh.new(); bm.from_mesh(me)
    rim = [e for e in bm.edges if len(e.link_faces) == 2 and (e.link_faces[0].normal.y > 0) != (e.link_faces[1].normal.y > 0)
           and abs(e.link_faces[0].normal.y) > 0.5 and abs(e.link_faces[1].normal.y) > 0.5]   # where front meets back
    nbr = {}
    for e in rim:
        a_, b_ = e.verts; nbr.setdefault(a_, set()).add(b_); nbr.setdefault(b_, set()).add(a_)
    for _ in range(6):
        new = {v: Vector(((v.co.x + sum(n.co.x for n in ns) / len(ns)) / 2, v.co.y, (v.co.z + sum(n.co.z for n in ns) / len(ns)) / 2)) for v, ns in nbr.items() if len(ns) == 2}
        for v, co in new.items(): v.co = co
    bm.to_mesh(me); bm.free(); me.update()
    ul = me.uv_layers.new(name='UVMap')
    for fi, poly in enumerate(me.polygons):
        poly.material_index = fmat[fi]; poly.use_smooth = True
        for loop in poly.loop_indices:
            co = me.vertices[me.loops[loop].vertex_index].co
            ul.data[loop].uv = (co.x / w + 0.5, 1 + co.z / h)
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    # shoulder line: the top of the outline per column (for the hanger), and the collar centre
    tops = [next((r for r in range(rows) if cells[r, c]), rows) for c in range(cols)]
    mid = cols // 2
    widths = [int(cells[r].sum()) for r in range(int(rows * 0.45), int(rows * 0.8))]   # the body below the sleeves
    info = dict(w=w, h=h, rows=rows, cols=cols, cell=cell, collar_top=-(tops[mid] / rows) * h, body_w=min(widths) * cell,
                shoulder=[((c / cols - 0.5) * w, -(tops[c] / rows) * h) for c in range(cols)], front=fpath, back=bpath)
    return o, info


def materials(o, name, knit_normal=None):
    """Photo textures on both panels, cotton sheen, a fine knit normal map."""
    for path, side in ((o['front'], 'front'), (o['back'], 'back')):
        m = bpy.data.materials.new(name + '_' + side); m.use_nodes = True
        nt = m.node_tree; N = nt.nodes; b = N['Principled BSDF']
        it = N.new('ShaderNodeTexImage'); it.image = _img(path); it.extension = 'EXTEND'; it.interpolation = 'Cubic'
        nt.links.new(it.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.62; b.inputs['Sheen Weight'].default_value = 0.4; b.inputs['Sheen Roughness'].default_value = 0.35
        if knit_normal:
            tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (38, 38, 38)
            nn = N.new('ShaderNodeTexImage'); nn.image = _img(knit_normal, 'Non-Color'); nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.2
            nt.links.new(tc.outputs['UV'], mp.inputs[0]); nt.links.new(mp.outputs[0], nn.inputs[0]); nt.links.new(nn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
        o.data.materials.append(m)


def drape(o, hanger, frames=48, pressure=0.35, pin=None, scene=None):
    """Hang the shell on the hanger (both in the same local frame, hook point at the origin) and bake the result."""
    sc = scene or bpy.context.scene
    col = hanger.modifiers.new('col', 'COLLISION'); hanger.collision.thickness_outer = 0.004; hanger.collision.cloth_friction = 40
    cl = o.modifiers.new('cloth', 'CLOTH'); cs = cl.settings
    cs.quality = 8; cs.mass = 0.15; cs.air_damping = 3.0
    cs.tension_stiffness = 45; cs.compression_stiffness = 45; cs.shear_stiffness = 12; cs.bending_stiffness = 1.6
    if pin: cs.vertex_group_mass = pin; cs.pin_stiffness = 1.0
    cs.use_pressure = pressure > 0; cs.uniform_pressure_force = pressure; cs.pressure_factor = 1.0
    cc = cl.collision_settings; cc.use_self_collision = True; cc.self_distance_min = 0.004; cc.distance_min = 0.004; cc.collision_quality = 3
    pc = cl.point_cache; pc.frame_start = 1; pc.frame_end = frames
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1): sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get(); coords = [v.co.copy() for v in o.evaluated_get(dg).data.vertices]
    o.modifiers.remove(cl); hanger.modifiers.remove(col)
    for v, c in zip(o.data.vertices, coords): v.co = c
    sc.frame_set(1)


def jersey(name, front_path, back_path, knit_normal=None, hanger_mat=None, h=0.74, frames=48):
    """Build shell + hanger, drape, return (jersey object, hanger object). Origin = hook point at the top of the collar."""
    o, info = panels(name, front_path, back_path, h=h)
    o['front'], o['back'] = info['front'], info['back']
    # hanger inside, its top a little under the collar edge and following the shoulder line
    width = min(0.40, info['body_w'] * 0.86)
    span = [(x, z) for x, z in info['shoulder'] if abs(x) < width / 2]
    collar = info['collar_top']
    tip = min(z for _, z in span) if span else collar - 0.05            # the outline top at the hanger tips
    slope = math.degrees(math.atan2(max(0.01, collar - tip), width / 2))
    hg = wood_hanger(name + '_hanger', width=width, slope_deg=min(24.0, max(8.0, slope + 2)), mat=hanger_mat)
    hg.location = (0, 0, collar - 0.045)
    bpy.context.view_layer.update()
    # the hanger is the collision body in the shell's frame; apply its location into the mesh
    hg.data.transform(Matrix.Translation(hg.location)); hg.location = (0, 0, 0)
    # the collar is held where the hook passes through the neck opening (otherwise it flops forward)
    vg = o.vertex_groups.new(name='collar')
    vg.add([v.index for v in o.data.vertices if v.co.z > collar - 0.035 and abs(v.co.x) < 0.075], 1.0, 'REPLACE')
    away = Vector((80.0, 80.0, 80.0))                # simulate far from the room (its floor, bed and walls collide too)
    o.location = away; hg.location = away; bpy.context.view_layer.update()
    drape(o, hg, frames=frames, pin='collar')
    o.location = (0, 0, 0); hg.location = (0, 0, 0)
    o.vertex_groups.remove(vg)
    materials(o, name, knit_normal)
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.0015; sol.offset = 1   # cloth edge thickness at the hem
    return o, hg
