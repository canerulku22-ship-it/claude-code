"""Procedural sound design + music, synchronised to the animation cue sheet.

Everything is synthesised (no samples): a 120 BPM funk/house groove whose
bars line up with the cuts, plus foley built from filtered noise and
oscillators -- searing sizzle, spice-shaker rattles, a rolling boil, sauce
pouring and simmering 'blups', splashes, wet splats, dry pasta clatter,
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
            else:
                continue
            sfx.add(t, st, g)
    mus = music(total, starts)
    n = min(len(mus), len(sfx.x))
    mix = 0.5 * mus[:n] + 0.85 * reverb(sfx.x[:n], 0.12)
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
