"""Build the complete Blender project.

    python build.py                 # -> out/spaghetti_bolognese.blend + out/timeline.json
    python build.py --only S4_sauce   # build a subset (for iteration)

Works with the `bpy` module (pip install bpy==5.2.3) or inside Blender:
    blender -b -P build.py -- [args]
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import bpy  # noqa: E402

import config as C  # noqa: E402
from cb import util as U, shots as SH  # noqa: E402


def make_edit_scene(names):
    sc = bpy.data.scenes.get("Scene") or bpy.data.scenes.new("FULL_FILM")
    sc.name = "FULL_FILM"
    sc.render.resolution_x, sc.render.resolution_y = C.RES_X, C.RES_Y
    sc.render.fps = C.FPS
    sc.frame_start, sc.frame_end = 1, C.TOTAL_FRAMES
    sed = sc.sequence_editor_create()
    strips = sed.strips if hasattr(sed, "strips") else sed.sequences
    starts = C.shot_starts()
    for name in names:
        st = strips.new_scene(name=name, scene=bpy.data.scenes[name], channel=1, frame_start=starts[name])
        st.scene_camera = bpy.data.scenes[name].camera
    return sc


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    only = [s for s in a.only.split(",") if s]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    U.set_linear_keys()
    data = {"fps": C.FPS, "res": [C.RES_X, C.RES_Y], "bpm": C.BPM, "total": C.TOTAL_FRAMES, "shots": []}
    starts = C.shot_starts()
    built = []
    for name, nf in C.SHOTS:
        if only and name not in only:
            continue
        print(f"[build] {name} ({nf} frames)", flush=True)
        S = SH.BUILDERS[name](name, nf)
        d = S.export()
        d["start"] = starts[name]
        data["shots"].append(d)
        built.append(name)
    make_edit_scene(built)
    tag = "_".join(only) if only else "spaghetti_bolognese"
    blend = os.path.join(a.out, f"{tag}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    with open(os.path.join(a.out, f"timeline{'_' + tag if only else ''}.json"), "w") as fh:
        json.dump(data, fh)
    print(f"[build] saved {blend}", flush=True)


if __name__ == "__main__":
    main()
