"""Download the CC0 Poly Haven textures, HDRI and models the scene needs into azur/.cache/ph (or $AZUR_CACHE).
Usage: python3 scene/fetch_assets.py"""
import json, subprocess, os, sys
BASE=os.environ.get('AZUR_CACHE', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.cache', 'ph'))
def get(url, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out)>0: return
    subprocess.run(["curl","-sSL","--max-time","300","-o",out,url],check=True)
def files(aid):
    return json.loads(subprocess.run(["curl","-sS","--max-time","60",f"https://api.polyhaven.com/files/{aid}"],capture_output=True,text=True).stdout)
def texture(aid,res='2k'):
    f=files(aid); out={}
    for m in ['Diffuse','nor_gl','Rough','Displacement','AO','arm']:
        if m in f and res in f[m]:
            fmt='jpg' if 'jpg' in f[m][res] else list(f[m][res].keys())[0]
            p=f"{BASE}/tex/{aid}/{aid}_{m}_{res}.{fmt}"; get(f[m][res][fmt]['url'],p); out[m]=p
    return out
def hdri(aid,res='4k'):
    f=files(aid); p=f"{BASE}/hdri/{aid}_{res}.hdr"; get(f['hdri'][res]['hdr']['url'],p); return p
def model(aid,res='1k'):
    f=files(aid); g=f['gltf'][res]['gltf']; d=f"{BASE}/models/{aid}"
    p=f"{d}/{aid}_{res}.gltf"; get(g['url'],p)
    for rel,inc in g.get('include',{}).items(): get(inc['url'],f"{d}/{rel}")
    return p
# Everything the scene uses (all CC0, polyhaven.com). Round 5: 4k textures and 2k models (2k/1k were soft on large screens)
TEX_RES, MODEL_RES = '4k', '2k'
TEXTURES=['white_plaster_02','laminate_floor_02','oak_veneer_01','cotton_jersey','dirty_carpet','rough_linen','grass_ground']   # grass: round 4, the lawn outside the window
HDRIS=['eilenriede_park']
MODELS=['football','desk_lamp_arm_01','Shelf_01','book_encyclopedia_set_01','alarm_clock_01','boombox','cardboard_box_01',
        'gamepad','throw_pillows_01','binder_notebook','stationery_supplies','modern_ceiling_lamp_01']
if __name__=='__main__' and len(sys.argv)==1:
    for t in TEXTURES: print(texture(t,TEX_RES))
    for h in HDRIS: print(hdri(h,'4k'))
    for m in MODELS: print(model(m,MODEL_RES))
elif __name__=='__main__':
    kind=sys.argv[1]; res=sys.argv[3] if len(sys.argv)>3 else None
    fn={'tex':texture,'hdri':hdri,'model':model}[kind]
    print(fn(sys.argv[2],res) if res else fn(sys.argv[2]))
