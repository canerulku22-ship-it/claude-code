"""Voiceover with Piper, a free offline text-to-speech engine (https://github.com/rhasspy/piper).

Setup (once):
    python -m venv tts-venv && tts-venv/bin/pip install piper-tts
    # voices: https://huggingface.co/rhasspy/piper-voices (e.g. en_GB-alan-medium.onnx + .onnx.json)
    export PIPER_BIN=tts-venv/bin/piper PIPER_VOICES=/path/to/voices

Each line is rendered to WAV, then given a trailer treatment with ffmpeg: pitched down
a little, compressed, EQ'd, and returned as 48 kHz mono float samples.

To use your own recorded voiceover instead, drop vo_01.wav, vo_02.wav, ... into sfx/
and they're used as-is.
"""

import os
import shutil
import subprocess

import numpy as np

from . import PROJECT_DIR

SR = 48000


def _piper_bin():
    for cand in (os.environ.get("PIPER_BIN"), shutil.which("piper"), "/opt/tts-venv/bin/piper"):
        if cand and os.path.exists(cand):
            return cand
    raise RuntimeError("Piper TTS not found. See hmtb/voice.py for setup (or set PIPER_BIN).")


def _voice_path(voice):
    for d in (os.environ.get("PIPER_VOICES"), "/opt/piper-voices", os.path.join(PROJECT_DIR, "voices")):
        if d and os.path.exists(os.path.join(d, voice + ".onnx")):
            return os.path.join(d, voice + ".onnx")
    raise RuntimeError("Voice %r not found. Download it from huggingface.co/rhasspy/piper-voices." % voice)


def _decode(path, filters=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if filters:
        cmd += ["-af", filters]
    cmd += ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


TRAILER_FX = ("asetrate=22050*0.92,aresample=48000,atempo=1/0.92,"
              "highpass=f=70,equalizer=f=140:t=q:w=1.2:g=3,equalizer=f=3200:t=q:w=1.5:g=2,"
              "acompressor=threshold=-20dB:ratio=4:attack=5:release=120:makeup=4")


def render_lines(cfg, work_dir):
    """Render every voiceover line. Returns a list of float arrays (48 kHz mono)."""
    os.makedirs(work_dir, exist_ok=True)
    lines = []
    for i, line in enumerate(cfg["voiceover"], 1):
        custom = os.path.join(PROJECT_DIR, "sfx", "vo_%02d.wav" % i)
        if os.path.exists(custom):
            lines.append(_decode(custom))
            continue
        raw = os.path.join(work_dir, "vo_%02d_raw.wav" % i)
        subprocess.run([_piper_bin(), "--model", _voice_path(cfg["voice"]), "--length_scale",
                        str(cfg.get("voice_speed", 1.0)), "--sentence_silence", "0.25", "--output_file", raw],
                       input=line["text"].encode(), check=True, capture_output=True)
        lines.append(_decode(raw, TRAILER_FX))
    return lines


def durations(lines):
    return [len(x) / float(SR) for x in lines]
