"""Procedural sound design, timed from the events log the renderer writes.

Every sound is synthesised with numpy, so episodes need no audio files. Any
sound can be replaced by a royalty-free file: drop it in assets/sfx/ (or the
config's "sfx_dir") using the slot name, e.g. `fold_crease.wav`. Variants
`fold_crease_1.wav`, `fold_crease_2.wav`... are picked at random per use.
Any format ffmpeg can read works (wav, mp3, ogg, flac...).

Slots:
    title_sting      hook at frame 0
    fold_flip        the flap swinging over (physical folds)
    fold_crease      the crisp crease when it lands
    grow_whoosh      each doubling of the column
    grow_tick        the column landing on its new height
    landmark_chime   a landmark appears
    landmark_whoosh  the camera pulls out to frame a landmark
    riser            rising tone during the pull-back (trimmed to fit)
    finale_hit       the big hit when the last fold lands
    cta_pop          "What should we fold next?"
    music            optional background bed, mixed quietly underneath
"""

import glob
import math
import os
import random
import subprocess

import numpy as np

SR = 48000
SLOTS = ("title_sting", "fold_flip", "fold_crease", "grow_whoosh", "grow_tick",
         "landmark_chime", "landmark_whoosh", "riser", "finale_hit", "cta_pop", "music")

# Pentatonic steps for landmark chimes: each landmark rings a little higher.
CHIME_NOTES = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21]


def db(x):
    return 10 ** (x / 20.0)


# --- DSP helpers -----------------------------------------------------------------

def shaped_noise(rng, n, lo=None, hi=None, tilt=0.0):
    """White noise band-limited in the frequency domain (smooth 4th-order edges)."""
    x = rng.standard_normal(n)
    if lo is None and hi is None and not tilt:
        return x
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = 1e-3
    h = np.ones_like(f)
    if lo:
        h *= 1.0 / np.sqrt(1.0 + (lo / f) ** 4)
    if hi:
        h *= 1.0 / np.sqrt(1.0 + (f / hi) ** 4)
    if tilt:
        h *= (f / 1000.0) ** tilt
    y = np.fft.irfft(spec * h, n)
    return y / (np.std(y) + 1e-9)


def sweep_bandpass(x, f_start, f_end, q=1.4):
    """State-variable band-pass whose centre glides from f_start to f_end."""
    n = len(x)
    fc = np.geomspace(f_start, f_end, n)
    g = 2.0 * np.sin(np.pi * np.minimum(fc, SR / 6.0) / SR)
    damp = 1.0 / q
    low = band = 0.0
    out = np.empty(n)
    for i in range(n):  # tiny loop; sounds are well under a second
        high = x[i] - low - damp * band
        band += g[i] * high
        low += g[i] * band
        out[i] = band
    return out / (np.max(np.abs(out)) + 1e-9)


def env_ar(n, attack, release_shape=3.0):
    """Attack fraction then curved decay to 0."""
    t = np.linspace(0, 1, n, endpoint=False)
    a = max(attack, 1e-4)
    up = np.clip(t / a, 0, 1)
    down = np.clip((1 - t) / (1 - a), 0, 1) ** release_shape
    return np.where(t < a, up, down)


def exp_decay(n, tau_s):
    return np.exp(-np.arange(n) / (tau_s * SR))


def crackles(rng, n, density_env, rate, hi=9000.0, amp=1.0):
    """Sparse clicks whose density follows `density_env` (paper rustle)."""
    out = np.zeros(n)
    count = int(rate * n / SR)
    if count <= 0:
        return out
    p = density_env / (density_env.sum() + 1e-9)
    pos = rng.choice(n, size=count, p=p)
    click_len = int(0.003 * SR)
    for c in pos:
        clen = min(click_len, n - c)
        if clen <= 4:
            continue
        click = rng.standard_normal(clen) * np.exp(-np.arange(clen) / (0.0006 * SR))
        out[c:c + clen] += click * rng.uniform(0.3, 1.0) * amp
    return shaped_noise_filter(out, lo=2500.0, hi=hi)


def shaped_noise_filter(x, lo=None, hi=None):
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = 1e-3
    h = np.ones_like(f)
    if lo:
        h *= 1.0 / np.sqrt(1.0 + (lo / f) ** 4)
    if hi:
        h *= 1.0 / np.sqrt(1.0 + (f / hi) ** 4)
    return np.fft.irfft(spec * h, n)


def sine_sweep(n, f0, f1, curve=1.0):
    t = np.linspace(0, 1, n, endpoint=False) ** curve
    freq = f0 * (f1 / f0) ** t
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def normalise(x, peak=1.0):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


# --- Sound recipes ----------------------------------------------------------------

PROFILES = {
    # band of the flip swish, crackle rate, crease brightness, thump pitch, scrape level
    "paper": dict(flip_lo=700, flip_hi=4500, crackle=90, crease_hi=12000, thump=120, scrape=0.35),
    "cloth": dict(flip_lo=250, flip_hi=1600, crackle=0, crease_hi=2500, thump=80, scrape=0.0),
    "dough": dict(flip_lo=200, flip_hi=1200, crackle=6, crease_hi=1800, thump=70, scrape=0.0),
}


def fold_flip(rng, dur, profile):
    p = PROFILES[profile]
    n = max(int(dur * SR), 256)
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    air = shaped_noise(rng, n, p["flip_lo"], p["flip_hi"]) * shape * 0.30
    rustle = crackles(rng, n, shape + 0.15, p["crackle"] * dur, amp=1.0) * 0.55 if p["crackle"] else 0
    return normalise(air + rustle, 0.30)


def fold_crease(rng, profile):
    p = PROFILES[profile]
    n = int(0.45 * SR)
    out = np.zeros(n)
    m = int(0.04 * SR)
    snap = shaped_noise(rng, m, 1800.0, p["crease_hi"]) * exp_decay(m, 0.006)
    out[:m] += snap * (0.9 if profile == "paper" else 0.5)
    m = int(0.12 * SR)
    thump = sine_sweep(m, p["thump"], p["thump"] * 0.5) * exp_decay(m, 0.035)
    out[:m] += thump * (0.55 if profile == "paper" else 0.95)
    if p["scrape"]:
        m = int(0.26 * SR)
        start = int(0.015 * SR)
        scrape = shaped_noise(rng, m, 2000.0, 8000.0) * env_ar(m, 0.12, 2.0)
        scrape += crackles(rng, m, env_ar(m, 0.1, 2.0), 160 * 0.26) * 0.8
        out[start:start + m] += scrape * p["scrape"]
    if profile == "dough":   # wet slap
        m = int(0.08 * SR)
        out[:m] += shaped_noise(rng, m, 300.0, 1600.0) * exp_decay(m, 0.012) * 0.7
    return normalise(out, 0.9)


def whoosh(rng, dur, f0, f1, level=0.5, q=1.3):
    n = max(int(dur * SR), 256)
    x = sweep_bandpass(rng.standard_normal(n), f0, f1, q)
    body = shaped_noise(rng, n, 120.0, 900.0) * 0.25
    return (x + body) * env_ar(n, 0.42, 2.2) * level


def tick(rng, freq=1500.0):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * freq * t) * exp_decay(n, 0.012)
    click = shaped_noise(rng, n, 3000.0, 10000.0) * exp_decay(n, 0.002) * 0.4
    return (tone + click) * 0.35


def chime(index, level=0.32):
    semis = CHIME_NOTES[index % len(CHIME_NOTES)] + 12 * (index // len(CHIME_NOTES))
    f = 659.25 * 2 ** (semis / 12.0)   # starts on E5
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * f * t) * exp_decay(n, 0.55)
            + 0.45 * np.sin(2 * np.pi * f * 2.0 * t) * exp_decay(n, 0.25)
            + 0.20 * np.sin(2 * np.pi * f * 3.01 * t) * exp_decay(n, 0.12)
            + 0.15 * np.sin(2 * np.pi * f * 0.5 * t) * exp_decay(n, 0.7))
    attack = np.clip(t / 0.004, 0, 1)
    return normalise(tone * attack, level)


def riser(times, log_view, t_start, t_end, ducks, rng):
    """Rising tone whose pitch follows the camera's log-scale pull-back."""
    n = int((t_end - t_start) * SR)
    if n <= 0:
        return np.zeros((0, 2))
    t = t_start + np.arange(n) / SR
    lv = np.interp(t, times, log_view)
    lo, hi = lv[0], max(lv[-1], lv[0] + 1e-3)
    u = np.clip((lv - lo) / (hi - lo), 0, 1)
    freq = 98.0 * 2 ** (u * 2.6)              # ~G2 up 2.6 octaves
    out = np.zeros((n, 2))
    for ch, detune in enumerate((0.997, 1.004)):
        phase = 2 * np.pi * np.cumsum(freq * detune) / SR
        voice = np.zeros(n)
        for k in range(1, 9):                  # soft saw, brighter as it climbs
            voice += np.sin(k * phase) / k * np.exp(-k / (2.0 + 4.0 * u))
        voice += 0.35 * np.sin(1.5 * phase)    # a fifth above
        out[:, ch] = voice
    swell = db(-27 + 15 * u ** 1.6)
    fade_in = np.clip((t - t_start) / 2.0, 0, 1)
    fade_out = np.clip((t_end - t) / 0.03, 0, 1)
    duck = np.ones(n)
    for a, b in ducks:                         # dip under landmark beats
        duck *= 1 - 0.45 * (np.clip((t - a) / 0.3, 0, 1) * np.clip((b - t) / 0.6, 0, 1))
    shimmer = 1 + 0.06 * np.sin(2 * np.pi * (3 + 5 * u) * (t - t_start))
    gain = swell * fade_in * fade_out * duck * shimmer
    return normalise(out, 1.0) * gain[:, None] * 0.5


def afterglow(base_freq, dur, rng):
    """Soft sustained chord after the finale hit, fading to silence."""
    n = int(dur * SR)
    if n <= 0:
        return np.zeros((0, 2))
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ratio, amp in ((1.0, 1.0), (1.5, 0.5), (2.0, 0.35), (3.0, 0.12)):
        for ch, det in enumerate((0.998, 1.002)):
            out[:, ch] += amp * np.sin(2 * np.pi * base_freq * ratio * det * t + rng.uniform(0, 6))
    env = np.clip(t / 1.2, 0, 1) * np.clip((dur - t) / (dur * 0.6), 0, 1) ** 1.5
    return normalise(out, 1.0) * env[:, None] * 0.12


def finale_hit(rng):
    n = int(3.6 * SR)
    t = np.arange(n) / SR
    sub = sine_sweep(n, 95.0, 34.0, 0.5) * exp_decay(n, 0.9) * 1.0
    m = int(0.5 * SR)
    burst = np.zeros(n)
    burst[:m] = shaped_noise(rng, m, 60.0, 3500.0) * exp_decay(m, 0.07) * 0.8
    crack = np.zeros(n)
    m = int(0.05 * SR)
    crack[:m] = shaped_noise(rng, m, 2000.0, 14000.0) * exp_decay(m, 0.008) * 0.6
    shimmer = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (2093.0, 2637.0, 3136.0, 4186.0))
    shimmer = shimmer * exp_decay(n, 0.9) * np.clip(t / 0.05, 0, 1) * 0.05
    dry = sub + burst + crack + shimmer
    tail = convolve(dry, reverb_ir(rng, 3.0, 0.9))
    return normalise(dry + 0.35 * normalise(tail[:n]), 0.98)


def title_sting(rng):
    n = int(0.9 * SR)
    sw = whoosh(rng, 0.5, 400.0, 3000.0, 0.5)
    out = np.zeros(n)
    out[:len(sw)] += sw
    pop = chime(3, 0.25)[: n - int(0.3 * SR)]
    out[int(0.3 * SR):int(0.3 * SR) + len(pop)] += pop
    return out


def cta_pop():
    a, b = chime(5, 0.25), chime(7, 0.22)
    out = np.zeros(len(a) + int(0.12 * SR))
    out[:len(a)] += a
    out[int(0.12 * SR):] += b
    return out


def reverb_ir(rng, length_s, decay_s):
    n = int(length_s * SR)
    ir = rng.standard_normal(n) * exp_decay(n, decay_s / 3.0)
    ir = shaped_noise_filter(ir, lo=150.0, hi=6000.0)
    return ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)


def convolve(x, h):
    size = 1 << int(math.ceil(math.log2(len(x) + len(h))))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(h, size), size)
    return y[:len(x) + len(h) - 1]


# --- Optional user files -----------------------------------------------------------

class SampleBank:
    """Finds user-supplied SFX files for each slot."""

    def __init__(self, dirs, seed):
        self.files = {s: [] for s in SLOTS}
        self.cache = {}
        self.rand = random.Random(seed)
        for d in dirs:
            if not d or not os.path.isdir(d):
                continue
            for slot in SLOTS:
                for path in sorted(glob.glob(os.path.join(d, slot + ".*"))
                                   + glob.glob(os.path.join(d, slot + "_*.*"))):
                    if not path.lower().endswith((".md", ".txt")):
                        self.files[slot].append(path)

    def has(self, slot):
        return bool(self.files.get(slot))

    def get(self, slot):
        path = self.rand.choice(self.files[slot])
        if path not in self.cache:
            self.cache[path] = load_audio(path)
        return self.cache[path]


def load_audio(path):
    """Decode any audio file to 48 kHz stereo float with ffmpeg."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


# --- Mixer -----------------------------------------------------------------------

class Mix:
    def __init__(self, duration):
        self.n = int(math.ceil(duration * SR)) + SR
        self.dry = np.zeros((self.n, 2))
        self.send = np.zeros((self.n, 2))

    def add(self, t, sound, gain_db=0.0, pan=0.0, reverb=0.15):
        if sound is None or len(sound) == 0:
            return
        s = sound if sound.ndim == 2 else np.stack([sound, sound], axis=1)
        if sound.ndim == 1:  # constant-power pan for mono sources
            a = (pan + 1) * math.pi / 4
            s = s * np.array([math.cos(a), math.sin(a)]) * math.sqrt(2)
        i = int(round(t * SR))
        if i >= self.n:
            return
        if i < 0:
            s, i = s[-i:], 0
        m = min(len(s), self.n - i)
        g = db(gain_db)
        self.dry[i:i + m] += s[:m] * g
        self.send[i:i + m] += s[:m] * g * reverb

    def render(self, rng):
        ir = reverb_ir(rng, 1.8, 1.1)
        wet = np.stack([convolve(self.send[:, c], ir)[:self.n] for c in range(2)], axis=1)
        out = self.dry + wet * 0.8
        peak = np.max(np.abs(out))
        if peak > 0.89:                     # gentle soft-knee limiting
            out = np.tanh(out / peak * 1.4) / np.tanh(1.4) * 0.89
        return out


# --- Building the episode soundtrack ------------------------------------------------

def build_soundtrack(log, out_path, sfx_dirs=()):
    cfg = log["config"]
    rng = np.random.default_rng(cfg.get("seed", 7))
    bank = SampleBank(sfx_dirs, cfg.get("seed", 7))
    profile = cfg.get("sound", "paper")
    duration = log["duration"]
    mix = Mix(duration)
    events = log["events"]

    def sound(slot, make):
        return bank.get(slot) if bank.has(slot) else make()

    beats_held = []
    chime_index = 0
    by_type = {}
    for e in events:
        by_type.setdefault(e["type"], []).append(e)

    for e in events:
        t, kind = e["t"], e["type"]
        if kind == "title_in":
            mix.add(t, sound("title_sting", lambda: title_sting(rng)), -6)
        elif kind == "fold_start":
            pan = 0.25 if e["n"] % 2 else -0.25
            mix.add(t, sound("fold_flip", lambda: fold_flip(rng, e["duration"] * 1.05, profile)), -4, pan)
        elif kind == "fold_land":
            mix.add(t - 0.004, sound("fold_crease", lambda: fold_crease(rng, profile)), -2, 0.0, 0.2)
        elif kind == "grow":
            if e.get("final"):
                continue  # the riser and the hit carry the final fold
            level = -16 + 6 * min(1.0, e["n"] / 40.0)
            f1 = 1800 + 120 * (e["n"] % 5)
            mix.add(t - 0.05, sound("grow_whoosh", lambda: whoosh(rng, 0.5, 260.0, f1, 0.6)),
                    level, rng.uniform(-0.3, 0.3))
        elif kind == "grow_land":
            if e["n"] != cfg["folds"]:
                mix.add(t, sound("grow_tick", lambda: tick(rng, 1300 + 40 * (e["n"] % 6))), -14, 0.1, 0.25)
        elif kind == "label_in":
            # Chime with the label, not when the model first appears (the Moon
            # drifts into view a couple of folds early).
            mix.add(t, sound("landmark_chime", lambda: chime(chime_index)), -9, -0.2, 0.35)
            chime_index += 1
        elif kind == "landmark_whoosh":
            mix.add(t, sound("landmark_whoosh", lambda: whoosh(rng, 1.1, 180.0, 1400.0, 0.7, 1.1)), -10)
            beats_held.append((t - 0.3, t + 2.2))
        elif kind == "finale_hit":
            mix.add(t, sound("finale_hit", lambda: finale_hit(rng)), 0, 0.0, 0.25)
        elif kind == "cta_in":
            mix.add(t, sound("cta_pop", cta_pop), -8, 0.0, 0.3)

    # Riser across the pull-back, pitched by the camera's log-scale.
    start = (by_type.get("pullback_start") or [None])[0]
    end = (by_type.get("pullback_end") or [None])[0]
    if start and end and end["t"] > start["t"]:
        frames = log["frames"]
        times = np.array([f["t"] for f in frames])
        views = np.log10(np.array([max(f["view_m"], 1e-9) for f in frames]))
        if bank.has("riser"):
            r = bank.get("riser")
            r = r[: int((end["t"] - start["t"]) * SR)]
            r *= np.clip(np.arange(len(r)) / (0.5 * SR), 0, 1)[:, None]
            mix.add(start["t"], r, -6)
        elif len(times) and times[-1] > start["t"]:
            t_end = min(end["t"], times[-1])
            mix.add(start["t"], riser(times, views, start["t"], t_end, beats_held, rng), 0, reverb=0.1)
            # Let the final note ring on quietly into the ending.
            final_freq = 98.0 * 2 ** 2.6 / 2
            mix.add(end["t"] + 0.4, afterglow(final_freq, duration - end["t"] - 0.4, rng), 0, reverb=0.3)

    if bank.has("music"):
        music = bank.get("music")[: mix.n]
        fade = np.clip((duration - np.arange(len(music)) / SR) / 2.5, 0, 1)
        mix.add(0.0, music * fade[:, None], -20, reverb=0.0)

    out = mix.render(rng)
    end_sample = int(log["render_end"] * SR)
    out = out[:end_sample]
    fade = min(len(out), int(0.05 * SR))
    if fade:
        out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    write_wav(out_path, out)
    return out_path


def write_wav(path, data):
    import wave
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
