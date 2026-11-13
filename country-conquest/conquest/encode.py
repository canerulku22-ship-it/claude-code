"""Parallel frame rendering piped straight into ffmpeg (H.264 + AAC MP4)."""
from __future__ import annotations

import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .timeline import Timeline

_worker = {}


def _init_worker(sea_km: float, timeline: Timeline, width: int, height: int, ss: int,
                 guides: bool) -> None:
    from .render.frame import FrameRenderer
    from .world import load_world
    _worker["r"] = FrameRenderer(load_world(sea_km), timeline, width, height, ss, guides)
    _worker["fps"] = timeline.fps


def _render_frame(i: int) -> bytes:
    return _worker["r"].render(i / _worker["fps"]).tobytes()


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH; install it (e.g. apt install ffmpeg / brew install ffmpeg)")


def encode(timeline: Timeline, out_path: Path, width: int, height: int, supersample: int,
           duration: float, audio: Path | None = None, crf: int = 18, preset: str = "medium",
           workers: int | None = None, guides: bool = False) -> None:
    check_ffmpeg()
    fps = timeline.fps
    n_frames = int(round(duration * fps))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-"]
    if audio is not None:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-r", str(fps), "-g", str(fps * 2), "-movflags", "+faststart"]
    if audio is not None:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest"]
    cmd.append(str(out_path))

    workers = workers or max(1, (os.cpu_count() or 2))
    ctx = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context("spawn")
    sea_km = timeline.cfg["sea_neighbour_km"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    try:
        with ctx.Pool(workers, _init_worker, (sea_km, timeline, width, height, supersample, guides)) as pool:
            for i, frame in enumerate(pool.imap(_render_frame, range(n_frames), chunksize=6)):
                proc.stdin.write(frame)
                if (i + 1) % fps == 0 or i + 1 == n_frames:
                    el = time.time() - t_start
                    print(f"\r  frame {i + 1}/{n_frames}  ({(i + 1) / el:.1f} fps)", end="", flush=True)
        print()
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {proc.returncode}")


def render_still(timeline: Timeline, t: float, out_path: Path, width: int, height: int, ss: int,
                 guides: bool = False) -> None:
    from .render.frame import FrameRenderer
    from .world import load_world
    r = FrameRenderer(load_world(timeline.cfg["sea_neighbour_km"]), timeline, width, height, ss, guides)
    r.render(t).save(out_path)
