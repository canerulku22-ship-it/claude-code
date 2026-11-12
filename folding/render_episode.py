"""Render one episode. Runs inside Blender:

    blender -b -P render_episode.py -- --config episodes/paper.json [--preview]

Steps:
  1. build the scene from the config (no .blend file, nothing manual)
  2. render every frame with Eevee to output/<episode>/<mode>/frames/
  3. write events.json: the timed events log + per-frame tracks
  4. run post.py: sound effects, counter overlay and final MP4 (ffmpeg)

Options (after the `--`):
  --config FILE     episode JSON (required)
  --preview         540x960, low samples, first ~10 seconds only
  --stills          also render one still per landmark beat (look check)
  --samples N       Eevee samples (default 24 full, 6 preview)
  --start/--end S   only render this time range (seconds)
  --out DIR         output root (default: ./output)
  --resume          keep frames that already exist
  --frames-only     skip post-processing (audio, overlay, encode)
  --dry-run         render nothing; write the events log and the soundtrack
                    only (fast check of pacing and audio)
"""

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402

from foldlib import DEFAULT_OUTPUT_DIR  # noqa: E402
from foldlib.config import load_config  # noqa: E402
from foldlib.timeline import Timeline  # noqa: E402

PREVIEW_SECONDS = 10.0


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="render_episode.py")
    p.add_argument("--config", required=True)
    p.add_argument("--preview", action="store_true")
    p.add_argument("--stills", action="store_true")
    p.add_argument("--samples", type=int)
    p.add_argument("--start", type=float)
    p.add_argument("--end", type=float)
    p.add_argument("--out", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--frames-only", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    args = parse_args()
    cfg = load_config(args.config)
    tl = Timeline(cfg)
    print(tl.summary())

    mode = "preview" if args.preview else "full"
    width, height = (540, 960) if args.preview else (1080, 1920)
    samples = args.samples or (6 if args.preview else 24)
    out_dir = os.path.join(os.path.abspath(args.out), cfg["slug"], mode)
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    from foldlib.blender import scene as scene_mod
    from foldlib.blender.animate import Animator

    refs = scene_mod.build(cfg, tl, width, height, samples)
    anim = Animator(refs, tl, cfg)

    end_t = tl.duration
    if args.preview:
        end_t = min(PREVIEW_SECONDS, end_t)
    if args.end is not None:
        end_t = min(end_t, args.end)
    start_t = args.start or 0.0
    f_start = int(round(start_t * tl.fps))
    f_end = int(round(end_t * tl.fps))

    # Render. Per-frame state is recorded for every frame (cheap) so the
    # events log is complete even when resuming.
    records = []
    t_begin = time.time()
    rendered = 0
    for f in range(0, f_end):
        t = f / tl.fps
        rec = anim.apply(t)
        rec["frame"] = f
        records.append(rec)
        if f < f_start:
            continue
        path = os.path.join(frames_dir, f"{f:05d}.png")
        if args.dry_run or (args.resume and os.path.exists(path)):
            continue
        render_to(path)
        rendered += 1
        if rendered % 10 == 0 or f == f_end - 1:
            per = (time.time() - t_begin) / rendered
            left = per * (f_end - 1 - f)
            print(f"[render] frame {f + 1}/{f_end}  {per:.2f}s/frame  ~{left / 60:.1f} min left", flush=True)

    events_path = os.path.join(out_dir, "events.json")
    log = dict(
        config=cfg, mode=mode, fps=tl.fps, width=width, height=height,
        duration=tl.duration, render_start=start_t, render_end=end_t,
        frames_dir=frames_dir, frame_count=f_end,
        events=tl.events(), frames=records,
    )

    if args.stills and not args.dry_run:
        stills_dir = os.path.join(out_dir, "stills")
        os.makedirs(stills_dir, exist_ok=True)
        stills = []
        for w in tl.landmark_windows:
            f = tl.folds[w["fold"] - 1]
            t = min(f.t_end + min(1.1, 0.5 * f.hold) + 0.5, tl.duration - 0.1)
            frame = int(round(t * tl.fps))
            t = frame / tl.fps
            rec = anim.apply(t)
            rec["frame"] = frame
            path = os.path.join(stills_dir, f"{w['fold']:02d}_{w['id']}.png")
            render_to(path)
            rec["path"] = path
            stills.append(rec)
            print(f"[stills] {w['id']} at {t:.1f}s")
        log["stills"] = stills

    with open(events_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1)
    print(f"[render] wrote {events_path}")

    if not args.frames_only:
        cmd = [sys.executable, os.path.join(HERE, "post.py"), "--events", events_path]
        if args.dry_run:
            cmd.append("--audio-only")
        print("[render] post-processing:", " ".join(cmd), flush=True)
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("[render] post-processing failed; rerun post.py once fixed", file=sys.stderr)
            sys.exit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
