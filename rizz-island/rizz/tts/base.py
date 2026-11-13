"""Shared TTS types and helpers.

Every engine turns (text, voice settings) into an `Utterance`: a 44.1 kHz mono
WAV plus per-word start/end times, which drive the word-by-word captions and
the talking animation. Engines only have to produce raw audio and, if they
can, word timings; pitch shifting, caching and timing fallbacks live here.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .. import config

TTS_CACHE = config.BUILD_DIR / "tts"
SAMPLE_RATE = 44100
CACHE_VERSION = "2"


@dataclass
class Word:
    text: str          # the word as it appears in the caption (may contain emoji/CAPS)
    start: float       # seconds from the start of the utterance
    end: float


@dataclass
class Utterance:
    wav: Path
    duration: float
    words: list[Word] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"wav": str(self.wav), "duration": self.duration,
                "words": [[w.text, round(w.start, 3), round(w.end, 3)] for w in self.words]}

    @staticmethod
    def from_json(d: dict) -> "Utterance":
        return Utterance(Path(d["wav"]), d["duration"], [Word(*w) for w in d["words"]])


# --------------------------------------------------------------------------
# Text preparation
# --------------------------------------------------------------------------
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍\U0001F1E6-\U0001F1FF]+")


def split_caption_words(text: str) -> list[str]:
    """Words as shown on screen. Pure-emoji tokens are glued onto the previous word."""
    out: list[str] = []
    for tok in text.split():
        if not _EMOJI_RE.sub("", tok).strip() and out:
            out[-1] = f"{out[-1]} {tok}"
        else:
            out.append(tok)
    return out


def speakable(word: str) -> str:
    """What the TTS engine should read for one caption word.

    Emoji are dropped, and SHOUTED words are lower-cased so engines don't
    spell them out letter by letter (the caption keeps the caps).
    """
    w = _EMOJI_RE.sub("", word).strip()
    # Engines tend to swallow "..." and merge words; a comma gives the same pause.
    w = re.sub(r"(\.\.\.|…)+", ",", w)
    if w in (",", ""):
        return ""
    core = re.sub(r"[^A-Za-z]", "", w)
    if len(core) > 3 and core.isupper():
        w = w.lower()
    return w


def speakable_text(caption_words: list[str]) -> str:
    return " ".join(s for s in (speakable(w) for w in caption_words) if s)


# --------------------------------------------------------------------------
# Audio helpers
# --------------------------------------------------------------------------
def write_wav(path: Path, samples: np.ndarray, rate: int) -> None:
    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        rate, n, ch, sw = wf.getframerate(), wf.getnframes(), wf.getnchannels(), wf.getsampwidth()
        raw = wf.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float32)
    data /= 32768.0 if sw == 2 else 2147483648.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, rate


def postprocess(raw_wav: Path, out_wav: Path, pitch_semitones: float) -> None:
    """Pitch-shift (tempo unchanged, so word timings stay valid) and resample to 44.1 kHz.

    Formants shift with the pitch on purpose: it makes small characters sound
    squeakier and big ones boomier, which suits cartoon creatures.
    """
    filters = []
    if abs(pitch_semitones) > 0.01:
        filters.append(f"rubberband=pitch={2 ** (pitch_semitones / 12):.5f}:formant=shifted")
    filters += [f"aresample={SAMPLE_RATE}", "highpass=f=70"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_wav), "-af", ",".join(filters),
                    "-ac", "1", "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16", str(out_wav)], check=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def proportional_words(caption_words: list[str], samples: np.ndarray, rate: int) -> list[Word]:
    """Fallback timing: spread words over the voiced part of the clip by length."""
    if not caption_words:
        return []
    env = np.abs(samples)
    thr = max(1e-4, env.max() * 0.06)
    voiced = np.nonzero(env > thr)[0]
    t0 = voiced[0] / rate if len(voiced) else 0.0
    t1 = voiced[-1] / rate if len(voiced) else len(samples) / rate
    weights = [max(1, len(re.sub(r"\W", "", speakable(w)))) + 1.5 for w in caption_words]
    total = sum(weights)
    out, t = [], t0
    for w, k in zip(caption_words, weights):
        d = (t1 - t0) * k / total
        out.append(Word(w, float(t), float(t + d)))
        t += d
    return out


def cache_key(engine: str, voice: dict, text: str) -> str:
    blob = json.dumps({"e": engine, "v": voice, "t": text, "cv": CACHE_VERSION}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# Engine interface
# --------------------------------------------------------------------------
class TTSEngine(ABC):
    """Implement `_synth` to add a new voice provider."""

    name = "base"

    @abstractmethod
    def _synth(self, text: str, voice: dict, raw_wav: Path) -> list[tuple[float, float]] | None:
        """Write raw speech for `text` to raw_wav (any sample rate, mono).

        Return one (start, end) pair per space-separated word of `text` if the
        engine knows them, else None (timings are then estimated).
        """

    def available(self, voice: dict) -> tuple[bool, str]:
        """(ok, reason) — can this engine speak with these voice settings right now?"""
        return True, ""

    def synthesize(self, text: str, voice: dict) -> Utterance:
        """Speak `text` (caption text, may contain emoji/CAPS) with cached results."""
        TTS_CACHE.mkdir(parents=True, exist_ok=True)
        key = cache_key(self.name, voice, text)
        meta = TTS_CACHE / f"{key}.json"
        if meta.exists():
            u = Utterance.from_json(json.loads(meta.read_text()))
            if u.wav.exists():
                return u

        cap_words = split_caption_words(text)
        # Keep a 1:1 list of caption words that actually produce speech.
        spoken = [(w, speakable(w)) for w in cap_words]
        spoken = [(w, s) for w, s in spoken if s]
        say = " ".join(s for _, s in spoken) or "..."
        raw = TTS_CACHE / f"{key}.raw.wav"
        out = TTS_CACHE / f"{key}.wav"
        timings = self._synth(say, voice, raw)
        postprocess(raw, out, float(voice.get("pitch", 0)))
        raw.unlink(missing_ok=True)

        samples, rate = read_wav(out)
        if timings and len(timings) == len(spoken):
            words = [Word(w, s, e) for (w, _), (s, e) in zip(spoken, timings)]
        else:
            words = proportional_words([w for w, _ in spoken], samples, rate)
        u = Utterance(out, len(samples) / rate, words)
        meta.write_text(json.dumps(u.to_json()))
        return u
