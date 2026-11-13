"""Text-to-speech front door.

    from rizz.tts import speak
    utt = speak("Freshly baked and emotionally available!", character.voice)

Engine choice per line:
  * RIZZ_TTS=elevenlabs (env) -> ElevenLabs for any voice with an elevenlabs_voice_id
  * otherwise voice["engine"] from cast.json ("piper" or "elevenlabs")
  * if the chosen engine can't run (no key, no voice id), fall back to Piper.

To add another provider, subclass TTSEngine (see base.py), implement _synth,
and register it in ENGINES.
"""
from __future__ import annotations

import os

from .base import TTSEngine, Utterance, Word  # noqa: F401
from .elevenlabs_engine import ElevenLabsEngine
from .piper_engine import PiperEngine

ENGINES: dict[str, type[TTSEngine]] = {"piper": PiperEngine, "elevenlabs": ElevenLabsEngine}
_instances: dict[str, TTSEngine] = {}
_warned: set[str] = set()


def engine(name: str) -> TTSEngine:
    if name not in _instances:
        _instances[name] = ENGINES[name]()
    return _instances[name]


def pick_engine(voice: dict) -> TTSEngine:
    wanted = os.environ.get("RIZZ_TTS") or voice.get("engine", "piper")
    if wanted not in ENGINES:
        wanted = "piper"
    eng = engine(wanted)
    ok, why = eng.available(voice)
    if not ok:
        if wanted not in _warned:
            print(f"  ! TTS engine '{wanted}' unavailable ({why}); using piper")
            _warned.add(wanted)
        eng = engine("piper")
    return eng


def speak(text: str, voice: dict) -> Utterance:
    return pick_engine(voice).synthesize(text, voice)
