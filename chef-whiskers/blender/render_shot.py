"""Render one shot of the 3D chicken burger film to a PNG sequence (resumable) and write its sound cues.

  python render_shot.py <shot> <seconds> <outdir> [--preview] [--scale 75] [--samples 12]
                        [--frames 0-30] [--only 12,40] [--save-blend file.blend] [--force]
  blender -b -P render_shot.py -- <same arguments>

Frames that already exist are skipped, so an interrupted render picks up where it stopped.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import lib  # noqa: E402
import shots  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("seconds", type=float)
    ap.add_argument("outdir")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--scale", type=int, default=int(os.environ.get("BLENDER_SCALE", 75)))
    ap.add_argument("--samples", type=int, default=int(os.environ.get("BLENDER_SAMPLES", 12)))
    ap.add_argument("--frames", default=None, help="range a-b (end exclusive)")
    ap.add_argument("--only", default=None, help="comma-separated frame numbers")
    ap.add_argument("--save-blend", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.shot == "list":
        print(json.dumps({k: v.seconds for k, v in shots.SHOTS.items()}))
        return
    if a.shot not in shots.SHOTS:
        sys.exit(f"unknown shot {a.shot!r}; available: {', '.join(shots.SHOTS)}")
    os.makedirs(a.outdir, exist_ok=True)
    scene = lib.reset()
    lib.setup_render(scene, a.scale, a.samples, a.preview)
    S = shots.SHOTS[a.shot]()
    S.build()
    D = a.seconds
    n = max(1, round(D * lib.FPS))
    scene.frame_start, scene.frame_end = 0, n - 1
    with open(os.path.join(a.outdir, "events.json"), "w") as f:
        json.dump({"duration": D, "events": S.events(D)}, f)
    if a.save_blend:
        S.update(0.0, D)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
    frames = range(n)
    if a.frames:
        lo, hi = (int(x) for x in a.frames.split("-"))
        frames = range(max(0, lo), min(n, hi))
    if a.only:
        frames = [int(x) for x in a.only.split(",") if 0 <= int(x) < n]
    t_start = time.time()
    done = 0
    for fr in frames:
        out = os.path.join(a.outdir, f"frame_{fr:04d}.png")
        if os.path.exists(out) and not a.force:
            continue
        scene.frame_set(fr)
        S.update(fr / lib.FPS, D)  # twice: labels and sprites that face the camera need this frame's camera
        bpy.context.view_layer.update()
        S.update(fr / lib.FPS, D)
        bpy.context.view_layer.update()
        tmp = out[:-4] + ".tmp.png"
        scene.render.filepath = tmp
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, out)
        done += 1
        print(f"FRAME {a.shot} {fr + 1}/{n} {time.time() - t0:.1f}s", flush=True)
    print(f"DONE {a.shot} {done} frames in {time.time() - t_start:.0f}s", flush=True)


main()
