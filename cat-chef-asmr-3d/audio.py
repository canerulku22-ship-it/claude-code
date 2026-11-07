"""Procedural sound design + music, synchronised to the animation cue sheet.

Everything is synthesised (no samples): a 120 BPM funk/house groove whose
bars line up with the cuts, plus foley built from filtered noise and
oscillators -- flour puffs, a dough slap, sauce splats, a crackling wood fire,
bubbling cheese, a pizza wheel crunching through the crust,
whooshes, risers and impacts.

    python audio.py --timeline out/timeline.json --out out/soundtrack.wav
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import config as C  # noqa: E402

SR = 48000
RNG = np.random.default_rng(11)


# ------------------------------------------------------------------ dsp ----
def t_axis(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return RNG.standard_normal(int(d * SR))


def bp(x, lo, hi, order=2):
    lo, hi = max(lo, 20), min(hi, SR / 2 - 100)
    return signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, min(fc, SR / 2 - 100), "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x)


def env_exp(d, decay, attack=0.002):
    t = t_axis(d)
    a = np.minimum(t / attack, 1.0) if attack > 0 else 1.0
    return a * np.exp(-t / decay)


def sweep_bp(x, f0, f1, bands=10, q=1.6):
    """Crossfade a bank of band-passes to fake a moving resonant filter."""
    n = len(x)
    centers = np.geomspace(min(f0, f1) * 0.8, max(f0, f1) * 1.25, bands)
    path = np.geomspace(f0, f1, n)
    out = np.zeros(n)
    for c in centers:
        y = bp(x, c / q, c * q)
        w = np.exp(-(np.log(path / c) / 0.35) ** 2)
        out += y * w
    return out


def pan(x, p):
    """p in [-1,1] (scalar or array) -> stereo"""
    p = np.clip(p, -1, 1)
    l, r = np.cos((p + 1) * math.pi / 4), np.sin((p + 1) * math.pi / 4)
    return np.stack([x * l, x * r], 1)


def reverb_ir(d=1.8, decay=0.45, seed=3):
    r = np.random.default_rng(seed)
    t = t_axis(d)
    e = np.exp(-t / decay)
    ir = np.stack([r.standard_normal(len(t)) * e, r.standard_normal(len(t)) * e], 1)
    ir[:, 0] = lp(ir[:, 0], 7000)
    ir[:, 1] = lp(ir[:, 1], 7000)
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


IR = reverb_ir()


def reverb(st, wet=0.25):
    out = np.stack([signal.fftconvolve(st[:, c], IR[:, c])[: len(st)] for c in range(2)], 1)
    return st * (1 - wet) + out * wet


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


class Bus:
    def __init__(self, dur):
        self.x = np.zeros((int(dur * SR) + SR * 3, 2))

    def add(self, t, st, gain=1.0):
        if st.ndim == 1:
            st = pan(st, 0)
        i = int(t * SR)
        if i < 0:
            st, i = st[-i:], 0
        j = min(i + len(st), len(self.x))
        self.x[i:j] += st[: j - i] * gain


# --------------------------------------------------------------- drums -----
def kick(level=1.0):
    d = 0.5
    t = t_axis(d)
    f = 46 + 120 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 6.5)
    x += 0.4 * hp(noise(d), 2000) * np.exp(-t * 300)
    return np.tanh(1.6 * x) * level


def snare(level=1.0):
    d = 0.35
    t = t_axis(d)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28)
    nz = bp(noise(d), 1200, 7500) * np.exp(-t * 16)
    clap = np.zeros_like(t)
    for k, off in enumerate((0.0, 0.011, 0.022)):
        i = int(off * SR)
        seg_ = bp(noise(0.25), 900, 3500) * np.exp(-t_axis(0.25) * (60 if k < 2 else 18))
        clap[i:i + len(seg_)] += seg_[: len(clap) - i]
    return (0.5 * body + 0.8 * nz + 0.6 * clap) * level


def hat(open_=False, level=1.0):
    d = 0.3 if open_ else 0.08
    t = t_axis(d)
    return hp(noise(d), 7000, 4) * np.exp(-t * (9 if open_ else 55)) * level


def crash(level=1.0):
    d = 2.0
    t = t_axis(d)
    return (hp(noise(d), 4500, 2) * np.exp(-t * 1.6) + 0.3 * bp(noise(d), 300, 1000) * np.exp(-t * 6)) * level


# ------------------------------------------------------------- tonal -------
def ep_note(f, d=1.2, vel=1.0):
    t = t_axis(d)
    idx = 1.6 * np.exp(-t * 5)
    mod = np.sin(2 * np.pi * f * t)
    x = np.sin(2 * np.pi * f * t + idx * mod)
    x += 0.12 * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 40)
    x *= np.exp(-t * 2.4) * np.minimum(t / 0.004, 1) * (1 + 0.15 * np.sin(2 * np.pi * 5.0 * t))
    return x * vel


def bass_note(f, d=0.25, vel=1.0):
    t = t_axis(d)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    e = np.minimum(t / 0.005, 1) * np.exp(-t * 3.0) * np.minimum((d - t) / 0.02, 1)
    return np.tanh(1.4 * x * e) * vel


def pad_chord(freqs, d, attack=0.6):
    t = t_axis(d)
    x = np.zeros_like(t)
    for f in freqs:
        for det in (-0.08, 0.0, 0.07):
            ff = f * 2 ** (det / 12)
            for h in range(1, int(min(9, 5000 / ff)) + 1):
                x += np.sin(2 * np.pi * ff * h * t + RNG.uniform(0, 6.28)) / h
    x = lp(x, 1600)
    e = np.minimum(t / attack, 1) * np.minimum((d - t) / 0.5, 1)
    return x * e / (len(freqs) * 6)


# ------------------------------------------------------------------ sfx ----
def whoosh(dur=0.4, up=False, pitch=1.0):
    d = dur + 0.15
    x = noise(d)
    f0, f1 = (400 * pitch, 5000 * pitch) if up else (4500 * pitch, 350 * pitch)
    y = sweep_bp(x, f0, f1)
    t = t_axis(d)
    peak = 0.7 if up else 0.35
    e = np.where(t < peak * dur, (t / (peak * dur)) ** 2, np.exp(-(t - peak * dur) / (0.25 * dur)))
    return pan(y * e * 0.9, np.linspace(-0.7, 0.7, len(y)))


def tick(pitch=1.0):
    t = t_axis(0.08)
    x = (np.sin(2 * np.pi * 1900 * pitch * t) + 0.5 * np.sin(2 * np.pi * 3800 * pitch * t)) * np.exp(-t * 70)
    return x * 0.5


def pop(pitch=1.0):
    t = t_axis(0.09)
    f = (300 + 700 * (1 - np.exp(-t * 60))) * pitch
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * 0.6


def thud(size=0.6, soft=False):
    d = 0.5
    t = t_axis(d)
    f = (62 if not soft else 140) * (1 + 0.8 * np.exp(-t * 25))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (9 if not soft else 14))
    x += lp(noise(d), 900 if not soft else 500) * np.exp(-t * 35) * 0.6
    if soft:
        x += bp(noise(d), 200, 700) * np.exp(-t * 20) * 0.5
    return np.tanh(x * 1.3) * size


def crunch(size=1.0):
    d = 0.4
    out = np.zeros(int(d * SR))
    times = np.sort(RNG.exponential(0.06, 45))
    for tt in times[times < d - 0.03]:
        g = bp(noise(0.02), RNG.uniform(1500, 3500), RNG.uniform(5000, 9000)) * np.exp(-t_axis(0.02) * 250)
        i = int(tt * SR)
        out[i:i + len(g)] += g * RNG.uniform(0.3, 1.0) * np.exp(-tt * 6)
    out += thud(0.5)[: len(out)] * 0.6
    return out * size * 1.2


def shake():
    d = 0.3
    out = np.zeros(int(d * SR))
    for tt in np.sort(RNG.uniform(0, 0.16, 14)):
        g = hp(noise(0.015), 4000) * np.exp(-t_axis(0.015) * 300)
        i = int(tt * SR)
        out[i:i + len(g)] += g * RNG.uniform(0.3, 1.0)
    return out * 0.8


def splash(size=1.0):
    d = 0.9
    t = t_axis(d)
    x = noise(d)
    body = sweep_bp(x, 5000, 600) * np.exp(-t * 5) * np.minimum(t / 0.01, 1)
    for _ in range(int(30 * size)):
        tt = RNG.uniform(0.02, 0.6)
        f0 = RNG.uniform(700, 2600)
        tb = t_axis(0.05)
        blip = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.6 * tb / 0.05)) / SR) * np.exp(-tb * 80)
        i = int(tt * SR)
        body[i:i + len(blip)] += blip * 0.25 * np.exp(-tt * 3)
    return body * size


def drip():
    t = t_axis(0.12)
    f = 900 + 1400 * (t / 0.12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * 0.35


def puff(size=1.0):
    d = 0.6
    t = t_axis(d)
    return lp(noise(d), 1300) * np.minimum(t / 0.012, 1) * np.exp(-t * 7) * size * 1.4


def sprinkle(dur=0.5):
    d = dur + 0.1
    out = np.zeros(int(d * SR))
    for tt in RNG.uniform(0, dur, int(120 * dur)):
        g = hp(noise(0.006), 5500) * np.exp(-t_axis(0.006) * 600)
        i = int(tt * SR)
        out[i:i + len(g)] += g * RNG.uniform(0.2, 0.8)
    return out * 0.6


def clack():
    t = t_axis(0.15)
    x = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((2300, 1), (3710, 0.7), (5230, 0.4)))
    return (x * np.exp(-t * 45) + hp(noise(0.15), 3000) * np.exp(-t * 200)) * 0.35


def squeeze(dur=0.7):
    d = dur + 0.2
    t = t_axis(d)
    x = noise(d)
    lfo = 1 + 0.45 * np.sin(2 * np.pi * 7.5 * t) + 0.2 * np.sin(2 * np.pi * 13 * t)
    y = np.zeros_like(x)
    for c in (380, 560, 820, 1150):
        y += bp(x, c * 0.8, c * 1.25) * np.exp(-((lfo * 700 - c) / 300) ** 2)
    e = np.minimum(t / 0.05, 1) * np.clip((dur - t) / 0.08, 0, 1)
    tail = hp(noise(d), 2000) * np.exp(-np.clip(t - dur, 0, None) * 25) * (t > dur) * 0.4
    return (y * e * 2.0 + tail) * 0.8


def sizzle(dur, onset=True, level=1.0):
    d = dur + 0.3
    t = t_axis(d)
    base = hp(noise(d), 2500, 3) * 0.35
    base *= 1 + 0.35 * lp(RNG.standard_normal(len(t)), 6)
    crack = np.zeros_like(t)
    for tt in RNG.uniform(0, dur, int(dur * 90)):
        g = bp(noise(0.012), 2500, 9000) * np.exp(-t_axis(0.012) * 400)
        i = int(tt * SR)
        crack[i:i + len(g)] += g * RNG.uniform(0.2, 1.2)
    x = base + crack * 0.8
    e = np.clip((dur - t) / 0.15, 0, 1)
    if onset:
        e = e * (1 + 1.6 * np.exp(-t * 2.2)) * np.minimum(t / 0.03, 1)
    return x * e * level


def _bubble(f0, f1, d, decay):
    tb = t_axis(d)
    f = f0 + (f1 - f0) * tb / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(tb / 0.003, 1) * np.exp(-tb / decay)


def boil(dur):
    """Rolling boil: dense small bubble blips over a low watery rumble."""
    d = dur + 0.3
    t = t_axis(d)
    x = lp(noise(d), 500) * 0.25 * (1 + 0.4 * lp(RNG.standard_normal(len(t)), 3))
    for tt in RNG.uniform(0, dur, int(dur * 55)):
        b = _bubble(RNG.uniform(250, 520), RNG.uniform(500, 1100), 0.04, RNG.uniform(0.006, 0.014))
        i = int(tt * SR)
        x[i:i + len(b)] += b * RNG.uniform(0.08, 0.3)
    e = np.minimum(t / 0.2, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return x * e


def simmer(dur, level=1.0):
    """Thick tomato sauce: slow, low 'blup' pops plus a faint sizzle."""
    d = dur + 0.3
    t = t_axis(d)
    x = hp(noise(d), 3000) * 0.04
    for tt in RNG.uniform(0, dur, int(dur * 7)):
        b = _bubble(RNG.uniform(90, 160), RNG.uniform(220, 420), 0.09, RNG.uniform(0.02, 0.04))
        b += lp(noise(0.09), 900) * np.exp(-t_axis(0.09) * 60) * 0.3
        i = int(tt * SR)
        x[i:i + len(b)] += b * RNG.uniform(0.25, 0.6)
    e = np.minimum(t / 0.3, 1) * np.clip((dur - t) / 0.25, 0, 1)
    return x * e * level


def pour(dur):
    """Thick sauce poured from a bowl: glugging band-passed noise."""
    d = dur + 0.4
    t = t_axis(d)
    x = bp(noise(d), 250, 1400) * 0.5
    glug = 0.5 + 0.5 * np.sin(2 * np.pi * 5.5 * t + 1.5 * np.sin(2 * np.pi * 1.3 * t))
    x *= 0.5 + 0.7 * glug
    for tt in np.arange(0.05, dur, 0.19) + RNG.uniform(-0.03, 0.03, len(np.arange(0.05, dur, 0.19))):
        b = _bubble(140, 380, 0.12, 0.04)
        i = int(max(tt, 0) * SR)
        x[i:i + len(b)] += b * 0.35
    e = np.minimum(t / 0.06, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return x * e


def splat():
    """Wet pasta landing in sauce."""
    d = 0.5
    t = t_axis(d)
    x = lp(noise(d), 1800) * np.exp(-t * 12) * np.minimum(t / 0.004, 1)
    x += np.sin(2 * np.pi * np.cumsum(110 * (1 + np.exp(-t * 25))) / SR) * np.exp(-t * 14) * 0.6
    for _ in range(10):
        b = _bubble(RNG.uniform(200, 500), RNG.uniform(400, 900), 0.06, 0.015)
        i = int(RNG.uniform(0.01, 0.25) * SR)
        x[i:i + len(b)] += b * 0.15
    return x


def clatter():
    """Dry spaghetti rattling against the pot."""
    d = 0.45
    x = np.zeros(int(d * SR))
    for tt in np.sort(RNG.uniform(0, 0.3, 26)):
        k = bp(noise(0.02), 3000, 9000) * np.exp(-t_axis(0.02) * 300)
        i = int(tt * SR)
        x[i:i + len(k)] += k * RNG.uniform(0.2, 0.7) * np.exp(-tt * 6)
    return x


def hiss(dur=1.4):
    """Wine hitting a hot pan: a loud sizzle burst plus a steamy whoosh."""
    x = sizzle(dur, onset=True, level=1.4)
    t = t_axis(len(x) / SR)
    x = x + bp(noise(len(x) / SR), 1500, 7000) * np.exp(-t * 2.5) * np.minimum(t / 0.02, 1) * 0.5
    return x


def stir(dur=1.3):
    """Wooden spoon scraping round the pan."""
    d = dur + 0.2
    t = t_axis(d)
    x = bp(noise(d), 700, 3200) * (0.25 + np.abs(np.sin(2 * np.pi * 1.6 * t)) ** 3)
    x += lp(noise(d), 300) * 0.15
    return x * np.minimum(t / 0.08, 1) * np.clip((dur - t) / 0.15, 0, 1) * 0.6


def crackle(dur=3.0):
    """Wood fire: sparse sharp crackles and pops over a low roar."""
    d = dur + 0.2
    t = t_axis(d)
    x = np.zeros_like(t)
    for tt in RNG.uniform(0, dur, int(dur * 16)):
        L = RNG.uniform(0.003, 0.012)
        g = bp(noise(L), 1200, 7000) * np.exp(-t_axis(L) * RNG.uniform(250, 600)) * RNG.uniform(0.3, 1.0)
        i = int(tt * SR)
        x[i:i + len(g)] += g[:max(0, len(x) - i)]
    roar = lp(noise(d), 220) * (0.5 + 0.25 * lp(RNG.standard_normal(len(t)), 3) * 20)
    x = x * 0.9 + roar * 0.35
    return x * np.minimum(t / 0.3, 1) * np.clip((dur - t) / 0.3, 0, 1)


def meow(pitch=1.0, dur=0.62):
    """Cartoon meow: a voiced glide 'mi-aa-ow' through moving formants."""
    t = t_axis(dur)
    u = t / dur
    f0 = pitch * (520 + 380 * np.sin(np.pi * np.clip(u * 1.25, 0, 1)) ** 1.2 - 120 * u)
    f0 = f0 * (1 + 0.012 * np.sin(2 * np.pi * 6.0 * t))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    src = sum(np.sin(k * ph) / k ** 1.1 for k in range(1, 14))
    f2 = np.interp(u, [0, 0.3, 0.7, 1.0], [2300, 1500, 1100, 900])
    f1 = np.interp(u, [0, 0.3, 0.7, 1.0], [420, 820, 700, 500])
    out = np.zeros_like(src)
    for fc, w in ((f1, 1.0), (f2, 0.6)):
        bands = np.geomspace(fc.min() * 0.9, fc.max() * 1.1, 8)
        for b in bands:
            g = np.exp(-0.5 * (np.log(fc / b) / 0.18) ** 2)
            out += w * g * bp(src, b / 1.25, b * 1.25)
    env = np.minimum(t / 0.04, 1) * np.clip((dur - t) / 0.12, 0, 1)
    out = out * env
    return out / max(np.abs(out).max(), 1e-9) * 0.8


def purr(dur=2.0):
    """Low rumbling purr: noise pulsed at ~25 Hz, breathing in and out."""
    d = dur + 0.2
    t = t_axis(d)
    x = lp(noise(d), 380) * (0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * 25.0 * t)) ** 2)
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t) ** 2
    x += 0.4 * np.sin(2 * np.pi * 50.0 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 25.0 * t))
    x = x * np.minimum(t / 0.2, 1) * np.clip((dur - t) / 0.3, 0, 1)
    return x / max(np.abs(x).max(), 1e-9) * 0.7


def sneeze():
    """Tiny kitten sneeze: a breathy 'h' then a sharp 'tchi'."""
    a = bp(noise(0.12), 900, 3000) * np.linspace(0, 1, int(0.12 * SR)) ** 2 * 0.25
    b = bp(noise(0.09), 2500, 8000) * env_exp(0.09, 0.03, 0.003)
    tt = t_axis(0.09)
    b = b + 0.3 * np.sin(2 * np.pi * 900 * tt) * env_exp(0.09, 0.025)
    x = np.concatenate([a, b])
    return x / max(np.abs(x).max(), 1e-9) * 0.8


def nom():
    """Happy chomp: one crisp crunch plus a short 'mm' hum."""
    c = crunch(0.6)[: int(0.16 * SR)]
    c = c * np.exp(-t_axis(len(c) / SR) / 0.06)
    t = t_axis(0.22)
    hum = (np.sin(2 * np.pi * 230 * t) + 0.4 * np.sin(2 * np.pi * 460 * t)) * np.minimum(t / 0.03, 1) * \
        np.clip((0.22 - t) / 0.08, 0, 1) * 0.1
    n = max(len(c), int(0.1 * SR) + len(hum))
    x = np.zeros(n)
    x[:len(c)] += c / max(np.abs(c).max(), 1e-9) * 0.7
    i = int(0.1 * SR)
    x[i:i + len(hum)] += hum
    return x


# ------------------------------------------------------------- ASMR foley --
def _tick(lo, hi, dur, decay, tone=None):
    t = t_axis(dur)
    x = bp(noise(dur), lo, hi) * np.exp(-t / decay)
    if tone:
        x = x + 0.5 * np.sin(2 * np.pi * tone * t) * np.exp(-t / (decay * 1.5))
    return x


GRAIN = {  # material: (lo, hi, dur, decay, gain)
    "flour": (3500, 12000, 0.012, 0.0025, 0.10),
    "cheese": (900, 5500, 0.03, 0.006, 0.24),
    "herb": (2500, 10000, 0.012, 0.002, 0.16),
}


def grains(items, mat, start, fps, bus):
    lo, hi, d, dec, g = GRAIN[mat]
    for fi, pn in items:
        t = (start + fi - 1) / fps + RNG.uniform(-0.012, 0.012)
        x = _tick(lo * RNG.uniform(0.8, 1.2), hi, d, dec * RNG.uniform(0.7, 1.4))
        bus.add(max(0.0, t), pan(x, pn), g * RNG.uniform(0.35, 1.0))


def _env_from(amps, fps, d):
    a = np.asarray(amps, dtype=float)
    a = a / max(a.max(), 1e-9)
    t = t_axis(d)
    return np.interp(t * fps, np.arange(len(a)), a)


def squish(size=1.0):
    """Paw pressing soft dough: a damp, padded squelch."""
    d = 0.2
    t = t_axis(d)
    x = lp(noise(d), 1100) * np.minimum(t / 0.012, 1) * np.exp(-t / 0.06)
    x += bp(noise(d), 250, 900) * np.exp(-t / 0.035) * 0.8
    x += 0.4 * np.sin(2 * np.pi * (120 - 200 * t) * t) * np.exp(-t / 0.05)
    return x / max(np.abs(x).max(), 1e-9) * 0.8 * size


def pat():
    x = squish(0.8)
    th = thud(0.25, soft=True)
    n = max(len(x), len(th))
    y = np.zeros(n)
    y[:len(x)] += x
    y[:len(th)] += th[:n] / max(np.abs(th).max(), 1e-9) * 0.4
    return y


def smear(amps, fps):
    """Back of a spoon spreading thick sauce: a wet, sticky swish."""
    d = len(amps) / fps + 0.2
    env = _env_from(amps, fps, d)
    x = bp(noise(d), 350, 2600) * env * 0.6
    x += lp(noise(d), 500) * env * 0.4
    t = t_axis(d)
    for tt in t[RNG.uniform(0, 1, len(t)) < env * 0.0012]:
        g = _tick(1500, 6000, 0.008, 0.002)
        i = int(tt * SR)
        x[i:i + len(g)] += g[:max(0, len(x) - i)] * 0.6
    return x * np.clip((d - t) / 0.1, 0, 1)


def plop():
    """A pepperoni slice landing on cheese: soft leathery tap."""
    x = _tick(250, 2200, 0.07, 0.012, tone=190)
    return x / max(np.abs(x).max(), 1e-9) * 0.8


def scrape(amps, fps):
    """Steel peel sliding over oven stone."""
    d = len(amps) / fps + 0.2
    env = _env_from(amps, fps, d)
    x = bp(noise(d), 900, 6500) * env * 0.5 + lp(noise(d), 220) * env * 0.4
    return x


def bubblepop(pitch=1.0):
    d = 0.04
    t = t_axis(d)
    f = pitch * (1100 - 18000 * t).clip(300)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.008)
    x += bp(noise(d), 1500, 6000) * np.exp(-t / 0.003) * 0.4
    return x * 0.6


def roll(amps, fps):
    """Pizza wheel rolling through cheese and crust: gritty, crackly."""
    d = len(amps) / fps + 0.2
    env = _env_from(amps, fps, d)
    x = bp(noise(d), 2200, 8000) * env * 0.35
    t = t_axis(d)
    for tt in t[RNG.uniform(0, 1, len(t)) < env * 0.0025]:
        g = _tick(1800, 7000, 0.01, 0.002)
        i = int(tt * SR)
        x[i:i + len(g)] += g[:max(0, len(x) - i)] * RNG.uniform(0.3, 1.0)
    return x


def stretch(amps, fps):
    """Molten cheese being pulled: a slow, sticky squelch with a creak."""
    d = len(amps) / fps + 0.3
    env = _env_from(amps, fps, d)
    t = t_axis(d)
    x = lp(noise(d), 900) * env * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t))
    f = 140 + 90 * env
    x += 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env
    return x * 0.7


def snap():
    return _tick(1200, 5200, 0.015, 0.004, tone=650) * 0.5


def chew():
    c = crunch(0.45)[: int(0.22 * SR)]
    t = t_axis(len(c) / SR)
    c = c * np.exp(-t / 0.08)
    return c / max(np.abs(c).max(), 1e-9) * 0.6


def riser(dur=1.0):
    t = t_axis(dur)
    x = sweep_bp(noise(dur), 500, 8000) * (t / dur) ** 2
    f = 200 * 2 ** (2.5 * t / dur)
    x += 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 2
    return x * 0.9


def boom():
    d = 2.2
    t = t_axis(d)
    f = 44 * (1 + 1.5 * np.exp(-t * 18))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2) * 1.2
    x += lp(noise(d), 600) * np.exp(-t * 8) * 0.7
    y = np.tanh(x * 1.2)
    cr = crash(0.5)
    y[: len(cr)] += cr[: len(y)]
    return y


def slam(size=0.6):
    d = 0.5
    t = t_axis(d)
    x = np.sin(2 * np.pi * np.cumsum(95 * (1 + np.exp(-t * 30))) / SR) * np.exp(-t * 10)
    x += bp(noise(d), 800, 3500) * np.exp(-t * 30) * 0.5
    return x * size


def swell():
    d = 2.4
    t = t_axis(d)
    x = sweep_bp(noise(d), 300, 6000) * (t / d) ** 2.5 * 0.6
    x += np.sin(2 * np.pi * 55 * t) * np.minimum(t / 1.5, 1) * np.exp(-np.clip(t - 1.8, 0, None) * 6) * 0.4
    return x


# ---------------------------------------------------------------- music ----
CHORDS = {  # (bass midi, chord midi notes)
    "Am9": (45, [57, 60, 64, 67, 71]),
    "Fmaj9": (41, [57, 60, 64, 65, 67]),
    "C6/9": (48, [55, 60, 62, 64, 69]),
    "G13": (43, [55, 59, 62, 64, 65]),
}
PROG = ["Am9", "Fmaj9", "C6/9", "G13"]


def music(total_s, starts):
    beat = 60.0 / C.BPM
    nbeats = int(math.ceil(total_s / beat))
    bus_d, bus_m = Bus(total_s), Bus(total_s)        # drums dry, music (reverb send)
    sec = {k: (v - 1) / C.FPS / beat for k, v in starts.items()}  # shot starts in beats
    b_groove, b_build, b_final = sec[C.MUSIC_GROOVE_FROM], sec[C.MUSIC_BUILD_SHOT], sec[C.MUSIC_FINAL_SHOT]
    order = [k for k, _ in C.SHOTS]
    # intro pad
    bus_m.add(0.0, pan(pad_chord([mtof(m) for m in CHORDS["Am9"][1]], b_groove * beat + 0.4, 1.2), 0), 0.55)
    for b in range(nbeats):
        t = b * beat
        bar, pos = divmod(b - int(b_groove), 4)
        ch = CHORDS[PROG[bar % 4]] if b >= b_groove else CHORDS["Am9"]
        groove = b_groove <= b < b_build or b_final <= b < b_final + 4
        building = b_build <= b < b_final
        if groove:
            bus_d.add(t, pan(kick(0.95), 0))
            if pos in (1, 3):
                bus_d.add(t, pan(snare(0.55), 0.05))
            if pos == 2 and bar % 2 == 1:
                bus_d.add(t + 0.75 * beat, pan(kick(0.6), 0))
            for k in range(2):
                bus_d.add(t + k * beat / 2 + (0.03 if k else 0), pan(hat(open_=(k == 1 and pos == 3), level=0.22 if k else 0.15), 0.3))
            # bass: root on the beat, octave pop on the off-beat
            bus_m.add(t, pan(bass_note(mtof(ch[0]), beat * 0.45, 0.55), 0))
            bus_m.add(t + beat * 0.5, pan(bass_note(mtof(ch[0] + (12 if pos % 2 else 7)), beat * 0.3, 0.35), 0))
            if pos in (0, 2):  # syncopated electric-piano stabs
                for i, m in enumerate(ch[1]):
                    bus_m.add(t + beat * (0.5 if pos == 0 else 0.75) + i * 0.004,
                              pan(ep_note(mtof(m), 0.9, 0.11), -0.3 + 0.15 * i))
            if pos == 0:
                bus_m.add(t, pan(pad_chord([mtof(m) for m in ch[1][:3]], beat * 4, 0.3), 0), 0.25)
        elif building:
            bus_d.add(t, pan(kick(0.8), 0))
            k = (b - b_build) / max(b_final - b_build, 1)
            nsub = 2 if k < 0.5 else 4
            for s in range(nsub):
                bus_d.add(t + s * beat / nsub, pan(snare(0.15 + 0.4 * k), 0.0))
            bus_m.add(t, pan(bass_note(mtof(45), beat * 0.9, 0.45), 0))
    # final chord + stinger
    end_b = b_final + 4
    bus_m.add(end_b * beat, pan(pad_chord([mtof(m) for m in CHORDS["Am9"][1]] + [mtof(76)], 4.0, 0.05), 0), 0.7)
    for i, m in enumerate(CHORDS["Am9"][1] + [76]):
        bus_m.add(end_b * beat + 0.01 * i, pan(ep_note(mtof(m), 2.5, 0.16), -0.3 + 0.12 * i))
    bus_d.add(end_b * beat, pan(kick(1.0), 0))
    bus_d.add(b_final * beat, pan(crash(0.55), 0.2))
    mus = reverb(bus_m.x, 0.3) + reverb(bus_d.x, 0.08)
    # duck music under the loudest cooking sounds
    tt = np.arange(len(mus)) / SR
    duck = np.ones(len(mus))
    for shot, amt in C.MUSIC_DUCK.items():
        i = order.index(shot)
        t0 = sec[shot] * beat
        t1 = sec[order[i + 1]] * beat if i + 1 < len(order) else total_s
        duck *= 1 - amt * np.clip((tt - t0) / 0.3, 0, 1) * np.clip((t1 - tt) / 0.3, 0, 1)
    return mus * duck[:, None]


# ----------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=os.path.join(ROOT, "out", "timeline.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "soundtrack.wav"))
    a = ap.parse_args()
    tl = json.load(open(a.timeline))
    total = tl["total"] / tl["fps"]
    starts = {s["name"]: s["start"] for s in tl["shots"]}
    sfx = Bus(total)
    for s in tl["shots"]:
        end_s = (s["start"] + s["n"] - 1) / tl["fps"]
        for c in s["cues"]:
            t = (s["start"] + c["f"] - 1) / tl["fps"]
            k = c["kind"]
            g = 1.0
            if k == "whoosh":
                st = whoosh(c.get("dur", 0.4), c.get("up", False), c.get("pitch", 1.0)); g = 0.55
            elif k == "tick":
                st = pan(tick(), 0); g = 0.5
            elif k == "pop":
                st = pan(pop(c.get("pitch", 1.0)), RNG.uniform(-0.4, 0.4)); g = 0.45
            elif k == "thud":
                st = pan(thud(c.get("size", 0.6), c.get("soft", False)), 0); g = 0.9
            elif k == "crunch":
                st = pan(crunch(c.get("size", 1.0)), 0); g = 0.9
            elif k == "shake":
                st = pan(shake(), 0.3); g = 0.9
            elif k == "splash":
                st = pan(splash(c.get("size", 1.0)), 0); g = 0.75
            elif k == "drip":
                st = pan(drip(), RNG.uniform(-0.3, 0.3)); g = 0.6
            elif k == "puff":
                st = pan(puff(c.get("size", 1.0)), 0); g = 0.8
            elif k == "sprinkle":
                st = pan(sprinkle(c.get("dur", 0.5)), 0); g = 0.8
            elif k == "clack":
                st = pan(clack(), 0.4); g = 0.7
            elif k == "squeeze":
                st = pan(squeeze(c.get("dur", 0.7)), 0); g = 0.9
            elif k == "sizzle_start":
                st = pan(sizzle(end_s - t + 1 / tl["fps"]), 0); g = 0.75
            elif k == "sizzle_soft":
                st = pan(sizzle(c.get("dur", 3.0), onset=False, level=0.25), 0); g = 0.6
            elif k == "riser":
                st = pan(riser(c.get("dur", 1.0)), 0); g = 0.5
            elif k == "boom":
                st = pan(boom(), 0); g = 0.75
            elif k == "slam":
                st = pan(slam(c.get("size", 0.6)), 0); g = 0.7
            elif k == "swell":
                st = pan(swell(), 0); g = 0.6
            elif k == "boil":
                st = pan(boil(c.get("dur", 3.0)), 0); g = 0.55
            elif k == "simmer":
                st = pan(simmer(c.get("dur", 3.0), c.get("level", 1.0)), 0); g = 0.6
            elif k == "pour":
                st = pan(pour(c.get("dur", 1.0)), -0.2); g = 0.7
            elif k == "splat":
                st = pan(splat(), 0); g = 0.8
            elif k == "clatter":
                st = pan(clatter(), 0.2); g = 0.6
            elif k == "hiss":
                st = pan(hiss(c.get("dur", 1.4)), 0); g = 0.7
            elif k == "stir":
                st = pan(stir(c.get("dur", 1.3)), 0.15); g = 0.6
            elif k == "crackle":
                st = pan(crackle(c.get("dur", 3.0)), -0.15); g = 0.7
            elif k == "grains":
                grains(c["items"], c.get("mat", "cheese"), s["start"], tl["fps"], sfx)
                continue
            elif k == "squish":
                st = pan(squish(c.get("size", 1.0)), 0); g = 0.9
            elif k == "pat":
                st = pan(pat(), 0); g = 0.9
            elif k == "smear":
                st = pan(smear(c["amps"], tl["fps"]), 0); g = 0.75
            elif k == "plop":
                st = pan(plop(), 0); g = 0.85
            elif k == "scrape":
                st = pan(scrape(c["amps"], tl["fps"]), 0); g = 0.55
            elif k == "bubblepop":
                st = pan(bubblepop(c.get("pitch", 1.0)), 0); g = 0.35
            elif k == "roll":
                st = pan(roll(c["amps"], tl["fps"]), 0); g = 0.7
            elif k == "stretch":
                st = pan(stretch(c["amps"], tl["fps"]), 0); g = 0.7
            elif k == "snap":
                st = pan(snap(), 0); g = 0.3
            elif k == "chew":
                st = pan(chew(), 0); g = 1.3
            elif k == "meow":
                st = pan(meow(c.get("pitch", 1.0)), 0.05); g = 0.75
            elif k == "purr":
                st = pan(purr(c.get("dur", 2.0)), 0); g = 0.55
            elif k == "sneeze":
                st = pan(sneeze(), 0.05); g = 0.7
            elif k == "nom":
                st = pan(nom(), 0); g = 0.8
            else:
                continue
            if "pan" in c:
                mono = st.mean(axis=1) * 1.414 if st.ndim == 2 else st
                st = pan(mono, c["pan"])
            sfx.add(t, st, g * c.get("gain", 1.0))
    if getattr(C, "MUSIC", True):
        mus = music(total, starts)
        n = min(len(mus), len(sfx.x))
        mix = 0.5 * mus[:n] + 0.85 * reverb(sfx.x[:n], 0.12)
    else:
        # ASMR: dry, close foley with a little air, a faint room tone and a
        # presence lift so every tick and squish reads
        n = len(sfx.x)
        dry = sfx.x[:n]
        mix = reverb(dry, 0.05) + 0.35 * hp(dry.T, 4000).T
        room = lp(noise(n / SR), 3000) * 0.0025
        mix = mix + np.stack([room, np.roll(room, 2400)], 1)[:n]
    mix = hp(mix.T, 28).T
    L = int(total * SR)
    mix = mix[:L]
    fade = np.ones(L)
    fade[-int(0.25 * SR):] = np.linspace(1, 0, int(0.25 * SR))
    mix *= fade[:, None]
    rms = np.sqrt((mix ** 2).mean())
    mix *= 0.14 / max(rms, 1e-9)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix *= 0.84 / max(np.abs(mix).max(), 1e-9)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    wavfile.write(a.out, SR, (mix * 32767).astype(np.int16))
    print(f"[audio] wrote {a.out} ({total:.2f}s)")


if __name__ == "__main__":
    main()
