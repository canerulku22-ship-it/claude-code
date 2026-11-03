"""Sound for Chef Whiskers, synthesized with numpy: no samples, so nothing to license.

usage: python audio.py sfx <events.json> <out.wav>     sound effects for one clip, from render.js events
       python audio.py music <seconds> <out.wav>       a cozy music bed for the whole video
"""
import json
import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t_axis(n):
    return np.arange(n) / SR


def noise(seconds):
    return rng.standard_normal(int(seconds * SR))


def band(x, lo, hi, soft=0.25):
    """Band-pass by FFT with smooth edges (lo/hi in Hz)."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    lo_edge = np.clip((f - lo * (1 - soft)) / (lo * soft * 2 + 1e-9), 0, 1) if lo > 0 else 1.0
    hi_edge = np.clip((hi * (1 + soft) - f) / (hi * soft * 2), 0, 1)
    return np.fft.irfft(spec * lo_edge * hi_edge, len(x))


def decay(n, tau, attack=0.002):
    t = t_axis(n)
    return np.exp(-t / tau) * np.clip(t / attack, 0, 1)


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


def add(buf, sig, t0, gain=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if i0 >= buf.shape[1] or len(sig) == 0:
        return
    sig = sig[:buf.shape[1] - i0].copy()
    k = min(len(sig) // 2, int(0.004 * SR))
    if k > 1:  # short fades so cut-off tails never click
        ramp = np.linspace(0, 1, k)
        sig[:k] *= ramp
        sig[-k:] *= ramp[::-1]
    th = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    buf[0, i0:i0 + len(sig)] += sig * gain * np.cos(th)
    buf[1, i0:i0 + len(sig)] += sig * gain * np.sin(th)


def sweep_tone(f0, f1, seconds):
    n = int(seconds * SR)
    freq = np.geomspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def bell(freq, seconds=1.2, index=1.6, ratio=3.5):
    t = t_axis(int(seconds * SR))
    mod = np.sin(2 * np.pi * freq * ratio * t) * index * np.exp(-t * 6)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 3.2) * np.clip(t / 0.003, 0, 1)


def resonate(x, freqs, q=8.0):
    """Sum of simple two-pole resonators (time-invariant), done in the frequency domain."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    resp = sum(1 / (1 + ((f - fc) / (fc / q)) ** 2) for fc in freqs)
    return np.fft.irfft(spec * resp, len(x))


# ------------------------------------------------------------------ effects

def fx_room(seconds):
    return band(noise(seconds), 60, 400) * 0.02


def fx_sizzle(seconds, attack=0.4):
    n = int(seconds * SR)
    hiss = band(noise(seconds), 2500, 11000)
    crackle = np.zeros(n)
    hits = rng.random(n) < 0.0016
    crackle[hits] = rng.standard_normal(hits.sum()) * 6
    crackle = band(np.convolve(crackle, np.exp(-t_axis(240) / 0.0012), 'same'), 1800, 12000)
    wobble = 0.75 + 0.25 * band(noise(seconds), 0.1, 6, soft=0.5) * 3
    env = np.clip(t_axis(n) / max(attack, 1e-3), 0, 1) * np.clip((seconds - t_axis(n)) / 0.15, 0, 1)
    return (norm(hiss) * 0.42 * wobble + norm(crackle) * 0.5) * env


def fx_chop():
    thud = sweep_tone(170, 85, 0.09) * decay(int(0.09 * SR), 0.025)
    click = band(noise(0.03), 1500, 7000) * decay(int(0.03 * SR), 0.004)
    knock = band(noise(0.06), 500, 1500) * decay(int(0.06 * SR), 0.012)
    out = np.zeros(int(0.09 * SR))
    out[:len(thud)] += thud * 0.8
    out[:len(click)] += norm(click) * 0.6
    out[:len(knock)] += norm(knock) * 0.5
    return out


def fx_place():
    thud = sweep_tone(120, 65, 0.16) * decay(int(0.16 * SR), 0.05)
    soft = band(noise(0.08), 80, 900) * decay(int(0.08 * SR), 0.02)
    out = thud.copy()
    out[:len(soft)] += norm(soft) * 0.4
    return out


def fx_smash():
    thump = sweep_tone(95, 45, 0.3) * decay(int(0.3 * SR), 0.09)
    slap = band(noise(0.15), 300, 4000) * decay(int(0.15 * SR), 0.03)
    out = thump * 1.0
    out[:len(slap)] += norm(slap) * 0.7
    return out


def fx_plop():
    blip = sweep_tone(320, 170, 0.08) * decay(int(0.08 * SR), 0.02)
    soft = band(noise(0.07), 100, 1200) * decay(int(0.07 * SR), 0.015)
    out = blip * 0.6
    out[:len(soft)] += norm(soft) * 0.6
    return out


def fx_squish():
    n = int(0.2 * SR)
    env = np.sin(np.pi * np.clip(t_axis(n) / 0.2, 0, 1)) ** 2
    return norm(band(noise(0.2), 250, 1300)) * env * 0.7


def fx_sparkle():
    out = np.zeros(int(1.4 * SR))
    for k, midi in enumerate([84, 88, 91, 96]):
        b = bell(440 * 2 ** ((midi - 69) / 12), 1.0)
        i = int(k * 0.07 * SR)
        out[i:i + len(b)] += b * (0.5 - k * 0.06)
    return out


def fx_lick():
    seconds = 0.32
    n = int(seconds * SR)
    src = noise(seconds)
    out = np.zeros(n)
    blocks = 16
    for b in range(blocks):  # sweep a formant upward: "slurp"
        i0, i1 = b * n // blocks, (b + 1) * n // blocks
        fc = 700 * (3.2 ** (b / (blocks - 1)))
        out[i0:i1] = band(src, fc * 0.7, fc * 1.4)[i0:i1]
    env = np.sin(np.pi * t_axis(n) / seconds) ** 1.5
    return norm(out) * env * 0.5


def fx_bite():
    out = np.zeros(int(0.25 * SR))
    for _ in range(14):  # crunchy grains
        g = band(noise(0.02), 1000, 6500) * decay(int(0.02 * SR), 0.004)
        i = int(rng.random() * 0.16 * SR)
        out[i:i + len(g)] += norm(g) * (0.4 + rng.random() * 0.5)
    thump = sweep_tone(140, 70, 0.12) * decay(int(0.12 * SR), 0.03)
    out[:len(thump)] += thump * 0.5
    return out * 0.8


def fx_mrrp():
    """A short, rising 'mrrp?' chirp: harmonics of a gliding pitch through two formants."""
    seconds = 0.34
    t = t_axis(int(seconds * SR))
    u = t / seconds
    f0 = 360 + 300 * np.sin(np.pi * np.clip(u * 0.8, 0, 1) / 1.6) + 12 * np.sin(2 * np.pi * 22 * t) * (u > 0.15)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    out = np.zeros_like(t)
    for k in range(1, 9):
        fk = f0 * k
        formant = np.exp(-((fk - 900) / 380) ** 2) + 0.6 * np.exp(-((fk - 2300) / 600) ** 2) + 0.15
        out += np.sin(k * phase) * formant / k
    trill = 0.75 + 0.25 * np.sign(np.sin(2 * np.pi * 26 * t)) * (u < 0.35)
    env = np.clip(t / 0.02, 0, 1) * np.clip((seconds - t) / 0.12, 0, 1)
    return norm(out) * trill * env * 0.55


def fx_sniff():
    out = np.zeros(int(0.3 * SR))
    for k in range(2):
        s = band(noise(0.07), 2000, 7000) * np.sin(np.pi * t_axis(int(0.07 * SR)) / 0.07)
        i = int(k * 0.12 * SR)
        out[i:i + len(s)] += norm(s) * 0.35
    return out


def fx_whoosh():
    seconds = 0.32
    n = int(seconds * SR)
    src, out, blocks = noise(seconds), np.zeros(n), 16
    for b in range(blocks):  # band sweeps down: a quick swoosh past the camera
        i0, i1 = b * n // blocks, (b + 1) * n // blocks
        fc = 3200 * (0.25 ** (b / (blocks - 1)))
        out[i0:i1] = band(src, fc * 0.6, fc * 1.6)[i0:i1]
    env = np.sin(np.pi * np.clip(t_axis(n) / seconds, 0, 1)) ** 2
    return norm(out) * env * 0.6


def fx_splash():
    out = np.zeros(int(0.6 * SR))
    body = band(noise(0.5), 300, 5000) * decay(int(0.5 * SR), 0.12)
    out[:len(body)] += norm(body) * 0.7
    for _ in range(18):  # droplets
        f = 600 + rng.random() * 1800
        d = np.sin(2 * np.pi * np.cumsum(np.linspace(f, f * 1.8, int(0.04 * SR))) / SR) * decay(int(0.04 * SR), 0.01)
        i = int((0.05 + rng.random() * 0.4) * SR)
        out[i:i + len(d)] += d * (0.15 + rng.random() * 0.2)
    thump = sweep_tone(130, 60, 0.15) * decay(int(0.15 * SR), 0.04)
    out[:len(thump)] += thump * 0.5
    return out


def fx_puff():
    n = int(0.35 * SR)
    env = np.clip(t_axis(n) / 0.01, 0, 1) * np.exp(-t_axis(n) / 0.09)
    return norm(band(noise(0.35), 150, 2500)) * env * 0.6 + sweep_tone(90, 50, 0.35) * decay(n, 0.05) * 0.3


def fx_pop():
    blip = sweep_tone(420, 900, 0.07) * decay(int(0.07 * SR), 0.018)
    click = band(noise(0.01), 2000, 8000) * decay(int(0.01 * SR), 0.002)
    out = blip.copy()
    out[:len(click)] += norm(click) * 0.3
    return out * 0.7


def fx_ding():
    return bell(1568.0, 1.2, index=0.8) * 0.5 + bell(2093.0, 1.2, index=0.5) * 0.25


def fx_clink():
    out = np.zeros(int(0.3 * SR))
    for k, f in enumerate([2600, 3900]):
        t = t_axis(int(0.25 * SR))
        tone = np.sin(2 * np.pi * f * t) * np.exp(-t * 28)
        i = int(k * 0.035 * SR)
        out[i:i + len(tone)] += tone * 0.35
    return out


def fx_bubbles(seconds):
    n = int(seconds * SR)
    out = np.zeros(n)
    for _ in range(int(seconds * 55)):  # little pops of frying bubbles
        f = 500 + rng.random() * 1500
        d = np.sin(2 * np.pi * np.cumsum(np.linspace(f, f * 1.5, int(0.025 * SR))) / SR) * decay(int(0.025 * SR), 0.006)
        i = int(rng.random() * (n - len(d)))
        out[i:i + len(d)] += d * (0.1 + rng.random() * 0.25)
    env = np.clip(t_axis(n) / 0.05, 0, 1) * np.clip((seconds - t_axis(n)) / 0.15, 0, 1)
    return out * env


def fx_squirt(seconds):
    n = int(seconds * SR)
    src = band(noise(seconds), 250, 1600)
    wobble = 0.6 + 0.4 * np.sin(2 * np.pi * 9 * t_axis(n)) ** 2
    env = np.clip(t_axis(n) / 0.05, 0, 1) * np.clip((seconds - t_axis(n)) / 0.1, 0, 1)
    return norm(src) * wobble * env * 0.35


def fx_rustle(seconds):
    n = int(seconds * SR)
    src = band(noise(seconds), 2500, 9000)
    grains = np.clip(band(noise(seconds), 4, 30, soft=0.5) * 6, 0, 1)
    env = np.clip(t_axis(n) / 0.05, 0, 1) * np.clip((seconds - t_axis(n)) / 0.1, 0, 1)
    return norm(src) * grains * env * 0.4


def fx_thump():
    boom = sweep_tone(110, 42, 0.35) * decay(int(0.35 * SR), 0.1)
    slap = band(noise(0.1), 200, 3000) * decay(int(0.1 * SR), 0.02)
    out = boom * 1.0
    out[:len(slap)] += norm(slap) * 0.5
    return out


def fx_crunch():
    out = np.zeros(int(0.45 * SR))
    for _ in range(34):  # loud, dense crunchy grains
        g = band(noise(0.025), 900, 7500) * decay(int(0.025 * SR), 0.005)
        i = int(rng.random() * 0.3 * SR)
        out[i:i + len(g)] += norm(g) * (0.4 + rng.random() * 0.6)
    thump = sweep_tone(150, 60, 0.15) * decay(int(0.15 * SR), 0.04)
    out[:len(thump)] += thump * 0.6
    return np.tanh(out * 1.3) * 0.9


def fx_sneeze():
    n = int(0.45 * SR)
    t = t_axis(n)
    inhale = band(noise(0.45), 800, 3000) * np.clip(t / 0.25, 0, 1) * (t < 0.25) * 0.25
    burst = band(noise(0.45), 1200, 6000) * np.exp(-np.clip(t - 0.28, 0, None) / 0.05) * (t >= 0.28)
    return norm(inhale + burst * 1.4) * 0.6


ONE_SHOTS = {'chop': (fx_chop, 0.75), 'place': (fx_place, 0.7), 'smash': (fx_smash, 0.9), 'plop': (fx_plop, 0.6), 'squish': (fx_squish, 0.5),
             'sparkle': (fx_sparkle, 0.32), 'lick': (fx_lick, 0.6), 'bite': (fx_bite, 0.85), 'mrrp': (fx_mrrp, 0.55), 'sniff': (fx_sniff, 0.5),
             'whoosh': (fx_whoosh, 0.5), 'splash': (fx_splash, 0.8), 'puff': (fx_puff, 0.8), 'pop': (fx_pop, 0.45), 'ding': (fx_ding, 0.45),
             'clink': (fx_clink, 0.4), 'thump': (fx_thump, 0.85), 'crunch': (fx_crunch, 0.95), 'sneeze': (fx_sneeze, 0.6)}
LOOPS = {'bubbles': (fx_bubbles, 0.5), 'squirt': (fx_squirt, 0.6), 'rustle': (fx_rustle, 0.5)}


def render_sfx(spec):
    seconds = float(spec['duration'])
    buf = np.zeros((2, int(seconds * SR) + 1))
    for ev in spec['events']:
        kind, t0 = ev['type'], float(ev['t'])
        if kind == 'room':
            add(buf, fx_room(float(ev.get('dur', seconds))), t0)
            add(buf, fx_room(float(ev.get('dur', seconds))), t0, pan=0.6)
        elif kind == 'sizzle':
            dur = max(0.05, float(ev.get('dur', seconds - t0)))
            level = float(ev.get('level', 0.3))
            add(buf, fx_sizzle(dur, float(ev.get('attack', 0.4))), t0, 0.6 * level, pan=-0.25)
            add(buf, fx_sizzle(dur, float(ev.get('attack', 0.4))), t0, 0.6 * level, pan=0.25)
        elif kind in ONE_SHOTS:
            fn, gain = ONE_SHOTS[kind]
            add(buf, fn(), t0, gain * float(ev.get('gain', 1.0)), pan=float(ev.get('pan', 0.0)))
        elif kind in LOOPS:
            fn, gain = LOOPS[kind]
            add(buf, fn(max(0.05, float(ev.get('dur', seconds - t0)))), t0, gain * float(ev.get('gain', 1.0)), pan=float(ev.get('pan', 0.0)))
    return np.tanh(buf * 1.1) * 0.9


# ------------------------------------------------------------------ music

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pluck(freq, seconds=0.5):
    t = t_axis(int(seconds * SR))
    tone = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 3.98 * t) * np.exp(-t * 30) + 0.12 * np.sin(2 * np.pi * freq * 9.9 * t) * np.exp(-t * 60)
    return tone * np.exp(-t * 7) * np.clip(t / 0.002, 0, 1)


def render_music(seconds):
    n = int(seconds * SR) + 1
    buf = np.zeros((2, n))
    bpm = 112
    beat = 60 / bpm
    bar = 4 * beat
    # F - Dm - Bb - C, a warm I-vi-IV-V loop
    chords = [[53, 57, 60, 65], [50, 57, 62, 65], [46, 58, 62, 65], [48, 55, 60, 64]]
    roots = [41, 38, 34, 36]
    melody = [(0, 72), (0.5, 74), (1, 77), (2, 76), (2.5, 74), (3, 72), (4, 74), (5, 77), (5.5, 79), (6, 81), (7, 79),
              (8, 77), (8.5, 76), (9, 74), (10, 72), (11, 74), (12, 76), (12.5, 77), (13, 79), (14, 76), (15, 72)]
    t_bar = 0.0
    b = 0
    while t_bar < seconds:
        ch, root = chords[b % 4], roots[b % 4]
        for step in range(8):  # arpeggiated plucks on eighth notes
            note = ch[[0, 1, 2, 3, 2, 1, 2, 3][step]] + 12
            add(buf, pluck(mtof(note), 0.45), t_bar + step * beat / 2, 0.11, pan=-0.35 + 0.1 * (step % 2))
        for k in (0, 2):  # bass on beats 1 and 3
            tb = t_axis(int(beat * 1.6 * SR))
            bass = np.tanh(1.6 * np.sin(2 * np.pi * mtof(root) * tb)) * np.exp(-tb * 2.2) * np.clip(tb / 0.01, 0, 1)
            add(buf, bass, t_bar + k * beat, 0.16)
            kick = sweep_tone(110, 45, 0.18) * decay(int(0.18 * SR), 0.05)
            add(buf, kick, t_bar + k * beat, 0.28)
        for k in (1, 3):  # soft snap on 2 and 4
            snap = band(noise(0.08), 1200, 5000) * decay(int(0.08 * SR), 0.018)
            add(buf, norm(snap), t_bar + k * beat, 0.08, pan=0.2)
        for step in range(8):  # shaker
            sh = band(noise(0.05), 6000, 14000) * decay(int(0.05 * SR), 0.012)
            add(buf, norm(sh), t_bar + step * beat / 2, 0.035 if step % 2 else 0.05, pan=0.45)
        for k in range(len(ch)):  # pad
            tp = t_axis(int(bar * SR))
            pad = (np.sin(2 * np.pi * mtof(ch[k]) * tp) + 0.5 * np.sin(2 * np.pi * mtof(ch[k]) * 1.003 * tp)) * np.sin(np.pi * tp / bar) ** 0.6
            add(buf, pad, t_bar, 0.025, pan=-0.6 + 0.4 * k)
        t_bar += bar
        b += 1
    loop = 16 * beat
    t0 = 0.0
    while t0 < seconds:  # glockenspiel melody
        for beat_pos, midi in melody:
            add(buf, bell(mtof(midi), 0.9, index=1.0), t0 + beat_pos * beat, 0.09, pan=0.25)
        t0 += loop
    fade = np.clip(t_axis(n) / 0.3, 0, 1) * np.clip((seconds - t_axis(n)) / 1.5, 0, 1)
    out = buf * fade
    return out / (np.abs(out).max() + 1e-9) * 0.32


def write_wav(path, stereo):
    pcm = (np.clip(stereo, -1, 1).T * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('sfx', 'music'):
        sys.exit(__doc__)
    mode, arg, out = sys.argv[1:]
    if mode == 'sfx':
        with open(arg, encoding='utf-8') as f:
            write_wav(out, render_sfx(json.load(f)))
    else:
        write_wav(out, render_music(float(arg)))
