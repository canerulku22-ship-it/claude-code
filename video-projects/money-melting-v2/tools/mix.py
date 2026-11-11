"""Procedural sound design + music bed + final mix.

Usage: python tools/mix.py
Reads  audio/vo.wav, audio/cues.json (from `node tools/render.js cues`)
Writes audio/mix_full.wav (voice + sfx + music), audio/mix_nomusic.wav (voice + sfx, for adding a trending sound in-app)
"""
import json
import os

import numpy as np
import soundfile as sf
from scipy import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
rng = np.random.default_rng(7)


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def env_exp(d, tau, attack=0.002):
    t = t_axis(d)
    return np.minimum(1, t / attack) * np.exp(-t / tau)


def sweep(f0, f1, d, kind="exp"):
    t = t_axis(d)
    f = f0 * (f1 / f0) ** (t / d) if kind == "exp" else f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def noise(d):
    return rng.standard_normal(int(d * SR))


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "highpass", fs=SR, output="sos"), x)


def swept_bp(x, centers, q=1.2, block=256):
    """Band-pass with a moving center frequency (array sampled per block)."""
    out = np.zeros_like(x)
    zi = None
    nb = int(np.ceil(len(x) / block))
    cs = np.interp(np.linspace(0, 1, nb), np.linspace(0, 1, len(centers)), centers)
    for b in range(nb):
        c = float(np.clip(cs[b], 60, SR / 2.3))
        sos = signal.butter(2, [c / (1 + 1 / q), c * (1 + 1 / q)], "bandpass", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        seg = x[b * block:(b + 1) * block]
        y, zi = signal.sosfilt(sos, seg, zi=zi)
        out[b * block:b * block + len(seg)] = y
    return out


def norm(x, peak=1.0):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


# ---------------------------------------------------------------- SFX library
def sfx_boom(d=1.4):
    t = t_axis(d)
    body = sweep(110, 32, d) * np.exp(-t / 0.45)
    thump = lp(noise(d), 300) * np.exp(-t / 0.05) * 0.9
    return norm(np.tanh(1.6 * (body + thump)))


def sfx_drop():
    x = sfx_boom(2.2)
    t = t_axis(2.2)
    x += 0.5 * np.sin(2 * np.pi * 41 * t) * np.exp(-t / 0.9)
    return norm(np.tanh(1.3 * x))


def sfx_hit():
    d = 0.35
    t = t_axis(d)
    return norm(np.tanh(2 * (sweep(170, 48, d) * np.exp(-t / 0.09) + hp(noise(d), 2000) * np.exp(-t / 0.008) * 0.6)))


def sfx_tick():
    d = 0.03
    t = t_axis(d)
    return norm(np.sin(2 * np.pi * 2600 * t) * np.exp(-t / 0.004) + hp(noise(d), 4000) * np.exp(-t / 0.002) * 0.4)


def sfx_clock():
    d = 0.12
    t = t_axis(d)
    return norm((np.sin(2 * np.pi * 1250 * t) + 0.5 * np.sin(2 * np.pi * 2480 * t)) * np.exp(-t / 0.025))


def sfx_pop(pitch=1.0):
    d = 0.14
    t = t_axis(d)
    x = np.concatenate([sweep(320 * pitch, 980 * pitch, 0.05), sweep(980 * pitch, 900 * pitch, d - 0.05)])
    return norm(x[:len(t)] * env_exp(d, 0.045))


def bell(f, d=1.0, tau=0.35):
    t = t_axis(d)
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau / r ** 0.5)) for r, a in [(1, 1), (2.0, 0.35), (3.01, 0.18), (4.2, 0.08)])


def sfx_ding():
    return norm(bell(1568) * env_exp(1.0, 10))


def sfx_cash():
    a, b = bell(2093, 0.8, 0.25), bell(2637, 0.9, 0.3)
    out = np.zeros(int(1.0 * SR))
    out[:len(a)] += a
    o = int(0.07 * SR)
    out[o:o + len(b)] += b[:len(out) - o]
    out[:int(0.2 * SR)] += hp(noise(0.2), 5000) * np.exp(-t_axis(0.2) / 0.05) * 0.3
    return norm(out)


def sfx_shimmer():
    d = 0.9
    t = t_axis(d)
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    x = hp(noise(d), 6000) * 0.25
    for f in rng.uniform(2500, 7000, 9):
        x += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(5, 14) * t))
    return norm(x * e)


def sfx_whoosh(d=0.5, f0=250, f1=3200):
    t = t_axis(d)
    centers = np.concatenate([np.geomspace(f0, f1, 60), np.geomspace(f1, f0 * 1.6, 40)])
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return norm(swept_bp(noise(d), centers, q=1.4) * e)


def sfx_swoosh():
    return sfx_whoosh(0.28, 600, 5000)


def sfx_riser(d=1.2):
    t = t_axis(d)
    e = (t / d) ** 2.2
    x = swept_bp(noise(d), np.geomspace(300, 6000, 100), q=2) * 0.8 + sweep(180, 1400, d) * 0.25
    x = x * e
    x[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return norm(x)


def sfx_down(d=1.2):
    t = t_axis(d)
    x = sweep(820, 140, d) * (1 + 0.3 * np.sin(2 * np.pi * 7 * t))
    e = np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.2)
    return norm(lp(x, 2500) * e)


def sfx_glitch():
    d = 0.3
    x = noise(d)
    x = np.round(x * 3) / 3  # crush
    sq = np.sign(np.sin(2 * np.pi * 180 * t_axis(d))) * 0.6
    gate = (np.floor(t_axis(d) * 40) % 2 == 0) * (rng.random(int(d * 40) + 1)[np.floor(t_axis(d) * 40).astype(int)] > 0.3)
    return norm(bp(x + sq, 400, 6000) * gate * env_exp(d, 0.2))


def sfx_stamp():
    d = 0.5
    t = t_axis(d)
    low = sweep(140, 55, d) * np.exp(-t / 0.08)
    slap = bp(noise(d), 800, 5000) * np.exp(-t / 0.02)
    return norm(np.tanh(2.2 * (low + 0.8 * slap)))


def sfx_buzz():
    d = 0.42
    t = t_axis(d)
    sq = signal.square(2 * np.pi * 110 * t) * ((t < 0.16) | ((t > 0.22) & (t < 0.38)))
    return norm(lp(sq, 1800) * 0.9)


def sfx_click():
    d = 0.09
    t = t_axis(d)
    x = hp(noise(d), 2500) * (np.exp(-t / 0.003) + 0.7 * np.exp(-np.maximum(0, t - 0.045) / 0.003) * (t > 0.045))
    return norm(x)


def sfx_type():
    d = 0.06
    t = t_axis(d)
    return norm(bp(noise(d), 1500, 6000) * np.exp(-t / 0.008) + np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.01) * 0.5)


def sfx_thunk():
    d = 0.4
    t = t_axis(d)
    return norm(np.tanh(2 * (sweep(200, 70, d) * np.exp(-t / 0.07) + bp(noise(d), 1500, 4000) * np.exp(-t / 0.01))))


def sfx_alarm():
    d = 0.9
    t = t_axis(d)
    f = np.where((t * 4).astype(int) % 2 == 0, 880, 660)
    x = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) * 0.6
    return norm(lp(x, 2200) * np.minimum(1, (d - t) / 0.1))


def sfx_melt():
    d = 1.4
    t = t_axis(d)
    tone = np.sin(2 * np.pi * np.cumsum(620 * (80 / 620) ** (t / d) * (1 + 0.04 * np.sin(2 * np.pi * 6 * t))) / SR)
    sizzle = hp(noise(d), 3000) * 0.25 * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * t))
    e = np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.3)
    return norm((lp(tone, 3000) + sizzle) * e)


LIB = {
    "boom": sfx_boom, "drop": sfx_drop, "hit": sfx_hit, "tick": sfx_tick, "clock": sfx_clock, "pop": sfx_pop,
    "ding": sfx_ding, "cash": sfx_cash, "shimmer": sfx_shimmer, "whoosh": sfx_whoosh, "swoosh": sfx_swoosh,
    "riser": sfx_riser, "down": sfx_down, "glitch": sfx_glitch, "stamp": sfx_stamp, "buzz": sfx_buzz,
    "click": sfx_click, "type": sfx_type, "thunk": sfx_thunk, "alarm": sfx_alarm, "melt": sfx_melt,
}
SFX_GAIN = {"tick": 0.5, "type": 0.45, "click": 0.6, "boom": 0.75, "drop": 0.85, "riser": 0.55, "whoosh": 0.55, "swoosh": 0.5,
            "shimmer": 0.4, "ding": 0.45, "cash": 0.45, "pop": 0.55, "glitch": 0.45, "down": 0.4, "alarm": 0.35, "buzz": 0.4,
            "melt": 0.55, "stamp": 0.85, "hit": 0.8, "thunk": 0.8, "clock": 0.55}


# ---------------------------------------------------------------- music bed
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def saw(f, d, detune=0.0):
    t = t_axis(d)
    return signal.sawtooth(2 * np.pi * f * (1 + detune) * t + rng.uniform(0, 6))


def build_music(dur, cues):
    bpm = 100
    beat = 60 / bpm
    n = int(dur * SR) + SR
    L = np.zeros(n)
    Rt = np.zeros(n)
    full = np.zeros(n)   # kick/hats layer, gated by intensity
    # A minor: Am  F  C  G  (two bars each)
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
    bar = 4 * beat
    seg = 2 * bar
    t0 = 0.0
    k = 0
    while t0 < dur + seg:
        ch = chords[k % 4]
        a, b = int(t0 * SR), int((t0 + seg) * SR)
        if a >= n:
            break
        d = (b - a) / SR + 0.6
        tt = t_axis(d)
        e = np.minimum(1, tt / 0.8) * np.minimum(1, np.maximum(0, (d - tt) / 0.9))
        padL = sum(saw(midi(m), d, -0.004) for m in ch) / 4
        padR = sum(saw(midi(m), d, 0.004) for m in ch) / 4
        padL, padR = lp(padL, 900) * e, lp(padR, 900) * e
        end = min(n, a + len(tt))
        L[a:end] += 0.22 * padL[:end - a]
        Rt[a:end] += 0.22 * padR[:end - a]
        # sub bass on beats 1 & 3, plucky arp on 8ths
        for bt in range(8):
            ts = t0 + bt * beat
            if bt % 2 == 0:
                bd = beat * 1.8
                s = np.sin(2 * np.pi * midi(ch[0] - 24) * t_axis(bd)) * env_exp(bd, 0.5, 0.01)
                i0 = int(ts * SR)
                if i0 < n:
                    e2 = min(n, i0 + len(s))
                    L[i0:e2] += 0.32 * s[:e2 - i0]
                    Rt[i0:e2] += 0.32 * s[:e2 - i0]
            for half in (0, 1):
                ta = ts + half * beat / 2
                note = ch[(bt * 2 + half) % 4] + 12
                ad = 0.35
                s = lp(signal.sawtooth(2 * np.pi * midi(note) * t_axis(ad), 0.5), 2600) * env_exp(ad, 0.09, 0.004)
                i0 = int(ta * SR)
                if i0 < n:
                    e2 = min(n, i0 + len(s))
                    pan = 0.5 + 0.35 * np.sin(k * 3 + bt + half)
                    L[i0:e2] += 0.07 * (1 - pan) * s[:e2 - i0]
                    Rt[i0:e2] += 0.07 * pan * s[:e2 - i0]
        # drums (full layer)
        for bt in range(8):
            ts = t0 + bt * beat
            i0 = int(ts * SR)
            if i0 >= n:
                break
            kd = 0.4
            kick = np.sin(2 * np.pi * np.cumsum(50 + 110 * np.exp(-t_axis(kd) / 0.03)) / SR) * env_exp(kd, 0.16, 0.002)
            e2 = min(n, i0 + len(kick))
            full[i0:e2] += 0.34 * kick[:e2 - i0]
            for h in range(2):
                hd = 0.05
                hat = hp(noise(hd), 8000) * env_exp(hd, 0.012)
                j = int((ts + h * beat / 2 + beat / 4) * SR)
                if j < n:
                    e3 = min(n, j + len(hat))
                    full[j:e3] += 0.08 * hat[:e3 - j]
        t0 += seg
        k += 1
    # intensity automation from cues
    tt = np.arange(n) / SR
    times = [c["t"] for c in cues] or [0]
    levels = [c["level"] for c in cues] or [0.7]
    # make steps (hold value until next cue) with 0.25 s smoothing
    step = np.zeros(n)
    for i, c in enumerate(cues):
        a = int(c["t"] * SR)
        step[a:] = c["level"]
    win = int(0.25 * SR)
    lvl = np.convolve(step, np.ones(win) / win, mode="same")
    drums_on = np.clip((lvl - 0.8) / 0.1, 0, 1)
    filt = np.zeros(n)
    for i, c in enumerate(cues):
        if c.get("filter"):
            a = int(c["t"] * SR)
            b = int(cues[i + 1]["t"] * SR) if i + 1 < len(cues) else n
            filt[a:b] = 1
    filt = np.convolve(filt, np.ones(win) / win, mode="same")
    musL = L + full * drums_on
    musR = Rt + full * drums_on
    # muffled version for "filter" sections (the twist)
    musL = musL * (1 - filt) + lp(musL, 380) * filt
    musR = musR * (1 - filt) + lp(musR, 380) * filt
    return np.stack([musL * lvl, musR * lvl], 1)


def main():
    cues = json.load(open(os.path.join(ROOT, "audio", "cues.json")))
    dur = cues["duration"] + 0.3
    n = int(dur * SR)
    vo, vsr = sf.read(os.path.join(ROOT, "audio", "vo.wav"))
    vo = signal.resample_poly(vo, SR, vsr)
    vo = hp(vo, 70)
    voice = np.zeros(n)
    voice[:min(n, len(vo))] = vo[:n]

    # SFX bus
    sfxb = np.zeros((n, 2))
    cache = {}
    for c in cues["sfx"]:
        name = c["name"]
        key = (name, c.get("dur"), c.get("pitch"))
        if key not in cache:
            fn = LIB[name]
            if name in ("riser", "down") and c.get("dur"):
                cache[key] = fn(max(0.2, c["dur"]))
            elif name == "pop" and c.get("pitch"):
                cache[key] = fn(c["pitch"])
            else:
                cache[key] = fn()
        s = cache[key] * c["gain"] * SFX_GAIN.get(name, 0.6)
        if name in ("tick", "type"):
            s = s * rng.uniform(0.8, 1.1)
        a = int(c["t"] * SR)
        if a >= n:
            continue
        e = min(n, a + len(s))
        pan = 0.5 if name in ("boom", "drop", "hit", "stamp", "melt") else 0.5 + rng.uniform(-0.18, 0.18)
        sfxb[a:e, 0] += s[:e - a] * np.sqrt(1 - pan) * 1.41
        sfxb[a:e, 1] += s[:e - a] * np.sqrt(pan) * 1.41

    music = build_music(dur, cues["music"])[:n]

    # sidechain: duck music under the voice
    envv = np.abs(voice)
    envv = signal.sosfilt(signal.butter(1, 6, "lowpass", fs=SR, output="sos"), envv)
    envv = envv / max(1e-6, envv.max())
    duck = 1 - 0.55 * np.clip(envv * 4, 0, 1)
    music = music * duck[:, None]

    v2 = np.stack([voice, voice], 1)
    full = v2 * 1.0 + sfxb * 0.5 + music * 0.28
    nomus = v2 * 1.0 + sfxb * 0.5
    vpk = np.abs(voice).max()
    for name, mix in (("mix_full", full), ("mix_nomusic", nomus)):
        mix = np.tanh(mix / vpk * 0.62) * 0.98  # voice peaks ~0.55, impacts soft-clip
        fade = int(0.25 * SR)
        mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        sf.write(os.path.join(ROOT, "audio", name + ".wav"), mix.astype(np.float32), SR, subtype="PCM_24")
        print("wrote", name, mix.shape[0] / SR, "s")


if __name__ == "__main__":
    main()
