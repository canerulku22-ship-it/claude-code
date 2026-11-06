# Tense news-explainer soundtrack for the bomb-hoax video: python3 hoax_audio.py events.json out.wav
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
# ---------------------------------------------------------------- music bed (D minor, 100 BPM)
BEAT = 0.6; BAR = 4 * BEAT
CH = {'Dm': [38, 50, 57, 62, 65, 69], 'Bb': [34, 46, 53, 58, 62, 65], 'Gm': [31, 43, 50, 55, 58, 62], 'A': [33, 45, 52, 57, 61, 64], 'F': [29, 41, 48, 53, 57, 60]}
PROG = ['Dm', 'Dm', 'Bb', 'Bb', 'Gm', 'Gm', 'A', 'A']
def chord_at(t): return PROG[int(t / BAR) % len(PROG)]
pad = np.zeros(N)
bars = int(DUR / BAR) + 1
for b in range(bars):
    t0 = b * BAR; n = int(BAR * SR) + int(0.6 * SR); tv = tt(n)
    name = chord_at(t0 + 0.01) if t0 < T_FIN else ('F' if t0 < T_FIN + 2 * BAR else 'Dm')
    sig = np.zeros(n)
    for m in CH[name][1:]:
        f = mtof(m)
        for det in (-0.12, 0.12):
            ph = 2 * np.pi * f * (1 + det / 100) * tv
            sig += (2 * ((ph / (2 * np.pi)) % 1) - 1) * 0.5
    sig = filt(sig, 'low', 1400) * np.minimum(1, tv / 0.5) * np.minimum(1, np.maximum(0, (BAR + 0.6 - tv) / 0.6))
    i0 = int(t0 * SR); k = min(n, N - i0)
    if k > 0: pad[i0:i0 + k] += sig[:k]
pad = norm(pad)
padGain = 0.22 + 0.10 * np.clip((TS - 3) / 40, 0, 1)
padGain *= np.where(TS > T_FIN, 1.25, 1.0)
add(pad * padGain, 0, 0.55)

# sub bass pulse on 8ths from 3 s
bass = np.zeros(N)
t = 3.0
while t < 59.0:
    name = chord_at(t) if t < T_FIN else 'F'
    f = mtof(CH[name][0] + 12); n = int(0.26 * SR); tv = tt(n)
    s = np.sin(2 * np.pi * f * tv) + 0.35 * np.sin(4 * np.pi * f * tv)
    bass[int(t * SR): int(t * SR) + n] += s * env(n, 0.005, 0.12)[:n]
    t += BEAT / 2
add(filt(bass, 'low', 300) * np.where((TS > 44.3) & (TS < T_FIN), 0.4, 1.0), 0, 0.16)

# heartbeat kick on beats 1 and 2& from 3 s, double-time on Thursday
def kick():
    n = int(0.35 * SR); tv = tt(n); f = 48 + 90 * np.exp(-tv * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv * 9)
K = kick()
t = 3.0
while t < 59.5:
    if 44.3 < t < T_FIN: add(K, t, 0.38)
    else:
        add(K, t, 0.5); add(K, t + BEAT * 1.5, 0.32)
        if 23.3 < t < 44.3: add(K, t + BEAT * 2, 0.42); add(K, t + BEAT * 3.5, 0.28)
    t += BAR / 2 if t < T_FIN else BAR

# ticking clock hats (16ths), louder during the live days
def hat(d=0.03):
    n = int(d * SR); return filt(noise(n), 'high', 7000) * np.exp(-tt(n) * 140)
t = 3.0; i = 0
while t < 59.0:
    a = 0.05 if i % 4 else 0.09
    if 44.3 < t < T_FIN: a *= 0.5
    add(hat(), t, a, 0.3 if i % 2 else -0.3); t += BEAT / 4; i += 1

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

# intro: riser into the title, impact, braam
add(norm(riser(0.25)), 0.0, 0.12)
add(norm(boom(3.0, 30, 70, 1.6)), ev['intro'][0], 0.75)
braam = np.zeros(int(2.4 * SR)); tv = tt(len(braam))
for m in (26, 38, 45, 50):
    braam += filt(2 * ((mtof(m) * tv) % 1) - 1, 'low', 900)
add(norm(braam) * np.minimum(1, tv / 0.05) * np.exp(-tv / 1.1), ev['intro'][0], 0.22)
add(norm(alarm()), 0.9, 0.06)
for x in ev['intro'][1:]: add(norm(pop()), x, 0.10)
add(norm(riser(1.2)), 3.0 - 1.2, 0.10)
add(norm(boom(1.4, 40, 90, 0.5)), 3.0, 0.35)

for x in ev['departs']: add(norm(blip(1568)), x, 0.05, 0.2)
for i, x in enumerate(ev['threats']):
    add(norm(alarm()), x, 0.075, (-0.3, 0.3)[i % 2]); add(norm(boom(1.2, 36, 70, 0.4)), x, 0.32); add(norm(squelch()), x + 0.32, 0.035, (0.4, -0.4)[i % 2])
for x in ev['diverts']: add(norm(whoosh_down()), x, 0.13)
for i, x in enumerate(ev['escorts']): add(norm(jet()), x - 0.3, 0.17, (-0.6, 0.6)[i % 2])
for x in ev['lands']: add(norm(ping(1046, 0.5)), x, 0.035)
for x in ev['grounds']:
    for k in range(3): add(norm(alarm()), x + k * 0.4, 0.06)
for x in ev['splashes']:
    add(norm(riser(0.7)), x - 0.7, 0.10); add(norm(boom(2.0, 32, 90, 0.9)), x, 0.55)
for x in ev['qa']: add(norm(stamp()), x, 0.5)
for x in ev['cards']: add(norm(pop()), x, 0.07)
for x in sorted(ev['ticks']): add(norm(tick()), x, 0.06)
# finale
for i, x in enumerate(ev['finale']): add(norm(boom(2.6, 30, 80, 1.4)), x, 0.6 + 0.1 * i)
add(norm(riser(1.0)), ev['finale'][0] - 1.0, 0.12)
for x in ev['rows']:
    add(norm(pop()), x, 0.12)
    for k in range(10): add(norm(tick()), x + 0.15 + k * 0.12, 0.04 * (1 - k / 12))
add(norm(ping(880, 2.5)), 59.0 - 2.5, 0.0)

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
