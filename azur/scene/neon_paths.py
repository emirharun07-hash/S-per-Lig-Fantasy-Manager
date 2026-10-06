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
    if len(p)<18 and (deg[p[0]]==1 or deg[p[-1]]==1): continue
    out.append(rdp(p,1.2))
width_m=0.62; s=width_m/W
polys=[[[ (x-W/2)*s, (H/2-y)*s ] for y,x in p] for p in out]
json.dump({'width':width_m,'height':H*s,'paths':polys},open(HERE+'/neon_paths.json','w'))
print('paths',len(polys),'points',sum(len(p) for p in polys),'size',W,H)
# preview
prev=Image.new('RGB',(W,H),(10,14,20)); import PIL.ImageDraw as D; d=D.Draw(prev)
for p in out: d.line([(x,y) for y,x in p],fill=(120,220,255),width=6)
os.makedirs(ROOT+'/.cache',exist_ok=True); prev.save(ROOT+'/.cache/neon_paths.png')
