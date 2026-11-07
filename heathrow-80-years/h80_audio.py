# Uplifting soundtrack for the Heathrow 80-years video: python3 h80_audio.py events.json out.wav
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000; DUR = 60.0; N = int(SR * DUR)
ev = json.load(open(sys.argv[1]))
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)

def tt(n): return np.arange(n) / SR
def noise(n): return rng.standard_normal(n)
def filt(x, kind, f, order=2):
    sos = butter(order, f, btype=kind, fs=SR, output='sos'); return sosfilt(sos, x)
def norm(x): return x / (np.abs(x).max() + 1e-9)
def add(sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N: return
    if i0 < 0: sig = sig[-i0:]; i0 = 0
    n = min(len(sig), N - i0)
    L[i0:i0 + n] += sig[:n] * gain * np.sqrt(0.5 * (1 - pan)); R[i0:i0 + n] += sig[:n] * gain * np.sqrt(0.5 * (1 + pan))
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def env(n, a, d):
    t = tt(n); return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)

T_FIN = ev['T_FIN']
TS = np.arange(N) / SR
T_FIN = ev['T_FIN']; T_ROUTES = ev['T_ROUTES']; T_FUT = ev['T_FUT']
TS = np.arange(N) / SR
# ---------------------------------------------------------------- music bed (D major, 112 BPM, uplifting)
BEAT = 60 / 112; BAR = 4 * BEAT
CH = {'D': [38, 50, 57, 62, 66, 69], 'A': [33, 45, 52, 57, 61, 64], 'Bm': [35, 47, 54, 59, 62, 66], 'G': [31, 43, 50, 55, 59, 62], 'Em': [28, 40, 47, 52, 55, 59]}
PROG = ['D', 'A', 'Bm', 'G', 'D', 'A', 'G', 'A']
def chord_at(t): return PROG[int(t / BAR) % len(PROG)]
pad = np.zeros(N)
for b in range(int(DUR / BAR) + 1):
    t0 = b * BAR; n = int(BAR * SR) + int(0.5 * SR); tv = tt(n)
    name = chord_at(t0 + 0.01)
    if ev['covidT'] - 0.3 < t0 < ev['recoverT']: name = 'Em'
    sig = np.zeros(n)
    for m in CH[name][1:]:
        f = mtof(m)
        for det in (-0.1, 0.1):
            ph = f * (1 + det / 100) * tv; sig += (2 * (ph % 1) - 1) * 0.5
    sig = filt(sig, 'low', 1800) * np.minimum(1, tv / 0.4) * np.minimum(1, np.maximum(0, (BAR + 0.5 - tv) / 0.5))
    i0 = int(t0 * SR); k = min(n, N - i0)
    if k > 0: pad[i0:i0 + k] += sig[:k]
pad = norm(pad)
covid = (TS > ev['covidT']) & (TS < ev['recoverT'])
padG = (0.20 + 0.08 * np.clip((TS - 3) / 40, 0, 1)) * np.where(covid, 0.6, 1.0)
add(pad * padG, 0, 0.55)
# arpeggio (plucks on 8ths) from 3.2 s, sparse in the COVID dip
t = 3.2; i = 0
while t < 59.0:
    if not (ev['covidT'] < t < ev['recoverT']) or i % 4 == 0:
        name = chord_at(t); notes = CH[name][2:]; m = notes[[0, 1, 2, 3, 2, 1, 3, 2][i % 8] % len(notes)] + 12
        n = int(0.32 * SR); tv = tt(n); f = mtof(m)
        add(np.sin(2 * np.pi * f * tv) * np.exp(-tv * 9) + 0.3 * np.sin(4 * np.pi * f * tv) * np.exp(-tv * 14), t, 0.05, (-0.35, 0.35)[i % 2])
    t += BEAT / 2; i += 1
# bass + kick
def kick():
    n = int(0.35 * SR); tv = tt(n); f = 50 + 95 * np.exp(-tv * 32)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv * 9)
K = kick(); t = 3.2
while t < 59.5:
    dip = ev['covidT'] < t < ev['recoverT']
    if not dip: add(K, t, 0.42)
    name = chord_at(t); n = int(BEAT * 0.9 * SR); tv = tt(n); f = mtof(CH[name][0] + 12)
    add(filt(np.sin(2 * np.pi * f * tv) + 0.3 * np.sign(np.sin(2 * np.pi * f * tv)), 'low', 400) * np.exp(-tv * 3), t, 0.10 if not dip else 0.05)
    t += BEAT
def hat(d=0.03):
    n = int(d * SR); return filt(noise(n), 'high', 7000) * np.exp(-tt(n) * 140)
t = 3.2 + BEAT / 2
while t < 59.0:
    if not (ev['covidT'] < t < ev['recoverT']): add(hat(), t, 0.06, 0.25)
    t += BEAT

# ---------------------------------------------------------------- one-shots
def boom(dur=2.4, f0=34, f1=80, dec=1.3):
    n = int(dur * SR); tv = tt(n); f = f0 + (f1 - f0) * np.exp(-tv * 14)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / dec) + 0.4 * filt(noise(n), 'low', 400) * np.exp(-tv * 6))
def riser(dur):
    n = int(dur * SR); tv = tt(n); x = noise(n) * (tv / dur) ** 2.2
    return filt(x, 'band', [600, 6000]) + 0.3 * np.sin(2 * np.pi * (200 + 900 * (tv / dur) ** 2) * tv) * (tv / dur) ** 2
def alarm():
    out = []
    for f in (988, 740, 988, 740):
        n = int(0.11 * SR); tv = tt(n); s = np.sign(np.sin(2 * np.pi * f * tv)) * 0.5 + np.sin(2 * np.pi * f * tv) * 0.5
        out.append(s * np.minimum(1, tv / 0.004) * np.minimum(1, (0.11 - tv) / 0.01)); out.append(np.zeros(int(0.025 * SR)))
    return filt(np.concatenate(out), 'band', [400, 3500])
def squelch():
    n = int(0.55 * SR); tv = tt(n); x = filt(noise(n), 'band', [500, 2600]) * (0.6 + 0.4 * np.sin(2 * np.pi * 17 * tv))
    return x * np.minimum(1, tv / 0.01) * np.exp(-tv * 2.5)
def whoosh_down(dur=0.9):
    n = int(dur * SR); tv = tt(n); out = np.zeros(n); blk = 512; x = noise(n)
    for i in range(0, n, blk):
        fc = 3200 * (1 - i / n) + 300; out[i:i + blk] = filt(x[max(0, i - 2048):i + blk], 'band', [fc * 0.7, fc * 1.3])[-min(blk, n - i):]
    return out * np.sin(np.pi * tv / dur)
def jet(dur=1.6):
    n = int(dur * SR); tv = tt(n); x = noise(n); out = np.zeros(n); blk = 512
    for i in range(0, n, blk):
        u = i / n; fc = 900 + 2600 * np.exp(-((u - 0.45) / 0.18) ** 2); out[i:i + blk] = filt(x[max(0, i - 2048):i + blk], 'band', [fc * 0.6, fc * 1.4])[-min(blk, n - i):]
    whine = np.sin(2 * np.pi * np.cumsum(2400 - 900 * tv / dur) / SR) * 0.15
    return (out + whine) * np.exp(-((tv / dur - 0.45) / 0.25) ** 2)
def ping(f=1320, d=0.6):
    n = int(d * SR); tv = tt(n); return (np.sin(2 * np.pi * f * tv) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tv)) * np.exp(-tv * 7)
def tick():
    n = int(0.03 * SR); return filt(noise(n), 'high', 2500) * np.exp(-tt(n) * 120)
def pop():
    n = int(0.09 * SR); tv = tt(n); return np.sin(2 * np.pi * (520 + 900 * np.exp(-tv * 40)) * tv) * np.exp(-tv * 45)
def stamp():
    n = int(0.9 * SR); tv = tt(n); return boom(0.9, 40, 120, 0.25) * 0.8 + filt(noise(n), 'band', [150, 1200]) * np.exp(-tv * 22) * 0.9
def blip(f=1760):
    n = int(0.07 * SR); tv = tt(n); return np.sin(2 * np.pi * f * tv) * np.exp(-tv * 50)


def chime(f=1568, d=1.2):
    n = int(d * SR); tv = tt(n); return (np.sin(2 * np.pi * f * tv) + 0.5 * np.sin(2 * np.pi * f * 2.76 * tv) * np.exp(-tv * 6)) * np.exp(-tv * 3.5)
# intro
add(norm(riser(0.25)), 0.0, 0.10)
add(norm(boom(3.0, 30, 70, 1.6)), ev['intro'][0], 0.6)
for x in ev['intro'][1:]: add(norm(pop()), x, 0.10)
add(norm(riser(1.2)), 3.2 - 1.2, 0.10); add(norm(boom(1.4, 40, 90, 0.5)), 3.2, 0.32)
# year ticks (odometer), card pops
for x in ev['years']: add(norm(tick()), x, 0.045, 0.2)
for x in ev['cards']: add(norm(pop()), x, 0.08)
for x in ev['build']: add(norm(chime(1318)), x, 0.07, -0.2); add(norm(chime(1976)), x + 0.08, 0.05, 0.2)
for x in ev['runwayClose']: add(norm(boom(0.8, 45, 110, 0.2)), x, 0.22)
for x, kind in ev['big']:
    if kind == 'jet': add(norm(jet(2.0)), x - 0.4, 0.20, 0.3)
    elif kind == 'down': add(norm(whoosh_down(1.4)), x, 0.16); add(norm(boom(2.4, 28, 60, 1.2)), x, 0.4)
    elif kind == 'rec': add(norm(riser(0.8)), x - 0.8, 0.09); add(norm(boom(1.6, 36, 90, 0.6)), x, 0.38)
add(norm(riser(1.6)), ev['recoverT'] - 1.6, 0.10)
# routes, future, finale
add(norm(boom(1.8, 34, 80, 0.8)), T_ROUTES, 0.4)
for x in ev['routes']: add(norm(jet(1.4)), x - 0.2, 0.12, 0.4)
add(norm(riser(1.0)), T_FUT - 1.0, 0.09); add(norm(boom(1.6, 36, 80, 0.7)), T_FUT, 0.35)
for i, x in enumerate(ev['fin']): add(norm(boom(2.6, 30, 80, 1.4)), x, 0.55 + 0.1 * i)
add(norm(riser(1.0)), ev['fin'][0] - 1.0, 0.12)
for x in ev['rows']: add(norm(pop()), x, 0.11); add(norm(chime(1760, 0.6)), x + 0.42, 0.03)

# ---------------------------------------------------------------- master
mix = np.stack([L, R])
fade = np.clip((DUR - TS) / 0.6, 0, 1) * np.clip(TS / 0.02, 0, 1)
mix *= fade
rms = np.sqrt(np.mean(mix ** 2)); mix *= 10 ** (-15 / 20) / (rms + 1e-9)
pk = np.abs(mix).max()
if pk > 0.9: mix = 0.95 * np.tanh(mix / 0.95)
print('peak', round(float(np.abs(mix).max()), 3), 'rms dBFS', round(20 * np.log10(np.sqrt(np.mean(mix ** 2))), 2))
seg = [round(20 * np.log10(np.sqrt(np.mean(mix[:, int(a * SR):int((a + 2) * SR)] ** 2)) + 1e-9)) for a in range(0, 60, 2)]
print(' '.join(f'{a*2}:{v}' for a, v in enumerate(seg)))
with wave.open(sys.argv[2], 'wb') as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((np.clip(mix.T, -1, 1) * 32767).astype(np.int16).tobytes())
