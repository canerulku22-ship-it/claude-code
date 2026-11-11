"""Soundtrack for the BMW M5 short: music, V8 engine model, EV whine and
sound effects synthesised from scratch, plus the Kokoro voiceover lines
from out/vo/, placed at the times in timeline.js with the music ducked
under the voice.

    python3 audio.py out/soundtrack.wav      (run voiceover.mjs first)
"""
import json
import os
import sys
import wave

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
src = open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read()
TL = json.loads(src[src.index('{'):src.rindex('}') + 1])
DUR = TL['duration']
N = int(SR * DUR)
rng = np.random.default_rng(7)


# ---------------------------------------------------------------- helpers
def lp(fc, order=2):
    return butter(order, fc, 'low', fs=SR, output='sos')


def hp(fc, order=2):
    return butter(order, fc, 'high', fs=SR, output='sos')


def bp(lo, hi, order=2):
    return butter(order, [lo, hi], 'band', fs=SR, output='sos')


def tt(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return rng.standard_normal(int(d * SR))


def saw(f, d, phase=0.0):
    return 2.0 * ((f * tt(d) + phase) % 1.0) - 1.0


def adsr(n, a=0.01, r=0.1):
    e = np.ones(n)
    na, nr = min(n, max(1, int(a * SR))), min(n, max(1, int(r * SR)))
    e[:na] = np.linspace(0, 1, na)
    e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def place(buf, t0, sig, gain=1.0, pan=0.0):
    """Mix a mono signal into a stereo buffer at t0 with an equal-power pan."""
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    if i0 < 0:
        sig, i0 = sig[-i0:], 0
    sig = sig[: N - i0]
    a = (pan + 1) * np.pi / 4
    buf[0, i0:i0 + len(sig)] += sig * gain * np.cos(a)
    buf[1, i0:i0 + len(sig)] += sig * gain * np.sin(a)


NOTE = {}
for i, nm in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']):
    for octv in range(0, 8):
        NOTE[f'{nm}{octv}'] = 440.0 * 2 ** ((i - 9) / 12 + (octv - 4))
CHORDS = {'Am': ['A2', 'C3', 'E3', 'A3'], 'F': ['F2', 'A2', 'C3', 'F3'], 'C': ['C3', 'E3', 'G3', 'C4'],
          'G': ['G2', 'B2', 'D3', 'G3'], 'Em': ['E2', 'G2', 'B2', 'E3'], 'Dm': ['D3', 'F3', 'A3', 'D4']}
ROOT = {'Am': 'A1', 'F': 'F1', 'C': 'C2', 'G': 'G1', 'Em': 'E1', 'Dm': 'D2'}

music = np.zeros((2, N))
send = np.zeros((2, N))
sfx = np.zeros((2, N))
kicks = []


# ------------------------------------------------------------ instruments
def kick(t0, g=1.0):
    t = tt(0.45)
    s = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-t * 28)) / SR) * np.exp(-t * 7.5)
    s[: int(0.004 * SR)] += noise(0.004) * 0.4
    place(music, t0, np.tanh(s * 1.6) * 0.75, g)
    kicks.append(t0)


def clap(t0, g=1.0):
    d = 0.35
    e = np.exp(-tt(d) * 18)
    for k in (0.0, 0.011, 0.022):
        e += np.roll(np.exp(-tt(d) * 60), int(k * SR)) * 0.6
    s = sosfilt(bp(900, 5000), noise(d)) * e * 0.35 + np.sin(2 * np.pi * 190 * tt(d)) * np.exp(-tt(d) * 30) * 0.3
    place(music, t0, s, g)
    place(send, t0, s, g * 0.5)


def hat(t0, g=1.0, open_=False, pan=0.15):
    d = 0.3 if open_ else 0.06
    place(music, t0, sosfilt(hp(7000), noise(d)) * np.exp(-tt(d) * (10 if open_ else 70)) * 0.3, g, pan)


def bass(t0, note, d, g=1.0, cutoff=420):
    f = NOTE[note]
    s = sosfilt(lp(cutoff), saw(f, d) * 0.6 + saw(f * 1.004, d, 0.3) * 0.4) + np.sin(2 * np.pi * f * tt(d)) * 0.7
    place(music, t0, s * adsr(len(s), 0.005, 0.05) * np.exp(-tt(d) * 2.5) * 0.32, g)


def pad(t0, chord, d, g=1.0, cutoff=1500):
    out = np.zeros(int(d * SR))
    for i, nm in enumerate(CHORDS[chord]):
        for det, ph in ((0.997, 0.1), (1.0, 0.5), (1.003, 0.8)):
            out += saw(NOTE[nm] * det, d, ph + i * 0.13)
    out = sosfilt(lp(cutoff), out) / 12 * adsr(len(out), min(0.6, d / 3), min(0.8, d / 3))
    s = np.vstack([out, np.roll(out, 211)])
    i0 = int(t0 * SR)
    m = min(len(out), N - i0)
    music[:, i0:i0 + m] += s[:, :m] * 0.5 * g
    send[:, i0:i0 + m] += s[:, :m] * 0.35 * g


def bell(t0, note, g=1.0, pan=0.0, d=1.6):
    f, t = NOTE[note], tt(d)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 5)
         + 0.25 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 8) + 0.12 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t * 12))
    s *= adsr(len(s), 0.002, 0.05)
    place(music, t0, s * 0.2, g, pan)
    place(send, t0, s * 0.18, g * 0.8, pan)


def riser(t0, d, g=1.0):
    t = tt(d)
    x, n = t / d, noise(d)
    s = (sosfilt(bp(300, 1500), n) * (1 - x) + sosfilt(bp(1500, 9000), n) * x) * x ** 2
    s += np.sin(2 * np.pi * np.cumsum(200 + 1400 * x ** 2) / SR) * 0.15 * x ** 2
    place(sfx, t0, s * 0.35, g)
    place(send, t0, s * 0.2, g)


def whoosh(t0, d=0.6, g=1.0, pan_from=-0.6, pan_to=0.6):
    x, n = tt(d) / d, noise(d)
    s = (sosfilt(bp(200, 900), n) * np.clip(1 - x * 1.6, 0, 1) + sosfilt(bp(900, 4000), n) * np.sin(np.pi * x)
         + sosfilt(bp(4000, 12000), n) * np.clip(x * 1.6 - 0.6, 0, 1)) * np.sin(np.pi * x) ** 1.5
    m = len(s)
    for k in range(8):
        a, b = k * m // 8, (k + 1) * m // 8
        place(sfx, t0 + a / SR, s[a:b] * 0.32, g, pan_from + (pan_to - pan_from) * (k + 0.5) / 8)


def impact(t0, g=1.0):
    d = 3.0
    t = tt(d)
    s = np.sin(2 * np.pi * np.cumsum(32 + 70 * np.exp(-t * 10)) / SR) * np.exp(-t * 2.2)
    s += sosfilt(lp(2500), noise(d)) * np.exp(-t * 9) * 0.5 + sosfilt(hp(5000), noise(d)) * np.exp(-t * 2.5) * 0.12
    place(sfx, t0, np.tanh(s * 1.3) * 0.75, g)
    place(send, t0, s * 0.4, g)


def thump(t0, g=1.0):
    t = tt(0.35)
    place(sfx, t0, np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 25)) * t) * np.exp(-t * 11) * 0.8, g)


def click(t0, g=1.0, f=3000, pan=0.0):
    d = 0.03
    place(sfx, t0, sosfilt(bp(f * 0.7, f * 1.4), noise(d)) * np.exp(-tt(d) * 220) * 0.5, g, pan)


def blip(t0, f, g=1.0):
    t = tt(0.18)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 22) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 35)
    place(sfx, t0, s * 0.18, g)
    place(send, t0, s * 0.1, g)


def shimmer(t0, d, f0, f1, g=1.0):
    """Rising glassy sweep (light-up / power-on)."""
    t = tt(d)
    f = f0 * (f1 / f0) ** (t / d)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3.01 * ph)) * np.sin(np.pi * t / d) ** 2
    place(sfx, t0, s * 0.08, g)
    place(send, t0, s * 0.08, g)


def groove(start, end, prog, kick_from=None, kick_every=1, clap_from=None, hat_from=None, hat_div=2,
           bass_from=None, bass_div=2, arp_from=None, pad_g=1.0, g=1.0, cutoff=1500, bass_cut=420):
    """One section on its own 120 bpm grid (beat 0.5 s, bar 2 s)."""
    for b in range(int(np.ceil((end - start) / 2.0))):
        t0 = start + b * 2.0
        ch = prog[b % len(prog)]
        if pad_g > 0:
            pad(t0, ch, min(2.0, end - t0) + 0.4, pad_g * g, cutoff)
        for beat in range(4):
            tb = t0 + beat * 0.5
            if tb >= end:
                break
            if kick_from is not None and tb >= kick_from and beat % kick_every == 0:
                kick(tb, g)
            if clap_from is not None and tb >= clap_from and beat % 2 == 1:
                clap(tb, g * 0.9)
            for h in range(hat_div):
                th = tb + h * 0.5 / hat_div
                if hat_from is not None and hat_from <= th < end and not (hat_div == 2 and h == 0):
                    hat(th, g * (0.8 if h % 2 else 1.0), open_=(hat_div == 2 and beat == 3))
            if bass_from is not None and tb >= bass_from:
                for k in range(bass_div):
                    tk = tb + k * 0.5 / bass_div
                    if tk < end:
                        bass(tk, ROOT[ch], 0.5 / bass_div * 0.95, g, bass_cut)
        if arp_from is not None:
            for k in range(16):
                ta = t0 + k * 0.125
                if arp_from <= ta < end:
                    nm = CHORDS[ch][[1, 2, 3, 2][k % 4]]
                    bell(ta, nm[:-1] + str(int(nm[-1]) + 2), g * 0.5, pan=0.35 * np.sin(k))


# ------------------------------------------------------------ arrangement
# 0 – 4.75 hook: power-on shimmer, light-signature thunk, engine start, beat enters
pad(0.0, 'Am', 4.9, 0.8, 600)
click(0.12, 1.2, 2200)
shimmer(0.12, 0.8, 300, 2400, 1.2)
thump(0.88, 1.2)
whoosh(0.7, 0.4, 0.6)
groove(2.0, 4.75, ['Am', 'F'], kick_from=2.0, kick_every=2, hat_from=3.0, bass_from=2.0, bass_div=1, pad_g=0, g=0.7)
riser(3.7, 1.05, 0.8)
# 4.75 – 9.15 origin
impact(4.75, 0.5)
groove(4.75, 9.15, ['Am', 'F', 'C', 'G'], kick_from=4.75, hat_from=5.75, bass_from=4.75, arp_from=5.25, g=0.7, cutoff=1300)
for i in range(7):
    click(6.9 + i * 0.24, 0.9, 2600, -0.3)
    blip(6.9 + i * 0.24, NOTE[['A4', 'C5', 'D5', 'E5', 'G5', 'A5', 'C6'][i]], 0.8 if i < 6 else 1.3)
whoosh(8.85, 0.5)
# 9.15 – 15.45 the heart, 727 slam
pad(9.15, 'Am', 3.8, 1.0, 900)
groove(9.15, 12.85, ['Am', 'Am'], kick_from=10.0, hat_from=11.0, hat_div=4, bass_from=9.15, bass_div=4, pad_g=0, g=0.7, bass_cut=600)
shimmer(9.2, 1.1, 600, 3000, 0.9)
for t0 in (10.0, 11.4, 12.0):
    blip(t0, NOTE['E6'], 0.7)
riser(11.6, 1.25, 1.0)
impact(12.85, 1.2)
groove(12.85, 15.45, ['F', 'G', 'Am'], kick_from=12.85, clap_from=12.85, hat_from=12.85, hat_div=4, bass_from=12.85, g=0.85, cutoff=1800)
whoosh(15.15, 0.5)
# 15.45 – 19.0 0–62 (engine leads)
groove(15.45, 19.0, ['Am', 'F'], kick_from=15.45, clap_from=15.45, hat_from=15.45, hat_div=4, bass_from=15.45, g=0.8, cutoff=2000)
impact(18.05, 0.8)
# 19.0 – 21.75 it plugs in
pad(19.0, 'C', 2.9, 0.9, 900)
groove(19.0, 21.75, ['C', 'G'], arp_from=19.6, pad_g=0, g=0.6)
click(19.5, 1.0, 1800)
click(20.65, 1.4, 1200)
thump(20.65, 0.6)
shimmer(20.65, 0.7, 800, 2600, 1.0)
bell(20.7, 'E5', 1.2)
bell(20.82, 'A5', 1.0)
# 21.75 – 27.3 43 miles
whoosh(21.45, 0.5)
groove(21.75, 27.3, ['C', 'G', 'Am', 'F'], kick_from=21.75, hat_from=22.25, bass_from=21.75, arp_from=22.75, g=0.75, cutoff=1500)
shimmer(22.3, 0.6, 500, 1500, 0.6)
bell(26.0, 'C6', 1.4)
bell(26.12, 'G5', 1.2)
# 27.3 – 31.65 tax + rain
whoosh(27.0, 0.5)
impact(27.3, 0.45)
groove(27.3, 31.65, ['Am', 'F', 'C', 'G'], kick_from=27.3, clap_from=29.2, hat_from=27.3, hat_div=4, bass_from=27.3, g=0.8, cutoff=1700)
for t0 in (27.7, 27.95):
    whoosh(t0, 0.35, 0.4, -0.4, 0.4)
d = 2.6
r = sosfilt(bp(400, 7000), noise(d)) * 0.07 * adsr(int(d * SR), 0.2, 0.3)
place(sfx, 29.1, r, 1.0, -0.2)
place(sfx, 29.1, np.roll(r, 3001), 1.0, 0.2)
for _ in range(90):
    click(29.2 + rng.random() * 2.4, rng.uniform(0.1, 0.35), rng.uniform(2000, 6000), rng.uniform(-0.9, 0.9))
# 31.65 – 33.95 saloon or Touring, build
whoosh(31.4, 0.5)
groove(31.65, 33.95, ['F', 'G'], kick_from=31.65, hat_from=31.65, hat_div=4, bass_from=31.65, bass_div=4, g=0.8, cutoff=1600)
whoosh(32.45, 0.7, 0.9, 0.8, -0.8)
shimmer(32.6, 0.7, 700, 2800, 0.8)
riser(32.9, 1.05, 0.9)
# 33.95 – 35.45 electric Monday: near silence
pad(33.95, 'Am', 1.7, 0.6, 700)
# 35.45 – 37.45 V8 Saturday: the drop
impact(35.45, 1.3)
groove(35.45, 37.45, ['Am', 'F'], kick_from=35.45, clap_from=35.45, hat_from=35.45, hat_div=4, bass_from=35.45, bass_div=2, g=0.9, cutoff=2400)
# 37.45 – end: end card
impact(37.45, 1.1)
pad(37.45, 'Am', DUR - 37.45, 0.9, 1400)
for k, nm in enumerate(['A4', 'C5', 'E5', 'B5']):
    bell(37.5 + k * 0.09, nm, 1.0, pan=-0.3 + 0.2 * k, d=3.4)

# ------------------------------------------------------------ motion-graphics sync
def ticks(t0, d, g=0.5, f=3200):
    """Accelerating-then-settling ticks for the rolling-digit counters."""
    tk = t0
    while tk < t0 + d:
        click(tk, g, f, 0.2)
        tk += 0.02 + 0.08 * ((tk - t0) / d) ** 2


def thunder(t0, g=1.0):
    d = 3.2
    t = tt(d)
    rumble = sosfilt(lp(160), noise(d)) * (1 - np.exp(-t * 12)) * np.exp(-t * 1.1)
    rumble *= 1 + 0.6 * np.sin(2 * np.pi * 3.1 * t)
    place(sfx, t0, rumble * 1.6, g)
    place(sfx, t0, sosfilt(hp(1500), noise(0.25)) * np.exp(-tt(0.25) * 14) * 0.5, g)
    place(send, t0, rumble * 0.5, g)


for c, kind in [(4.75, 'stripe'), (9.15, 'zoom'), (15.45, 'whip'), (19.0, 'stripe'), (21.75, 'whip'), (27.3, 'zoom'),
                (29.2, 'whip'), (31.65, 'stripe'), (33.95, 'zoom'), (37.45, 'stripe')]:
    if kind == 'whip':
        whoosh(c - 0.24, 0.42, 0.9, 0.9, -0.9)
    elif kind == 'stripe':
        whoosh(c - 0.26, 0.5, 0.8, -0.8, 0.8)
    else:
        whoosh(c - 0.3, 0.45, 0.6, -0.2, 0.2)
        impact(c, 0.35)
ticks(4.9, 0.8, 0.35)          # first year rolls in
ticks(12.9, 0.85, 0.5)         # 727
ticks(21.9, 0.6, 0.4)          # 43
ticks(27.4, 0.6, 0.4)          # 37
thunder(29.45, 1.0)
for i in range(16):            # spark crackle at the charge port
    click(20.65 + 0.02 + rng.random() * 0.5, rng.uniform(0.3, 0.8), rng.uniform(2500, 7000), rng.uniform(-0.3, 0.6))
blip(24.45, NOTE['E5'], 0.8)   # arrive at work
blip(26.25, NOTE['A5'], 0.8)   # back home

# ------------------------------------------------------------ engine model
t = np.arange(N) / SR
rpm = np.full(N, 800.0)
thr = np.zeros(N)
eng_g = np.zeros(N)
speed = np.zeros(N)
ev_g = np.zeros(N)
pops, shifts = [], []


def seg(a, b):
    return (t >= a) & (t < b)


def ramp(a, b, v0, v1, curve=1.0):
    m = seg(a, b)
    rpm[m] = v0 + (v1 - v0) * ((t[m] - a) / (b - a)) ** curve


def gain(points):
    a, b = points[0][0], points[-1][0]
    m = seg(a, b)
    eng_g[m] = np.interp(t[m], [p[0] for p in points], [p[1] for p in points])


def blip_rev(t0, peak, idle=850, up=0.15, down=0.7):
    ramp(t0, t0 + up, idle, peak, 0.6)
    ramp(t0 + up, t0 + up + down, peak, idle, 0.5)
    thr[seg(t0, t0 + up)] = 1.0
    pops.extend(t0 + up + 0.1 + rng.random(4) * down * 0.7)


def pull(a, gears, top=7000):
    ts = a
    for dd, r0 in gears:
        ramp(ts, ts + dd, r0, top, 0.8)
        thr[seg(ts, ts + dd)] = 1.0
        shifts.append(ts + dd)
        ts += dd
    return ts


# hook: starter, catch, flare, idle
ramp(0.9, 1.25, 150, 260)
ramp(1.25, 1.45, 260, 3300, 0.6)
thr[seg(1.25, 1.45)] = 1.0
ramp(1.45, 2.3, 3300, 900, 0.5)
pops.extend(1.6 + rng.random(4) * 0.5)
gain([(0.9, 0), (0.95, 0.5), (1.3, 0.9), (2.3, 0.55), (4.4, 0.45), (4.75, 0)])
d = 0.35  # starter motor whirr
st = np.sin(2 * np.pi * 230 * tt(d)) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 18 * tt(d)))) * adsr(int(d * SR), 0.02, 0.05)
place(sfx, 0.9, sosfilt(bp(150, 2000), st) * 0.25)
# 727 slam: a big blip
blip_rev(12.85, 6800, 850, 0.16, 0.9)
gain([(12.8, 0), (12.85, 0.85), (13.9, 0.5), (14.6, 0)])
# 0–62: full-throttle pull
rpm[seg(15.45, 15.55)] = 1600
end = pull(15.55, [(0.55, 3200), (0.65, 4600), (0.7, 5000), (0.6, 5300)])
ramp(end, end + 0.9, 6400, 2400, 0.6)
pops.extend(end + 0.05 + rng.random(9) * 0.8)
gain([(15.45, 0.4), (15.55, 1.0), (18.05, 1.0), (18.6, 0.5), (19.0, 0)])
# rain: brisk B-road driving
ramp(29.2, 29.9, 3000, 5200)
thr[seg(29.2, 29.9)] = 0.7
shifts.append(29.9)
ramp(29.9, 30.8, 3800, 5000)
thr[seg(29.9, 30.8)] = 0.6
ramp(30.8, 31.65, 5000, 3000)
pops.extend(30.85 + rng.random(5) * 0.6)
gain([(29.1, 0), (29.3, 0.45), (31.4, 0.45), (31.65, 0)])
# Monday: electric; Saturday: blip, then launch away into the distance
speed[seg(33.95, 35.45)] = 22
ev_g[seg(33.95, 35.45)] = np.interp(t[seg(33.95, 35.45)], [33.95, 34.3, 35.2, 35.45], [0, 0.4, 0.4, 0])
blip_rev(35.45, 5200, 900, 0.12, 0.2)
rpm[seg(35.77, 35.8)] = 3000
end = pull(35.8, [(0.5, 3000), (0.6, 4800), (0.7, 5100)])
ramp(end, end + 0.5, 6800, 6000)
gain([(35.4, 0), (35.45, 0.9), (35.8, 1.0), (36.6, 0.8), (37.45, 0.25), (37.9, 0)])

k = int(0.012 * SR)
rpm = np.maximum(np.convolve(rpm, np.ones(k) / k, mode='same'), 1)
thr = np.convolve(thr, np.ones(k * 4) / (k * 4), mode='same')
phi = 2 * np.pi * np.cumsum(rpm / 60.0) / SR
eng = np.zeros(N)
for o, a, load in [(0.5, 0.35, 0.2), (1, 0.45, 0.2), (1.5, 0.3, 0.3), (2, 0.75, 0.4), (3, 0.3, 0.5), (4, 1.0, 0.6),
                   (5, 0.25, 0.8), (6, 0.4, 0.9), (8, 0.45, 1.2), (10, 0.18, 1.4), (12, 0.15, 1.6), (16, 0.08, 2.0)]:
    eng += a * (1 + load * thr) * np.sin(o * phi + o * 1.3)
roar = sosfilt(lp(2200), rng.standard_normal(N)) * (0.5 + 0.5 * np.sin(4 * phi)) ** 3 * (0.5 + 1.6 * thr)
eng = np.tanh((eng * 0.55 + roar * 1.2) * (0.45 + 0.9 * thr))
eng += np.sin(2 * np.pi * np.cumsum(900 + rpm * 0.55) / SR) * 0.035 * thr * (rpm / 7000)  # turbo whistle
eng = sosfilt(hp(28), sosfilt(lp(4200), eng)) * eng_g
for p in pops:
    dd = 0.025 + rng.random() * 0.03
    s = sosfilt(lp(3500), noise(dd)) * np.exp(-tt(dd) * 90) * (0.6 + rng.random() * 0.8) + np.sin(2 * np.pi * 90 * tt(dd)) * np.exp(-tt(dd) * 60) * 0.5
    i = min(N - 1, int(p * SR))
    eng[i:i + len(s)] += s[: N - i] * 0.9 * max(eng_g[i], 0.3)
for p in shifts:
    s = sosfilt(bp(200, 3000), noise(0.06)) * np.exp(-tt(0.06) * 70)
    i = min(N - 1, int(p * SR))
    eng[i:i + len(s)] += s[: N - i] * 1.1 * eng_g[i]
ph = 2 * np.pi * np.cumsum(140 + speed * 9.5) / SR
eng += ((np.sin(ph) + 0.4 * np.sin(2.07 * ph) + 0.2 * np.sin(3.1 * ph)) * 0.18
        + sosfilt(bp(300, 1200), rng.standard_normal(N)) * 0.03) * ev_g * 0.7
engine = np.vstack([eng, eng]) * np.sqrt(0.5)
place(send, 0, eng * 0.1)

# ------------------------------------------------------------ voiceover
vo = np.zeros(N)
for line in TL['vo']:
    path = os.path.join(HERE, 'out', 'vo', f"{line['id']}.wav")
    sr_in, x = wavfile.read(path)  # Kokoro writes 32-bit float WAV
    x = x.astype(float) / (32768 if x.dtype == np.int16 else 1)
    x = resample_poly(x, SR, sr_in)
    i0 = int(line['at'] * SR)
    m = min(len(x), N - i0)
    vo[i0:i0 + m] += x[:m]
vo = sosfilt(hp(85), vo)
vo += sosfilt(bp(2500, 6000), vo) * 0.35          # presence
env = np.abs(vo)
a_att, a_rel = np.exp(-1 / (0.005 * SR)), np.exp(-1 / (0.12 * SR))
lev = np.zeros(N)                                   # gentle compression
acc = 0.0
for i in range(0, N, 48):                           # 1 ms control rate
    v = env[i:i + 48].max()
    acc = a_att * acc + (1 - a_att) * v if v > acc else a_rel * acc + (1 - a_rel) * v
    lev[i:i + 48] = acc
gr = np.minimum(1.0, (0.12 / np.maximum(lev, 1e-6)) ** 0.5)
vo = vo * gr
vo /= np.max(np.abs(vo)) + 1e-9
# ducking envelope from the voice
denv = np.convolve(np.abs(vo), np.ones(int(0.03 * SR)) / int(0.03 * SR), mode='same')
duckc = np.clip(denv / 0.08, 0, 1)
k = int(0.25 * SR)
duckc = np.convolve(duckc, np.ones(k) / k, mode='same')
duckc = np.clip(duckc * 1.6, 0, 1)

# ------------------------------------------------------------ mix
duck = np.ones(N)
dk = 1 - 0.45 * np.exp(-tt(0.25) * 18)
for k0 in kicks:
    i = int(k0 * SR)
    m = min(len(dk), N - i)
    duck[i:i + m] = np.minimum(duck[i:i + m], dk[:m])
music *= duck
music *= 1 - 0.72 * duckc        # about -11 dB under the narrator
engine *= 1 - 0.6 * duckc
sfx *= 1 - 0.45 * duckc

ir_t = tt(2.2)
ir = np.vstack([rng.standard_normal(len(ir_t)), rng.standard_normal(len(ir_t))]) * np.exp(-ir_t * 3.2)
ir[:, : int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
ir = np.vstack([sosfilt(lp(5000), ir[0]), sosfilt(lp(5000), ir[1])]) * 0.012
rev = np.vstack([fftconvolve(send[0], ir[0])[:N], fftconvolve(send[1], ir[1])[:N]]) * (1 - 0.5 * duckc)

bed = music * 0.5 + sfx * 0.7 + engine * 0.6 + rev * 0.8
bed = np.vstack([sosfilt(hp(25), bed[0]), sosfilt(hp(25), bed[1])])
bed /= np.max(np.abs(bed)) + 1e-9
mix = bed * 0.42 + np.vstack([vo, vo]) * 0.62
fade = np.ones(N)
fade[-int(1.0 * SR):] = np.linspace(1, 0, int(1.0 * SR)) ** 2
fade[: int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
mix *= fade
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.4) / np.tanh(1.4) * 0.95

out = sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav'
with wave.open(out, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype('<i2').tobytes())
speech = denv > 0.02
ratio = 10 * np.log10(np.mean((vo * 0.62)[speech] ** 2) / np.mean((bed * 0.42)[:, speech] ** 2))
print(f'wrote {out}: {DUR:.1f}s, voice sits {ratio:.1f} dB above the bed while speaking')
