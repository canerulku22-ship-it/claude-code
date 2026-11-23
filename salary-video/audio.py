"""Voiceover (text-to-speech) and synthesised sound effects. Audio is 48 kHz mono float32.

Voice engines, chosen by the config's "voice": {"engine": ...}:
  flite   ffmpeg's built-in speech synthesiser (works anywhere ffmpeg does, robotic)
  kokoro  Kokoro-82M neural voice; needs `pip install kokoro-onnx` and the model files
          (kokoro-v1.0.onnx, voices-v1.0.bin) in models/ or at "model"/"voices" in the config
Clips are cached in .cache/vo/ by engine, settings and text.
"""
import hashlib, json, os, subprocess, wave
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
VO_CACHE = os.path.join(HERE, ".cache", "vo")
_rng = np.random.default_rng(7)


def read_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    return x


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def _to_48k(src, dst, speed=1.0):
    af = ["-af", f"atempo={speed}"] if abs(speed - 1) > 1e-3 else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, *af, "-ar", str(SR), "-ac", "1",
                    "-c:a", "pcm_s16le", dst], check=True)


def _flite(text, voice, dst):
    txt = dst + ".txt"
    with open(txt, "w", encoding="utf-8") as f:
        f.write(text)
    esc = txt.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    raw = dst + ".raw.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"flite=textfile={esc}:voice={voice.get('voice', 'slt')}", raw], check=True)
    _to_48k(raw, dst, voice.get("speed", 1.0))
    os.remove(txt)
    os.remove(raw)


_kokoro = None
def _kokoro_tts(text, voice, dst):
    global _kokoro
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        raise SystemExit('voice engine "kokoro" needs: pip install kokoro-onnx (see README)')
    if _kokoro is None:
        model = voice.get("model", os.path.join(HERE, "models", "kokoro-v1.0.onnx"))
        voices = voice.get("voices", os.path.join(HERE, "models", "voices-v1.0.bin"))
        _kokoro = Kokoro(model, voices)
    x, sr = _kokoro.create(text, voice=voice.get("voice", "bm_george"), speed=voice.get("speed", 1.0),
                           lang=voice.get("lang", "en-gb"))
    raw = dst + ".raw.wav"
    with wave.open(raw, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    _to_48k(raw, dst)
    os.remove(raw)


def _trim(x, thresh=0.01, pad=0.03):
    loud = np.flatnonzero(np.abs(x) > thresh)
    if not len(loud):
        return x
    p = int(pad * SR)
    return x[max(0, loud[0] - p): loud[-1] + p]


def tts(text, voice):
    """Speech for `text`, trimmed of leading and trailing silence."""
    engine = voice.get("engine", "flite")
    key = hashlib.sha1(json.dumps([text, voice], sort_keys=True).encode()).hexdigest()[:16]
    path = os.path.join(VO_CACHE, f"{engine}-{key}.wav")
    if not os.path.exists(path):
        os.makedirs(VO_CACHE, exist_ok=True)
        tmp = path[:-4] + ".part.wav"
        if engine == "flite":
            _flite(text, voice, tmp)
        elif engine == "kokoro":
            _kokoro_tts(text, voice, tmp)
        else:
            raise SystemExit(f'unknown voice engine "{engine}" (use "flite" or "kokoro")')
        os.replace(tmp, path)
    return _trim(read_wav(path))


# ---------------------------------------------------------------- sound effects

def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _lowpass(x, cutoff):
    """One-pole low-pass; `cutoff` in Hz, scalar or per sample."""
    a = 1 - np.exp(-2 * np.pi * np.broadcast_to(np.asarray(cutoff, np.float64), x.shape) / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _tone(freq, dur, decay, attack=0.004):
    """Sine with a per-sample frequency glide and an exponential decay."""
    t = _t(dur)
    f = np.broadcast_to(np.asarray(freq, np.float64), t.shape)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t / decay) * np.clip(t / attack, 0, 1)


def _norm(x, peak=0.9):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def whoosh(dur=0.6, rise=True):
    t = _t(dur)
    k = t / dur
    sweep = 300 + 5200 * (k ** 2 if rise else (1 - k) ** 2)
    env = np.sin(np.pi * np.clip(k ** (0.6 if rise else 1.6), 0, 1)) ** 2
    x = _lowpass(_rng.standard_normal(len(t)), sweep)
    return _norm(x * env)


def spin(dur=2.5):
    """Airy whirr that slows down, for the spinning globe."""
    t = _t(dur)
    k = t / dur
    rate = 14 * (1 - k) ** 2 + 1.5
    flutter = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    x = _lowpass(_rng.standard_normal(len(t)), 500 + 1800 * (1 - k))
    env = np.clip(t / 0.25, 0, 1) * (1 - k) ** 1.5
    return _norm(x * flutter * env)


def pop(f=600):
    t = _t(0.14)
    return _norm(_tone(f * (1 + 1.4 * np.exp(-t / 0.014)), 0.14, 0.045))


def boop():
    """Falling blip for money going out."""
    t = _t(0.24)
    f = 440 * np.exp(-t / 0.25)
    x = _tone(f, 0.24, 0.09, 0.006) + 0.3 * _tone(2 * f, 0.24, 0.05, 0.006)
    return _norm(x)


def tick():
    x = _rng.standard_normal(int(0.012 * SR))
    x = x - _lowpass(x, 2500)
    return _norm(x * np.exp(-_t(0.012) / 0.0025))


def ticks(dur=1.4, n=18):
    """Counter ticks that slow down like an ease-out count."""
    out = np.zeros(int((dur + 0.05) * SR))
    tk = tick()
    for i in range(n):
        s = int(dur * (1 - (1 - i / n) ** (1 / 3)) * SR)
        out[s:s + len(tk)] += tk * (0.6 + 0.4 * _rng.random())
    return _norm(out, 0.8)


def ding(f=1318.5):
    x = sum(a * _tone(f * m, 1.4, dcy) for m, a, dcy in ((1, 1, 0.9), (1.5, 0.5, 0.6), (2, 0.35, 0.4), (3, 0.15, 0.25)))
    return _norm(x)


def cash():
    """Cash-register ka-ching: a click, then two bright bells."""
    out = np.zeros(int(1.3 * SR))
    click = _rng.standard_normal(int(0.03 * SR)) * np.exp(-_t(0.03) / 0.006)
    out[:len(click)] += 0.6 * click
    for delay, f in ((0.0, 2093), (0.07, 2637)):
        b = sum(a * _tone(f * m, 1.1, dcy) for m, a, dcy in ((1, 1, 0.5), (2.4, 0.4, 0.25), (3.9, 0.2, 0.12)))
        s = int(delay * SR)
        out[s:s + len(b)] += b[:len(out) - s]
    return _norm(out)


def impact():
    t = _t(1.0)
    sub = _tone(42 + 70 * np.exp(-t / 0.08), 1.0, 0.32, 0.002)
    hit = _lowpass(_rng.standard_normal(len(t)), 1400) * np.exp(-t / 0.05)
    return _norm(sub + 0.9 * _norm(hit))


def ping():
    """Sonar ping with two echoes, for the map pin."""
    p = _tone(1100, 1.6, 0.35) + 0.35 * _tone(2200, 1.6, 0.15)
    out = p.copy()
    for d, g in ((0.17, 0.35), (0.34, 0.12)):
        s = int(d * SR)
        out[s:] += g * p[:len(p) - s]
    return _norm(out)


SFX = {"whoosh": whoosh, "spin": spin, "pop": pop, "boop": boop, "ticks": ticks, "ding": ding,
       "cash": cash, "impact": impact, "ping": ping}


def mix(duration, voice_clips, effects, path):
    """Write the soundtrack: voice clips [(start, samples)] over effects [(start, name, kwargs, gain)],
    with the effects ducked while the voice speaks."""
    n = int(duration * SR)
    vo, fx = np.zeros(n + SR), np.zeros(n + SR)

    def add(buf, start, x):
        s = max(0, int(start * SR))
        x = x[:len(buf) - s]
        buf[s:s + len(x)] += x

    for start, x in voice_clips:
        add(vo, start, x)
    cache = {}
    for start, name, kw, gain in effects:
        key = (name, tuple(sorted(kw.items())))
        if key not in cache:
            cache[key] = SFX[name](**kw)
        add(fx, start, cache[key] * gain)
    win = int(0.08 * SR)
    env = np.convolve(np.abs(vo), np.ones(win) / win, mode="same")
    duck = 1 - 0.5 * np.clip(env / 0.05, 0, 1)
    out = (vo + 0.8 * fx * duck)[:n]
    write_wav(path, _norm(out, 0.95) if np.max(np.abs(out)) > 0.95 else out)
