"""Make one episode end to end: 3D render -> soundtrack -> overlay + encode.

    python make_episode.py episodes/bowling_balls_glass_table.json --preview
    python make_episode.py episodes/bowling_balls_glass_table.json
    python make_episode.py --check

Output: out/<slug>/<slug>.mp4 (or out/<slug>_preview/<slug>_preview.mp4).
Re-running resumes an interrupted render; --fresh starts the frames over.
"""

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from hmtb import FULL_RES, PREVIEW_RES, tools  # noqa: E402
from hmtb.config import load_config  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("config", nargs="?", help="episode JSON file")
    p.add_argument("--preview", action="store_true", help="540x960, low samples, first 10 seconds")
    p.add_argument("--check", action="store_true", help="check Blender/ffmpeg/Python packages and exit")
    p.add_argument("--blender", help="path to blender (or a python with bpy)")
    p.add_argument("--samples", type=int, help="override Eevee samples")
    p.add_argument("--scale", type=float, default=1.0,
                   help="render 3D at this fraction of the output size, upscaled when encoding (e.g. 0.67)")
    p.add_argument("--fresh", action="store_true", help="re-render all frames")
    p.add_argument("--skip-render", action="store_true", help="reuse existing frames and events.json")
    p.add_argument("--crf", type=int, default=18, help="x264 quality (lower = better, bigger)")
    p.add_argument("--chunk", type=int, default=0,
                   help="render N frames per Blender process (e.g. 60 on CPU-only machines, where "
                        "software GPU drivers can crash after ~80 renders)")
    return p.parse_args(argv)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def run_render(cmd, frames_dir, max_retries=100):
    """Run the Blender render, resuming automatically if it crashes part-way.

    Software (CPU-only) GPU drivers can crash Blender during long renders. Frames already
    on disk are kept, so a retry continues where it stopped. It gives up only when a
    retry makes no progress at all.
    """
    def count():
        return len(os.listdir(frames_dir)) if os.path.isdir(frames_dir) else 0

    stalled = 0
    for attempt in range(max_retries + 1):
        before = count()
        rc = subprocess.run(cmd).returncode
        if rc == 0:
            return
        stalled = stalled + 1 if count() == before else 0
        if stalled >= 2:
            raise SystemExit("Render failed twice in a row without progress (exit %d)." % rc)
        print("Render exited with %d after %d frames; resuming (retry %d)..." % (rc, count(), attempt + 1),
              flush=True)
        cmd = [c for c in cmd if c != "--fresh"]
    raise SystemExit("Render kept failing; giving up.")


def chunk_ranges(total, chunk):
    if not chunk:
        return [None]
    return ["%d:%d" % (a, min(total, a + chunk)) for a in range(0, total, chunk)]


def make_episode(config_path, preview=False, blender=None, samples=None, scale=1.0, fresh=False,
                 skip_render=False, crf=18, chunk=0):
    from hmtb.audio import build_soundtrack
    from hmtb.encode import encode

    with open(config_path) as fh:
        raw = json.load(fh)
    fill_mode = raw.get("mode") == "fill"
    kaiju_mode = raw.get("mode") == "kaiju"
    if fill_mode:
        from hmtb.fill import resolve_fill
        cfg = resolve_fill(raw, config_path)
    elif kaiju_mode:
        from hmtb.kaiju import resolve_kaiju
        cfg = resolve_kaiju(raw, config_path)
    else:
        cfg = load_config(config_path)
    slug = cfg["slug"] + ("_preview" if preview else "")
    out_dir = os.path.join(HERE, "out", slug)
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()

    # 1. 3D frames + events log (Blender)
    if not skip_render:
        found = tools.find_blender(blender)
        if not found:
            tools.check(blender)
            raise SystemExit("Blender not found.")
        args = ["--config", os.path.abspath(config_path), "--out", out_dir, "--scale", str(scale)]
        if preview:
            args.append("--preview")
        if samples:
            args += ["--samples", str(samples)]
        if fresh:
            args.append("--fresh")
        from hmtb.timeline import build_timeline
        from hmtb import FPS, PREVIEW_SECONDS
        if preview:
            total = int(PREVIEW_SECONDS * FPS)
        elif fill_mode or kaiju_mode:
            total = int(round(cfg["duration_s"] * FPS))
        else:
            total = build_timeline(cfg).total_frames
        for i, rng_ in enumerate(chunk_ranges(total, chunk)):
            chunk_args = args + (["--frames", rng_] if rng_ else [])
            if i > 0 and "--fresh" in chunk_args:
                chunk_args.remove("--fresh")
            cmd = tools.blender_command(found, os.path.join(HERE, "render.py"), chunk_args)
            print("[1/3] Rendering 3D%s: %s" % (" (frames %s)" % rng_ if rng_ else "", " ".join(cmd)), flush=True)
            run_render(cmd, os.path.join(out_dir, "frames"))

    with open(os.path.join(out_dir, "events.json")) as fh:
        events = json.load(fh)

    # 2. Soundtrack
    audio = os.path.join(out_dir, "audio.wav")
    print("[2/3] Building soundtrack ->", audio, flush=True)
    if fill_mode:
        from hmtb.audio import build_fill_soundtrack
        build_fill_soundtrack(events, audio, seed=cfg["seed"])
    elif kaiju_mode:
        # Voiceover first: its line lengths time the captions in the overlay.
        from hmtb import voice
        from hmtb.audio_kaiju import build_kaiju_soundtrack
        lines = voice.render_lines(cfg, os.path.join(out_dir, "vo"))
        events["vo_durations"] = [round(d, 3) for d in voice.durations(lines)]
        for line, d in zip(cfg["voiceover"], events["vo_durations"]):
            print("  VO %5.2fs-%5.2fs  %s" % (line["at_s"], line["at_s"] + d, line["text"]), flush=True)
        with open(os.path.join(out_dir, "events.json"), "w") as fh:
            json.dump(events, fh, indent=1)
        build_kaiju_soundtrack(events, lines, audio, seed=cfg["seed"])
    else:
        build_soundtrack(events, audio, seed=cfg["seed"])

    # 3. Overlay + encode
    width, height = PREVIEW_RES if preview else FULL_RES
    first, end = events["render"]["frames"]
    mp4 = os.path.join(out_dir, slug + ".mp4")
    print("[3/3] Overlay + encode ->", mp4, flush=True)
    encode(out_dir, mp4, audio, width, height, frame_range=(first, end), crf=crf)

    info = probe(mp4)
    v = next(s for s in info["streams"] if s["codec_name"] == "h264")
    a = next((s for s in info["streams"] if s["codec_name"] == "aac"), None)
    print("\nDone in %.1f min: %s" % ((time.time() - t0) / 60, mp4))
    print("  %sx%s %s fps, H.264 + %s, %.2fs" % (v["width"], v["height"], v["r_frame_rate"],
                                                 "AAC" if a else "NO AUDIO", float(info["format"]["duration"])))
    return mp4


def main():
    args = parse_args()
    if args.check:
        sys.exit(0 if tools.check(args.blender) else 1)
    if not args.config:
        raise SystemExit("Give an episode config, e.g. episodes/bowling_balls_glass_table.json (or --check)")
    need_blender = not args.skip_render
    if not tools.check(args.blender, verbose=False, need_blender=need_blender):
        tools.check(args.blender, need_blender=need_blender)
        raise SystemExit(1)
    make_episode(args.config, preview=args.preview, blender=args.blender, samples=args.samples,
                 scale=args.scale, fresh=args.fresh, skip_render=args.skip_render, crf=args.crf,
                 chunk=args.chunk)


if __name__ == "__main__":
    main()
