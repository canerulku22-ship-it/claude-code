"""Blender provider: every shot is a procedural Blender scene rendered with Cycles.

blender/shots.py builds each shot (food models, studio, physics-style particles, 3D labels)
and blender/render_shot.py renders it frame by frame to PNGs. Frames are kept between runs,
so an interrupted render resumes where it stopped. Sound comes from renderer/audio.py.

Needs Blender: either the `bpy` Python module (pip install bpy, in a Python version that has
wheels) or the Blender app on PATH. Point BLENDER_PYTHON at a Python that can `import bpy`
if it isn't the one running generate.py. Quality knobs: BLENDER_SCALE (percent of 1080x1920,
default 75) and BLENDER_SAMPLES (default 12, denoised).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .base import Provider, ProviderConfigError, ProviderError

PROJECT = Path(__file__).resolve().parent.parent
BLENDER_DIR = PROJECT / "blender"
AUDIO = PROJECT / "renderer" / "audio.py"
FRAMES = PROJECT / "output" / "blender_frames"
FPS = 30


class BlenderProvider(Provider):
    name = "blender"
    ai_generated = False

    def __init__(self) -> None:
        self.scale = int(os.environ.get("BLENDER_SCALE", "75") or 75)
        self.samples = int(os.environ.get("BLENDER_SAMPLES", "12") or 12)
        py = os.environ.get("BLENDER_PYTHON", "").strip() or sys.executable
        if subprocess.run([py, "-c", "import bpy"], capture_output=True).returncode == 0:
            self.cmd = [py, str(BLENDER_DIR / "render_shot.py")]
        elif shutil.which("blender"):
            self.cmd = ["blender", "-b", "--python-exit-code", "1", "-P", str(BLENDER_DIR / "render_shot.py"), "--"]
        else:
            raise ProviderConfigError(
                "Blender was not found. Install Blender and put it on PATH, or `pip install bpy` and set BLENDER_PYTHON "
                "to that Python (see README)."
            )
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            raise ProviderConfigError("numpy is needed for the synthesized sound. Run: pip install -r requirements.txt") from exc
        self._shots: Optional[dict] = None

    @classmethod
    def describe(cls) -> str:
        return 'Blender Cycles render (no API, no key); each shot uses its "scene"; slow on CPU (about 20-40 s per frame)'

    def cache_key_extra(self) -> str:
        h = hashlib.sha256(f"{self.scale}/{self.samples}".encode())
        for path in sorted([*BLENDER_DIR.glob("*.py"), AUDIO]):
            h.update(path.name.encode())
            h.update(path.read_bytes())
        return h.hexdigest()[:12]

    def shots(self) -> dict:
        if self._shots is None:
            out = self._run([*self.cmd, "list", "0", str(FRAMES)], "listing Blender shots")
            self._shots = json.loads([l for l in out.splitlines() if l.startswith("{")][-1])
        return self._shots

    def generate_image(self, prompt: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            self._run([*self.cmd, "b_reveal", "2.8", tmp, "--scale", str(self.scale), "--samples", str(self.samples), "--only", "70"], "rendering the reference image")
            return (Path(tmp) / "frame_0070.png").read_bytes()

    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0, scene: Optional[str] = None) -> bytes:
        shots = self.shots()
        if not scene or scene not in shots:
            raise ProviderError(f'the blender provider needs a "scene" on every shot, one of: {", ".join(shots)}.')
        frames_dir = FRAMES / f"{scene}_{duration:g}s_{self.cache_key_extra()}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        total = max(1, round(duration * FPS))
        proc = subprocess.Popen([*self.cmd, scene, f"{duration}", str(frames_dir), "--scale", str(self.scale), "--samples", str(self.samples)],
                                cwd=BLENDER_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        tail = []
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line.startswith("FRAME"):
                parts = line.split()
                done = int(parts[2].split("/")[0])
                if done % 10 == 0 or done == total:
                    print(f"    blender: {scene} frame {parts[2]} ({parts[3]} each)", flush=True)
            elif line:
                tail = (tail + [line])[-15:]
        if proc.wait() != 0:
            raise ProviderError(f"Blender failed on {scene}:\n" + "\n".join(tail))
        missing = [i for i in range(total) if not (frames_dir / f"frame_{i:04d}.png").exists()]
        if missing:
            raise ProviderError(f"Blender left {len(missing)} frames of {scene} unrendered (first: {missing[0]}).")
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            video, sfx, out = t / "video.mp4", t / "sfx.wav", t / "clip.mp4"
            self._run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "frame_%04d.png"),
                       "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(video)], "encoding frames")
            self._run([sys.executable, str(AUDIO), "sfx", str(frames_dir / "events.json"), str(sfx)], "synthesizing sound effects")
            self._run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-i", str(sfx), "-map", "0:v:0", "-map", "1:a:0",
                       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], "adding sound")
            return out.read_bytes()

    def soundtrack(self, duration: float) -> Optional[bytes]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "music.wav"
            self._run([sys.executable, str(AUDIO), "music", f"{duration}", str(out)], "synthesizing the music bed")
            return out.read_bytes()

    @staticmethod
    def _run(cmd: list[str], what: str) -> str:
        proc = subprocess.run(cmd, cwd=BLENDER_DIR, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ProviderError(f"{what} failed:\n" + "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-12:]))
        return proc.stdout
