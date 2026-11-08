"""Soundtrack for the BMW M5 film, synthesised from scratch.

Music (pads, bass, drums, bells), a V8 engine model driven by an rpm
timeline, an electric-motor whine, rain, birds and UI sound effects, all
timed to the scenes in film.html.

    python3 audio.py out/soundtrack.wav
"""
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
DUR = 103.0
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
    t = tt(d)
    return 2.0 * ((f * t + phase) % 1.0) - 1.0


def adsr(n, a=0.01, r=0.1, sustain=1.0):
    e = np.full(n, sustain)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    na = min(na, n)
    e[:na] = np.linspace(0, sustain, na)
    nr = min(nr, n)
    e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def place(buf, t0, sig, gain=1.0, pan=0.0):
    """Mix a mono signal into a stereo buffer at time t0 with equal-power pan."""
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    sig = sig[: N - i0]
    a = (pan + 1) * np.pi / 4
    buf[0, i0:i0 + len(sig)] += sig * gain * np.cos(a)
    buf[1, i0:i0 + len(sig)] += sig * gain * np.sin(a)


NOTE = {}
for i, nm in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']):
    for octv in range(0, 8):
        NOTE[f'{nm}{octv}'] = 440.0 * 2 ** ((i - 9) / 12 + (octv - 4))

CHORDS = {
    'Am': ['A2', 'C3', 'E3', 'A3'], 'F': ['F2', 'A2', 'C3', 'F3'], 'C': ['C3', 'E3', 'G3', 'C4'],
    'G': ['G2', 'B2', 'D3', 'G3'], 'Em': ['E2', 'G2', 'B2', 'E3'], 'Dm': ['D3', 'F3', 'A3', 'D4'],
}
ROOT = {'Am': 'A1', 'F': 'F1', 'C': 'C2', 'G': 'G1', 'Em': 'E1', 'Dm': 'D2'}

music = np.zeros((2, N))
send = np.zeros((2, N))   # reverb send
sfx = np.zeros((2, N))
kicks = []


# ------------------------------------------------------------ instruments
def kick(t0, g=1.0):
    d = 0.45
    t = tt(d)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    s[: int(0.004 * SR)] += noise(0.004) * 0.4
    place(music, t0, np.tanh(s * 1.6) * 0.75, g)
    kicks.append(t0)


def clap(t0, g=1.0):
    d = 0.35
    n = sosfilt(bp(900, 5000), noise(d))
    e = np.exp(-tt(d) * 18)
    for k in (0.0, 0.011, 0.022):  # flam
        e += np.roll(np.exp(-tt(d) * 60), int(k * SR)) * 0.6
    s = n * e * 0.35 + np.sin(2 * np.pi * 190 * tt(d)) * np.exp(-tt(d) * 30) * 0.3
    place(music, t0, s, g)
    place(send, t0, s, g * 0.5)


def hat(t0, g=1.0, open_=False, pan=0.15):
    d = 0.3 if open_ else 0.06
    s = sosfilt(hp(7000), noise(d)) * np.exp(-tt(d) * (10 if open_ else 70))
    place(music, t0, s * 0.3, g, pan)


def bass(t0, note, d, g=1.0, cutoff=420):
    f = NOTE[note]
    s = saw(f, d) * 0.6 + saw(f * 1.004, d, 0.3) * 0.4
    s = sosfilt(lp(cutoff), s)
    s += np.sin(2 * np.pi * f * tt(d)) * 0.7
    s *= adsr(len(s), 0.005, 0.05) * np.exp(-tt(d) * 2.5)
    place(music, t0, s * 0.32, g)


def pad(t0, chord, d, g=1.0, cutoff=1500, up=1):
    out = np.zeros(int(d * SR))
    for i, nm in enumerate(CHORDS[chord]):
        f = NOTE[nm] * up
        for det, ph in ((0.997, 0.1), (1.0, 0.5), (1.003, 0.8)):
            out += saw(f * det, d, ph + i * 0.13)
    out = sosfilt(lp(cutoff), out) / 12
    out *= adsr(len(out), min(0.6, d / 3), min(0.8, d / 3))
    s = np.vstack([out, np.roll(out, 211)])  # slight stereo width
    i0 = int(t0 * SR)
    m = min(len(out), N - i0)
    music[:, i0:i0 + m] += s[:, :m] * 0.5 * g
    send[:, i0:i0 + m] += s[:, :m] * 0.35 * g


def bell(t0, note, g=1.0, pan=0.0, d=1.6):
    f = NOTE[note]
    t = tt(d)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3)
         + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 5)
         + 0.25 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 8)
         + 0.12 * np.sin(2 * np.pi * 4.2 * f * t) * np.exp(-t * 12))
    s *= adsr(len(s), 0.002, 0.05)
    place(music, t0, s * 0.2, g, pan)
    place(send, t0, s * 0.18, g * 0.8, pan)


def riser(t0, d, g=1.0):
    t = tt(d)
    n = noise(d)
    lo = sosfilt(bp(300, 1500), n)
    hi = sosfilt(bp(1500, 9000), n)
    x = t / d
    s = (lo * (1 - x) + hi * x) * x ** 2
    f = 200 + 1400 * x ** 2
    s += np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 * x ** 2
    place(sfx, t0, s * 0.35, g)
    place(send, t0, s * 0.2, g)


def whoosh(t0, d=0.7, g=1.0, pan_from=-0.6, pan_to=0.6):
    t = tt(d)
    x = t / d
    n = noise(d)
    s = (sosfilt(bp(200, 900), n) * np.clip(1 - x * 1.6, 0, 1)
         + sosfilt(bp(900, 4000), n) * np.sin(np.pi * x)
         + sosfilt(bp(4000, 12000), n) * np.clip(x * 1.6 - 0.6, 0, 1))
    s *= np.sin(np.pi * x) ** 1.5
    # pan sweep: render in 8 chunks
    m = len(s)
    for k in range(8):
        a, b = k * m // 8, (k + 1) * m // 8
        place(sfx, t0 + a / SR, s[a:b] * 0.32, g, pan_from + (pan_to - pan_from) * (k + 0.5) / 8)


def impact(t0, g=1.0):
    d = 3.0
    t = tt(d)
    f = 32 + 70 * np.exp(-t * 10)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    s += sosfilt(lp(2500), noise(d)) * np.exp(-t * 9) * 0.5
    s += sosfilt(hp(5000), noise(d)) * np.exp(-t * 2.5) * 0.12  # crash shimmer
    place(sfx, t0, np.tanh(s * 1.3) * 0.75, g)
    place(send, t0, s * 0.4, g)


def thump(t0, g=1.0):
    d = 0.35
    t = tt(d)
    s = np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 25)) * t) * np.exp(-t * 11)
    place(sfx, t0, s * 0.8, g)


def click(t0, g=1.0, f=3000, pan=0.0):
    d = 0.03
    s = sosfilt(bp(f * 0.7, f * 1.4), noise(d)) * np.exp(-tt(d) * 220)
    place(sfx, t0, s * 0.5, g, pan)


def blip(t0, f, g=1.0):
    d = 0.18
    t = tt(d)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 22) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 35)
    place(sfx, t0, s * 0.18, g)
    place(send, t0, s * 0.1, g)


# ------------------------------------------------------------ arrangement
def groove(start, end, prog, kick_from=None, kick_every=1, clap_from=None, hat_from=None,
           hat_div=2, bass_div=2, bass_from=None, arp_from=None, pad_g=1.0,
           g=1.0, cutoff=1500, bass_cut=420):
    """Arrange a section on its own 120 bpm grid (beat 0.5 s, bar 2 s)."""
    bar = 2.0
    nbars = int(np.ceil((end - start) / bar))
    for b in range(nbars):
        t0 = start + b * bar
        ch = prog[b % len(prog)]
        d = min(bar, end - t0)
        if pad_g > 0:
            pad(t0, ch, d + 0.4, pad_g * g, cutoff)
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
                if hat_from is not None and th >= hat_from and th < end:
                    if hat_div == 2 and h == 0:
                        continue  # off-beats only
                    hat(th, g * (0.8 if h % 2 else 1.0), open_=(hat_div == 2 and beat == 3))
            if bass_from is not None and tb >= bass_from:
                for k in range(bass_div):
                    tk = tb + k * 0.5 / bass_div
                    if tk < end:
                        bass(tk, ROOT[ch], 0.5 / bass_div * 0.95, g, bass_cut)
        if arp_from is not None and t0 + bar > arp_from:
            for k in range(16):
                ta = t0 + k * 0.125
                if arp_from <= ta < end:
                    nm = CHORDS[ch][[1, 2, 3, 2][k % 4]]
                    bell(ta, nm[:-1] + str(int(nm[-1]) + 2), g * 0.55, pan=0.35 * np.sin(k))


# 0 – 6.2 cold open: drone, heartbeat thumps, riser
pad(0.0, 'Am', 6.4, 0.7, 500)
for k, tb in enumerate([0.6, 1.8, 3.0, 4.2, 5.4]):
    thump(tb, 0.9)
    thump(tb + 0.22, 0.55)
riser(3.9, 2.3, 1.0)
impact(6.2, 1.0)

# 6.2 – 13.5 title groove
groove(6.2, 13.5, ['Am', 'F', 'C', 'G'], kick_from=6.2, hat_from=8.2, bass_from=6.2, bass_div=2, g=0.85)
riser(12.3, 1.2, 0.7)
whoosh(13.3, 0.7)

# 13.5 – 28.5 origin + chart
impact(13.5, 0.45)
pad(13.5, 'Am', 1.9, 1.1, 1100)
groove(15.1, 18.3, ['F', 'G'], arp_from=15.1, g=0.85, cutoff=1300)
for i in range(26):  # typewriter
    click(15.25 + i / 36, 0.35, 4200, -0.2)
groove(18.3, 28.5, ['Am', 'F', 'C', 'G'], kick_from=18.3, kick_every=2, hat_from=20.3, bass_from=18.3,
       bass_div=1, arp_from=20.3, g=0.7)
for i in range(7):
    blip(18.9 + i * 0.85, NOTE[['A4', 'C5', 'D5', 'E5', 'G5', 'A5', 'C6'][i]], 1.2 if i == 6 else 0.9)
bell(25.5, 'E5', 1.2)
whoosh(28.3, 0.6)

# 28.5 – 45 anatomy
impact(28.5, 0.45)
pad(28.5, 'Am', 1.7, 1.1, 1100)
groove(30.1, 45, ['Am', 'Am', 'F', 'G'], kick_from=31.5, clap_from=36.4, hat_from=38.8, hat_div=4,
       bass_from=30.1, bass_div=4, g=0.75, cutoff=1200, bass_cut=600)
for t0 in (31.5, 34.0, 36.4, 38.8):
    blip(t0, NOTE['E6'], 0.7)
riser(43.0, 2.0, 1.0)
impact(45.0, 1.0)

# 45 – 57.5 numbers
pad(45.0, 'Am', 1.7, 0.8, 900)
groove(46.6, 57.5, ['Am', 'F', 'C', 'G'], kick_from=46.6, clap_from=46.6, hat_from=46.6, hat_div=4,
       bass_from=46.6, bass_div=2, g=0.9, cutoff=1800)
for t0 in (46.7, 49.0, 51.2, 53.4, 55.6):
    whoosh(t0 - 0.25, 0.5, 0.6, 0.6, -0.2)
whoosh(57.3, 0.6)

# 57.5 – 85.5 a day in Britain
impact(57.5, 0.35)
pad(57.5, 'C', 1.6, 1.1, 1100)
groove(59.0, 64.5, ['C', 'G', 'Am'], arp_from=59.6, g=0.75, cutoff=1100)
groove(64.5, 71.0, ['C', 'G', 'Am', 'F'], kick_from=64.5, hat_from=65.5, bass_from=64.5, bass_div=2,
       arp_from=66.5, g=0.55, cutoff=1300)
groove(71.0, 76.0, ['Am', 'F', 'C'], arp_from=72.0, g=0.7, cutoff=1000)
groove(76.0, 82.0, ['Am', 'Am', 'F', 'G'], kick_from=76.5, hat_from=78.4, hat_div=4, bass_from=76.0, bass_div=4,
       g=0.55, cutoff=1000, bass_cut=500)
groove(82.0, 85.5, ['F', 'G'], kick_from=82.0, kick_every=2, bass_from=82.0, g=0.6, cutoff=1600)
riser(84.0, 1.5, 0.8)
for t0 in (64.5, 71.0, 76.0, 82.0):
    whoosh(t0 - 0.3, 0.6, 0.6)
whoosh(83.2, 0.8, 0.9, 0.8, -0.8)  # Touring morph

# 85.5 – 96 why Britain
impact(85.5, 0.8)
pad(85.5, 'C', 1.7, 0.8, 1200)
groove(87.1, 96.0, ['C', 'G', 'Am', 'F'], kick_from=87.1, clap_from=89.1, hat_from=87.1, hat_div=4,
       bass_from=87.1, bass_div=2, arp_from=91.1, g=0.85, cutoff=2200)
for i in range(5):
    bell(87.35 + i * 1.2, ['C5', 'E5', 'G5', 'A5', 'C6'][i], 1.6)
whoosh(95.8, 0.6)

# 96 – 103 outro
pad(96.0, 'Am', 4.2, 0.7, 900)
riser(98.4, 1.6, 1.0)
impact(100.0, 1.1)
pad(100.0, 'Am', 3.0, 0.9, 1400)
for k, nm in enumerate(['A4', 'C5', 'E5', 'B5']):
    bell(100.05 + k * 0.09, nm, 1.0, pan=-0.3 + 0.2 * k, d=2.9)


# ------------------------------------------------------------ engine model
t = np.arange(N) / SR
rpm = np.zeros(N)
thr = np.zeros(N)
eng_g = np.zeros(N)
eng_pan = np.zeros(N)
speed = np.zeros(N)  # mph, for the electric whine
ev_g = np.zeros(N)
pops = []
shifts = []


def seg(a, b):
    return (t >= a) & (t < b)


def ramp(a, b, v0, v1, curve=1.0):
    m = seg(a, b)
    x = ((t[m] - a) / (b - a)) ** curve
    rpm[m] = v0 + (v1 - v0) * x


def blip_rev(t0, peak, idle=800, up=0.15, down=0.7):
    ramp(t0, t0 + up, idle, peak, 0.6)
    ramp(t0 + up, t0 + up + down, peak, idle, 0.5)
    thr[seg(t0, t0 + up)] = 1.0
    pops.extend(t0 + up + 0.1 + rng.random(4) * down * 0.7)


def pull(a, gears, top=7000):
    """Full-throttle run through gears: list of (duration, start_rpm)."""
    ts = a
    for d, r0 in gears:
        ramp(ts, ts + d, r0, top, 0.8)
        thr[seg(ts, ts + d)] = 1.0
        shifts.append(ts + d)
        ts += d
    return ts


# cold open: idle with three blips
rpm[seg(0, 6.2)] = 760
eng_g[seg(0, 6.2)] = 0.55
for b in (1.0, 2.95, 4.65):
    blip_rev(b, 3400, 760)
# title: arrives on the overrun, idles, launches away
ramp(6.2, 8.4, 4200, 900, 0.7)
for b in (6.9, 7.5):
    ramp(b, b + 0.08, rpm[int(b * SR)], rpm[int(b * SR)] + 1100)
    ramp(b + 0.08, b + 0.5, rpm[int(b * SR)] + 1100, rpm[int((b + 0.5) * SR)])
pops.extend(6.3 + rng.random(10) * 1.9)
rpm[seg(8.4, 12.55)] = 820
eng_g[seg(6.2, 12.55)] = 0.75
eng_pan[seg(6.2, 8.4)] = np.linspace(-0.9, 0.0, seg(6.2, 8.4).sum())
pull(12.55, [(0.55, 2400), (0.6, 5000)])
eng_g[seg(12.55, 13.8)] = np.linspace(0.85, 0.0, seg(12.55, 13.8).sum())
eng_pan[seg(12.55, 13.8)] = np.linspace(0.0, 1.0, seg(12.55, 13.8).sum())

# numbers: blips, then the 0–62 / top-speed run
rpm[seg(46.5, 51.2)] = 850
eng_g[seg(46.5, 51.2)] = 0.6
blip_rev(46.75, 6800, 850, 0.18, 0.9)
blip_rev(49.05, 5200, 850, 0.15, 0.8)
end = pull(51.2, [(0.6, 3200), (0.75, 4700), (0.85, 5000), (1.0, 5300), (1.2, 5500)])
ramp(end, 55.6, 5600, 6600)
thr[seg(end, 55.6)] = 1.0
eng_g[seg(51.2, 55.6)] = 1.0
eng_g[seg(55.6, 56.0)] = np.linspace(1.0, 0.0, seg(55.6, 56.0).sum())
rpm[seg(55.6, 56.0)] = np.linspace(6600, 2500, seg(55.6, 56.0).sum())
speed[seg(55.6, 57.5)] = np.interp(t[seg(55.6, 57.5)], [55.6, 56.6, 57.5], [190, 87, 87])
ev_g[seg(55.6, 57.5)] = np.interp(t[seg(55.6, 57.5)], [55.6, 55.9, 57.2, 57.5], [0, 0.5, 0.5, 0])

# dawn village: EV only
speed[seg(59.0, 64.5)] = 28
ev_g[seg(59.0, 64.5)] = np.interp(t[seg(59.0, 64.5)], [59.0, 59.6, 64.0, 64.5], [0, 0.35, 0.35, 0])

# Wales: spirited run through hairpins
w0 = 76.6
rpm[seg(76.0, w0)] = 1500
end = pull(w0, [(0.7, 3500), (0.8, 4800)])
ramp(end, end + 0.9, 5200, 3000)  # braking, downshift blips
for b in (end + 0.15, end + 0.45):
    ramp(b, b + 0.06, 4200, 5600)
    ramp(b + 0.06, b + 0.3, 5600, 3800)
pops.extend(end + rng.random(8) * 0.9)
end = pull(end + 0.9, [(0.8, 3200), (0.9, 4900)])
ramp(end, end + 0.8, 5500, 2800)
pops.extend(end + rng.random(6) * 0.8)
end2 = pull(end + 0.8, [(0.9, 3000)])
ramp(end2, 82.0, 5000, 2000)
eng_g[seg(76.0, 82.0)] = np.interp(t[seg(76.0, 82.0)], [76.0, 76.6, 81.5, 82.0], [0.2, 0.55, 0.55, 0.0])
eng_pan[seg(76.0, 82.0)] = 0.4 * np.sin(t[seg(76.0, 82.0)] * 1.7)

# outro: idle, then launch out of frame
rpm[seg(96.0, 97.0)] = 850
end = pull(97.0, [(0.55, 3000), (0.7, 5000), (0.8, 5300)])
eng_g[seg(96.0, 99.6)] = np.interp(t[seg(96.0, 99.6)], [96.0, 96.4, 97.0, 97.8, 99.6], [0, 0.6, 0.65, 1.0, 0.0])
eng_pan[seg(97.0, 99.6)] = np.linspace(0, 1, seg(97.0, 99.6).sum())

# smooth rpm slightly (keep shifts snappy)
k = int(0.012 * SR)
rpm = np.convolve(rpm, np.ones(k) / k, mode='same')
rpm = np.maximum(rpm, 1)
thr = np.convolve(thr, np.ones(k * 4) / (k * 4), mode='same')

active = eng_g > 0.001
fc = rpm / 60.0
phi = 2 * np.pi * np.cumsum(fc) / SR
eng = np.zeros(N)
for o, a, load in [(0.5, 0.35, 0.2), (1, 0.45, 0.2), (1.5, 0.3, 0.3), (2, 0.75, 0.4), (3, 0.3, 0.5), (4, 1.0, 0.6),
                   (5, 0.25, 0.8), (6, 0.4, 0.9), (8, 0.45, 1.2), (10, 0.18, 1.4), (12, 0.15, 1.6), (16, 0.08, 2.0)]:
    eng += a * (1 + load * thr) * np.sin(o * phi + o * 1.3)
pulse = (0.5 + 0.5 * np.sin(4 * phi)) ** 3
roar = sosfilt(lp(2200), rng.standard_normal(N)) * pulse * (0.5 + 1.6 * thr)
eng = eng * 0.55 + roar * 1.2
eng = np.tanh(eng * (0.45 + 0.9 * thr))
# turbo whistle
tw = np.sin(2 * np.pi * np.cumsum(900 + rpm * 0.55) / SR) * 0.035 * thr * (rpm / 7000)
eng = sosfilt(lp(4200), eng + tw)
eng = sosfilt(hp(28), eng)
eng *= eng_g * active

# overrun pops and shift cracks
for p in pops:
    d = 0.025 + rng.random() * 0.03
    s = sosfilt(lp(3500), noise(d)) * np.exp(-tt(d) * 90) * (0.6 + rng.random() * 0.8)
    s += np.sin(2 * np.pi * 90 * tt(d)) * np.exp(-tt(d) * 60) * 0.5
    i = min(N - 1, int(p * SR))
    eng[i:i + len(s)] += s[: N - i] * 0.9 * max(eng_g[i], 0.3)
for p in shifts:
    d = 0.06
    s = sosfilt(bp(200, 3000), noise(d)) * np.exp(-tt(d) * 70)
    i = min(N - 1, int(p * SR))
    eng[i:i + len(s)] += s[: N - i] * 1.1 * eng_g[i]

engine = np.zeros((2, N))
a = (eng_pan + 1) * np.pi / 4
engine[0] = eng * np.cos(a)
engine[1] = eng * np.sin(a)
place(send, 0, eng * 0.12, 1.0)

# electric whine
fw = 140 + speed * 9.5
ph = 2 * np.pi * np.cumsum(fw) / SR
ew = (np.sin(ph) + 0.4 * np.sin(2.07 * ph) + 0.2 * np.sin(3.1 * ph)) * ev_g * 0.18
ew += sosfilt(bp(300, 1200), rng.standard_normal(N)) * ev_g * 0.03
engine += ew * 0.7

# ------------------------------------------------------------ foley
# birds at dawn
for _ in range(16):
    t0 = 59.3 + rng.random() * 4.8
    pan = rng.uniform(-0.8, 0.8)
    base = rng.uniform(2800, 4600)
    for c in range(rng.integers(2, 6)):
        d = rng.uniform(0.05, 0.12)
        tc = tt(d)
        f = base + rng.uniform(-600, 900) * np.sin(np.pi * tc / d) + 400 * np.sin(2 * np.pi * 28 * tc)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tc / d) ** 2
        place(sfx, t0 + c * rng.uniform(0.09, 0.16), s * 0.08, 1.0, pan)
# crickets at night
for k in range(int(4.6 / 0.42)):
    t0 = 71.2 + k * 0.42
    for c in range(3):
        d = 0.03
        s = np.sin(2 * np.pi * 4300 * tt(d)) * np.sin(np.pi * tt(d) / d)
        place(sfx, t0 + c * 0.045, s * 0.025, 1.0, -0.5 if k % 2 else 0.5)
# charging: plug click, hum, chime
click(71.95, 1.4, 1800)
click(71.97, 1.0, 900)
d = 3.3
hum = (np.sin(2 * np.pi * 100 * tt(d)) + 0.3 * np.sin(2 * np.pi * 300 * tt(d))) * adsr(int(d * SR), 0.3, 0.4) * 0.03
place(sfx, 72.0, hum, 1.0, 0.3)
bell(75.25, 'E5', 1.3)
bell(75.4, 'A5', 1.3)
# rain in Wales
d = 6.2
r = sosfilt(bp(400, 7000), noise(d)) * 0.07 * adsr(int(d * SR), 0.5, 0.6)
place(sfx, 75.9, r, 1.0, -0.2)
place(sfx, 75.9, np.roll(r, 3001), 1.0, 0.2)
for _ in range(220):
    click(76.0 + rng.random() * 5.9, rng.uniform(0.1, 0.35), rng.uniform(2000, 6000), rng.uniform(-0.9, 0.9))
# check-mark ticks, chart counter ticks
for i in range(5):
    click(87.4 + i * 1.2, 0.8, 2500)
# clock flips in the Britain chapter
for t0 in (59.2, 64.7, 71.2, 73.8, 76.2):
    click(t0, 0.6, 2200, 0.7)
    click(t0 + 0.05, 0.4, 1500, 0.7)

# ------------------------------------------------------------ mix
# sidechain duck on the music bus
duck = np.ones(N)
dk = 1 - 0.45 * np.exp(-tt(0.25) * 18)
for k0 in kicks:
    i = int(k0 * SR)
    m = min(len(dk), N - i)
    duck[i:i + m] = np.minimum(duck[i:i + m], dk[:m])
music *= duck

# music level automation (dip under the engine runs)
lvl = np.interp(t, [0, 12.4, 12.6, 13.5, 51.0, 51.3, 55.4, 55.8, 96.8, 97.1, 98.8, 99.3, 103],
                   [1, 1, 0.65, 1, 1, 0.45, 0.45, 1, 1, 0.6, 0.6, 1, 1])
music *= lvl

ir_d = 2.4
ir_t = tt(ir_d)
ir = np.vstack([rng.standard_normal(len(ir_t)), rng.standard_normal(len(ir_t))]) * np.exp(-ir_t * 3.2)
ir[:, : int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
ir = np.vstack([sosfilt(lp(5000), ir[0]), sosfilt(lp(5000), ir[1])]) * 0.012
rev = np.vstack([fftconvolve(send[0], ir[0])[:N], fftconvolve(send[1], ir[1])[:N]])

mix = music * 0.9 + sfx * 0.9 + engine * 0.75 + rev
mix = np.vstack([sosfilt(hp(25), mix[0]), sosfilt(hp(25), mix[1])])
fade = np.ones(N)
fade[-int(1.0 * SR):] = np.linspace(1, 0, int(1.0 * SR)) ** 2
fade[: int(0.05 * SR)] = np.linspace(0, 1, int(0.05 * SR))
mix *= fade
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.6) / np.tanh(1.6) * 0.95

out = sys.argv[1] if len(sys.argv) > 1 else 'soundtrack.wav'
pcm = (np.clip(mix.T, -1, 1) * 32767).astype('<i2')
with wave.open(out, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f'wrote {out}: {DUR:.1f}s, peak-normalised')
