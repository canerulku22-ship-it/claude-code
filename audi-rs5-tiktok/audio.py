"""Soundtrack for the Audi RS5 TikTok review: music, a twin-turbo V6 engine model,
the electric motor's whine, and sound effects synthesised from scratch, mixed with
the Chatterbox narration from out/vo/. Every cue is placed from the measured
voiceover timing in out/vo/durations.json (written by voiceover.py), using the
same word-timing estimate as film.html.

    python3 audio.py out/soundtrack.wav
"""
import json
import os
from types import SimpleNamespace
import re
import sys
import wave

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
src = open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read()
TL = json.loads(src[src.index('{'):src.rindex('}') + 1])
VOJ = json.load(open(os.path.join(HERE, 'out', 'vo', 'durations.json')))
TIM, DUR = VOJ['timing'], VOJ['duration']
N = int(SR * DUR)
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- timing (mirrors film.html)
VO = {l['id']: {**l, 'at': TIM[l['id']]['at'], 'on': TIM[l['id']]['at'] + TIM[l['id']]['on'],
                'off': TIM[l['id']]['at'] + TIM[l['id']]['off']} for l in TL['vo']}
SPOKEN = {'RS5,': 12, 'RS.': 6, '2.9-litre': 14, 'V6,': 8, '639': 32, '825': 32, '0–62': 18, '3.6': 14, '50': 8, '2.4': 12, '£89,400': 40}


def wt(i, word):
    line = VO[i]
    words = line['text'].split(' ')
    wts = [SPOKEN.get(re.sub(r'[.,?:!]+$', '', w), len(re.sub(r"[^\w’']", '', w)) + 2) + (6 if re.search(r'[.,?:]$', w) else 0) for w in words]
    acc, total = 0, sum(wts)
    for w, k in zip(words, wts):
        if word.lower() in w.lower():
            return line['on'] + (line['off'] - line['on']) * acc / total
        acc += k
    return line['on']


ON = {i: VO[i]['on'] for i in VO}
OFF = {i: VO[i]['off'] for i in VO}
CUT = [0] + [ON[i] - 0.3 for i in ['02', '03', '04', '05', '06', '07', '08', '09']] + [DUR]
B = SimpleNamespace(brand=wt('01', 'brand-new'), rs5=wt('01', 'RS5'), phev=wt('01', 'plug-in'),
                    v6=wt('02', 'V6'), motor=wt('02', 'electric'),
                    ps=wt('03', '639'), nm=wt('03', '825'), s36=wt('03', '3.6'),
                    world=wt('04', 'world-first'), shuffle=wt('04', 'shuffles'), ms=wt('04', 'five'),
                    ev=wt('05', '50'), t24=wt('06', '2.4'), price=wt('07', '£89,400'),
                    fast=wt('08', 'Ridiculously'), clever=wt('08', 'seriously'), weight=wt('08', 'weight'),
                    comments=wt('09', 'comments'))


# ---------------------------------------------------------------- helpers
def lp(fc, o=2): return butter(o, fc, 'low', fs=SR, output='sos')
def hp(fc, o=2): return butter(o, fc, 'high', fs=SR, output='sos')
def bp(lo, hi, o=2): return butter(o, [lo, hi], 'band', fs=SR, output='sos')
def tt(d): return np.arange(int(d * SR)) / SR
def noise(d): return rng.standard_normal(int(d * SR))
def saw(f, d, ph=0.0): return 2.0 * ((f * tt(d) + ph) % 1.0) - 1.0


def adsr(n, a=0.01, r=0.1):
    e = np.ones(n)
    na, nr = min(n, max(1, int(a * SR))), min(n, max(1, int(r * SR)))
    e[:na] = np.linspace(0, 1, na)
    e[n - nr:] *= np.linspace(1, 0, nr)
    return e


def place(buf, t0, sig, gain=1.0, pan=0.0):
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
    for o in range(8):
        NOTE[f'{nm}{o}'] = 440.0 * 2 ** ((i - 9) / 12 + (o - 4))
CHORDS = {'Dm': ['D3', 'F3', 'A3', 'D4'], 'Bb': ['A#2', 'D3', 'F3', 'A#3'], 'F': ['F2', 'A2', 'C3', 'F3'], 'C': ['C3', 'E3', 'G3', 'C4'],
          'Gm': ['G2', 'A#2', 'D3', 'G3'], 'Am': ['A2', 'C3', 'E3', 'A3']}
ROOT = {'Dm': 'D2', 'Bb': 'A#1', 'F': 'F1', 'C': 'C2', 'Gm': 'G1', 'Am': 'A1'}
music, send, sfx = np.zeros((2, N)), np.zeros((2, N)), np.zeros((2, N))
kicks = []


def kick(t0, g=1.0):
    t = tt(0.45)
    s = np.sin(2 * np.pi * np.cumsum(45 + 120 * np.exp(-t * 30)) / SR) * np.exp(-t * 7)
    place(music, t0, np.tanh(s * 1.7) * 0.75, g)
    kicks.append(t0)


def snare(t0, g=1.0):
    d = 0.3
    s = sosfilt(bp(1200, 7000), noise(d)) * np.exp(-tt(d) * 20) * 0.4 + np.sin(2 * np.pi * 200 * tt(d)) * np.exp(-tt(d) * 25) * 0.35
    place(music, t0, s, g)
    place(send, t0, s, g * 0.4)


def hat(t0, g=1.0, open_=False):
    d = 0.28 if open_ else 0.05
    place(music, t0, sosfilt(hp(7500), noise(d)) * np.exp(-tt(d) * (11 if open_ else 75)) * 0.28, g, 0.2)


def bass(t0, note, d, g=1.0, cutoff=500):
    f = NOTE[note]
    s = sosfilt(lp(cutoff), saw(f, d) * 0.6 + saw(f * 1.005, d, 0.3) * 0.4) + np.sin(2 * np.pi * f * tt(d)) * 0.7
    place(music, t0, s * adsr(len(s), 0.004, 0.04) * np.exp(-tt(d) * 2.2) * 0.32, g)


def pad(t0, chord, d, g=1.0, cutoff=1500):
    out = np.zeros(int(d * SR))
    for i, nm in enumerate(CHORDS[chord]):
        for det, ph in ((0.996, 0.1), (1.0, 0.5), (1.004, 0.8)):
            out += saw(NOTE[nm] * det, d, ph + i * 0.13)
    out = sosfilt(lp(cutoff), out) / 12 * adsr(len(out), min(0.5, d / 3), min(0.7, d / 3))
    s = np.vstack([out, np.roll(out, 223)])
    i0 = int(t0 * SR)
    m = min(len(out), N - i0)
    if m > 0:
        music[:, i0:i0 + m] += s[:, :m] * 0.5 * g
        send[:, i0:i0 + m] += s[:, :m] * 0.35 * g


def pluck(t0, note, g=1.0, pan=0.0):
    f, t = NOTE[note], tt(0.6)
    s = (saw(f, 0.6) * 0.5 + np.sin(2 * np.pi * f * t)) * np.exp(-t * 9)
    s = sosfilt(lp(3200), s)
    place(music, t0, s * 0.16, g, pan)
    place(send, t0, s * 0.12, g, pan)


def bell(t0, note, g=1.0, pan=0.0, d=1.6):
    f, t = NOTE[note], tt(d)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 5)
         + 0.25 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 8)) * adsr(int(d * SR), 0.002, 0.05)
    place(music, t0, s * 0.2, g, pan)
    place(send, t0, s * 0.18, g, pan)


def groove(start, end, prog, kick_from=None, snare_from=None, hat_from=None, hat_div=2, bass_from=None, bass_div=2,
           arp_from=None, pad_g=1.0, g=1.0, cutoff=1500):
    for b in range(int(np.ceil((end - start) / 2.0))):
        t0 = start + b * 2.0
        ch = prog[b % len(prog)]
        if pad_g > 0:
            pad(t0, ch, min(2.0, end - t0) + 0.4, pad_g * g, cutoff)
        for beat in range(4):
            tb = t0 + beat * 0.5
            if tb >= end:
                break
            if kick_from is not None and tb >= kick_from and (beat in (0, 2) or (beat == 3 and b % 2)):
                kick(tb + (0.25 if beat == 3 else 0), g)
            if snare_from is not None and tb >= snare_from and beat in (1, 3):
                snare(tb, g * 0.85)
            for h in range(hat_div):
                th = tb + h * 0.5 / hat_div
                if hat_from is not None and hat_from <= th < end:
                    hat(th, g * (0.7 if h % 2 else 1.0), open_=(hat_div == 2 and h == 1 and beat == 3))
            if bass_from is not None and tb >= bass_from:
                for k in range(bass_div):
                    tk = tb + k * 0.5 / bass_div
                    if tk < end:
                        bass(tk, ROOT[ch], 0.5 / bass_div * 0.9, g)
        if arp_from is not None:
            for k in range(8):
                ta = t0 + k * 0.25
                if arp_from <= ta < end:
                    nm = CHORDS[ch][[1, 2, 3, 2, 1, 3, 2, 3][k]]
                    pluck(ta, nm[:-1] + str(int(nm[-1]) + 1), g * 0.8, pan=0.4 * np.sin(k * 1.3))


def riser(t0, d, g=1.0):
    t = tt(d)
    x, n = t / d, noise(d)
    s = (sosfilt(bp(300, 1500), n) * (1 - x) + sosfilt(bp(1500, 9000), n) * x) * x ** 2
    s += np.sin(2 * np.pi * np.cumsum(200 + 1400 * x ** 2) / SR) * 0.15 * x ** 2
    place(sfx, t0, s * 0.35, g)
    place(send, t0, s * 0.2, g)


def whoosh(t0, d=0.5, g=1.0, p0=-0.6, p1=0.6):
    x, n = tt(d) / d, noise(d)
    s = (sosfilt(bp(200, 900), n) * np.clip(1 - x * 1.6, 0, 1) + sosfilt(bp(900, 4000), n) * np.sin(np.pi * x)
         + sosfilt(bp(4000, 12000), n) * np.clip(x * 1.6 - 0.6, 0, 1)) * np.sin(np.pi * x) ** 1.5
    m = len(s)
    for k in range(8):
        a, b = k * m // 8, (k + 1) * m // 8
        place(sfx, t0 + a / SR, s[a:b] * 0.32, g, p0 + (p1 - p0) * (k + 0.5) / 8)


def impact(t0, g=1.0):
    t = tt(3.0)
    s = np.sin(2 * np.pi * np.cumsum(32 + 70 * np.exp(-t * 10)) / SR) * np.exp(-t * 2.2)
    s += sosfilt(lp(2500), noise(3.0)) * np.exp(-t * 9) * 0.5 + sosfilt(hp(5000), noise(3.0)) * np.exp(-t * 2.5) * 0.12
    place(sfx, t0, np.tanh(s * 1.3) * 0.75, g)
    place(send, t0, s * 0.4, g)


def click(t0, g=1.0, f=3000, pan=0.0):
    place(sfx, t0, sosfilt(bp(f * 0.7, f * 1.4), noise(0.03)) * np.exp(-tt(0.03) * 220) * 0.5, g, pan)


def blip(t0, f, g=1.0, pan=0.0):
    t = tt(0.18)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 22) + 0.3 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 35)
    place(sfx, t0, s * 0.18, g, pan)
    place(send, t0, s * 0.1, g, pan)


def shimmer(t0, d, f0, f1, g=1.0):
    t = tt(d)
    ph = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / d)) / SR
    s = (np.sin(ph) + 0.4 * np.sin(2 * ph)) * np.sin(np.pi * t / d) ** 2
    place(sfx, t0, s * 0.08, g)
    place(send, t0, s * 0.08, g)


def ticks(t0, d, g=0.5, f=3200):
    tk = t0
    while tk < t0 + d:
        click(tk, g, f, 0.2)
        tk += 0.02 + 0.08 * ((tk - t0) / d) ** 2


def squeal(t0, d, g=1.0, pan=0.0):
    t = tt(d)
    f = 1900 + 300 * np.sin(2 * np.pi * 3.3 * t) + 120 * np.sin(2 * np.pi * 11 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + sosfilt(bp(1500, 3800), noise(d)) * 0.6
    s *= adsr(len(s), 0.08, 0.4) * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * t))
    place(sfx, t0, s * 0.22, g, pan)





def ewhine(t0, d, f0, f1, g=1.0):   # the electric motor: a clean rising whine with a little inverter buzz
    t = tt(d)
    f = f0 + (f1 - f0) * (t / d) ** 0.8
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) + 0.25 * np.sin(2.01 * ph) + 0.08 * np.sign(np.sin(3 * ph))) * adsr(len(t), 0.2, 0.4)
    place(sfx, t0, sosfilt(lp(6000), s) * 0.05, g)


# ---------------------------------------------------------------- arrangement
pad(0.0, 'Dm', CUT[1] + 0.4, 0.6, 500)
riser(max(0, B.rs5 - 1.0), 1.0, 0.5)
impact(B.rs5, 0.9)
shimmer(B.rs5, 0.7, 400, 2400, 1.0)
click(B.phev, 0.8, 2600)
blip(B.phev, NOTE['A5'], 0.7)
groove(B.rs5 + 0.5, CUT[1], ['Dm', 'Bb'], hat_from=B.rs5 + 0.5, bass_from=B.rs5 + 0.5, pad_g=0, g=0.6)

groove(CUT[1], CUT[2], ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[1] + 0.2, hat_from=CUT[1], hat_div=4, bass_from=CUT[1], g=0.6, cutoff=1300)
blip(B.v6, NOTE['A5'], 0.7, -0.3)
blip(B.motor, NOTE['D6'], 0.7, 0.3)
ewhine(B.motor, 1.2, 600, 2400, 1.0)

groove(CUT[2], CUT[3], ['Dm', 'Bb'], kick_from=CUT[2], hat_from=CUT[2], bass_from=CUT[2], pad_g=0.45, g=0.5, cutoff=1500)
for t0 in (B.ps, B.nm, B.s36):
    ticks(t0, 0.6, 0.4)
impact(B.s36 + 0.05, 0.4)

groove(CUT[3], CUT[4], ['Gm', 'Dm', 'Bb', 'C'], kick_from=CUT[3], hat_from=CUT[3], hat_div=4, bass_from=CUT[3], arp_from=B.shuffle, g=0.62, cutoff=1500)
click(B.world, 0.9, 2400)
for k in range(10):                       # the 5 ms recalculation, as fast ticks
    click(B.ms + k * 0.05, 0.5, 4200, 0.3 * (-1) ** k)

pad(CUT[4], 'F', CUT[5] - CUT[4] + 0.4, 0.55, 700)          # EV: hushed
ewhine(CUT[4] + 0.1, CUT[5] - CUT[4] - 0.2, 900, 1700, 0.9)
shimmer(B.ev, 0.8, 600, 3000, 0.8)

groove(CUT[5], CUT[6], ['Dm', 'Bb'], kick_from=OFF['06'], bass_from=CUT[5], pad_g=0.4, g=0.45, cutoff=1100)
impact(OFF['06'] + 0.05, 0.9)             # the weight lands, just after it's said
impact(B.t24, 0.25)

groove(CUT[6], CUT[7], ['Bb', 'F'], kick_from=CUT[6], hat_from=CUT[6], bass_from=CUT[6], g=0.58, cutoff=1300)
ticks(B.price - 0.05, 0.7, 0.45)
bell(B.price + 0.6, 'F5', 1.0)

groove(CUT[7], CUT[8], ['Dm', 'Bb', 'C', 'Dm'], kick_from=CUT[7], snare_from=CUT[7], hat_from=CUT[7], hat_div=4, bass_from=CUT[7], g=0.72, cutoff=1900)
for t0, nm in ((B.fast, 'A5'), (B.clever, 'C6'), (B.weight, 'E5')):
    blip(t0, NOTE[nm], 0.8)
groove(CUT[8], DUR - 1.0, ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[8], hat_from=CUT[8], bass_from=CUT[8], arp_from=CUT[8], g=0.65, cutoff=1600)
blip(B.comments, NOTE['D6'], 1.0)
for k, nm in enumerate(['D5', 'F5', 'A5', 'E6']):
    bell(DUR - 2.2 + k * 0.09, nm, 0.9, pan=-0.3 + 0.2 * k, d=2.0)
for c, kind in zip(CUT[1:-1], ['zoom', 'whip', 'zoom', 'whip', 'stripe', 'whip', 'zoom', 'whip']):
    if kind == 'whip':
        whoosh(c - 0.22, 0.38, 0.8, 0.9, -0.9)
    elif kind == 'stripe':
        whoosh(c - 0.24, 0.45, 0.7, -0.8, 0.8)
    else:
        whoosh(c - 0.26, 0.4, 0.55, -0.2, 0.2)
        impact(c, 0.3)


# ---------------------------------------------------------------- engine: twin-turbo V6
t = np.arange(N) / SR
# (order, amplitude, extra under load): orders are multiples of crank speed. The five's
# firing order sits at 2.5x with strong half orders -> the warble; the six fires at 3x.
FIVE = [(0.5, 0.3, 0.4), (1, 0.25, 0.3), (1.5, 0.35, 0.5), (2, 0.2, 0.4), (2.5, 1.0, 0.6), (3.5, 0.2, 0.6), (5, 0.55, 1.0), (7.5, 0.25, 1.4), (10, 0.1, 1.6)]
SIX = [(1, 0.12, 0.2), (1.5, 0.18, 0.4), (3, 1.0, 0.5), (4.5, 0.15, 0.6), (6, 0.5, 1.0), (9, 0.28, 1.3), (12, 0.12, 1.6)]


class Engine:
    def __init__(self, orders, idle=850, redline=7000, whistle=0.05, rasp=2600):
        self.rpm, self.thr, self.g = np.full(N, float(idle)), np.zeros(N), np.zeros(N)
        self.orders, self.idle, self.red, self.whistle, self.rasp = orders, idle, redline, whistle, rasp
        self.pops, self.shifts, self.bov = [], [], []

    def seg(self, a, b):
        return (t >= a) & (t < b)

    def ramp(self, a, b, v0, v1, c=1.0):
        m = self.seg(a, b)
        self.rpm[m] = v0 + (v1 - v0) * ((t[m] - a) / (b - a)) ** c

    def gain(self, pts):
        m = self.seg(pts[0][0], pts[-1][0])
        self.g[m] = np.interp(t[m], [p[0] for p in pts], [p[1] for p in pts])

    def blip(self, t0, peak, up=0.14, down=0.6, bov=True):
        self.ramp(t0, t0 + up, self.idle, peak, 0.6)
        self.ramp(t0 + up, t0 + up + down, peak, self.idle, 0.5)
        self.thr[self.seg(t0, t0 + up)] = 1.0
        if bov:
            self.bov.append(t0 + up + 0.02)
        self.pops.extend(t0 + up + 0.08 + rng.random(3) * down * 0.6)

    def pull(self, a, gears, top=None, gap=0.0):
        top, ts = top or self.red - 200, a
        for d, r0 in gears:
            self.ramp(ts, ts + d, r0, top, 0.75)
            self.thr[self.seg(ts, ts + d)] = 1.0
            self.shifts.append(ts + d)
            ts += d + gap
        return ts

    def render(self):
        k = int(0.01 * SR)
        rpm = np.maximum(np.convolve(self.rpm, np.ones(k) / k, mode='same'), 1)
        thr = np.convolve(self.thr, np.ones(k * 4) / (k * 4), mode='same')
        phi = 2 * np.pi * np.cumsum(rpm / 60.0) / SR
        e = np.zeros(N)
        for o, a, load in self.orders:
            e += a * (1 + load * thr) * np.sin(o * phi + o * 0.7)
        main = max(self.orders, key=lambda x: x[1])[0]
        roar = sosfilt(lp(self.rasp), rng.standard_normal(N)) * (0.5 + 0.5 * np.sin(main * phi)) ** 2 * (0.4 + 1.5 * thr)
        e = np.tanh((e * 0.6 + roar * 1.0) * (0.5 + 0.9 * thr))
        e += np.sin(2 * np.pi * np.cumsum(1400 + rpm * 0.9) / SR) * self.whistle * thr * (rpm / self.red)   # turbo whistle
        e = sosfilt(hp(35), sosfilt(lp(5200), e)) * self.g
        for p in self.pops + self.shifts:   # crackle on the overrun and on upshifts
            for _ in range(2 if p in self.shifts else 1):
                d = 0.02 + rng.random() * 0.025
                s = sosfilt(lp(4000), noise(d)) * np.exp(-tt(d) * 100) * (0.6 + rng.random() * 0.6)
                i = min(N - 1, int((p + rng.random() * 0.04) * SR))
                e[i:i + len(s)] += s[: N - i] * 0.8 * max(self.g[i], 0.3)
        for p in self.bov:                   # blow-off valve
            d = 0.28
            s = sosfilt(bp(1800, 7000), noise(d)) * np.exp(-tt(d) * 9) * adsr(int(d * SR), 0.01, 0.05) * 0.3
            i = min(N - 1, int(p * SR))
            e[i:i + len(s)] += s[: N - i] * self.g[i]
        return e


V6 = [(1.5, 0.35, 0.5), (3, 1.0, 0.6), (4.5, 0.3, 0.8), (6, 0.45, 1.0), (7.5, 0.12, 1.2), (9, 0.2, 1.4)]
v6 = Engine(V6, 780, 7000, 0.05, 2800)
v6.blip(B.rs5 + 0.05, 5200, 0.2, 0.8)                     # it fires up as it's named
v6.gain([(B.rs5 - 0.05, 0), (B.rs5 + 0.05, 0.7), (B.rs5 + 1.2, 0.25), (CUT[1], 0.12), (CUT[1] + 0.3, 0)])
v6.blip(B.v6 + 0.05, 5800, 0.16, 0.7)
v6.gain([(B.v6 - 0.05, 0), (B.v6 + 0.05, 0.55), (B.v6 + 1.0, 0)])
d = max(CUT[3] - CUT[2] - 0.4, 1.5)                        # flat out through the numbers
v6.ramp(CUT[2] - 0.2, CUT[2], 1500, 3200)
end = v6.pull(CUT[2], [(d * 0.3, 3200), (d * 0.34, 4600), (d * 0.36, 5000)])
v6.ramp(end, end + 0.5, 6600, 3200, 0.6)
v6.gain([(CUT[2] - 0.2, 0), (CUT[2], 0.2), (end, 0.2), (end + 0.5, 0.08), (end + 0.7, 0)])
m = v6.seg(CUT[3], CUT[4])                                 # cornering through the torque-vectoring shot
v6.rpm[m] = 4800 + 900 * np.sin(2 * np.pi * 0.35 * (t[m] - CUT[3]))
v6.thr[m] = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * (t[m] - CUT[3]))
v6.gain([(CUT[3], 0), (CUT[3] + 0.3, 0.25), (CUT[4] - 0.3, 0.25), (CUT[4], 0)])
v6.blip(B.fast, 6200)
v6.gain([(B.fast - 0.05, 0), (B.fast, 0.6), (B.fast + 0.9, 0)])
ev6 = v6.render()
engine = np.vstack([ev6, ev6]) * 0.7
place(send, 0, ev6 * 0.06)

# ---------------------------------------------------------------- narration + mix
vo = np.zeros(N)
for line in TL['vo']:
    sr_in, x = wavfile.read(os.path.join(HERE, 'out', 'vo', f"{line['id']}.wav"))
    x = resample_poly(x.astype(float) / (32768 if x.dtype == np.int16 else 1), SR, sr_in)
    i0 = int(TIM[line['id']]['at'] * SR)
    m = min(len(x), N - i0)
    vo[i0:i0 + m] += x[:m]
vo = sosfilt(hp(85), vo)
vo += sosfilt(bp(2500, 6000), vo) * 0.35
env, lev, acc = np.abs(vo), np.zeros(N), 0.0
a_att, a_rel = np.exp(-1 / (0.005 * SR)), np.exp(-1 / (0.12 * SR))
for i in range(0, N, 48):
    v = env[i:i + 48].max()
    acc = a_att * acc + (1 - a_att) * v if v > acc else a_rel * acc + (1 - a_rel) * v
    lev[i:i + 48] = acc
vo *= np.minimum(1.0, (0.12 / np.maximum(lev, 1e-6)) ** 0.5)
vo /= np.max(np.abs(vo)) + 1e-9
denv = np.convolve(np.abs(vo), np.ones(int(0.03 * SR)) / int(0.03 * SR), mode='same')
duckc = np.clip(np.convolve(np.clip(denv / 0.08, 0, 1), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode='same') * 1.6, 0, 1)

duck = np.ones(N)
dk = 1 - 0.45 * np.exp(-tt(0.25) * 18)
for k0 in kicks:
    i = int(k0 * SR)
    m = min(len(dk), N - i)
    if m > 0:
        duck[i:i + m] = np.minimum(duck[i:i + m], dk[:m])
music *= duck * (1 - 0.8 * duckc)
engine *= 1 - 0.72 * duckc
sfx *= 1 - 0.55 * duckc
ir_t = tt(2.0)
ir = np.vstack([rng.standard_normal(len(ir_t)), rng.standard_normal(len(ir_t))]) * np.exp(-ir_t * 3.4)
ir[:, : int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
ir = np.vstack([sosfilt(lp(5000), ir[0]), sosfilt(lp(5000), ir[1])]) * 0.012
rev = np.vstack([fftconvolve(send[0], ir[0])[:N], fftconvolve(send[1], ir[1])[:N]]) * (1 - 0.5 * duckc)
bed = music * 0.5 + sfx * 0.7 + engine * 0.6 + rev * 0.8
bed = np.vstack([sosfilt(hp(25), bed[0]), sosfilt(hp(25), bed[1])])
bed /= np.max(np.abs(bed)) + 1e-9
mix = bed * 0.38 + np.vstack([vo, vo]) * 0.62
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
ratio = 10 * np.log10(np.mean((vo * 0.62)[speech] ** 2) / np.mean((bed * 0.38)[:, speech] ** 2))
for i in VO:  # per-line balance
    m = speech & (t >= VO[i]['on']) & (t < VO[i]['off'])
    if m.any():
        print(i, f"{10 * np.log10(np.mean((vo * 0.62)[m] ** 2) / np.mean((bed * 0.38)[:, m] ** 2)):.1f} dB", end='  ')
print()
print(f'wrote {out}: {DUR:.1f}s, voice sits {ratio:.1f} dB above the bed while speaking')


