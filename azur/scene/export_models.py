"""AZUR jersey models for the product view: every jersey as it hangs in the room (draped shell + wooden hanger)
as a small GLB the browser can turn and zoom (prototype/js/azur-viewer.js).

Each model is in its own space: the hook point at the origin, the front facing the viewer, metres, Y up (glTF).
Textures are the shop photos (front and back), WebP, at most 1024 px. A later 3D scan of a product can replace its
GLB under the same name (models.json says which file belongs to which jersey).

Usage:  python3 azur/scene/export_models.py     -> prototype/assets/<set>/models/<key>.glb + models.json
No rendering: reads the saved scene (builds it first if needed).
"""
import os, sys, json
import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq

OUT = os.environ.get('AZUR_MODELS_OUT') or os.path.join(rq.ROOT, 'prototype', 'assets', rq.SET, 'models')
MAX_TEX = 1024


def simplify_materials(o):
    """Keep what glTF carries: the photo as base colour, roughness, sheen. (The knit normal map is a room detail.)"""
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.use_nodes: continue
        nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
        if not b: continue
        for l in list(b.inputs['Normal'].links): nt.links.remove(l)
        for n in [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image]:
            im = n.image; w, h = im.size
            if max(w, h) > MAX_TEX:
                k = MAX_TEX / max(w, h); im.scale(int(w * k), int(h * k))


def plain_wood(o):
    """The hanger without its 2k oak textures (2.5 MB): a flat wood colour is plenty at product-view size."""
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.use_nodes: continue
        nt = m.node_tree; b = nt.nodes.get('Principled BSDF')
        for n in [n for n in nt.nodes if n.type in ('TEX_IMAGE', 'NORMAL_MAP', 'BUMP')]: nt.nodes.remove(n)
        if b:
            b.inputs['Base Color'].default_value = (0.42, 0.26, 0.14, 1); b.inputs['Roughness'].default_value = 0.45
            b.inputs['Metallic'].default_value = 0.0


def main():
    rq.hand_over_to_watch_v2()
    rq.ensure_blend()
    rq.open_scene()
    os.makedirs(OUT, exist_ok=True)
    jerseys = sorted([o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('jersey_') and not o.name.endswith('_hanger')],
                     key=lambda o: o.matrix_world.translation.x)
    meta = {}; out = []
    for o in jerseys:
        key = o.name[len('jersey_'):]
        hg = bpy.data.objects.get(o.name + '_hanger')
        yaw = o.matrix_world.to_euler().z
        for x in [o] + ([hg] if hg else []):
            x.matrix_world = Matrix.Identity(4)        # own space: hook point at the origin, front toward -Y
            for m in [m for m in x.modifiers if m.type in ('SOLIDIFY', 'SUBSURF')]: x.modifiers.remove(m)   # light: the browser smooths
        simplify_materials(o)
        if hg: plain_wood(hg)
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        if hg: hg.select_set(True)
        bpy.context.view_layer.objects.active = o
        dst = os.path.join(OUT, key + '.glb')
        bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=True,
                                  export_yup=True, export_texcoords=True, export_normals=True, export_materials='EXPORT',
                                  export_image_format='WEBP', export_image_quality=86, export_cameras=False,
                                  export_lights=False, export_animations=False, export_extras=False)
        pts = [v.co for v in o.data.vertices]
        meta[key] = dict(file=f'models/{key}.glb', bytes=os.path.getsize(dst), source='cloth-sim from shop photos',
                         height=round(-min(p.z for p in pts), 3), width=round(max(p.x for p in pts) - min(p.x for p in pts), 3),
                         room_yaw=round(yaw, 4))
        rq.log('model', key, meta[key]['bytes'] // 1024, 'KB'); out.append(dst)
    mpath = os.path.join(OUT, 'models.json'); json.dump(meta, open(mpath, 'w'), indent=1)
    rq.git_save(out + [mpath], 'AZUR jersey models for the product view')
    rq.git_push(force=True)


if __name__ == '__main__':
    main()
