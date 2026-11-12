"""ffmpeg steps: loudness-normalise the audio, burn in the overlay, encode MP4."""

import json
import os
import re
import shutil
import subprocess

TARGET_LUFS = -14.0      # typical loudness for short-form social video
TRUE_PEAK = -1.5


def require_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found on PATH - see README.md for install steps")


def run(cmd, cwd=None):
    print("[ffmpeg]", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        raise SystemExit(f"ffmpeg failed ({result.returncode})")
    return result


def filter_path(path, cwd):
    """A path usable inside an ffmpeg filter argument (relative when possible)."""
    try:
        path = os.path.relpath(path, cwd)
    except ValueError:  # different drive on Windows
        pass
    path = path.replace("\\", "/")
    return "'" + path.replace("'", r"'\''").replace(":", r"\:") + "'"


def loudnorm(src, dst):
    """Two-pass EBU R128 normalisation to TARGET_LUFS."""
    target = f"I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11"
    probe = run(["ffmpeg", "-hide_banner", "-nostats", "-i", src,
                 "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", probe.stderr, re.S)
    if not m:
        shutil.copyfile(src, dst)
        return dst
    stats = json.loads(m.group(0))
    if stats["input_i"] in ("-inf", "inf"):
        shutil.copyfile(src, dst)
        return dst
    second = (f"loudnorm={target}:measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
              f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
              f":offset={stats['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-hide_banner", "-i", src, "-af", second, "-ar", "48000", dst])
    return dst


def encode(frames_dir, fps, ass_path, fonts_dir, audio_path, out_path, first_frame=0):
    """PNG frames + overlay + audio -> H.264/AAC MP4 (vertical, TikTok-ready)."""
    cwd = os.path.dirname(ass_path)
    vf = (f"ass={filter_path(ass_path, cwd)}:fontsdir={filter_path(fonts_dir, cwd)},"
          f"format=yuv420p")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-framerate", str(fps), "-start_number", str(first_frame),
           "-i", os.path.join(frames_dir, "%05d.png")]
    if audio_path:
        cmd += ["-i", audio_path]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "17",
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(fps), "-g", str(fps * 2)]
    if audio_path:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"]
    cmd += ["-movflags", "+faststart", out_path]
    run(cmd, cwd=cwd)
    return out_path


def overlay_still(png, t, ass_path, fonts_dir, out_png):
    """Burn the overlay as it looks at time t onto a single rendered still."""
    cwd = os.path.dirname(ass_path)
    # Microsecond timebase so the still lands exactly on its frame's time.
    vf = (f"settb=AVTB,setpts={t:.6f}/TB,ass={filter_path(ass_path, cwd)}:"
          f"fontsdir={filter_path(fonts_dir, cwd)}")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", png, "-vf", vf,
         "-frames:v", "1", out_png], cwd=cwd)
    return out_png


def contact_sheet(pngs, out_png, columns=4, width=1600):
    n = len(pngs)
    if not n:
        return None
    cols = min(columns, n)
    rows = (n + cols - 1) // cols
    inputs = []
    for p in pngs:
        inputs += ["-i", p]
    # xstack layout: each tile's offset as sums of the first tile's w/h.
    parts = []
    for i in range(n):
        c, r = i % cols, i // cols
        x = "+".join(["w0"] * c) or "0"
        y = "+".join(["h0"] * r) or "0"
        parts.append(f"{x}_{y}")
    fill = ":fill=black" if rows * cols > n else ""
    filt = (f"{''.join(f'[{i}]' for i in range(n))}xstack=inputs={n}:layout={'|'.join(parts)}{fill},"
            f"scale={width}:-2")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
         "-filter_complex", filt, "-frames:v", "1", out_png])
    return out_png
