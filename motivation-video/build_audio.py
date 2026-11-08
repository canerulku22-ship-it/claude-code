#!/usr/bin/env python3
"""Builds the voiceover, music and sound design for "Same Position. Different Level."

Outputs (in ./build):
  timeline.json   - when every voice line, beat and impact happens (drives the visuals)
  voiceover.wav   - processed voice only
  music_sfx.wav   - music + sound effects only
  mix.wav         - final stereo mix (before loudness normalisation)

Voice: Kokoro TTS (open-source, runs locally). Set KOKORO_MODELS to the folder holding
kokoro-v1.0.onnx and voices-v1.0.bin (github.com/thewh1teagle/kokoro-onnx releases).
Everything else is synthesised from scratch with numpy/scipy, so there are no licensing
questions about the music or the effects.
"""
import json
import os

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")
MODELS = os.environ.get("KOKORO_MODELS", os.path.join(HERE, "models"))
os.makedirs(OUT, exist_ok=True)

SR = 48000
BPM = 120
BEAT = 60 / BPM
STEP = BEAT / 4  # 16th note
rng = np.random.default_rng(7)

VOICE_BLEND = {"am_michael": 0.7, "am_onyx": 0.3}
SPEED = 0.96

# (id, line, pause before it in seconds)
SCRIPT = [
    ("hook", "You feel stuck.", 0.30),
    ("same1", "Same room.", 0.35),
    ("same2", "Same routine.", 0.10),
    ("same3", "Same view.", 0.10),
    ("run", "Like you've been running for months...", 0.35),
    ("nowhere", "and going nowhere.", 0.05),
    ("but", "But here's the thing.", 0.70),
    ("above", "Look at a spiral staircase from above,", 0.45),
    ("circles", "and it looks like you're walking in circles.", 0.05),
    ("spot", "Same spot.", 0.30),
    ("lap", "Every single lap.", 0.10),
    ("side", "Now look from the side.", 0.40),
    ("higher", "Every lap... you're higher.", 0.30),
    ("punch1", "Same position.", 0.45),
    ("punch2", "Different level.", 0.45),
    ("xp1", "Every rep nobody saw.", 0.55),
    ("xp1x", "That's XP.", 0.08),
    ("xp2", "Every early morning you didn't feel like it.", 0.25),
    ("xp2x", "XP.", 0.08),
    ("xp3", "Every rejection that stung.", 0.25),
    ("xp3x", "XP.", 0.08),
    ("notstuck", "You're not stuck.", 0.45),
    ("loading", "You're loading.", 0.10),
    ("climb", "So keep climbing.", 0.40),
    ("lookdown", "Because one day, you'll look down,", 0.55),
    ("recognize", "and you won't even recognize where you started.", 0.05),
    ("levelup", "Level up.", 0.70),
]
TAIL = 3.0
# lines after the drop snap to the 8th-note grid so the slams land on the beat
QUANTIZE = {"xp1", "xp1x", "xp2", "xp2x", "xp3", "xp3x", "notstuck", "loading", "climb"}


# ----------------------------------------------------------------------------- helpers
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tarr(n):
    return np.arange(n) / SR


def nsamp(sec):
    return max(1, int(round(sec * SR)))


def place(buf, x, t, gain=1.0, pan=0.0):
    """Add mono or stereo x into stereo buf at time t (seconds)."""
    i = int(round(t * SR))
    if i >= len(buf):
        return
    if x.ndim == 1:
        a = np.pi / 4 * (pan + 1)
        x = np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(buf) - i)
    buf[i : i + n] += x[:n] * gain


def sos_lp(fc, order=2):
    return signal.butter(order, min(fc, SR / 2 * 0.95), "low", fs=SR, output="sos")


def sos_hp(fc, order=2):
    return signal.butter(order, fc, "high", fs=SR, output="sos")


def sos_bp(lo, hi, order=2):
    return signal.butter(order, [lo, min(hi, SR / 2 * 0.95)], "band", fs=SR, output="sos")


def filt(sos, x):
    return signal.sosfilt(sos, x, axis=0)


def biquad(kind, f0, gain_db=0.0, q=0.707):
    """RBJ cookbook peaking / shelving filters as an sos row."""
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    cw, sw = np.cos(w), np.sin(w)
    alpha = sw / (2 * q)
    if kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "lowshelf":
        s = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + s), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - s)]
        a = [(A + 1) + (A - 1) * cw + s, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - s]
    else:  # highshelf
        s = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + s), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - s)]
        a = [(A + 1) - (A - 1) * cw + s, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - s]
    b, a = np.array(b) / a[0], np.array(a) / a[0]
    return np.array([[*b, *a]])


def sweep(x, f0, f1, kind="band", width=1.5, block=256, curve="exp"):
    """Time-varying filter: cutoff/centre moves from f0 to f1 over the length of x."""
    y = np.zeros_like(x)
    nb = int(np.ceil(len(x) / block))
    zi = None
    for b in range(nb):
        u = b / max(1, nb - 1)
        fc = f0 * (f1 / f0) ** u if curve == "exp" else f0 + (f1 - f0) * u
        if kind == "band":
            sos = sos_bp(max(20, fc / width), fc * width)
        elif kind == "low":
            sos = sos_lp(fc)
        else:
            sos = sos_hp(fc)
        if zi is None:
            zi = np.zeros((sos.shape[0], 2) + x.shape[1:])
        seg = x[b * block : (b + 1) * block]
        y[b * block : (b + 1) * block], zi = signal.sosfilt(sos, seg, axis=0, zi=zi)
    return y


TABLE_N = 4096


def _table(harmonics):
    ph = np.arange(TABLE_N) / TABLE_N * 2 * np.pi
    t = sum(np.sin(h * ph) * amp for h, amp in harmonics)
    return t / np.max(np.abs(t))


SAW = _table([(h, 1 / h) for h in range(1, 40)])
SQR = _table([(h, 1 / h) for h in range(1, 40, 2)])
TRI = _table([(h, (1 if (h // 2) % 2 == 0 else -1) / h**2) for h in range(1, 30, 2)])


def osc(freq, n, table=SAW, phase=None):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    ph = np.cumsum(f) / SR + (rng.random() if phase is None else phase)
    return table[((ph * TABLE_N) % TABLE_N).astype(int)]


def make_ir(sec, decay, seed=1, lp=7000):
    n = nsamp(sec)
    t = tarr(n)
    r = np.random.default_rng(seed)
    ir = r.standard_normal((n, 2)) * np.exp(-t / decay)[:, None]
    ir = filt(sos_lp(lp), ir)
    ir[: nsamp(0.008)] = 0
    return ir / np.sqrt(np.sum(ir**2) / 2)


def reverb(x, ir, wet):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    w = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet * 0.3) + w * wet


def pingpong(x, delay, fb=0.45, taps=5, tone=4000):
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    y = x.copy()
    d = nsamp(delay)
    src = filt(sos_lp(tone), x.mean(1))
    for k in range(1, taps + 1):
        g = fb**k
        ch = k % 2
        if d * k < len(x):
            y[d * k :, ch] += src[: len(x) - d * k] * g
    return y


def norm(x, peak=1.0):
    m = np.max(np.abs(x))
    return x if m == 0 else x / m * peak


# ----------------------------------------------------------------------------- voice
def build_voice():
    from kokoro_onnx import Kokoro

    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    style = sum(k.get_voice_style(v) * w for v, w in VOICE_BLEND.items())
    clips = {}
    for cid, text, _ in SCRIPT:
        audio, sr = k.create(text, voice=style, speed=SPEED, lang="en-us")
        audio = signal.resample_poly(audio.astype(np.float64), SR, sr)
        # trim leading/trailing silence
        env = np.abs(audio)
        thr = np.max(env) * 10 ** (-42 / 20)
        idx = np.where(env > thr)[0]
        a = max(0, idx[0] - nsamp(0.015))
        b = min(len(audio), idx[-1] + nsamp(0.06))
        audio = audio[a:b]
        fade = nsamp(0.01)
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)
        clips[cid] = audio
    return clips


def layout(clips):
    t = 0.0
    lines = {}
    anchor = None
    for cid, text, gap in SCRIPT:
        start = t + gap
        if cid in QUANTIZE and anchor is not None:
            g = BEAT / 2
            start = anchor + np.ceil((start - anchor) / g - 1e-6) * g
        dur = len(clips[cid]) / SR
        lines[cid] = {"text": text, "start": round(start, 4), "end": round(start + dur, 4)}
        if cid == "punch2":
            anchor = start
        t = start + dur
    return lines, t + TAIL


def process_voice(v):
    v = filt(sos_hp(75), v)
    v = signal.sosfilt(biquad("lowshelf", 160, 2.5), v)
    v = signal.sosfilt(biquad("peak", 350, -2.0, 1.0), v)
    v = signal.sosfilt(biquad("peak", 3200, 3.5, 0.9), v)
    v = signal.sosfilt(biquad("highshelf", 9000, 2.0), v)
    # simple feed-forward compressor
    lvl = np.maximum(signal.sosfilt(sos_lp(25), np.abs(v)), 1e-9)
    db = 20 * np.log10(lvl / np.max(lvl))
    thr, ratio = -20.0, 3.0
    gain_db = np.where(db > thr, (thr - db) * (1 - 1 / ratio), 0.0)
    v = v * 10 ** (gain_db / 20)
    v = norm(v, 0.9)
    return v


# ----------------------------------------------------------------------------- drums & instruments
def kick(dur=0.5, f0=170, f1=44, drive=1.8):
    n = nsamp(dur)
    t = tarr(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.17)
    x += rng.standard_normal(n) * np.exp(-t / 0.002) * 0.4
    return np.tanh(x * drive) * 0.95


def sub808(freq, dur=0.9):
    n = nsamp(dur)
    t = tarr(n)
    f = freq * (1 + 0.5 * np.exp(-t / 0.02))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    x *= np.minimum(1, t / 0.004)
    return np.tanh(x * 2.2) * 0.8


def clap():
    n = nsamp(0.35)
    t = tarr(n)
    noise = filt(sos_bp(900, 3500), rng.standard_normal(n))
    e = np.zeros(n)
    for off in (0, 0.011, 0.022):
        tt = t - off
        e += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) / 0.007), 0) * 0.6
    tt = t - 0.03
    e += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) / 0.11), 0)
    return norm(noise * e, 0.8)


def snare(tone=200, dur=0.25):
    n = nsamp(dur)
    t = tarr(n)
    x = filt(sos_bp(1200, 9000), rng.standard_normal(n)) * np.exp(-t / 0.09)
    x += np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.05) * 0.7
    return norm(x, 0.8)


def hat(open_=False):
    n = nsamp(0.3 if open_ else 0.06)
    t = tarr(n)
    x = filt(sos_hp(7500), rng.standard_normal(n)) * np.exp(-t / (0.12 if open_ else 0.018))
    return norm(x, 0.5)


def supersaw(midis, dur, voices=5, spread=14, attack=0.02, release=0.3, lp=3800):
    n = nsamp(dur + release)
    out = np.zeros((n, 2))
    for m in midis:
        for v in range(voices):
            cents = (v - (voices - 1) / 2) / ((voices - 1) / 2) * spread if voices > 1 else 0
            f = mtof(m) * 2 ** (cents / 1200)
            pan = (v / (voices - 1) * 2 - 1) * 0.8 if voices > 1 else 0
            x = osc(f, n)
            a = np.pi / 4 * (pan + 1)
            out[:, 0] += x * np.cos(a)
            out[:, 1] += x * np.sin(a)
    t = tarr(n)
    env = np.minimum(1, t / attack) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (release / 4)))
    out *= env[:, None]
    out = filt(sos_lp(lp), out)
    return out / (len(midis) * voices) * 2.2


def pluck(freq, dur=0.5, bright=0.05, body=0.25, table=SAW):
    n = nsamp(dur)
    t = tarr(n)
    x = osc(freq, n, table) * np.exp(-t / bright) + osc(freq, n, TRI) * np.exp(-t / body) * 0.8
    x *= np.minimum(1, t / 0.002)
    return x * 0.6


def bell(freq, dur=2.0):
    n = nsamp(dur)
    t = tarr(n)
    x = np.zeros(n)
    for ratio, amp, tau in ((1, 1, 0.9), (2.76, 0.45, 0.4), (5.4, 0.25, 0.18), (8.93, 0.12, 0.1)):
        x += np.sin(2 * np.pi * freq * ratio * t) * amp * np.exp(-t / tau)
    return x * np.minimum(1, t / 0.002) * 0.5


def boom(dur=3.0, f0=90, f1=27):
    n = nsamp(dur)
    t = tarr(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.18)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    x += filt(sos_lp(900), rng.standard_normal(n)) * np.exp(-t / 0.22) * 0.9
    x += rng.standard_normal(n) * np.exp(-t / 0.004) * 0.5
    return np.tanh(x * 1.7) * 0.9


def whoosh(dur=0.55, f0=500, f1=5000, peak=0.6):
    n = nsamp(dur)
    t = np.linspace(0, 1, n)
    x = sweep(rng.standard_normal((n, 2)), f0, f1, "band", width=1.6)
    env = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.5)
    return norm(x * env[:, None], 0.8)


def riser(dur, f0=250, f1=9000):
    n = nsamp(dur)
    u = np.linspace(0, 1, n)
    x = sweep(rng.standard_normal((n, 2)), f0, f1, "band", width=1.8) * (u**2.2)[:, None]
    glide = mtof(45) * 2 ** (u * 24 / 12)
    s = osc(glide, n) * (u**2) * 0.35
    s = filt(sos_lp(5000), s)
    x[:, 0] += s
    x[:, 1] += s
    return norm(x, 0.8)


def rev_cymbal(dur=1.2):
    n = nsamp(dur)
    u = np.linspace(0, 1, n)
    x = filt(sos_hp(3500), rng.standard_normal((n, 2))) * (np.exp(u * 5) - 1)[:, None] / (np.e**5 - 1)
    return norm(x, 0.7)


def ping(freq=1567.98, dur=1.4):
    n = nsamp(dur)
    t = tarr(n)
    x = (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2.01 * t)) * np.exp(-t / 0.35)
    return x * np.minimum(1, t / 0.002) * 0.6


def blip(freq, dur=0.07, table=SQR):
    n = nsamp(dur)
    t = tarr(n)
    return osc(freq, n, table, 0) * np.exp(-t / (dur / 3)) * np.minimum(1, t / 0.001) * 0.4


def coin():
    a = blip(mtof(83), 0.08)
    b = blip(mtof(88), 0.45)
    out = np.zeros(len(a) + len(b))
    out[: len(a)] += a
    out[len(a) - nsamp(0.01) : len(a) - nsamp(0.01) + len(b)] += b
    return out


def glitch(dur=0.35):
    n = nsamp(dur)
    out = np.zeros(n)
    i = 0
    while i < n:
        seg = nsamp(rng.uniform(0.012, 0.04))
        kind = rng.integers(0, 4)
        m = min(seg, n - i)
        if kind == 0:
            out[i : i + m] = rng.standard_normal(m) * 0.5
        elif kind == 1:
            out[i : i + m] = osc(rng.uniform(150, 2500), m, SQR) * 0.4
        elif kind == 2:
            out[i : i + m] = np.round(rng.standard_normal(m) * 3) / 6
        i += seg
    return filt(sos_hp(120), out)


def tick(hi=True):
    n = nsamp(0.04)
    t = tarr(n)
    f = 3100 if hi else 2200
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.004) + rng.standard_normal(n) * np.exp(-t / 0.0015) * 0.3) * 0.5


def heartbeat():
    def thump(amp):
        n = nsamp(0.35)
        t = tarr(n)
        f = 48 + 40 * np.exp(-t / 0.03)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09) * amp

    a = thump(1.0)
    b = thump(0.7)
    out = np.zeros(nsamp(0.65))
    out[: len(a)] += a
    o = nsamp(0.24)
    out[o : o + len(b)] += b
    return np.tanh(out * 1.5)


def tape_stop(buf, t_end, dur=0.55):
    """Slow the bus down to a halt, ending at t_end; silence after."""
    i0, i1 = nsamp(t_end - dur), nsamp(t_end)
    n = i1 - i0
    u = np.linspace(0, 1, n)
    rate = (1 - u) ** 1.6
    pos = i0 + np.cumsum(rate)
    for c in range(2):
        buf[i0:i1, c] = np.interp(pos, np.arange(len(buf)), buf[:, c]) * (1 - u**4)
    buf[i1:] = 0


# ----------------------------------------------------------------------------- arrangement
def build_music(L, total):
    N = nsamp(total)
    drums = np.zeros((N, 2))
    bass = np.zeros((N, 2))
    pads = np.zeros((N, 2))
    leads = np.zeros((N, 2))
    sfx = np.zeros((N, 2))
    events = {"beats": [], "impacts": [], "ticks": []}

    def S(cid):
        return L[cid]["start"]

    def E(cid):
        return L[cid]["end"]

    # ---- A: stuck. heartbeat + clock tick + dark drone ----------------------------------
    a0, a1 = 0.0, S("but")
    t = 0.0
    k = 0
    while t < a1 - 0.05:
        place(drums, tick(k % 2 == 0), t, 0.32, pan=0.35 if k % 2 == 0 else -0.35)
        events["ticks"].append(round(t, 4))
        if k % 2 == 0:
            place(drums, heartbeat(), t, 0.9)
            events["beats"].append(round(t, 4))
        t += BEAT
        k += 1
    n = nsamp(a1 - a0)
    tt = tarr(n)
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * tt)
    drone = osc(mtof(33), n) + osc(mtof(40) * 1.003, n) * 0.6 + osc(mtof(45) * 0.998, n) * 0.4
    drone = sweep(drone, 180, 700, "low")
    drone *= (0.55 + 0.45 * lfo) * np.minimum(1, tt / 0.4)
    place(pads, drone, a0, 0.32)

    # ---- B: but. tape stop on everything, then silence ----------------------------------
    # (applied after summing section A, see below)

    # ---- C: spiral from above. circling arpeggio + soft pad ------------------------------
    c0, c1 = S("above") - 0.1, S("side")
    arp_notes = [69, 72, 76, 79, 81, 79, 76, 72]  # A C E G A G E C : a loop that goes round
    t = c0
    k = 0
    while t < c1 + BEAT * 2:
        fade = min(1, (t - c0) / 1.0)
        place(leads, pluck(mtof(arp_notes[k % 8]), 0.45, 0.04, 0.2, TRI), t, 0.24 * fade, pan=np.sin(k * 0.785) * 0.6)
        t += BEAT / 2
        k += 1
    place(pads, supersaw([57, 60, 64], c1 - c0 + 0.3, voices=4, spread=10, attack=0.8, release=1.0, lp=1800), c0, 0.28)
    place(bass, sub808(mtof(33), c1 - c0) * np.linspace(1, 0.6, nsamp(c1 - c0)), c0, 0.35)

    # ---- D: side reveal build. snare roll + riser, chords VI -> VII ----------------------
    d0, d1 = S("side"), S("punch1")
    place(sfx, riser(d1 - d0 + 0.05), d0, 0.36)
    t = d0
    while t < d1 - 0.02:
        u = (t - d0) / (d1 - d0)
        place(drums, snare(170 + 160 * u, 0.2), t, 0.1 + 0.4 * u**2, pan=rng.uniform(-0.2, 0.2))
        t += BEAT if u < 0.3 else BEAT / 2 if u < 0.6 else BEAT / 4 if u < 0.85 else BEAT / 8
    mid = d0 + (d1 - d0) / 2
    place(pads, supersaw([53, 57, 60, 65], mid - d0, attack=0.3, release=0.2, lp=2500), d0, 0.32)
    place(pads, supersaw([55, 59, 62, 67], d1 - mid, attack=0.05, release=0.15, lp=3500), mid, 0.36)
    for tb in np.arange(d0, d1 - 0.1, BEAT):
        place(drums, kick(0.4, 150, 48, 1.4), tb, 0.55)

    # pre-drop: near silence + reverse cymbal into the drop
    drop = S("punch2")
    place(sfx, rev_cymbal(drop - S("punch1") + 0.05), S("punch1") - 0.05, 0.4)

    # ---- E: DROP -------------------------------------------------------------------------
    e0, e1 = drop, S("lookdown") - 0.05
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60, 64], [55, 59, 62, 67]]
    roots = [33, 29, 36, 31]
    arp_shapes = [0, 1, 2, 3, 2, 1, 2, 3]
    kicks = []
    bar = 0
    tb = e0
    while tb < e1 - 0.01:
        ci = bar % 4
        bar_len = min(BEAT * 4, e1 - tb)
        place(pads, supersaw(chords[ci], bar_len, attack=0.01, release=0.25, lp=4200), tb, 0.42)
        for s in range(16):
            ts = tb + s * STEP
            if ts >= e1 - 0.01:
                break
            if s in (0, 4, 8, 12):
                place(drums, kick(), ts, 0.9)
                kicks.append(ts)
                events["beats"].append(round(ts, 4))
            if s in (4, 12):
                place(drums, clap(), ts, 0.5)
            if s % 2 == 0:
                place(drums, hat(), ts + 0.004, 0.22 if s % 4 else 0.12, pan=0.25)
            if s == 14:
                place(drums, hat(True), ts, 0.18, pan=-0.2)
            if bar % 2 == 1 and s >= 13:
                place(drums, hat(), ts + STEP / 2, 0.14, pan=0.25)
            if s in (0, 3, 6, 10, 11):
                place(bass, sub808(mtof(roots[ci] + (12 if s == 11 else 0)), 0.45 if s else 0.9), ts, 0.62)
            note = chords[ci][arp_shapes[s % 8] % len(chords[ci])] + 12
            place(leads, pluck(mtof(note), 0.3, 0.035, 0.12), ts, 0.16, pan=0.4 if s % 2 else -0.4)
        tb += BEAT * 4
        bar += 1

    # "you're loading": filter the drop down then let it open back up for "keep climbing"
    f0_, f1_ = S("notstuck") - 0.1, S("climb")

    # ---- F: breakdown (look down / where you started) --------------------------------------
    f0 = S("lookdown")
    f1 = S("levelup")
    place(pads, supersaw([45, 57, 60, 64], f1 - f0 - 0.25, voices=6, spread=18, attack=0.6, release=0.6, lp=1600), f0, 0.4)
    place(bass, sub808(mtof(33), f1 - f0), f0, 0.4)
    melody = [(0.0, 76), (0.75, 74), (1.5, 72), (2.25, 71), (3.0, 69)]
    for off, m in melody:
        if f0 + off < f1 - 0.4:
            place(leads, bell(mtof(m), 2.0), f0 + off, 0.25, pan=0.2)
    place(sfx, rev_cymbal(1.0), f1 - 1.0, 0.3)

    # ---- G: LEVEL UP ------------------------------------------------------------------------
    g0 = E("levelup") + 0.08  # hit lands right after the words
    place(sfx, riser(g0 - f1 + 0.02), f1, 0.25)
    fan = [69, 73, 76, 81, 85, 88, 93]
    for i, m in enumerate(fan):
        place(leads, blip(mtof(m), 0.16, SQR), g0 + 0.05 + i * 0.055, 0.22, pan=(i - 3) * 0.15)
    place(leads, pluck(mtof(81), 2.0, 0.3, 1.2, SQR), g0 + 0.05 + 7 * 0.055, 0.25)
    place(pads, supersaw([57, 61, 64, 69, 73], total - g0 - 0.5, voices=7, spread=20, attack=0.02, release=1.4, lp=5200), g0, 0.48)
    place(bass, sub808(mtof(33), 3.0), g0, 0.7)
    place(drums, kick(0.8, 180, 40, 2.2), g0, 1.0)
    for i in range(10):
        place(leads, ping(mtof(rng.choice([93, 97, 100, 105])), 1.0), g0 + 0.4 + i * 0.13, 0.06, pan=rng.uniform(-0.8, 0.8))
    events["beats"].append(round(g0, 4))

    # ---- sound design keyed to the lines -------------------------------------------------
    def impact(t, strength, sound=True, gain=0.55):
        if sound:
            place(sfx, boom(2.5), t, gain)
        events["impacts"].append([round(t, 4), strength])

    place(sfx, glitch(0.3), 0.0, 0.35)
    impact(S("hook"), 0.7, True, 0.32)
    for cid in ("same1", "same2", "same3"):
        place(sfx, kick(0.35, 120, 50, 2.5), S(cid), 0.5)
        place(sfx, whoosh(0.25, 2000, 600, 0.2), S(cid) - 0.18, 0.25)
        impact(S(cid), 0.45, False)
    place(sfx, whoosh(0.6, 400, 3000), S("run") - 0.3, 0.3)
    # progress bar resets: descending error blips (visual resets use the same times)
    resets = [S("run") + 1.15, E("nowhere") - 0.05]
    for rt in resets:
        place(sfx, blip(mtof(64), 0.08), rt, 0.25)
        place(sfx, blip(mtof(58), 0.18), rt + 0.08, 0.25)
    events["resets"] = [round(x, 4) for x in resets]
    events["tapestop"] = round(S("but"), 4)
    place(sfx, whoosh(0.5, 3000, 300, 0.15), S("but") - 0.45, 0.25)
    place(sfx, sub808(mtof(28), 1.4), S("but"), 0.3)
    place(sfx, whoosh(0.8, 300, 2500), S("above") - 0.35, 0.3)

    # laps of the spiral: one ping each time the dot passes the pin
    lap_period = 1.25
    lap0 = S("above") + 0.4
    events["lap_period"] = lap_period
    events["lap0"] = round(lap0, 4)
    tl = lap0 + lap_period
    while tl < S("side") + 0.6:
        place(sfx, ping(), tl, 0.22, pan=0.3)
        tl += lap_period

    place(sfx, whoosh(1.2, 200, 6000, 0.7), S("side") - 0.1, 0.35)
    for i in range(6):
        tl = S("higher") + i * 0.42
        if tl < S("punch1") - 0.1:
            place(sfx, blip(mtof(76 + i * 2), 0.1, SQR), tl, 0.16)

    impact(S("punch1"), 0.35, False)
    place(sfx, whoosh(0.4, 4000, 800, 0.3), S("punch1") - 0.15, 0.25)
    impact(drop, 1.0, True, 0.6)

    for x, xx, amt in (("xp1", "xp1x", 0), ("xp2", "xp2x", 1), ("xp3", "xp3x", 2)):
        place(sfx, whoosh(0.35, 800, 5000, 0.8), S(x) - 0.3, 0.3, pan=0.5)
        impact(S(x), 0.35, False)
        place(sfx, coin(), S(xx) + 0.05, 0.28)
        for j in range(4 + amt * 2):
            place(sfx, blip(mtof(84 + (j % 5) * 2), 0.05), S(xx) + 0.25 + j * 0.05, 0.08)
        impact(S(xx), 0.55, False)

    place(sfx, glitch(0.4), S("notstuck") + 0.35, 0.16)
    impact(S("notstuck"), 0.4, False)
    # loading blips accelerating up to a ding at 100%
    l0, l1 = S("loading"), E("loading") + 0.25
    events["load_done"] = round(l1, 4)
    k = 0
    tl = l0
    while tl < l1 - 0.02:
        u = (tl - l0) / (l1 - l0)
        place(sfx, blip(mtof(72 + int(u * 14)), 0.04, TRI), tl, 0.12)
        tl += 0.09 * (1 - u * 0.7)
        k += 1
    place(sfx, bell(mtof(88), 1.5), l1, 0.3)
    impact(l1, 0.5, False)

    for i in range(8):
        place(sfx, blip(mtof(69 + i * 2), 0.06, TRI), S("climb") + i * BEAT / 2, 0.07)
    place(sfx, whoosh(1.4, 6000, 150, 0.25), S("lookdown") - 0.2, 0.35)
    impact(S("lookdown"), 0.6, True, 0.38)
    place(sfx, riser(f1 - S("recognize")), S("recognize"), 0.18)
    impact(g0, 1.0, True, 0.8)
    events["levelup"] = round(g0, 4)

    # ---- mix the music bus -------------------------------------------------------------
    ir_big = make_ir(2.8, 0.75, seed=3)
    ir_mid = make_ir(1.6, 0.4, seed=5)
    leads = pingpong(leads, BEAT * 0.75, 0.35, 4)
    leads = reverb(leads, ir_big, 0.35)
    pads = reverb(pads, ir_big, 0.3)
    drums = reverb(drums, ir_mid, 0.12)
    # sidechain pump on pads/leads/bass in the drop
    gain = np.ones(N)
    if kicks:
        tt = tarr(N)
        kt = np.array(kicks)
        idx = np.searchsorted(kt, tt, side="right") - 1
        valid = idx >= 0
        since = np.where(valid, tt - kt[np.clip(idx, 0, None)], 10)
        gain = 1 - 0.55 * np.exp(-since / 0.13) * (since < 0.5)
    pads *= gain[:, None]
    leads *= (0.5 + 0.5 * gain)[:, None]
    music = drums + bass + pads + leads

    # filter dip for "you're not stuck / you're loading"
    i0, i1 = nsamp(f0_), nsamp(f1_)
    seg = music[i0:i1]
    half = len(seg) // 2
    seg[:half] = sweep(seg[:half].copy(), 18000, 500, "low")
    seg[half:] = sweep(seg[half:].copy(), 500, 18000, "low")
    music[i0:i1] = seg

    # tape stop at "But", silence until the spiral starts
    stop_buf = music.copy()
    tape_stop(stop_buf, S("but") - 0.05, 0.6)
    j = nsamp(S("above") - 0.15)
    music[:j] = stop_buf[:j]

    sfx = reverb(sfx, ir_mid, 0.18)
    return music, sfx, events


def master(src, dst, lufs=-14.0, tp=-1.0):
    """Two-pass EBU R128 loudness normalisation (social platforms play back around -14 LUFS)."""
    import subprocess

    af = f"loudnorm=I={lufs}:TP={tp}:LRA=11"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", af + ":print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):])
    af2 = (f"{af}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", af2, "-ar", str(SR), "-c:a", "pcm_s24le", dst],
                   check=True)


def main():
    clips = build_voice()
    lines, total = layout(clips)
    N = nsamp(total)
    vo = np.zeros(N)
    for cid, info in lines.items():
        c = clips[cid]
        i = nsamp(info["start"])
        vo[i : i + len(c)] += c[: N - i]
    vo = process_voice(vo)
    vo_st = reverb(vo, make_ir(1.2, 0.25, seed=9, lp=5000), 0.12)

    music, sfx, events = build_music(lines, total)

    # duck music under the voice
    env = signal.sosfilt(sos_lp(6), np.abs(vo))
    env = env / (np.max(env) + 1e-9)
    duck = 1 - 0.62 * np.clip(env * 3, 0, 1)
    music *= duck[:, None]

    music = norm(music, 1.0) * 0.34
    sfx = norm(sfx, 1.0) * 0.42
    bed = music + sfx
    mix = vo_st * 0.85 + bed
    # fade out
    fo = nsamp(0.8)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    bed[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)

    sf.write(os.path.join(OUT, "voiceover.wav"), norm(vo_st, 0.89), SR, subtype="PCM_24")
    sf.write(os.path.join(OUT, "music_sfx.wav"), norm(bed, 0.89), SR, subtype="PCM_24")
    sf.write(os.path.join(OUT, "mix.wav"), norm(mix, 0.95), SR, subtype="PCM_24")
    master(os.path.join(OUT, "mix.wav"), os.path.join(OUT, "mix_master.wav"))

    timeline = {"duration": round(total, 3), "bpm": BPM, "drop": lines["punch2"]["start"], "lines": lines, **events}
    with open(os.path.join(OUT, "timeline.json"), "w") as f:
        json.dump(timeline, f, indent=1)
    print(f"duration {total:.2f}s")
    for cid, info in lines.items():
        print(f"  {info['start']:6.2f}-{info['end']:6.2f}  {cid:10s} {info['text']}")


if __name__ == "__main__":
    main()
