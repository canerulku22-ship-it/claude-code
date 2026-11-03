"""Look-dev: hero burger under several view transforms -> contact sheet.
Usage: python tools/lookdev.py OUTDIR"""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import bpy
import config as C
from cb import util as U, materials as M, models as MD, stage as ST
out = sys.argv[1]; C.RENDER_SCALE = 0.35
U.set_linear_keys()
w = M.backdrop_world("w_look")
sc = ST.new_scene("look", 1, w, samples=16)
co = sc.collection
b = MD.burger("hero", co, C.ASSEMBLY_ORDER, C.SAUCE_COLOR)
zs, H = MD.stack_heights(C.ASSEMBLY_ORDER)
for k, o in b.items():
    o.location = (0, 0, zs[k]); o.rotation_euler = (0, 0, 0.5 + MD.LAYER_ROT.get(k, 0.0))
L = ST.studio_rig(sc, (0, 0, 0.4))
cam = ST.camera(sc, "cam", 60, 4.0)
tr = U.CamTrack(cam)
tr.set(1, (0.0, -3.4, 1.0), (0, 0, 0.36), 60)
base = {k: l.data.energy for k, l in L.items()}
cfgs = [("agx_punchy_k1", "AgX", "AgX - Punchy", 1.0),
        ("agx_punchy_k07", "AgX", "AgX - Punchy", 0.7),
        ("pbrneutral_k07", "Khronos PBR Neutral", "None", 0.7)]
from PIL import Image
ims = []
for name, vt, lk, k in cfgs:
    sc.view_settings.view_transform = vt; sc.view_settings.look = lk
    for kk, l in L.items():
        l.data.energy = base[kk] * k
    sc.render.filepath = os.path.join(out, f"ld_{name}.png")
    bpy.ops.render.render(write_still=True, scene=sc.name)
    ims.append(Image.open(sc.render.filepath).convert("RGB"))
W, Hh = ims[0].size
sheet = Image.new("RGB", (W * len(ims), Hh))
for i, im in enumerate(ims):
    sheet.paste(im, (i * W, 0))
sheet.save(os.path.join(out, "sheet.png"))
print("done")
