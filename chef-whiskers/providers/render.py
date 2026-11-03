"""Local 3D render provider: Chef Whiskers as a Three.js scene, rendered frame by frame.

The same method as a programmatic animation: renderer/main.js builds the cat, the kitchen and the
food in 3D, renderer/render.js renders each frame in headless Chromium and pipes it into ffmpeg,
and renderer/audio.py synthesizes the sound. No API, no key, no cost, and the character is
identical in every shot because it is the same 3D model.

Prompts are not used: each recipe shot names a pre-built animated scene in its "scene" field.

Needs Node.js 18+, `npm install` and `npx playwright install chromium` in renderer/, and numpy.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .base import Provider, ProviderConfigError, ProviderError

RENDERER = Path(__file__).resolve().parent.parent / "renderer"
FPS = 30
SETUP_HINT = "cd renderer && npm install && npx playwright install chromium"


class RenderProvider(Provider):
    name = "render"
    ai_generated = False  # a scripted 3D animation, not generative AI

    def __init__(self) -> None:
        if shutil.which("node") is None:
            raise ProviderConfigError("Node.js was not found. Install Node.js 18 or newer, then run: " + SETUP_HINT)
        if not (RENDERER / "node_modules" / "three").is_dir():
            raise ProviderConfigError("The 3D renderer is not installed yet. Run: " + SETUP_HINT)
        check = subprocess.run(["node", "-e", "require.resolve('playwright')"], cwd=RENDERER, capture_output=True, text=True)
        if check.returncode != 0:
            raise ProviderConfigError("Playwright is missing for the 3D renderer. Run: " + SETUP_HINT)
        try:
            import numpy  # noqa: F401  (used by renderer/audio.py)
        except ImportError as exc:
            raise ProviderConfigError("numpy is needed for the synthesized sound. Run: pip install -r requirements.txt") from exc
        self.workers = max(1, int(os.environ.get("RENDER_WORKERS", "1") or 1))
        self._scenes: Optional[list[str]] = None

    @classmethod
    def describe(cls) -> str:
        return 'local 3D render (no API, no key, no cost); each shot uses its "scene", prompts are not sent anywhere'

    def cache_key_extra(self) -> str:
        """Re-render cached clips whenever the scenes or the sound change."""
        h = hashlib.sha256()
        for path in sorted([*RENDERER.glob("*.js"), RENDERER / "index.html", RENDERER / "audio.py"]):
            h.update(path.name.encode()); h.update(path.read_bytes())
        return h.hexdigest()[:12]

    # ------------------------------------------------------------ provider interface

    def generate_image(self, prompt: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ref.png"
            self._node(["still", "ref", "0", "3", str(out)], "rendering the character reference")
            return out.read_bytes()

    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0, scene: Optional[str] = None) -> bytes:
        scenes = self.scenes()
        if not scene:
            raise ProviderError(f'the render provider needs a "scene" on every shot. Available scenes: {", ".join(scenes)}.')
        if scene not in scenes:
            raise ProviderError(f'unknown scene "{scene}". Available scenes: {", ".join(scenes)}.')
        frames = max(1, round(duration * FPS))
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            parts = self._render_frames(scene, duration, frames, tmp_path)
            video = tmp_path / "video.mp4"
            if len(parts) == 1:
                parts[0].replace(video)
            else:
                listing = tmp_path / "parts.txt"
                listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
                self._ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(video)], "joining render chunks")
            events, sfx, out = tmp_path / "events.json", tmp_path / "sfx.wav", tmp_path / "clip.mp4"
            self._node(["events", scene, f"{duration}", str(events)], "exporting sound cues")
            self._run([sys.executable, str(RENDERER / "audio.py"), "sfx", str(events), str(sfx)], "synthesizing sound effects")
            self._ffmpeg(["-i", str(video), "-i", str(sfx), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                          "-shortest", "-movflags", "+faststart", str(out)], "adding sound to the clip")
            return out.read_bytes()

    def soundtrack(self, duration: float) -> Optional[bytes]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "music.wav"
            self._run([sys.executable, str(RENDERER / "audio.py"), "music", f"{duration}", str(out)], "synthesizing the music bed")
            return out.read_bytes()

    # ------------------------------------------------------------ helpers

    def scenes(self) -> list[str]:
        if self._scenes is None:
            out = self._node(["scenes"], "listing scenes")
            self._scenes = json.loads(out.strip().splitlines()[-1])
        return self._scenes

    def _render_frames(self, scene: str, duration: float, frames: int, tmp: Path) -> list[Path]:
        """Render [0, frames) in `workers` parallel chunks; show progress as it goes."""
        n = min(self.workers, frames)
        bounds = [round(frames * k / n) for k in range(n + 1)]
        parts = [tmp / f"part{k}.mp4" for k in range(n)]
        procs = [subprocess.Popen(["node", "render.js", "clip", scene, f"{duration}", str(FPS), str(bounds[k]), str(bounds[k + 1]), str(parts[k])],
                                  cwd=RENDERER, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True) for k in range(n)]
        errors = []
        for proc in procs:
            tail = []
            assert proc.stderr is not None
            for line in proc.stderr:
                line = line.rstrip()
                if " frame " in line and n == 1:
                    print(f"    render: {line.strip()}", flush=True)
                elif line and not line.startswith("[page]"):
                    tail.append(line)
            if proc.wait() != 0:
                errors.append("\n".join(tail[-12:]))
        if errors:
            raise ProviderError(f"rendering scene {scene} failed:\n{errors[0]}")
        print(f"    render: {scene} done ({frames} frames)", flush=True)
        return parts

    def _node(self, args: list[str], what: str) -> str:
        return self._run(["node", "render.js", *args], what)

    def _ffmpeg(self, args: list[str], what: str) -> None:
        self._run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], what)

    @staticmethod
    def _run(cmd: list[str], what: str) -> str:
        proc = subprocess.run(cmd, cwd=RENDERER, capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join([l for l in proc.stderr.strip().splitlines() if not l.startswith("[page]")][-12:])
            raise ProviderError(f"{what} failed:\n{tail}")
        return proc.stdout


# Rough cost, for the README and dry run: about 4 s per frame with software WebGL on 4 CPU cores.
SECONDS_PER_FRAME = 4.0


def estimate_minutes(total_seconds: float) -> int:
    return max(1, math.ceil(total_seconds * FPS * SECONDS_PER_FRAME / 60))
