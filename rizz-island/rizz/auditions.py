"""Voice auditions: the narrator introduces each character, who says their catchphrase.

Produces one MP3 so you can judge every voice (engine, pitch, speed) in one
listen before approving the cast.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from . import config
from .cast import Cast
from .tts import speak
from .tts.base import SAMPLE_RATE, read_wav, write_wav


def make_auditions(cast: Cast, out: Path, only: list[str] | None = None) -> Path:
    gap = np.zeros(int(0.35 * SAMPLE_RATE), np.float32)
    pieces: list[np.ndarray] = []

    def add(text: str, voice: dict) -> None:
        u = speak(text, voice)
        data, _ = read_wav(u.wav)
        pieces.extend([data / max(1e-3, np.abs(data).max()) * 0.9, gap])

    add(f"Welcome to {cast.show.get('title', 'Rizz Island')}. Meet the singles.", cast.narrator_voice)
    for c in cast.characters.values():
        if only and c.id not in only:
            continue
        add(f"{c.name}. {c.raw.get('role', '')}.", cast.narrator_voice)
        add(c.raw["catchphrase"], c.voice)
        pieces.append(gap)

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".wav")
    write_wav(tmp, np.concatenate(pieces), SAMPLE_RATE)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-b:a", "160k", str(out)], check=True)
    tmp.unlink()
    return out
