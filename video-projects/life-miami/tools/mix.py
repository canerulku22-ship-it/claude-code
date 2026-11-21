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


def sfx_step():
    d = 0.18
    t = t_axis(d)
    return norm(np.sin(2 * np.pi * 70 * t) * np.exp(-t / 0.03) + bp(noise(d), 200, 1200) * np.exp(-t / 0.02) * 0.5)


def sfx_rumble(d=1.3):
    t = t_axis(d)
    x = lp(noise(d), 120) * 3 + np.sin(2 * np.pi * 38 * t) * 0.6 + bp(noise(d), 300, 900) * 0.15 * (np.sin(2 * np.pi * 9 * t) > 0)
    e = np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.3)
    return norm(np.tanh(1.5 * x) * e)



def sfx_blowout():
    d = 0.45
    t = t_axis(d)
    return norm(bp(noise(d), 300, 2500) * np.exp(-t / 0.12) * np.minimum(1, t / 0.02))



def sfx_clink(pitch=1.0):
    d = 0.35
    t = t_axis(d)
    f = 3100 * pitch
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.05) + 0.5 * np.sin(2 * np.pi * f * 1.52 * t) * np.exp(-t / 0.03) + 0.3 * np.sin(2 * np.pi * f * 0.51 * t) * np.exp(-t / 0.08)
    return norm(x)



def sfx_engine(d=4.0):
    """Diesel idle/cruise hum: low harmonics with slow wobble + filtered rumble, soft edges."""
    t = t_axis(d)
    wob = 1 + 0.015 * np.sin(2 * np.pi * 0.7 * t)
    tone = sum(a * np.sin(2 * np.pi * f * wob * t + i) for i, (f, a) in enumerate([(41, 1.0), (82, 0.55), (123, 0.3), (164, 0.18)]))
    rum = lp(noise(d), 260) * 3.0
    x = lp(tone * 0.6 + rum * 0.5, 600) * (0.85 + 0.15 * np.sin(2 * np.pi * 9.5 * t))
    f_in, f_out = min(len(t) // 3, int(0.3 * SR)), min(len(t) // 3, int(0.12 * SR))
    env = np.ones(len(t)); env[:f_in] = np.linspace(0, 1, f_in); env[-f_out:] = np.linspace(1, 0, f_out)
    return norm(x * env, 0.5)


def sfx_hiss():
    """Pneumatic door / air release."""
    d = 0.9
    x = bp(noise(d), 1800, 9000) * env_exp(d, 0.28, attack=0.015)
    return norm(x, 0.7)


def sfx_brake():
    """Air-brake squeal + release."""
    d = 1.3
    t = t_axis(d)
    sq = np.sin(2 * np.pi * (1650 + 60 * np.sin(2 * np.pi * 6 * t)) * t) * np.clip(t / 0.15, 0, 1) * np.exp(-t / 0.55) * 0.35
    rel = bp(noise(d), 1500, 7000) * np.exp(-np.maximum(0, t - 0.75) / 0.2) * (t > 0.75) * 0.8
    return norm(sq + rel, 0.7)


def sfx_boing(pitch=1.0):
    """Cartoon spring: rising sine with fast vibrato."""
    d = 0.45
    t = t_axis(d)
    f = (260 + 380 * (1 - np.exp(-t / 0.12))) * pitch * (1 + 0.09 * np.sin(2 * np.pi * 17 * t))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    return norm(x + 0.3 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * np.exp(-t / 0.08), 0.8)


def sfx_drumroll(d=2.5):
    """Snare roll that speeds up and swells."""
    n = int(d * SR)
    out = np.zeros(n)
    hit_t = t_axis(0.09)
    hit = bp(noise(0.09), 1200, 7000) * np.exp(-hit_t / 0.03) + 0.4 * np.sin(2 * np.pi * 190 * hit_t) * np.exp(-hit_t / 0.03)
    tt = 0.0
    while tt < d - 0.05:
        k = tt / d
        a = int(tt * SR)
        e = min(n, a + len(hit))
        out[a:e] += hit[:e - a] * (0.35 + 0.65 * k) * (0.85 + 0.3 * rng.random())
        tt += 1.0 / (11 + 13 * k)
    return norm(out, 0.8)


def sfx_trombone():
    """Sad 'wah-wah-wah-wahhh'."""
    notes = [(233.1, 0.36), (220.0, 0.36), (207.7, 0.36), (196.0, 1.15)]
    out = []
    for i, (f0, d) in enumerate(notes):
        t = t_axis(d)
        f = f0 * (1 + (0.025 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.25) / 0.3, 0, 1) if i == 3 else 0))
        ph = 2 * np.pi * np.cumsum(f) / SR
        saw = sum(np.sin(k * ph) / k for k in range(1, 12))
        wah = np.clip(t / 0.08, 0, 1) * np.exp(-np.maximum(0, t - d + 0.12) / 0.05)
        cut = 500 + 1600 * np.clip(t / 0.15, 0, 1) * (0.6 + 0.4 * np.cos(2 * np.pi * 2 * t))
        out.append(swept_bp(saw, cut[::256] if len(cut) > 256 else cut[:1], q=0.8) * wah)
    return norm(np.concatenate(out), 0.8)


def sfx_bleep(d=0.3):
    t = t_axis(d)
    env = np.clip(t / 0.005, 0, 1) * np.clip((d - t) / 0.005, 0, 1)
    return norm(np.sin(2 * np.pi * 1000 * t) * env, 0.6)


def sfx_rain(d=2.0):
    t = t_axis(d)
    x = bp(noise(d), 800, 7000) * 0.6 + hp(noise(d), 3000) * (rng.random(len(t)) > 0.997) * 3
    env = np.clip(t / 0.3, 0, 1) * np.clip((d - t) / 0.3, 0, 1)
    return norm(x * env, 0.6)


def sfx_squawk(pitch=1.0):
    out = []
    for i, d in enumerate([0.16, 0.13, 0.22]):
        t = t_axis(d)
        f = (1250 - 500 * t / d) * pitch * (1 + 0.04 * np.sin(2 * np.pi * 38 * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        saw = sum(np.sin(k * ph) / k for k in range(1, 8))
        out.append(bp(saw, 900, 4000) * np.sin(np.pi * t / d) ** 0.6)
        out.append(np.zeros(int(0.05 * SR)))
    return norm(np.concatenate(out), 0.7)


def sfx_fanfare():
    out = []
    for f0, d in [(523.3, 0.11), (659.3, 0.11), (784.0, 0.11), (1046.5, 0.5)]:
        t = t_axis(d)
        ph = 2 * np.pi * f0 * t * (1 + 0.004 * np.sin(2 * np.pi * 6 * t))
        x = sum(np.sin(k * ph) * (0.8 ** k) for k in range(1, 10)) * np.clip(t / 0.015, 0, 1) * np.clip((d - t) / 0.04, 0, 1)
        out.append(lp(x, 3500))
    return norm(np.concatenate(out), 0.7)


def sfx_scratch():
    d = 0.4
    t = t_axis(d)
    c = 600 + 2600 * np.abs(np.sin(2 * np.pi * 2.6 * t))
    return norm(swept_bp(noise(d), c[::256], q=2.5) * np.clip((d - t) / 0.05, 0, 1), 0.8)


def sfx_horn():
    d = 0.55
    t = t_axis(d)
    x = sum(np.sign(np.sin(2 * np.pi * f * t)) * a for f, a in [(392, 0.6), (494, 0.5)])
    return norm(lp(x, 2400) * np.clip(t / 0.01, 0, 1) * np.clip((d - t) / 0.04, 0, 1), 0.7)


def sfx_splash():
    d = 0.9
    t = t_axis(d)
    x = bp(noise(d), 300, 5000) * np.exp(-t / 0.18) + lp(noise(d), 400) * np.exp(-t / 0.08) * 1.5
    return norm(x, 0.8)


def sfx_splat():
    d = 0.5
    t = t_axis(d)
    x = lp(noise(d), 900) * np.exp(-t / 0.07) + np.sin(2 * np.pi * (180 - 120 * t) * t) * np.exp(-t / 0.1) * 0.6
    return norm(x, 0.8)


def sfx_riff():
    """Distorted power-chord riff (E5-E5-G5-A5)."""
    out = []
    for f0, d in [(82.4, 0.22), (82.4, 0.22), (98.0, 0.22), (110.0, 0.6)]:
        t = t_axis(d)
        x = np.sin(2 * np.pi * f0 * t) + 0.8 * np.sin(2 * np.pi * f0 * 1.5 * t) + 0.5 * np.sin(2 * np.pi * f0 * 2 * t)
        x = np.tanh(x * 6) * np.exp(-t / 0.5) * np.clip((d - t) / 0.02, 0, 1)
        out.append(lp(x, 3000))
    return norm(np.concatenate(out), 0.8)


def sfx_cheer(d=1.6):
    t = t_axis(d)
    x = bp(noise(d), 500, 3500) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 7 * t + rng.random(len(t)) * 0.3)))
    return norm(x * np.clip(t / 0.15, 0, 1) * np.clip((d - t) / 0.5, 0, 1), 0.6)


def sfx_sizzle(d=1.2):
    t = t_axis(d)
    x = hp(noise(d), 4000) * (0.5 + 0.5 * (rng.random(len(t)) > 0.98) * 3)
    return norm(x * np.clip(t / 0.1, 0, 1) * np.clip((d - t) / 0.3, 0, 1), 0.5)


LIB = {
    "boom": sfx_boom, "hit": sfx_hit, "tick": sfx_tick, "clock": sfx_clock, "pop": sfx_pop, "ding": sfx_ding,
    "shimmer": sfx_shimmer, "whoosh": sfx_whoosh, "swoosh": sfx_swoosh, "riser": sfx_riser, "down": sfx_down,
    "glitch": sfx_glitch, "click": sfx_click, "type": sfx_type, "thunk": sfx_thunk,
    "buzz": sfx_buzz, "stinger": sfx_stinger, "creak": sfx_creak, "slam": sfx_slam, "knock": sfx_knock,
    "whisper": sfx_whisper, "flicker": sfx_flicker, "cloth": sfx_cloth, "birds": sfx_birds, "step": sfx_step, "rumble": sfx_rumble, "blowout": sfx_blowout, "clink": sfx_clink,
    "engine": sfx_engine, "hiss": sfx_hiss, "brake": sfx_brake,
    "boing": sfx_boing, "drumroll": sfx_drumroll, "trombone": sfx_trombone, "bleep": sfx_bleep, "cash": sfx_cash, "stamp": sfx_stamp, "rain": sfx_rain, "squawk": sfx_squawk, "fanfare": sfx_fanfare, "scratch": sfx_scratch, "horn": sfx_horn, "splash": sfx_splash, "splat": sfx_splat, "riff": sfx_riff, "cheer": sfx_cheer, "sizzle": sfx_sizzle,
}
SFX_GAIN = {"tick": 0.5, "type": 0.35, "click": 0.6, "boom": 0.8, "riser": 0.5, "whoosh": 0.45, "swoosh": 0.4, "shimmer": 0.35,
            "pop": 0.45, "down": 0.4, "buzz": 0.55, "stinger": 0.85, "creak": 0.6, "slam": 0.95, "knock": 0.8, "whisper": 0.45,
            "flicker": 0.4, "cloth": 0.5, "birds": 0.35, "step": 0.45, "rumble": 0.6, "blowout": 0.5, "clink": 0.35, "hit": 0.7, "thunk": 0.7, "clock": 0.65, "engine": 0.55, "hiss": 0.5, "brake": 0.55, "boing": 0.5, "drumroll": 0.6, "trombone": 0.8, "bleep": 0.5, "rain": 0.4, "squawk": 0.5, "fanfare": 0.6, "scratch": 0.7, "horn": 0.5, "splash": 0.6, "splat": 0.6, "riff": 0.6, "cheer": 0.4, "sizzle": 0.35}


def pluck(f, d=0.9):
    t = t_axis(d)
    x = sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t / (0.5 / k)) for k in range(1, 9))
    return x * np.clip(t / 0.003, 0, 1)


def build_music(dur, cues):
    """Cheeky ukulele-ish I-V-vi-IV loop at 118 bpm: plucked strums, bass, kick/clap/hats."""
    n = int(dur * SR) + SR
    bpm = 118.0
    beat = 60 / bpm
    C4 = 261.63
    semi = lambda k: C4 * 2 ** (k / 12)
    chords = [[0, 4, 7, 12], [-5, -1, 2, 7], [-3, 0, 4, 9], [-7, -3, 0, 5]]   # C G Am F
    roots = [0, -5, -3, -7]
    L = np.zeros(n); R_ = np.zeros(n)
    cache = {}

    def put(buf, x, t0, g=1.0):
        a = int(t0 * SR)
        if a >= n:
            return
        e = min(n, a + len(x))
        buf[a:e] += x[:e - a] * g
    kick_t = t_axis(0.3); kick = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-kick_t / 0.04)) / SR) * np.exp(-kick_t / 0.12)
    clap = bp(noise(0.18), 900, 5000) * np.exp(-t_axis(0.18) / 0.05)
    hat = hp(noise(0.05), 7000) * np.exp(-t_axis(0.05) / 0.012)
    strum = [(0, 1.0, 1), (1, 0.8, 1), (1.5, 0.6, -1), (2.5, 0.6, -1), (3, 0.8, 1), (3.5, 0.6, -1)]   # D D U U D U (in beats)
    bars = int(dur / (4 * beat)) + 2
    for bar in range(bars):
        t_bar = bar * 4 * beat
        ch = chords[bar % 4]
        for (b_, g, dirn) in strum:
            notes = ch if dirn > 0 else ch[::-1]
            for j, k in enumerate(notes):
                key = (k,)
                if key not in cache:
                    cache[key] = pluck(semi(k + 12) * 0.5)
                tt = t_bar + b_ * beat + j * 0.012
                put(L, cache[key], tt, 0.16 * g * (1.1 if j % 2 else 0.9))
                put(R_, cache[key], tt + 0.004, 0.16 * g * (0.9 if j % 2 else 1.1))
        bassf = semi(roots[bar % 4] - 24)
        for b_ in (0, 2, 2.5):
            bt = t_axis(beat * 0.9)
            bass = (np.sin(2 * np.pi * bassf * bt) + 0.3 * np.sin(4 * np.pi * bassf * bt)) * np.exp(-bt / 0.35)
            put(L, bass, t_bar + b_ * beat, 0.5); put(R_, bass, t_bar + b_ * beat, 0.5)
        for b_ in (0, 2):
            put(L, kick, t_bar + b_ * beat, 0.8); put(R_, kick, t_bar + b_ * beat, 0.8)
        for b_ in (1, 3):
            put(L, clap, t_bar + b_ * beat, 0.35); put(R_, clap, t_bar + b_ * beat + 0.006, 0.35)
        for e in range(8):
            put(L if e % 2 else R_, hat, t_bar + e * beat / 2, 0.12)
    win = int(0.12 * SR)
    lvl = np.zeros(n)
    for c in cues:
        lvl[int(c["t"] * SR):] = c["level"]
    lvl = np.convolve(lvl, np.ones(win) / win, mode="same")
    return np.stack([L * lvl, R_ * lvl], 1)


def build_synthwave(dur, cues):
    """80s Miami synthwave loop at 112 bpm: Am-F-C-G pads, driving octave bass, 16th arp, gated snare."""
    n = int(dur * SR) + SR
    beat = 60 / 112.0
    A3 = 220.0
    semi = lambda k: A3 * 2 ** (k / 12)
    chords = [[0, 3, 7, 12], [-4, 0, 3, 8], [3, 7, 10, 15], [-2, 2, 5, 10]]   # Am F C G
    roots = [0, -4, 3, -2]
    L = np.zeros(n); R_ = np.zeros(n)

    def put(buf, x, t0, g=1.0):
        a = int(t0 * SR)
        if a >= n:
            return
        e = min(n, a + len(x))
        buf[a:e] += x[:e - a] * g

    def saw(f, d, harm=10, det=0.0):
        t = t_axis(d); y = np.zeros_like(t)
        for h in range(1, harm + 1):
            if f * h > 9000:
                break
            y += np.sin(2 * np.pi * f * (1 + det) * h * t) / h
        return y
    kick_t = t_axis(0.35); kick = np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-kick_t / 0.03)) / SR) * np.exp(-kick_t / 0.16)
    st = t_axis(0.42)
    snare = (bp(noise(0.42), 300, 7000) * 0.9 + np.sin(2 * np.pi * 190 * st) * np.exp(-st / 0.05)) * np.where(st < 0.2, 1.0, np.exp(-(st - 0.2) / 0.015))
    snare = snare + 0.35 * lp(np.convolve(snare, np.random.RandomState(4).randn(int(0.25 * SR)) * np.exp(-t_axis(0.25) / 0.08), "full")[:len(st)] * 0.05, 6000) * np.where(st < 0.26, 1.0, 0.0)
    hat = hp(noise(0.04), 8000) * np.exp(-t_axis(0.04) / 0.01)
    pads, arps, basses = {}, {}, {}
    bars = int(dur / (4 * beat)) + 2
    for bar in range(bars):
        t_bar = bar * 4 * beat
        ci = bar % 4
        if ci not in pads:
            d = 4 * beat + 0.3
            env = np.minimum(1, t_axis(d) / 0.35) * np.minimum(1, (d - t_axis(d)) / 0.3)
            p = sum(saw(semi(k), d, 6, det) for k in chords[ci] for det in (-0.004, 0.004))
            pads[ci] = lp(p, 1800) * env * 0.05
            bd = beat / 2 * 0.92; bt = t_axis(bd)
            basses[ci] = [lp(saw(semi(roots[ci] - 24 + o), bd, 12), 900) * np.exp(-bt / 0.25) * 0.22 for o in (0, 12)]
            ad = beat / 4 * 0.9; at = t_axis(ad)
            arps[ci] = [(np.sin(2 * np.pi * semi(k + 12) * at) + np.sin(6 * np.pi * semi(k + 12) * at) / 3 + np.sin(10 * np.pi * semi(k + 12) * at) / 5) * np.exp(-at / 0.07) * 0.07 for k in chords[ci]]
        put(L, pads[ci], t_bar, 1.0); put(R_, pads[ci], t_bar + 0.011, 1.0)
        for e in range(8):
            b = basses[ci][e % 2]; put(L, b, t_bar + e * beat / 2); put(R_, b, t_bar + e * beat / 2)
        order = [0, 1, 2, 3, 2, 1, 2, 3] * 2
        for s16 in range(16):
            a = arps[ci][order[s16]]; tt = t_bar + s16 * beat / 4
            put(L, a, tt, 1.0); put(R_, a, tt + 0.006, 0.7)
            put(R_, a, tt + beat * 0.75, 0.35); put(L, a, tt + beat * 0.75 + 0.01, 0.25)   # dotted-eighth echo
        for b_ in (0, 2):
            put(L, kick, t_bar + b_ * beat, 0.85); put(R_, kick, t_bar + b_ * beat, 0.85)
        for b_ in (1, 3):
            put(L, snare, t_bar + b_ * beat, 0.42); put(R_, snare, t_bar + b_ * beat + 0.008, 0.42)
        for e in range(8):
            put(L if e % 2 else R_, hat, t_bar + e * beat / 2, 0.1 if e % 2 else 0.06)
    win = int(0.12 * SR)
    lvl = np.zeros(n)
    for c in cues:
        lvl[int(c["t"] * SR):] = c["level"]
    lvl = np.convolve(lvl, np.ones(win) / win, mode="same")
    return np.stack([L * lvl, R_ * lvl], 1)


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
            elif name in ("pop", "clink", "boing", "squawk") and c.get("pitch"):
                cache[key] = fn(c["pitch"])
            elif name in ("creak", "rumble", "engine", "drumroll", "bleep", "rain") and c.get("dur"):
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

    music = build_synthwave(dur, cues["music"])[:n]

    # sidechain: duck music under the voice
    envv = np.abs(voice)
    envv = signal.sosfilt(signal.butter(1, 6, "lowpass", fs=SR, output="sos"), envv)
    envv = envv / max(1e-6, envv.max())
    duck = 1 - 0.55 * np.clip(envv * 4, 0, 1)
    music = music * duck[:, None]

    # bleeped voice: mute the swear words, drop a 1 kHz tone in their place
    timing = json.load(open(os.path.join(ROOT, "audio", "timing.json")))
    vbleep = voice.copy()
    bleeps = np.zeros(n)
    for ln in timing["lines"]:
        for c in ln["caps"]:
            if c.get("style") == "swear":
                a_, e_ = int((c["s"] - 0.03) * SR), int((c["e"] + 0.03) * SR)
                vbleep[a_:e_] = 0
                bleeps[a_:e_] += np.sin(2 * np.pi * 1000 * np.arange(e_ - a_) / SR) * np.abs(voice).max() * 0.55
    v2 = np.stack([voice, voice], 1)
    vb2 = np.stack([vbleep + bleeps, vbleep + bleeps], 1)
    full = v2 * 1.0 + sfxb * 0.55 + music * 0.3
    nomus = v2 * 1.0 + sfxb * 0.55
    bleeped = vb2 * 1.0 + sfxb * 0.55 + music * 0.3
    vpk = np.abs(voice).max()
    for name, mix in (("mix_full", full), ("mix_nomusic", nomus), ("mix_bleep", bleeped)):
        mix = np.tanh(mix / vpk * 0.62) * 0.98  # voice peaks ~0.55, impacts soft-clip
        fade = int(0.25 * SR)
        mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
        sf.write(os.path.join(ROOT, "audio", name + ".wav"), mix.astype(np.float32), SR, subtype="PCM_24")
        print("wrote", name, mix.shape[0] / SR, "s")


if __name__ == "__main__":
    main()
