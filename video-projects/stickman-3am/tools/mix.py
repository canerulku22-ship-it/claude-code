"""Horror sound design: procedural SFX, drone + heartbeat bed, voice ducking, final mix.

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




def sfx_buzz():
    d = 0.6
    t = t_axis(d)
    tone = signal.square(2 * np.pi * 172 * t) * 0.5 + np.sin(2 * np.pi * 344 * t) * 0.3
    gate = (np.sin(2 * np.pi * 2.6 * t) > -0.2).astype(float)
    return norm(lp(tone, 900) * gate * np.minimum(1, (d - t) / 0.05))


def sfx_stinger(soft=0):
    d = 2.2
    t = t_axis(d)
    freqs = [110, 116.5, 155.6, 233, 246.9, 329.6, 349.2]
    x = sum(signal.sawtooth(2 * np.pi * f * (1 + 0.003 * np.sin(2 * np.pi * 5 * t + i)) * t) for i, f in enumerate(freqs)) / len(freqs)
    x = lp(x, 2600 if not soft else 1200) * np.exp(-t / (0.9 if not soft else 0.6))
    hit = (lp(noise(d), 4000) * np.exp(-t / 0.05) * (0.9 if not soft else 0.3)) + np.sin(2 * np.pi * 45 * t) * np.exp(-t / 0.35)
    screech = hp(noise(d), 3000) * np.exp(-t / 0.25) * (0.35 if not soft else 0.05)
    return norm(np.tanh(1.8 * (x + hit + screech)))


def sfx_creak(d=1.6):
    t = t_axis(d)
    f = 180 + 120 * np.sin(2 * np.pi * 0.7 * t) + 60 * np.sin(2 * np.pi * 3.1 * t) + 40 * rng.standard_normal(len(t)).cumsum() / np.sqrt(len(t)) * 3
    ph = 2 * np.pi * np.cumsum(np.clip(f, 60, 700)) / SR
    x = signal.sawtooth(ph) * (0.6 + 0.4 * (np.sin(2 * np.pi * 23 * t) > 0))
    x = swept_bp(x, np.clip(f * 3, 300, 3000), q=4) + bp(noise(d), 800, 2500) * 0.08
    e = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.2)
    return norm(x * e)


def sfx_slam():
    d = 1.2
    t = t_axis(d)
    low = sweep(95, 38, d) * np.exp(-t / 0.22)
    crack = bp(noise(d), 600, 5000) * np.exp(-t / 0.03)
    rattle = bp(noise(d), 2000, 6000) * np.exp(-t / 0.18) * 0.15 * (np.sin(2 * np.pi * 31 * t) > 0)
    return norm(np.tanh(2.2 * (low + 0.9 * crack + rattle)))


def sfx_knock():
    d = 0.25
    t = t_axis(d)
    return norm(np.tanh(2.5 * (np.sin(2 * np.pi * 118 * t) * np.exp(-t / 0.05) + bp(noise(d), 300, 2000) * np.exp(-t / 0.015) * 0.8)))


def sfx_whisper():
    d = 1.6
    t = t_axis(d)
    x = noise(d)
    centers = 900 + 700 * np.abs(np.sin(2 * np.pi * np.array([2.1, 3.3])[0] * np.linspace(0, d, 80)))
    x = swept_bp(x, centers, q=3) * (0.35 + 0.65 * np.abs(np.sin(2 * np.pi * 4.3 * t)) ** 2)
    e = np.sin(np.pi * np.clip(t / d, 0, 1))
    return norm(hp(x, 500) * e)


def sfx_flicker():
    d = 0.5
    t = t_axis(d)
    hum = sum(np.sin(2 * np.pi * 120 * k * t) / k for k in range(1, 6))
    gate = (rng.random(int(d * 40) + 1)[np.minimum((t * 40).astype(int), int(d * 40))] > 0.4).astype(float)
    crackle = hp(noise(d), 4000) * (rng.random(len(t)) > 0.995) * 3
    return norm((hum * 0.5 + crackle) * gate * np.exp(-t / 0.3))


def sfx_cloth():
    d = 0.9
    t = t_axis(d)
    x = bp(noise(d), 1500, 7000) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 3 * t)))
    return norm(x * np.sin(np.pi * np.clip(t / d, 0, 1)))


def sfx_birds():
    d = 2.5
    out = np.zeros(int(d * SR))
    for k in range(7):
        st = rng.uniform(0, d - 0.3)
        cd = rng.uniform(0.06, 0.14)
        f0 = rng.uniform(2800, 4200)
        c = sweep(f0, f0 * rng.uniform(1.2, 1.6), cd) * np.sin(np.pi * np.clip(t_axis(cd) / cd, 0, 1))
        a = int(st * SR)
        out[a:a + len(c)] += c * rng.uniform(0.4, 1)
    return norm(out)


LIB = {
    "boom": sfx_boom, "hit": sfx_hit, "tick": sfx_tick, "clock": sfx_clock, "pop": sfx_pop, "ding": sfx_ding,
    "shimmer": sfx_shimmer, "whoosh": sfx_whoosh, "swoosh": sfx_swoosh, "riser": sfx_riser, "down": sfx_down,
    "glitch": sfx_glitch, "click": sfx_click, "type": sfx_type, "thunk": sfx_thunk,
    "buzz": sfx_buzz, "stinger": sfx_stinger, "creak": sfx_creak, "slam": sfx_slam, "knock": sfx_knock,
    "whisper": sfx_whisper, "flicker": sfx_flicker, "cloth": sfx_cloth, "birds": sfx_birds,
}
SFX_GAIN = {"tick": 0.5, "type": 0.35, "click": 0.6, "boom": 0.8, "riser": 0.5, "whoosh": 0.45, "swoosh": 0.4, "shimmer": 0.35,
            "pop": 0.45, "down": 0.4, "buzz": 0.55, "stinger": 0.85, "creak": 0.6, "slam": 0.95, "knock": 0.8, "whisper": 0.45,
            "flicker": 0.4, "cloth": 0.5, "birds": 0.35, "hit": 0.7, "thunk": 0.7, "clock": 0.65}


def build_music(dur, cues):
    n = int(dur * SR) + SR
    t = np.arange(n) / SR
    # drone: low fifths, slow beating, plus a dissonant minor-second shimmer
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.4 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t)
             + 0.25 * np.sin(2 * np.pi * 116.5 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)))
    drone = lp(drone, 400) * 0.35
    air = lp(hp(rng.standard_normal(n), 200), 1800) * 0.05 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t))
    pad = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate([220, 233.1, 329.6])) / 3
    pad = lp(pad, 1200) * 0.08 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t))
    L = drone + air + pad
    R_ = drone + air * 0.9 + np.roll(pad, int(0.013 * SR))
    # step automation
    win = int(0.35 * SR)
    lvl = np.zeros(n); heart = np.zeros(n)
    for c in cues:
        a = int(c["t"] * SR)
        lvl[a:] = c["level"]
        heart[a:] = c.get("heart", 0)
    lvl = np.convolve(lvl, np.ones(win) / win, mode="same")
    heart = np.convolve(heart, np.ones(win) / win, mode="same")
    # heartbeat: lub-dub; rate rises with intensity
    hb = np.zeros(n)
    ph = 0.0
    i = 0
    beat = np.sin(2 * np.pi * 48 * t_axis(0.18)) * np.exp(-t_axis(0.18) / 0.05)
    while i < n:
        h = heart[i]
        bpm = 62 + 40 * h
        if h > 0.02:
            for off, g in ((0, 1.0), (0.17, 0.7)):
                j = i + int(off * SR)
                if j < n:
                    e = min(n, j + len(beat))
                    hb[j:e] += beat[:e - j] * g * h
        i += int(60 / bpm * SR)
    hb = lp(hb, 160) * 0.9
    music = np.stack([L * lvl + hb, R_ * lvl + hb], 1)
    return music


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
        key = (name, c.get("dur"), c.get("pitch"), c.get("soft"))
        if key not in cache:
            fn = LIB[name]
            if name in ("riser", "down") and c.get("dur"):
                cache[key] = fn(max(0.2, c["dur"]))
            elif name == "pop" and c.get("pitch"):
                cache[key] = fn(c["pitch"])
            elif name == "creak" and c.get("dur"):
                cache[key] = fn(max(0.3, c["dur"]))
            elif name == "stinger" and c.get("soft"):
                cache[key] = fn(soft=1)
            else:
                cache[key] = fn()
        s = cache[key] * c["gain"] * SFX_GAIN.get(name, 0.6)
        if name in ("tick", "type"):
            s = s * rng.uniform(0.8, 1.1)
        a = int(c["t"] * SR)
        if a >= n:
            continue
        e = min(n, a + len(s))
        pan = 0.5 if name in ("boom", "hit", "stinger", "slam", "knock") else 0.5 + rng.uniform(-0.18, 0.18)
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
    full = v2 * 1.0 + sfxb * 0.55 + music * 0.5
    nomus = v2 * 1.0 + sfxb * 0.55
    vpk = np.abs(voice).max()
    for name, mix in (("mix_full", full), ("mix_nomusic", nomus)):
        mix = np.tanh(mix / vpk * 0.62) * 0.98  # voice peaks ~0.55, impacts soft-clip
        fade = int(0.25 * SR)
        mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        sf.write(os.path.join(ROOT, "audio", name + ".wav"), mix.astype(np.float32), SR, subtype="PCM_24")
        print("wrote", name, mix.shape[0] / SR, "s")


if __name__ == "__main__":
    main()
