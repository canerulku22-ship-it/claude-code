"""Post-processing: overlay + sound effects + final MP4, from an events log.

Run automatically at the end of render_episode.py, or by hand to redo the
text or audio without re-rendering any frames:

    python post.py --events output/paper/full/events.json

Needs Python 3.9+ with numpy (Blender's own Python has it) and ffmpeg.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from foldlib import FONTS_DIR, SFX_DIR  # noqa: E402
from foldlib import compose  # noqa: E402
from foldlib.overlay import write_overlay  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--events", required=True, help="events.json written by render_episode.py")
    p.add_argument("--no-audio", action="store_true", help="encode without sound")
    p.add_argument("--audio-only", action="store_true", help="only build the soundtrack")
    args = p.parse_args()

    compose.require_ffmpeg()
    with open(args.events, encoding="utf-8") as f:
        log = json.load(f)
    mode_dir = os.path.dirname(os.path.abspath(args.events))
    episode_dir = os.path.dirname(mode_dir)
    cfg = log["config"]
    slug = cfg["slug"]

    ass_path = write_overlay(log, os.path.join(mode_dir, "overlay.ass"))
    print(f"[post] overlay -> {ass_path}")

    audio = None
    if not args.no_audio:
        from foldlib.audio import build_soundtrack
        sfx_dirs = [SFX_DIR]
        if cfg.get("sfx_dir"):
            sfx_dirs.insert(0, os.path.join(os.path.dirname(cfg["config_path"]), cfg["sfx_dir"]))
        raw = build_soundtrack(log, os.path.join(mode_dir, "audio_raw.wav"), sfx_dirs)
        audio = compose.loudnorm(raw, os.path.join(mode_dir, "audio.wav"))
        print(f"[post] audio -> {audio}")

    if args.audio_only:
        return

    suffix = "" if log["mode"] == "full" else "_" + log["mode"]
    out = os.path.join(episode_dir, f"{slug}{suffix}.mp4")
    compose.encode(log["frames_dir"], log["fps"], ass_path, FONTS_DIR, audio, out)
    print(f"[post] video -> {out}")

    if log.get("stills"):
        stills_log = dict(log, frames=log["frames"] + log["stills"], render_end=log["duration"])
        stills_ass = write_overlay(stills_log, os.path.join(mode_dir, "overlay_stills.ass"))
        shots = []
        for s in log["stills"]:
            dst = s["path"].replace(".png", "_overlay.png")
            compose.overlay_still(s["path"], s["t"], stills_ass, FONTS_DIR, dst)
            shots.append(dst)
        sheet = compose.contact_sheet(shots, os.path.join(episode_dir, f"{slug}{suffix}_beats.png"))
        print(f"[post] landmark stills -> {sheet}")


if __name__ == "__main__":
    main()
