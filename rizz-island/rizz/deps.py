"""Dependency check (and optional install) for the whole pipeline."""
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys

from . import config

# (import name, pip package, what it is for)
PY_DEPS = [
    ("PIL", "Pillow", "drawing and compositing frames"),
    ("numpy", "numpy", "image/audio maths"),
    ("scipy", "scipy", "alpha cleanup, audio filters"),
    ("anthropic", "anthropic", "Claude API script writer"),
    ("rembg", "rembg", "background removal for your AI art"),
    ("onnxruntime", "onnxruntime", "runs rembg + Piper models"),
    ("piper", "piper-tts", "open-source text-to-speech"),
    ("onnx", "onnx", "enables word timings from Piper voices"),
]
FFMPEG_FILTERS = ["rubberband", "loudnorm", "sidechaincompress", "acompressor"]


def check(install: bool = False) -> bool:
    ok = True
    print("Python packages:")
    missing = []
    for mod, pkg, why in PY_DEPS:
        try:
            m = importlib.import_module(mod)
            print(f"  ✓ {pkg:<12} {getattr(m, '__version__', ''):<10} {why}")
        except Exception:  # noqa: BLE001
            print(f"  ✗ {pkg:<12} {'MISSING':<10} {why}")
            missing.append(pkg)
    if missing and install:
        print(f"Installing: {' '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=False)
    elif missing:
        ok = False
        print(f"  -> pip install {' '.join(missing)}   (or run with --check --install)")

    print("Tools:")
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        print(f"  {'✓' if path else '✗'} {tool:<12} {path or 'MISSING (install ffmpeg)'}")
        ok &= bool(path)
    if shutil.which("ffmpeg"):
        filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        for f in FFMPEG_FILTERS:
            has = f" {f} " in filters
            print(f"  {'✓' if has else '✗'} ffmpeg filter {f}")
            ok &= has or f == "rubberband"   # rubberband is only needed for voice pitch

    print("Fonts:")
    for label, cands in (("display", config.FONT_CANDIDATES_BOLD), ("emoji", config.FONT_CANDIDATES_EMOJI)):
        f = config.find_font(cands)
        print(f"  {'✓' if f else '✗'} {label:<12} {f or 'not found (set RIZZ_FONT_BOLD / RIZZ_FONT_EMOJI)'}")

    print("Credentials:")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    print(f"  {'✓' if has_key else '!'} ANTHROPIC_API_KEY {'set' if has_key else 'not set (needed to write scripts)'}")
    el = bool(os.environ.get("ELEVENLABS_API_KEY"))
    print(f"  {'✓' if el else '-'} ELEVENLABS_API_KEY {'set' if el else 'not set (optional, paid voices)'}")
    return ok
