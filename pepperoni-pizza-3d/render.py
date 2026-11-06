"""Render shot frames with Cycles (resumable: existing frames are skipped).

    python render.py --blend out/pepperoni_pizza.blend --frames-dir out/frames
    python render.py --shots S4_sauce --range 1-40 --scale 0.25 --samples 6 --step 5
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import bpy  # noqa: E402
import config as C  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", default=os.path.join(ROOT, "out", "pepperoni_pizza.blend"))
    ap.add_argument("--frames-dir", default=os.path.join(ROOT, "out", "frames"))
    ap.add_argument("--shots", default="")
    ap.add_argument("--range", default="")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--scale", type=float, default=None)
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--frames", default="", help="explicit comma list of shot-local frames")
    a = ap.parse_args(argv)
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    names = [s for s in a.shots.split(",") if s] or [n for n, _ in C.SHOTS if n in bpy.data.scenes]
    for name in names:
        sc = bpy.data.scenes[name]
        if a.scale:
            sc.render.resolution_percentage = int(round(a.scale * 100))
        if a.samples:
            sc.cycles.samples = a.samples
        out = os.path.join(a.frames_dir, name)
        os.makedirs(out, exist_ok=True)
        if a.frames:
            frames = [int(x) for x in a.frames.split(",")]
        elif a.range:
            lo, hi = (int(x) for x in a.range.split("-"))
            frames = list(range(lo, hi + 1, a.step))
        else:
            frames = list(range(sc.frame_start, sc.frame_end + 1, a.step))
        todo = [f for f in frames if not os.path.exists(os.path.join(out, f"{f:04d}.png"))]
        # group into contiguous runs and render each with Blender's own
        # animation loop (keeps persistent data, single depsgraph evaluation)
        runs, cur = [], []
        for f in todo:
            if cur and (f != cur[-1] + a.step):
                runs.append(cur)
                cur = []
            cur.append(f)
        if cur:
            runs.append(cur)
        fs, fe, fstep = sc.frame_start, sc.frame_end, sc.frame_step
        for run in runs:
            t = time.time()
            sc.frame_start, sc.frame_end, sc.frame_step = run[0], run[-1], a.step
            sc.render.filepath = os.path.join(out, "")
            # the scene must be the *context* scene, otherwise its animation
            # is not evaluated when running headless
            with bpy.context.temp_override(scene=sc, view_layer=sc.view_layers[0]):
                bpy.ops.render.render(animation=True)
            dt = time.time() - t
            print(f"[render] {name} {run[0]:04d}-{run[-1]:04d} ({len(run)} fr) {dt:6.1f}s "
                  f"= {dt / len(run):.1f}s/frame", flush=True)
        sc.frame_start, sc.frame_end, sc.frame_step = fs, fe, fstep


if __name__ == "__main__":
    main()
