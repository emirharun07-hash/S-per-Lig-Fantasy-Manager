"""AZUR quick look: small, fast renders of the scene for checking it before the long render run.

Every view in every time of day (day, morning, evening, night) plus close-ups of the jerseys, the neon sign and the desk,
as JPGs in azur/previews/ (overwritten each time; pushed, so the cloud session can look at them).

Usage:  python azur/scene/render_preview.py            (all)
        python azur/scene/render_preview.py jerseys    (only shots whose name contains a word)
        python azur/scene/render_preview.py full room_day   (a test still at the plates' size and samples)
Env:    AZUR_PREVIEW_SAMPLES=64  AZUR_PREVIEW_RES=1280x720
About 2 minutes on the owner's PC (RX 6750 XT), not counting a scene rebuild.
"""
import os, sys, json, time
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_queue as rq
import render_moves as rm

OUT = os.environ.get('AZUR_PREVIEW_OUT') or os.path.join(rq.ROOT, 'previews')
SAMPLES = int(os.environ.get('AZUR_PREVIEW_SAMPLES', 64))
RES = tuple(int(x) for x in os.environ.get('AZUR_PREVIEW_RES', '1280x720').split('x'))
LIGHT = {'day': 'day', 'morning': 'day', 'evening': 'evening', 'night': 'night'}


def hook_x(i):
    hooks = sorted([o for o in bpy.data.objects if o.name.startswith('hook')], key=lambda o: o.matrix_world.translation.x)
    return hooks[min(i, len(hooks) - 1)].matrix_world.translation.x


def shots():
    """(name, state, camera) where camera is a view key or (loc, target, lens)."""
    out = []
    for v in ('room', 'bed', 'rail'):
        for st in rq.STATES:
            out.append((f'{v}_{st}', st, v))
    out.append(('rail_m_day', 'day', 'rail_m'))
    cx = (hook_x(0) + hook_x(5)) / 2
    out.append(('jerseys', 'day', ((cx, 1.75, 1.20), (cx, 2.95, 1.05), 24)))
    x1 = hook_x(1)
    out.append(('jersey_detail', 'day', ((x1 + 0.05, 2.25, 1.25), (x1, 2.95, 1.15), 35)))
    out.append(('jersey_side', 'day', ((x1 + 0.9, 2.35, 1.30), (x1 + 0.25, 2.95, 1.20), 30)))
    out.append(('neon', 'night', ((1.76, 2.55, 1.85), (1.76, 4.0, 2.22), 45)))
    out.append(('desk', 'day', ((1.25, 1.55, 1.35), (0.30, 2.85, 0.80), 30)))
    out.append(('floor_evening', 'evening', ((2.2, 1.0, 1.5), (1.0, 2.2, 0.0), 26)))
    out.append(('bed_close_night', 'night', ((1.6, 2.4, 1.3), (0.5, 1.2, 0.45), 26)))
    return out


def main():
    rq.hand_over_to_watch_v2()
    rq.ensure_blend()
    sc = rq.open_scene()
    os.makedirs(OUT, exist_ok=True)
    want = [w for w in rq.ONLY if w != 'full']
    full = 'full' in rq.ONLY               # round 5: a test still as the long run will make it, before that run
    done = []; t_all = time.time()
    for name, state, camv in shots():
        if want and not any(w in name for w in want): continue
        rq.restore_visibility()
        rm.light_variant(sc, LIGHT[state])
        rq.set_state(state)
        sc.cycles.samples = SAMPLES; sc.cycles.adaptive_threshold = 0.03
        if full: sc.cycles.samples = rq.SAMPLES['beauty']; sc.cycles.adaptive_threshold = rq.NOISE
        if isinstance(camv, str):
            rq.set_view(sc, camv)
            rx, ry = rq.VIEWS[camv]['res']; k = 1.0 if full else RES[0] / max(rx, ry) if camv == 'rail_m' else RES[0] / rx
            sc.render.resolution_x, sc.render.resolution_y = int(rx * k), int(ry * k)
        else:
            loc, tgt, lens = camv; cam = sc.camera; cd = cam.data
            cd.sensor_fit = 'AUTO'; cd.sensor_width = 36
            cam.location = loc; cd.lens = lens
            cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
            cd.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
            sc.render.resolution_x, sc.render.resolution_y = RES
        png = os.path.join(OUT, name + '.png'); dst = png.replace('.png', '.jpg')
        secs = rq.render_to(sc, png)
        from PIL import Image
        Image.open(png).convert('RGB').save(dst, 'JPEG', quality=95 if full else 85, optimize=True); os.remove(png)
        rq.log('preview', name, secs, 's'); done.append(dst)
    info = os.path.join(OUT, 'info.json')
    json.dump(dict(request=os.environ.get('AZUR_REQUEST_ID'), set=rq.SET, samples=rq.SAMPLES['beauty'] if full else SAMPLES, res=RES, full=full,
                   seconds=round(time.time() - t_all), shots=[os.path.basename(p) for p in done],
                   time=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())), open(info, 'w'), indent=1)
    rq.git_save(done + [info], 'AZUR preview renders')
    rq.git_push(force=True)
    rq.log('preview finished', len(done), 'shots')


if __name__ == '__main__':
    main()
