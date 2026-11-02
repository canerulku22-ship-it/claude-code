"""Offline test provider: makes test-pattern media with ffmpeg instead of calling an AI API.

Use it to check the edit (crop and scale, on-screen text, concat, soundtrack) for
free before spending credits. Its output goes to output/test/ and is never meant
for posting.
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

from .base import Provider, ProviderError


class PlaceholderProvider(Provider):
    name = "placeholder"
    is_test_provider = True

    def generate_image(self, prompt: str) -> bytes:
        return _render(["-f", "lavfi", "-i", "color=c=0xE8955A:s=1080x1920", "-frames:v", "1"], ".png")

    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0) -> bytes:
        # Mimic a typical video API: fixed 5 s or 10 s clips, at a size that is close to
        # but not exactly 9:16, so the trim, crop and scale steps all get exercised.
        seconds = 5 if duration <= 5 else 10
        hue = int(hashlib.sha256(prompt.encode()).hexdigest()[:4], 16) % 360
        return _render(
            [
                "-f", "lavfi", "-i", f"testsrc2=s=768x1344:r=24:d={seconds}",
                "-f", "lavfi", "-i", f"sine=f=220:d={seconds}",
                "-vf", f"hue=h={hue}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            ],
            ".mp4",
        )


def _render(args: list[str], suffix: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"out{suffix}"
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, str(out)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise ProviderError(f"placeholder render failed: {proc.stderr.strip()}")
        return out.read_bytes()
