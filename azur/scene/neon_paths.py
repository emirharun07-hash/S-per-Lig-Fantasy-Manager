# Trace the AZUR signature into monoline centre paths for an LED neon-flex sign.
import json, numpy as np
from PIL import Image, ImageFilter
from skimage.morphology import skeletonize, remove_small_objects
import os
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
im=Image.open(ROOT+'/assets/logo/azur-logo-ink.webp').convert('RGBA')
a=im.getchannel('A').resize((im.width*3,im.height*3),Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
m=np.array(a)>110
m=remove_small_objects(m,200)
sk=skeletonize(m)
H,W=sk.shape
pts=set(zip(*np.nonzero(sk)))
def nb(p):
    y,x=p
    return [(y+dy,x+dx) for dy in (-1,0,1) for dx in (-1,0,1) if (dy or dx) and (y+dy,x+dx) in pts]
deg={p:len(nb(p)) for p in pts}
nodes={p for p in pts if deg[p]!=2}
visited=set(); paths=[]
def walk(a,b):
    path=[a,b]; prev,cur=a,b
    while cur not in nodes:
        nxt=[q for q in nb(cur) if q!=prev and (min(cur,q),max(cur,q)) not in visited]
        if not nxt: break
        visited.add((min(cur,nxt[0]),max(cur,nxt[0])))
        prev,cur=cur,nxt[0]; path.append(cur)
    return path
for n in nodes:
    for q in nb(n):
        e=(min(n,q),max(n,q))
        if e in visited: continue
        visited.add(e); paths.append(walk(n,q))
# loops without nodes
rest=[p for p in pts if not any(p in pa for pa in paths)]
def rdp(P,eps):
    if len(P)<3: return P
    a,b=np.array(P[0],float),np.array(P[-1],float); d=b-a; L=np.hypot(*d) or 1
    dist=[abs(np.cross(d,np.array(p,float)-a))/L for p in P[1:-1]]
    i=int(np.argmax(dist))+1
    if dist[i-1]>eps: return rdp(P[:i+1],eps)[:-1]+rdp(P[i:],eps)
    return [P[0],P[-1]]
# merge tiny spurs: drop paths shorter than 18px that end in an endpoint
out=[]
for p in paths:
    ends=(deg[p[0]]==1)+(deg[p[-1]]==1)
    # spurs: short twigs that the skeleton grows into thick brush ends (one free end, one junction)
    if ends==1 and len(p)<60: continue
    out.append(rdp(p,1.2))
# thick brush strokes become a double tube (a loop around the stroke), thin strokes stay a single tube
from scipy.ndimage import distance_transform_edt
dist=distance_transform_edt(m)
R0=11.0          # half-width in px (3x scale) above which a stroke counts as thick
def offset_loop(run):
    P=np.array(run,float); n=len(P)
    T=np.gradient(P,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True)+1e-9
    Nn=np.stack([-T[:,1],T[:,0]],1)
    r=np.array([dist[int(y),int(x)] for y,x in run])*0.5
    a=[tuple(v) for v in P+Nn*r[:,None]]; b=[tuple(v) for v in (P-Nn*r[:,None])[::-1]]
    # simplify each side on its own (a closed loop has identical end points, which defeats RDP)
    return rdp(a,1.0)+rdp(b,1.0)+[a[0]]
final=[]
for p in out:
    # densify the simplified path again so widths can be sampled along it
    dense=[]
    for (y0,x0),(y1,x1) in zip(p,p[1:]):
        k=max(1,int(np.hypot(y1-y0,x1-x0)/4))
        dense+= [(y0+(y1-y0)*t/k, x0+(x1-x0)*t/k) for t in range(k)]
    dense.append(p[-1])
    thick=[dist[int(round(y)),int(round(x))]>R0 for y,x in dense]
    i=0
    while i<len(dense):
        j=i
        while j<len(dense) and thick[j]==thick[i]: j+=1
        run=dense[max(0,i-1):min(len(dense),j+1)]
        if thick[i] and len(run)>=34: final.append(offset_loop(run))
        elif len(run)>=2: final.append(rdp(run,1.2))
        i=j
width_m=0.62; s=width_m/W
polys=[[[ (x-W/2)*s, (H/2-y)*s ] for y,x in p] for p in final]
json.dump({'width':width_m,'height':H*s,'paths':polys},open(HERE+'/neon_paths.json','w'))
print('paths',len(polys),'points',sum(len(p) for p in polys),'size',W,H)
# preview
prev=Image.new('RGB',(W,H),(10,14,20)); import PIL.ImageDraw as D; d=D.Draw(prev)
for p in final: d.line([(x,y) for y,x in p],fill=(120,220,255),width=6)
os.makedirs(ROOT+'/.cache',exist_ok=True); prev.save(ROOT+'/.cache/neon_paths.png')
