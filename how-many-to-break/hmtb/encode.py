"""Final assembly with ffmpeg: 3D frames + overlay + soundtrack -> H.264/AAC MP4.

The overlay frames never touch the disk: Python renders them and pipes raw RGBA into
ffmpeg, which scales the 3D frames to the output size, lays the overlay on top and
encodes. Unchanged overlay frames are re-sent from a cache, so this is fast.
"""

import json
import os
import shutil
import subprocess
import sys
import time

from .overlay import Overlay


def find_ffmpeg():
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg not found on PATH. See README.md -> Setup.")
    return path


def encode(episode_dir, out_path, audio_path, width, height, frame_range=None, crf=18, preset="medium"):
    """Composite and encode. ``frame_range`` = (first, end_exclusive) video frames."""
    with open(os.path.join(episode_dir, "events.json")) as fh:
        events = json.load(fh)
    fps = events["fps"]
    first, end = frame_range or (0, events["total_frames"])
    n = end - first
    frames_pattern = os.path.join(episode_dir, "frames", "%05d.png")
    missing = [f for f in range(first, end) if not os.path.exists(frames_pattern % f)]
    if missing:
        raise RuntimeError("%d frames are missing (first: %d). Render them first." % (len(missing), missing[0]))

    if events.get("mode") == "fill":
        from .overlay_fill import FillOverlay
        overlay = FillOverlay(events, width, height)
    else:
        overlay = Overlay(events, width, height)
    cmd = [
        find_ffmpeg(), "-y", "-v", "error", "-stats",
        "-framerate", str(fps), "-start_number", str(first), "-i", frames_pattern,
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", "%dx%d" % (width, height), "-framerate", str(fps), "-i", "-",
        "-ss", "%.4f" % (first / float(fps)), "-i", audio_path,
        "-filter_complex",
        "[0:v]scale=%d:%d:flags=lanczos,setsar=1,format=rgba[bg];"
        "[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v]" % (width, height),
        "-map", "[v]", "-map", "2:a",
        "-frames:v", str(n), "-r", str(fps),
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", "%.4f" % (n / float(fps)),
        "-movflags", "+faststart",
        out_path,
    ]
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(first, end):
            proc.stdin.write(overlay.frame_bytes(f))
        proc.stdin.close()
    except BrokenPipeError:
        pass
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed (exit %d)" % proc.returncode)
    sys.stderr.write("\nEncoded %s (%d frames) in %.1fs\n" % (out_path, n, time.time() - t0))
    return out_path
