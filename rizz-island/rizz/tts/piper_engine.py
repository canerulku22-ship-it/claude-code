"""Piper (open-source, offline) text-to-speech.

Voices are downloaded on first use into voices/. To get word timings, the
pipeline makes a copy of each voice model with Piper's alignment output
switched on (voices/aligned/), which reports how many audio samples every
phoneme took. Phonemes are grouped into words at the spaces.

Voice settings used from cast.json:
  voice_id  e.g. "en_US-ryan-high" (browse: https://rhasspy.github.io/piper-samples/)
  speaker   speaker number for multi-speaker models (e.g. en_US-libritts_r-medium), else null
  speed     1.0 = normal, >1 faster (mapped to Piper's length_scale = 1/speed)
  pitch     semitones, applied afterwards with ffmpeg rubberband
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .. import config
from .base import TTSEngine, write_wav

_PUNCT = set(".,!?;:…¡¿—-\"'()ˈˌ")
SENTENCE_GAP = 0.14   # seconds of silence between sentences


class PiperEngine(TTSEngine):
    name = "piper"

    def __init__(self) -> None:
        self._voices: dict[str, object] = {}

    # -- model management ------------------------------------------------------
    def model_path(self, voice_id: str) -> Path:
        return config.VOICES_DIR / f"{voice_id}.onnx"

    def ensure_model(self, voice_id: str) -> Path:
        p = self.model_path(voice_id)
        if not p.exists():
            from piper.download_voices import download_voice

            print(f"    downloading Piper voice {voice_id}...")
            config.VOICES_DIR.mkdir(parents=True, exist_ok=True)
            download_voice(voice_id, config.VOICES_DIR)
        return p

    def aligned_model(self, voice_id: str) -> tuple[Path, Path, bool]:
        """(model, config, has_alignment). Patches a copy of the model once."""
        src = self.ensure_model(voice_id)
        cfg = src.with_suffix(".onnx.json")
        out = config.VOICES_DIR / "aligned" / src.name
        if out.exists():
            return out, cfg, True
        try:
            import onnx
            from piper.patch_voice_with_alignment import add_alignment_output

            out.parent.mkdir(parents=True, exist_ok=True)
            model = onnx.load(str(src))
            add_alignment_output(model)
            onnx.save(model, str(out))
            return out, cfg, True
        except Exception as e:  # noqa: BLE001 - alignment is a nice-to-have
            print(f"    (no word alignment for {voice_id}: {e}; timings will be estimated)")
            return src, cfg, False

    def _voice(self, voice_id: str):
        if voice_id not in self._voices:
            from piper import PiperVoice

            model, cfg, aligned = self.aligned_model(voice_id)
            self._voices[voice_id] = (PiperVoice.load(model, config_path=cfg, include_alignments=aligned), aligned)
        return self._voices[voice_id]

    def available(self, voice: dict) -> tuple[bool, str]:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False, "piper-tts is not installed (pip install piper-tts)"
        return True, ""

    # -- synthesis -------------------------------------------------------------
    def _synth(self, text: str, voice: dict, raw_wav: Path) -> list[tuple[float, float]] | None:
        from piper import SynthesisConfig

        pv, aligned = self._voice(voice["voice_id"])
        syn = SynthesisConfig(
            speaker_id=voice.get("speaker"),
            length_scale=1.0 / float(voice.get("speed", 1.0) or 1.0),
            noise_scale=float(voice.get("noise_scale", 0.72)),     # a bit livelier than default
            noise_w_scale=float(voice.get("noise_w_scale", 0.85)),
        )
        audio: list[np.ndarray] = []
        words: list[tuple[float, float]] = []
        rate = pv.config.sample_rate
        offset = 0
        for chunk in pv.synthesize(text, syn_config=syn, include_alignments=aligned):
            audio.append(chunk.audio_float_array)
            if aligned and chunk.phoneme_alignments:
                words += self._group_words(chunk.phoneme_alignments, offset, rate)
            offset += len(chunk.audio_float_array)
            gap = np.zeros(int(SENTENCE_GAP * rate), np.float32)
            audio.append(gap)
            offset += len(gap)
        write_wav(raw_wav, np.concatenate(audio) if audio else np.zeros(rate // 2, np.float32), rate)
        return words if aligned else None

    @staticmethod
    def _group_words(alignments, offset: int, rate: int) -> list[tuple[float, float]]:
        """Turn per-phoneme sample counts into (start, end) seconds per word."""
        out: list[tuple[float, float]] = []
        pos = offset
        start = None
        last_voiced_end = None
        for al in alignments:
            ph, n = al.phoneme, int(al.num_samples)
            if ph == " ":
                if start is not None:
                    out.append((start / rate, last_voiced_end / rate))
                    start = None
            elif ph not in ("^", "$", "_") and not all(ch in _PUNCT for ch in ph):
                if start is None:
                    start = pos
                last_voiced_end = pos + n
            pos += n
        if start is not None:
            out.append((start / rate, last_voiced_end / rate))
        return out
