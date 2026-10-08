"""AZUR scene check: things that stick into each other (round 4: the chair stood in the desk).

For every time of day, every pair of visible mesh objects whose surfaces cross is listed with how deep one reaches into
the other (vertices of A inside B, measured along B's surface normal). Resting contact (a book on the desk, a leg on
the floor) is not a fault and stays under the depth threshold; parts of one object (children of the same group) are
not compared with each other.

Usage:  python3 azur/scene/check_scene.py [blend] [--depth 0.006]     (default: the saved scene3 blend)
Prints the pairs, deepest first, and writes them to azur/.cache/check_scene.json.
"""
import os, sys, json, itertools
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
DEPTH = float(argv[argv.index('--depth') + 1]) if '--depth' in argv else 0.006
blend = next((a for a in argv if a.endswith('.blend')), os.path.join(ROOT, '.cache', 'azur_room_scene3.blend'))
STATES = ['day', 'morning', 'evening', 'night']
# the room shell and big surfaces: objects meet them all the time (legs on the floor, posters on the wall)
SHELL = ('floor', 'ceiling', 'wall_', 'sk_', 'rug', 'mattress', 'hall_light_area')


def visible(o, state):
    if o.hide_render or not o.visible_camera: return False
    tags = str(o.get('azur_state', '')).split()
    if not tags: return True
    return state in tags or (any(t.startswith('!') for t in tags) and '!' + state not in tags)


def root_of(o):
    while o.parent: o = o.parent
    return o


def main():
    bpy.ops.wm.open_mainfile(filepath=blend)
    dg = bpy.context.evaluated_depsgraph_get()
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith(SHELL)]
    trees, data = {}, {}
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        if not me or not len(me.polygons): ev.to_mesh_clear(); continue
        mw = o.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [list(p.vertices) for p in me.polygons]
        trees[o.name] = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
        data[o.name] = verts
        ev.to_mesh_clear()
    names = list(trees)
    lo = {n: Vector([min(v[i] for v in data[n]) for i in range(3)]) for n in names}
    hi = {n: Vector([max(v[i] for v in data[n]) for i in range(3)]) for n in names}
    found = {}
    for a, b in itertools.combinations(names, 2):
        if any(lo[a][i] > hi[b][i] or lo[b][i] > hi[a][i] for i in range(3)): continue
        oa, ob = bpy.data.objects[a], bpy.data.objects[b]
        if root_of(oa) is root_of(ob) and (oa.parent or ob.parent): continue
        states = [s for s in STATES if visible(oa, s) and visible(ob, s)]
        if not states: continue
        pairs = trees[a].overlap(trees[b])
        if not pairs: continue
        # how deep: vertices of one object behind the other's surface (nearest point, against its normal)
        def depth(x, y):
            d = 0.0
            for v in data[x]:
                hit = trees[y].find_nearest(v, 0.2)
                if hit[0] is None: continue
                loc, nrm = hit[0], hit[1]
                s_ = (v - loc).dot(nrm)
                if s_ < 0 and (v - loc).length > d: d = (v - loc).length
            return d
        dep = max(depth(a, b), depth(b, a))
        if dep < DEPTH: continue
        found[(a, b)] = dict(a=a, b=b, crossings=len(pairs), depth=round(dep, 4), states=states)
    out = sorted(found.values(), key=lambda r: -r['depth'])
    for r in out:
        print(f"{r['depth'] * 100:5.1f} cm  {r['a']}  x  {r['b']}  ({r['crossings']} crossings; {' '.join(r['states'])})")
    print(f'{len(out)} pairs deeper than {DEPTH * 100:.1f} cm')
    json.dump(out, open(os.path.join(ROOT, '.cache', 'check_scene.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
