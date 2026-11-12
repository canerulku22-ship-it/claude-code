"""Soundtrack for Cupra 290 vs Audi S3 vs Golf R: music, three turbo four-cylinder
engine models, tyre smoke and sound effects synthesised from scratch, mixed with
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
SPOKEN = {'290': 12, '290?': 12, 'S3': 8, 'S3?': 8, 'R': 3, '333': 30, '2.0-litre': 10, '4.6': 14, '4.7': 14, '5.7': 14, '£20k': 12, '£46k': 14, 'R-Performance': 16}


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
B = SimpleNamespace(three=wt('01', 'Three'), hot=wt('01', 'hot'), hatches=wt('01', 'hatches'), question=wt('01', 'question'),
                    cupra=wt('01', 'Cupra'), s3=wt('01', 'Audi'), golf=wt('01', 'Golf'),
                    turbo=wt('02', '2.0'), different=wt('02', 'different'), go=wt('02', 'go'),
                    oldsch=wt('03', 'old-school'), hp290=wt('03', '290'), front=wt('03', 'front'),
                    hp333=wt('04', '333'), awd=wt('04', 'four-wheel'),
                    grip=wt('05', 'grip'), g46=wt('05', '4.6'), s47=wt('05', '4.7'), c57=wt('05', '5.7'),
                    drift=wt('06', 'Drift'), pack=wt('06', 'R-Performance'),
                    kicker=wt('07', 'kicker'), p20=wt('07', '£20k'), p46=wt('07', '£46k'),
                    bargain=wt('08', 'bargain'), vC=wt('08', 'Cupra'), vS=wt('08', 'S3'), vG=wt('08', 'Golf'),
                    comments=wt('09', 'comments'))
GO = max(CUT[4] + 0.75, ON['05'] + 0.2)          # same race launch as film.html


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



# ---------------------------------------------------------------- arrangement
# intro: a low drone, a hit as each car's lights come on, a shimmer on each name
pad(0.0, 'Dm', CUT[1] + 0.4, 0.7, 500)
riser(0.1, 1.1, 0.6)
for k, t0 in enumerate((B.three, B.hot, B.hatches)):
    impact(t0, 0.55 + 0.1 * k)
    click(t0 - 0.02, 1.0, 900 + 300 * k)
impact(B.question, 0.8)
for t0, f0 in ((B.cupra - 0.08, 330), (B.s3 - 0.08, 440), (B.golf - 0.08, 560)):
    click(t0, 1.0, 2200)
    shimmer(t0, 0.6, f0, f0 * 6, 1.0)
    whoosh(t0 - 0.25, 0.35, 0.6, -0.6, 0.6)
groove(B.cupra, CUT[1], ['Dm', 'Bb'], kick_from=B.cupra, hat_from=B.s3, bass_from=B.cupra, pad_g=0, g=0.7)
riser(CUT[1] - 1.0, 1.0, 0.7)

for k in range(3):                        # studio lights clunking on
    click(CUT[1] + 0.05 + k * 0.07, 1.2, 900 + k * 300)
groove(CUT[1], CUT[2], ['Dm', 'Bb', 'F', 'C'], kick_from=B.turbo, hat_from=CUT[1] + 0.6, hat_div=4, bass_from=CUT[1], arp_from=B.different, g=0.65, cutoff=1400)
for k in range(3):
    blip(B.turbo + k * 0.12, NOTE['A5'], 0.7, -0.5 + 0.5 * k)
impact(B.go, 0.6)

groove(CUT[2], CUT[3], ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[2], hat_from=CUT[2], bass_from=CUT[2], arp_from=B.hp290, g=0.62, cutoff=1500)
ticks(B.hp290, 0.7, 0.45)
impact(B.hp290 + 0.05, 0.45)
squeal(B.front + 0.1, CUT[3] - B.front - 0.05, 0.4, -0.2)
groove(CUT[3], CUT[4], ['Gm', 'Dm', 'Bb', 'C'], kick_from=CUT[3], snare_from=B.hp333, hat_from=CUT[3], bass_from=CUT[3], g=0.62, cutoff=1500)
ticks(B.hp333, 0.7, 0.45)
ticks(B.hp333 + 0.1, 0.7, 0.4)
impact(B.hp333 + 0.05, 0.45)
for k in range(4):
    blip(B.awd + 0.1 + k * 0.07, NOTE['D6'] * (1 + 0.12 * k), 0.6, -0.6 + 0.4 * k)

groove(CUT[4], CUT[5], ['Dm', 'Bb'], kick_from=GO, snare_from=B.g46, hat_from=CUT[4], bass_from=GO, pad_g=0.6, g=0.55, cutoff=1600)
for k in range(3):                        # start-light beeps
    blip(GO - 0.9 + k * 0.3, NOTE['A5'] if k < 2 else NOTE['A6'], 0.9)
squeal(GO, 1.3, 0.4, 0.4)                 # the front-driver lights up its tyres
for t0 in (B.g46, B.s47, B.c57):
    impact(t0, 0.3)

groove(CUT[5], CUT[6], ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[5], snare_from=B.drift, hat_from=CUT[5], hat_div=4, bass_from=CUT[5], arp_from=B.drift, g=0.7, cutoff=1700)
squeal(CUT[5] + 0.1, CUT[6] - CUT[5] - 0.2, 0.42, 0.2)
impact(B.drift, 0.4)

groove(CUT[6], CUT[7], ['Bb', 'F'], kick_from=CUT[6], hat_from=CUT[6], bass_from=CUT[6], g=0.6, cutoff=1300)
impact(B.kicker, 0.35)
ticks(B.p20 - 0.1, 0.7, 0.45)
bell(B.p20 + 0.4, 'A5', 1.0)
ticks(B.p46 - 0.1, 0.7, 0.45)
ticks(B.p46 + 0.05, 0.7, 0.4)

groove(CUT[7], CUT[8], ['Dm', 'Bb', 'C', 'Dm'], kick_from=CUT[7], snare_from=CUT[7], hat_from=CUT[7], hat_div=4, bass_from=CUT[7], g=0.8, cutoff=2000)
for t0 in (B.vC, B.vS, B.vG):
    impact(t0, 0.45)
groove(CUT[8], DUR - 1.0, ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[8], hat_from=CUT[8], bass_from=CUT[8], arp_from=CUT[8], g=0.7, cutoff=1600)
blip(B.comments, NOTE['D6'], 1.0)
for k, nm in enumerate(['D5', 'F5', 'A5', 'E6']):
    bell(DUR - 2.4 + k * 0.09, nm, 0.9, pan=-0.3 + 0.2 * k, d=2.2)
for c, kind in zip(CUT[1:-1], ['zoom', 'whip', 'whip', 'stripe', 'whip', 'stripe', 'zoom', 'whip']):
    if kind == 'whip':
        whoosh(c - 0.24, 0.42, 0.9, 0.9, -0.9)
    elif kind == 'stripe':
        whoosh(c - 0.26, 0.5, 0.8, -0.8, 0.8)
    else:
        whoosh(c - 0.3, 0.45, 0.6, -0.2, 0.2)
        impact(c, 0.35)


# ---------------------------------------------------------------- engines: three turbo fours
t = np.arange(N) / SR

class Engine:
    def __init__(self, idle=850, tone=1.0):
        self.rpm, self.thr, self.g = np.full(N, float(idle)), np.zeros(N), np.zeros(N)
        self.idle, self.tone, self.pops, self.shifts, self.bov = idle, tone, [], [], []

    def seg(self, a, b):
        return (t >= a) & (t < b)

    def ramp(self, a, b, v0, v1, c=1.0):
        m = self.seg(a, b)
        self.rpm[m] = v0 + (v1 - v0) * ((t[m] - a) / (b - a)) ** c

    def gain(self, pts):
        m = self.seg(pts[0][0], pts[-1][0])
        self.g[m] = np.interp(t[m], [p[0] for p in pts], [p[1] for p in pts])

    def blip(self, t0, peak, up=0.14, down=0.6):
        self.ramp(t0, t0 + up, self.idle, peak, 0.6)
        self.ramp(t0 + up, t0 + up + down, peak, self.idle, 0.5)
        self.thr[self.seg(t0, t0 + up)] = 1.0
        self.bov.append(t0 + up + 0.02)
        self.pops.extend(t0 + up + 0.08 + rng.random(3) * down * 0.6)

    def pull(self, a, gears, top=6800):
        ts = a
        for d, r0 in gears:
            self.ramp(ts, ts + d, r0, top, 0.75)
            self.thr[self.seg(ts, ts + d)] = 1.0
            self.shifts.append(ts + d)
            ts += d
        return ts

    def render(self):
        k = int(0.01 * SR)
        rpm = np.maximum(np.convolve(self.rpm, np.ones(k) / k, mode='same'), 1)
        thr = np.convolve(self.thr, np.ones(k * 4) / (k * 4), mode='same')
        phi = 2 * np.pi * np.cumsum(rpm / 60.0) / SR
        e = np.zeros(N)
        for o, a, load in [(0.5, 0.15, 0.2), (1, 0.3, 0.2), (2, 1.0, 0.5), (3, 0.18, 0.4), (4, 0.55, 0.8), (6, 0.3, 1.0), (8, 0.16, 1.4), (10, 0.08, 1.6)]:
            e += a * (1 + load * thr) * np.sin(o * phi * self.tone ** (o > 3) + o * 0.7)
        roar = sosfilt(lp(2600), rng.standard_normal(N)) * (0.5 + 0.5 * np.sin(2 * phi)) ** 2 * (0.4 + 1.5 * thr)
        e = np.tanh((e * 0.6 + roar * 1.0) * (0.5 + 0.9 * thr))
        e += np.sin(2 * np.pi * np.cumsum(1400 + rpm * 0.9) / SR) * 0.05 * thr * (rpm / 6800)   # turbo whistle
        e = sosfilt(hp(35), sosfilt(lp(5200), e)) * self.g
        for p in self.pops + self.shifts:   # crackle on the overrun and on every twin-clutch upshift
            for _ in range(2 if p in self.shifts else 1):
                d = 0.02 + rng.random() * 0.025
                s = sosfilt(lp(4000), noise(d)) * np.exp(-tt(d) * 100) * (0.6 + rng.random() * 0.6)
                i = min(N - 1, int((p + rng.random() * 0.04) * SR))
                e[i:i + len(s)] += s[: N - i] * 0.8 * max(self.g[i], 0.3)
        for p in self.bov:                   # blow-off valve
            d = 0.28
            s = sosfilt(bp(1800, 7000), noise(d)) * np.exp(-tt(d) * 9) * adsr(int(d * SR), 0.01, 0.05) * 0.35
            i = min(N - 1, int(p * SR))
            e[i:i + len(s)] += s[: N - i] * self.g[i]
        return e



cupra, audi, golf = Engine(860, 0.97), Engine(820, 1.02), Engine(850, 1.0)
for eng, t0, peak in ((cupra, B.cupra, 5400), (audi, B.s3, 5200), (golf, B.golf, 5600)):   # each clears its throat as it's named
    eng.blip(t0 + 0.05, peak)
    eng.gain([(t0 - 0.05, 0), (t0 + 0.05, 0.7), (t0 + 1.0, 0.25), (t0 + 1.6, 0)])
cupra.blip(B.hp290 + 0.05, 6300, 0.15, 0.8)                     # the Cupra's hero shot, then wheelspin on "front"
cupra.ramp(B.front, B.front + 0.3, 1500, 5400)
m = cupra.seg(B.front + 0.3, CUT[3])
cupra.rpm[m] = 5400 + 400 * np.sin(2 * np.pi * 2.1 * (t[m] - B.front))
cupra.thr[cupra.seg(B.front, CUT[3])] = 0.85
cupra.gain([(B.hp290 - 0.05, 0), (B.hp290 + 0.05, 0.75), (B.front, 0.35), (B.front + 0.3, 0.4), (OFF['03'], 0.4), (OFF['03'] + 0.15, 0.7), (CUT[3] - 0.1, 0.65), (CUT[3] + 0.1, 0)])
for eng, dt in ((audi, 0.0), (golf, 0.1)):                     # S3 and Golf R on "333"
    eng.blip(B.hp333 + 0.05 + dt, 6400, 0.15, 0.7)
    eng.gain([(B.hp333 - 0.05 + dt, 0), (B.hp333 + 0.05 + dt, 0.6), (B.hp333 + 1.0 + dt, 0.15), (B.hp333 + 1.4 + dt, 0)])
for eng, fin in ((golf, B.g46), (audi, B.s47), (cupra, B.c57)):   # all three launch together; each pulls until its time is said
    d = max(fin - GO, 0.8)
    eng.ramp(GO - 0.3, GO, 1200, 2800)
    end = eng.pull(GO, [(d * 0.24, 3000), (d * 0.24, 4400), (d * 0.26, 4800), (d * 0.26, 5100)])
    eng.ramp(end, end + 0.6, 6600, 3000, 0.6)
    eng.bov.append(end + 0.02)
    eng.gain([(GO - 0.35, 0), (GO, 0.32), (end, 0.32), (end + 0.6, 0.1), (end + 0.9, 0)])
golf.ramp(CUT[5], B.drift, 3800, 5200)                          # Golf R sideways
m = golf.seg(B.drift, CUT[6])
golf.rpm[m] = 5400 + 600 * np.sin(2 * np.pi * 1.6 * (t[m] - B.drift))
golf.thr[golf.seg(CUT[5], CUT[6])] = 0.8
golf.gain([(CUT[5], 0), (CUT[5] + 0.3, 0.3), (B.drift, 0.35), (OFF['06'], 0.4), (OFF['06'] + 0.15, 0.7), (CUT[6] - 0.2, 0.65), (CUT[6], 0)])
for eng, t0 in ((cupra, B.vC), (audi, B.vS), (golf, B.vG)):    # the verdict picks
    eng.blip(t0, 6000)
    eng.gain([(t0 - 0.05, 0), (t0, 0.7), (t0 + 0.9, 0)])
ec, ea, eg = cupra.render(), audi.render(), golf.render()
engine = np.zeros((2, N))
for e, pan in ((ec, -0.4), (ea, 0.0), (eg, 0.4)):
    a = (pan + 1) * np.pi / 4
    engine[0] += e * np.cos(a)
    engine[1] += e * np.sin(a)
place(send, 0, (ec + ea + eg) * 0.06)

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

