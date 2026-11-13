"""ElevenLabs (paid, cloud) text-to-speech — drop-in replacement for Piper.

To switch a character over:
  1. export ELEVENLABS_API_KEY=...            (never commit the key)
  2. put the ElevenLabs voice id in cast.json -> voice.elevenlabs_voice_id
  3. either set voice.engine to "elevenlabs" for that character, or run with
     RIZZ_TTS=elevenlabs to use ElevenLabs for every character that has an id.

Uses the /with-timestamps endpoint, which returns per-character timings, so
captions stay perfectly in sync. Speed is passed to the API; pitch is still
applied afterwards with rubberband (set it to 0 if the voice is already right).

Optional voice settings: elevenlabs_model (default eleven_multilingual_v2),
stability, similarity_boost, style.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

import numpy as np

from .base import TTSEngine, write_wav

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=pcm_44100"


class ElevenLabsEngine(TTSEngine):
    name = "elevenlabs"

    def available(self, voice: dict) -> tuple[bool, str]:
        if not os.environ.get("ELEVENLABS_API_KEY"):
            return False, "ELEVENLABS_API_KEY is not set"
        if not voice.get("elevenlabs_voice_id"):
            return False, "no elevenlabs_voice_id in cast.json"
        return True, ""

    def _synth(self, text: str, voice: dict, raw_wav: Path) -> list[tuple[float, float]] | None:
        body = {
            "text": text,
            "model_id": voice.get("elevenlabs_model", "eleven_multilingual_v2"),
            "voice_settings": {
                "stability": voice.get("stability", 0.35),
                "similarity_boost": voice.get("similarity_boost", 0.8),
                "style": voice.get("style", 0.6),
                "use_speaker_boost": True,
                "speed": max(0.7, min(1.2, float(voice.get("speed", 1.0)))),
            },
        }
        req = urllib.request.Request(
            API.format(voice=voice["elevenlabs_voice_id"]), data=json.dumps(body).encode(),
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        pcm = np.frombuffer(base64.b64decode(data["audio_base64"]), dtype=np.int16).astype(np.float32) / 32768
        write_wav(raw_wav, pcm, 44100)

        al = data.get("alignment") or data.get("normalized_alignment")
        if not al:
            return None
        words, start, end = [], None, None
        for ch, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
            if ch.isspace():
                if start is not None:
                    words.append((start, end))
                start = None
            else:
                start = s if start is None else start
                end = e
        if start is not None:
            words.append((start, end))
        return words
