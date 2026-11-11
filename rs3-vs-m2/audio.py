"""Soundtrack for Audi RS3 vs BMW M2: music, a five-cylinder and a straight-six
engine model, a manual gearchange, tyre smoke, door thunks and sound effects,
all synthesised from scratch and mixed with the Chatterbox narration from
out/vo/. Every cue is placed from the measured voiceover timing in
out/vo/durations.json (written by voiceover.py), using the same word-timing
estimate as film.html.

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
SPOKEN = {'RS3': 10, 'BMW': 8, 'M2': 5, 'M2’s': 6, 'RS': 4, '400': 12, '480': 22, '0–62': 18, '3.8': 16, '4.0': 12, '£60k': 12, '£69k': 10, 'coupé': 6}


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
CUT = [0] + [ON[i] - 0.3 for i in ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']] + [DUR]
B = SimpleNamespace(rs3=wt('01', 'RS3'), m2=wt('01', 'M2'), weapons=wt('01', 'weapons'), different=wt('01', 'different'),
                    look=wt('02', 'look'), hatch=wt('03', 'five-door'), cyl=wt('03', 'five-cylinder'), hp400=wt('03', '400'), awd=wt('03', 'four-wheel'),
                    coupe=wt('04', 'two-door'), i6=wt('04', 'twin-turbo'), hp480=wt('04', '480'), rwd=wt('04', 'rear'),
                    pays=wt('05', 'pays'), rM2=wt('05', 'M2'), r38=wt('05', '3.8'), r40=wt('05', '4.0'),
                    trick=wt('06', 'party'), manual=wt('06', 'six-speed'), old=wt('06', 'old'),
                    torque=wt('07', 'Torque'), outside=wt('07', 'outside'), drift=wt('07', 'Drift'),
                    easy=wt('08', 'Easy'), five=wt('08', 'Five'), seat=wt('08', 'back'),
                    p60=wt('09', '£60k'), p69=wt('09', '£69k'), allw=wt('10', 'all-weather'), vRS3=wt('10', 'RS3'), vM2=wt('10', 'M2'),
                    comments=wt('11', 'comments'))
B.vs = B.m2 + 0.55
B.rS = max(B.pays - 0.3, CUT[4] + 0.6)          # same race timing as film.html: each timer lands on its spoken number
B.mS = max(B.rM2 - 1.1, B.rS + 0.8)


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



def thunk(t0, g=1.0, pan=0.0):  # a car door shutting
    t = tt(0.5)
    s = np.sin(2 * np.pi * np.cumsum(70 + 60 * np.exp(-t * 30)) / SR) * np.exp(-t * 14)
    s += sosfilt(lp(900), noise(0.5)) * np.exp(-t * 40) * 0.6 + sosfilt(bp(2500, 6000), noise(0.5)) * np.exp(-t * 90) * 0.15
    place(sfx, t0, np.tanh(s * 1.5) * 0.5, g, pan)
    place(send, t0, s * 0.1, g, pan)


def projector(t0, d, g=1.0):  # old film projector clatter + vinyl crackle
    s = np.zeros(int(d * SR))
    for k in range(int(d * 24)):
        i = int(k / 24 * SR)
        c = sosfilt(bp(1200, 5000), noise(0.012)) * np.exp(-tt(0.012) * 400)
        s[i:i + len(c)] += c[: len(s) - i] * (0.6 + 0.4 * (k % 2))
    cr = noise(d) * (rng.random(int(d * SR)) > 0.9985) * 3
    s += sosfilt(hp(2000), cr) * 0.4 + sosfilt(bp(80, 400), noise(d)) * 0.03
    s *= adsr(len(s), 0.05, 0.2)
    place(sfx, t0, s * 0.35, g)


# ---------------------------------------------------------------- arrangement
pad(0.0, 'Dm', CUT[1] + 0.4, 0.8, 700)
for t0, f0 in ((B.rs3 - 0.08, 400), (B.m2 - 0.08, 520)):
    click(t0, 1.0, 2200)
    shimmer(t0, 0.6, f0, f0 * 6, 1.0)
impact(B.vs, 1.2)
whoosh(B.vs - 0.4, 0.4, 0.8)
groove(B.vs, CUT[1], ['Dm', 'Bb'], kick_from=B.vs, hat_from=B.vs + 0.5, bass_from=B.vs, pad_g=0, g=0.75)
blip(B.weapons, NOTE['D6'], 0.9)
for k in range(3):
    click(B.different + k * 0.09, 0.8, 2600, 0.0)
riser(CUT[1] - 1.0, 1.0, 0.8)

for k in range(3):                        # studio lights clunking on
    click(CUT[1] + 0.05 + k * 0.07, 1.2, 900 + k * 300)
impact(CUT[1] + 0.05, 0.6)
groove(CUT[1], CUT[2], ['Dm', 'Bb', 'F', 'C'], hat_from=CUT[1] + 1.0, hat_div=4, bass_from=B.look, arp_from=CUT[1] + 0.5, g=0.65, cutoff=1200)
shimmer(CUT[1] + 0.4, 1.2, 300, 2400, 0.8)
blip(B.look - 0.1, NOTE['A5'], 0.8, -0.4)
blip(B.look + 0.1, NOTE['D6'], 0.8, 0.4)

groove(CUT[2], CUT[3], ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[2], hat_from=CUT[2], hat_div=2, bass_from=CUT[2], arp_from=B.cyl, g=0.65, cutoff=1500)
blip(B.hatch, NOTE['A5'], 0.8, -0.3)
blip(B.cyl, NOTE['A5'], 0.8, 0.3)
ticks(B.hp400, 0.7, 0.45)
impact(B.hp400 + 0.05, 0.45)
for k in range(4):
    blip(B.awd + 0.1 + k * 0.07, NOTE['D6'] * (1 + 0.12 * k), 0.6, -0.6 + 0.4 * k)
groove(CUT[3], CUT[4], ['Gm', 'Dm', 'Bb', 'C'], kick_from=CUT[3], snare_from=B.hp480, hat_from=CUT[3], bass_from=CUT[3], bass_div=2, g=0.65, cutoff=1500)
blip(B.coupe, NOTE['A5'], 0.8, 0.3)
blip(B.i6, NOTE['A5'], 0.8, -0.3)
ticks(B.hp480, 0.7, 0.45)
impact(B.hp480 + 0.05, 0.45)
squeal(B.rwd + 0.1, CUT[4] - B.rwd - 0.05, 0.45, 0.2)

groove(CUT[4], CUT[5], ['Dm', 'Bb'], kick_from=CUT[4], snare_from=B.r38, hat_from=CUT[4], hat_div=2, bass_from=CUT[4], pad_g=0.6, g=0.55, cutoff=1600)
for k in range(3):
    blip(B.rS - 1.2 + k * 0.4, NOTE['A5'] if k < 2 else NOTE['A6'], 0.9)      # launch lights
impact(B.r38, 0.4)
impact(B.r40, 0.35)
blip(B.r40 + 0.5, NOTE['D6'], 1.0)

groove(CUT[5], B.old - 0.1, ['Gm', 'Dm', 'Bb', 'C'], kick_from=CUT[5], hat_from=CUT[5], bass_from=CUT[5], g=0.6, cutoff=1400)
projector(B.old - 0.1, CUT[6] - B.old + 0.1, 1.0)
pad(B.old - 0.1, 'F', CUT[6] - B.old + 0.4, 0.5, 900)

groove(CUT[6], CUT[7], ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[6], snare_from=B.torque, hat_from=CUT[6], hat_div=4, bass_from=CUT[6], arp_from=B.torque, g=0.7, cutoff=1700)
squeal(CUT[6] + 0.1, B.torque - CUT[6] - 0.3, 0.35, -0.3)
squeal(B.outside, CUT[7] - B.outside - 0.1, 0.45, 0.3)
impact(B.drift, 0.35)

groove(CUT[7], CUT[8], ['F', 'C', 'Dm', 'Bb'], kick_from=CUT[7], hat_from=CUT[7] + 0.5, bass_from=CUT[7], arp_from=CUT[7], g=0.6, cutoff=1500)
bell(B.easy, 'A5', 1.0)
for k in range(5):
    thunk(B.five + k * 0.12, 0.8, -0.5)
for k in range(2):
    thunk(B.five + 0.25 + k * 0.14, 0.8, 0.5)
groove(CUT[8], CUT[9], ['Bb', 'F'], kick_from=CUT[8], hat_from=CUT[8], bass_from=CUT[8], g=0.6, cutoff=1300)
ticks(B.p60, 0.7, 0.45)
ticks(B.p69, 0.7, 0.45)
thunk(B.p69 + 0.3, 1.0, 0.3)
bell(B.p69 + 0.6, 'F5', 1.1)
groove(CUT[9], CUT[10], ['Dm', 'Bb', 'C', 'Dm'], kick_from=CUT[9], snare_from=CUT[9], hat_from=CUT[9], hat_div=4, bass_from=CUT[9], g=0.8, cutoff=2000)
for t0 in (B.vRS3, B.vM2):
    impact(t0, 0.5)
groove(CUT[10], DUR - 1.0, ['Dm', 'Bb', 'F', 'C'], kick_from=CUT[10], hat_from=CUT[10], bass_from=CUT[10], arp_from=CUT[10], g=0.7, cutoff=1600)
blip(B.comments, NOTE['D6'], 1.0)
for k, nm in enumerate(['D5', 'F5', 'A5', 'E6']):
    bell(DUR - 2.4 + k * 0.09, nm, 0.9, pan=-0.3 + 0.2 * k, d=2.2)
for c, kind in zip(CUT[1:-1], ['zoom', 'whip', 'whip', 'stripe', 'whip', 'stripe', 'zoom', 'stripe', 'whip', 'zoom']):
    if kind == 'whip':
        whoosh(c - 0.24, 0.42, 0.9, 0.9, -0.9)
    elif kind == 'stripe':
        whoosh(c - 0.26, 0.5, 0.8, -0.8, 0.8)
    else:
        whoosh(c - 0.3, 0.45, 0.6, -0.2, 0.2)
        impact(c, 0.35)


# ---------------------------------------------------------------- engines
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


rs3 = Engine(FIVE, 850, 7000, 0.06, 2400)
m2 = Engine(SIX, 800, 7200, 0.03, 3200)
# hook: each car clears its throat as it's named
rs3.blip(B.rs3 + 0.05, 5600)
rs3.gain([(B.rs3 - 0.05, 0), (B.rs3 + 0.05, 0.8), (B.rs3 + 1.2, 0.3), (B.vs, 0)])
m2.blip(B.m2 + 0.05, 5800)
m2.gain([(B.m2 - 0.05, 0), (B.m2 + 0.05, 0.8), (B.m2 + 1.2, 0.3), (B.vs + 0.6, 0)])
# hero shots: the five-cylinder warble, then the straight-six and a burnout
rs3.blip(B.cyl + 0.1, 6200, 0.18, 0.7)
rs3.blip(B.hp400 + 0.05, 6600, 0.15, 0.8)
rs3.gain([(B.cyl, 0), (B.cyl + 0.1, 0.85), (B.hp400 + 1.0, 0.5), (CUT[3], 0)])
m2.blip(B.i6 + 0.1, 6400, 0.18, 0.7)
m2.blip(B.hp480 + 0.05, 6800, 0.15, 0.6, bov=False)
m2.ramp(B.rwd, B.rwd + 0.3, 1500, 5600)
m = m2.seg(B.rwd + 0.3, CUT[4])
m2.rpm[m] = 5600 + 400 * np.sin(2 * np.pi * 2.3 * (t[m] - B.rwd))
m2.thr[m2.seg(B.rwd, CUT[4])] = 0.9
m2.gain([(B.i6, 0), (B.i6 + 0.1, 0.8), (B.rwd, 0.4), (B.rwd + 0.3, 0.45), (OFF['04'], 0.45), (OFF['04'] + 0.15, 0.75), (CUT[4] - 0.15, 0.7), (CUT[4] + 0.1, 0)])
# 0-62: each car pulls until its time is said
for eng, st, fin in ((rs3, B.rS, B.r38), (m2, B.mS, B.r40)):
    d = max(fin - st, 0.8)
    eng.ramp(st - 0.3, st, 1200, 3000)
    end = eng.pull(st, [(d * 0.24, 3400), (d * 0.24, 4600), (d * 0.26, 5000), (d * 0.26, 5300)])
    eng.ramp(end, end + 0.6, eng.red - 300, 3000, 0.6)
    eng.bov.append(end + 0.02)
    eng.gain([(st - 0.35, 0), (st, 0.42), (end, 0.42), (end + 0.6, 0.12), (end + 0.9, 0)])
# the manual: rev, dip the clutch, clunk into the next gear (synced to the H-pattern graphic)
g0 = B.manual + 0.1
gear_at = [g0 + i / 12 * 2.2 for i in (0, 2, 5, 7, 10, 12)]
m2.ramp(B.manual - 0.2, g0, 900, 2200)
for a, b in zip(gear_at[:-1], gear_at[1:]):
    m2.ramp(a + 0.05, b - 0.08, 2600, 5400, 0.8)
    m2.thr[m2.seg(a + 0.05, b - 0.08)] = 1.0
    m2.ramp(b - 0.08, b + 0.05, 5400, 2600, 0.5)
for g in gear_at:
    click(g, 1.2, 700, 0.1)
    click(g + 0.015, 0.8, 1800, 0.1)
m2.ramp(gear_at[-1] + 0.05, B.old - 0.1, 2600, 1200)
m2.gain([(B.manual - 0.25, 0), (B.manual, 0.45), (gear_at[-1], 0.55), (B.old - 0.1, 0)])
# the RS3 sideways on snow, then the Torque Rear top view
rs3.ramp(CUT[6], B.torque, 3800, 5200)
m = rs3.seg(B.torque, CUT[7])
rs3.rpm[m] = 5400 + 600 * np.sin(2 * np.pi * 1.6 * (t[m] - B.torque))
rs3.thr[rs3.seg(CUT[6], CUT[7])] = 0.8
rs3.gain([(CUT[6], 0), (CUT[6] + 0.3, 0.25), (B.torque, 0.25), (B.outside, 0.35), (OFF['07'], 0.4), (OFF['07'] + 0.15, 0.75), (CUT[7] - 0.2, 0.7), (CUT[7], 0)])
# verdict
rs3.blip(B.vRS3, 6000)
rs3.gain([(B.vRS3 - 0.05, 0), (B.vRS3, 0.8), (B.vRS3 + 1.0, 0)])
m2.blip(B.vM2, 6200)
m2.gain([(B.vM2 - 0.05, 0), (B.vM2, 0.8), (B.vM2 + 1.0, 0)])
er, em = rs3.render(), m2.render()
engine = np.zeros((2, N))
for e, pan in ((er, -0.35), (em, 0.35)):
    a = (pan + 1) * np.pi / 4
    engine[0] += e * np.cos(a)
    engine[1] += e * np.sin(a)
place(send, 0, (er + em) * 0.08)

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

