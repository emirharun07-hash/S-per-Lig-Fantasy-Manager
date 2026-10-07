"""Time this machine: render one full-size rail plate (1600x900, the queue's beauty settings) into azur/.cache.
Usage: python azur/scene/bench.py        (AZUR_GPU=1 to use the graphics chip). Nothing is committed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq
import bpy
from mathutils import Vector

rq.ensure_blend()
sc = rq.open_scene()
rq.set_view(sc, 'rail'); rq.render_settings(sc, 'beauty'); rq.lights_off(sc)
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 2.2; rq.world_tint(sc, (1.0, 0.86, 0.72))
s = bpy.data.objects['sun']; s.hide_render = False; s.data.energy = 3.0; s.data.color = (1.0, 0.60, 0.33)
s.rotation_euler = Vector(rq.SUN['sun_low']).normalized().to_track_quat('-Z', 'Y').to_euler()
out = os.path.join(rq.ROOT, '.cache', 'bench.png')
secs = rq.render_to(sc, out)
rq.log('bench: rail plate 1600x900,', sc.cycles.samples, 'samples:', secs, 's (cloud CPU: about 545 s)')
