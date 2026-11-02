"""Soundtrack for 'HEATHROW: 24 HOURS IN THE SKY' (v2), built from events.json exported by the page."""
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

SR = 48000; DUR = 60.0; N = int(SR * DUR)
ev = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "events.json"))
rng = np.random.default_rng(2611)
L = np.zeros(N); R = np.zeros(N)

def tt(n): return np.arange(n) / SR
def noise(n): return rng.standard_normal(n)
def filt(x, kind, f, order=2):
    nyq = SR / 2
    sos = butter(order, [f[0] / nyq, f[1] / nyq], "band", output="sos") if kind == "bp" else butter(order, min(f, nyq * 0.95) / nyq, kind, output="sos")
    return sosfilt(sos, x)
def sweep(x, kind, fc, blk=512, q=0.5):
    out = np.zeros_like(x); zi = None
    for i in range(0, len(x), blk):
        c = float(np.clip(fc[min(i, len(fc) - 1)], 30, SR * 0.45))
        sos = butter(1, [c * (1 - q) / (SR / 2), min(0.98, c * (1 + q) / (SR / 2))], "band", output="sos") if kind == "bp" else butter(2, c / (SR / 2), kind, output="sos")
        if zi is None: zi = sosfilt_zi(sos) * 0
        out[i:i + blk], zi = sosfilt(sos, x[i:i + blk], zi=zi)
    return out
def add(sig, t0, gain=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if i0 >= N: return
    if i0 < 0:
        sig = sig[-i0:]
        if isinstance(pan, np.ndarray): pan = pan[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    p = pan[:n] if isinstance(pan, np.ndarray) else pan
    th = (np.clip(p, -1, 1) + 1) * np.pi / 4
    L[i0:i0 + n] += sig[:n] * gain * np.cos(th); R[i0:i0 + n] += sig[:n] * gain * np.sin(th)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def bell(f, dur=2.2, idx=2.2, ratio=3.5, dec=2.2):
    t = tt(int(dur * SR)); mod = np.sin(2 * np.pi * f * ratio * t) * idx * np.exp(-t * 3.0)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * dec) * np.clip(t / 0.004, 0, 1)
def boom(dur=2.6, f0=36, f1=90, dec=1.5):
    t = tt(int(dur * SR)); return np.sin(2 * np.pi * np.cumsum(f0 + f1 * np.exp(-t * 9)) / SR) * np.exp(-t * dec)
def norm(x): return x / (np.abs(x).max() + 1e-9)

S = ev["samples"]; st = np.array([s["t"] for s in S])
def curve(k): return np.interp(np.arange(N) / SR, st, np.array([s[k] for s in S], dtype=float))
kt = curve("kt"); rain = curve("rain"); rate = curve("rate"); night = curve("night")
T0, TE, TR = ev["T0"], ev["TE"], ev["T_RISE"]
TS = np.arange(N) / SR

# ------------------------------------------------------------------ music
CH = {"Bm": [35, 47, 54, 61, 62, 69], "G": [31, 43, 50, 59, 61, 66], "D": [38, 50, 57, 64, 66, 73], "A": [33, 45, 52, 57, 61, 64],
      "Em": [28, 40, 47, 54, 55, 62], "Dend": [26, 38, 50, 57, 62, 66, 69, 74, 78]}
PROG = [(0, "Bm"), (4, "G"), (8, "Em"), (12, "D"), (16, "Bm"), (20, "G"), (24, "A"), (28, "D"), (32, "Bm"), (36, "G"), (40, "A"),
        (44, "D"), (48, "A"), (52, "Dend")]
pad = np.zeros(N)
for i, (t0, name) in enumerate(PROG):
    t1 = PROG[i + 1][0] if i + 1 < len(PROG) else 60.0
    n = int(((t1 - t0) + 1.6) * SR); t = tt(n); seg = np.zeros(n)
    for m in CH[name]:
        f = mtof(m)
        for det in (-0.0045, 0.0045):
            for h in range(1, 9):
                if f * h > 7000: break
                seg += np.sin(2 * np.pi * f * (1 + det) * h * t + h * 1.3 + det * 900) / h * (0.5 if m < 40 else 1.0)
    e = np.clip(t / 0.9, 0, 1) * np.where(t > (t1 - t0), np.exp(-(t - (t1 - t0)) / 0.5), 1)
    if name == "Dend": e = np.clip(t / 0.35, 0, 1) * (0.62 + 0.38 * np.exp(-t / 2.0))
    i0 = int(t0 * SR); n2 = min(n, N - i0); pad[i0:i0 + n2] += (seg * e)[:n2]
bright = 450 + 2700 * (1 - night)
bright = np.where(TS < TR, np.interp(TS, [0, TR], [380, 900]), bright)
bright = np.where((TS >= TR) & (TS < T0), np.interp(TS, [TR, T0], [900, 2200]), bright)
bright = np.where(TS >= TE, 3800, bright)
pad = sweep(pad, "low", bright, blk=1024) * 0.030
add(pad, 0, 1.0, np.sin(TS * 2 * np.pi * 0.07) * 0.35)

BEAT = 0.5
for i, (t0, name) in enumerate(PROG):
    if name == "Dend": continue
    tones = [m + 12 for m in CH[name][2:]] + [CH[name][3] + 24]
    order = [0, 2, 1, 3, 2, 4, 3, 1]
    for k in range(16):
        ts = t0 + k * BEAT / 2
        if ts < T0 or ts >= TE: continue
        f = mtof(tones[order[k % 8] % len(tones)]); t = tt(int(0.6 * SR))
        s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t * 9)) * np.exp(-t * 6.5) * np.clip(t / 0.003, 0, 1)
        add(s, ts, 0.055 * (0.55 + 0.45 * (1 - night[int(ts * SR)])) * (1.0 if k % 2 == 0 else 0.7), 0.35 if k % 2 else -0.35)
for k in range(int((TE - T0) / BEAT)):
    ts = T0 + k * BEAT; t = tt(int(0.35 * SR))
    kick = np.sin(2 * np.pi * np.cumsum(46 + 40 * np.exp(-t * 30)) / SR) * np.exp(-t * 11)
    add(kick, ts, 0.16 if k % 2 == 0 else 0.10, 0)
    d = 1 - night[int(ts * SR)]
    if d > 0.2:
        m = int(0.06 * SR); add(filt(noise(m), "high", 6000) * np.exp(-tt(m) * 60), ts + BEAT / 2, 0.035 * d, 0.25)

# finale arpeggio under the totals
fin_tones = [74, 78, 81, 86, 90, 86, 81, 78]
for k in range(int((59.6 - 54.5) / (BEAT / 2))):
    ts = 54.5 + k * BEAT / 2; f = mtof(fin_tones[k % 8]); t = tt(int(0.7 * SR))
    s2 = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 9)) * np.exp(-t * 5.5) * np.clip(t / 0.003, 0, 1)
    add(s2, ts, 0.06 * (1.0 if k % 2 == 0 else 0.7), 0.3 if k % 2 else -0.3)
for k in range(int((59.5 - 55.0) / BEAT)):
    ts = 55.0 + k * BEAT; t = tt(int(0.35 * SR))
    add(np.sin(2 * np.pi * np.cumsum(46 + 40 * np.exp(-t * 30)) / SR) * np.exp(-t * 11), ts, 0.12 if k % 2 == 0 else 0.07, 0)

# ------------------------------------------------------------------ ambience, wind, rain
amb = norm(filt(np.cumsum(noise(N)) * 0.02, "low", 220))
add(amb * (0.04 + 0.045 * np.clip(rate / 90, 0, 1) + 0.03 * (TS < T0)), 0, 1.0, 0)
gl = np.interp(TS, np.arange(0, 61, 0.7), rng.uniform(0.55, 1.0, len(np.arange(0, 61, 0.7))))
wk = np.clip(kt / 20, 0, 1.4) ** 1.6
add(filt(noise(N), "bp", (260, 1100)) * gl * wk * 0.055, 0, 1.0, -0.3)
add(filt(noise(N), "bp", (300, 1300)) * gl[::-1] * wk * 0.055, 0, 1.0, 0.3)
drops = filt((rng.random(N) < 0.0009) * rng.uniform(0.3, 1.0, N), "bp", (1800, 6000))
add((filt(noise(N), "high", 2600) * 0.022 + drops * 0.3) * rain, 0, 1.0, -0.5)
add((filt(noise(N), "high", 2600) * 0.022 + drops[::-1] * 0.3) * rain, 0, 1.0, 0.5)

# ------------------------------------------------------------------ aircraft (durations stretch with each shot's speed)
def tpl_departure(wide, k):
    d = 3.4 * k; n = int(d * SR); t = tt(n) / k
    roar = sweep(noise(n), "low", np.interp(t, [0, 0.4, 1.2, 2.2, 3.4], [260, 700, 1700, 1300, 600]))
    rumble = filt(noise(n), "low", 140) * 1.6
    e = np.interp(t, [0, 0.25, 0.95, 1.9, 3.4], [0, 0.35, 1.0, 0.75, 0])
    whine = np.sin(2 * np.pi * np.cumsum(np.interp(t, [0, 1.0, 3.4], [1500, 2500, 2100]) * (0.9 if wide else 1.0)) / SR) * 0.05 * np.interp(t, [0, 0.4, 1.4, 3.0], [0, 1, 0.7, 0])
    crk = filt((rng.random(n) < 0.004) * rng.uniform(-1, 1, n), "bp", (150, 900)) * 6 * np.interp(t, [0, 0.8, 1.5, 2.8, 3.4], [0, 0, 1, 0.4, 0])
    s = (roar + rumble * (1.3 if wide else 1.0)) * e + whine + crk * e
    return norm(s), np.interp(t, [0, 0.9, 2.4, 3.4], [0.55, 0.3, -0.5, -0.85])
def tpl_arrival(wide, k, td=1.4):
    d = 2.9 * k; n = int(d * SR); t = tt(n) / k - td
    wh = sweep(noise(n), "bp", np.interp(t, [-td, -0.2, 0.2, 1.5], [1400, 650, 500, 400]), q=0.6) * np.interp(t, [-td, -0.15, 0.1, 0.4], [0, 0.8, 0.45, 0.2])
    chirp = np.zeros(n)
    for j, dt in enumerate((0.0, 0.075)):
        i0 = int((td * k + dt) * SR); m = int(0.05 * SR)
        chirp[i0:i0 + m] += filt(noise(m), "bp", (1700, 3800)) * np.exp(-tt(m) * 70) * (1.0 if j == 0 else 0.6) * 3.2
    rev = filt(noise(n), "low", 650) * np.interp(t, [0, 0.15, 0.35, 0.8, 1.5], [0, 0, 1.0, 0.6, 0]) * (1.25 if wide else 1.0)
    return norm(wh + chirp + rev * 0.9), np.interp(t, [-td, 0, 1.5], [0.85, 0.1, -0.35])
TPL = {}
def tpl(typ, wide, sf):
    key = (typ, wide, round(sf, 2))
    if key not in TPL:
        k = 1 / sf
        TPL[key] = [tpl_departure(wide, k) if typ == "D" else tpl_arrival(wide, k) for _ in range(2)]
    return TPL[key][rng.integers(2)]
for e in ev["inset"]:
    if e["t"] > TE + 0.3: continue
    s, pan = tpl(e["type"], e["wide"], e["sf"])
    near = e["rw"] == "27L"
    g = 0.10 * rng.uniform(0.8, 1.15) * (1.25 if e["wide"] else 1.0) * (1.1 if near else 0.9) * e["near"]
    if e["intro"]: g *= 1.7
    start = e["t"] - (0 if e["type"] == "D" else 1.4 / e["sf"])
    add(s, start, g, pan)

# ------------------------------------------------------------------ intro: title impact, subtitles, rise into the sky
n = int(0.75 * SR); t = tt(n)
add(norm(sweep(noise(n), "bp", np.interp(t, [0, 0.75], [600, 5000]), q=0.5) * (t / 0.75) ** 2.2), ev["title"] - 0.72, 0.16, 0)
add(boom(3.2, 34, 80, 1.1), ev["title"], 0.55, 0)
for m, d in ((50, 0), (57, 0.02), (62, 0.04), (69, 0.06)): add(bell(mtof(m + 12), 3.0, 1.0, 2.0, 1.2), ev["title"] + d, 0.035, -0.3 + d * 8)
n = int(1.4 * SR); t = tt(n)
add(norm(sweep(noise(n), "bp", np.interp(t, [0, 1.4], [3000, 8000]), q=0.4) * np.sin(np.pi * t / 1.4) ** 2), ev["sky"] - 0.1, 0.05, 0)
for i, ts in enumerate(ev["subs"]):
    f = mtof([74, 78, 81][i]); add(bell(f, 2.0, 1.1, 2.0, 2.6), ts, 0.075, (-0.4, 0, 0.4)[i]); add(boom(0.9, 55, 60, 5), ts, 0.10, 0)
n = int(2.6 * SR); t = tt(n)
add(norm(sweep(noise(n), "bp", np.interp(t, [0, 1.6, 2.6], [250, 3200, 900]), q=0.7) * np.interp(t, [0, 1.5, 2.6], [0, 1, 0])), TR - 0.3, 0.26, np.interp(t, [0, 2.6], [-0.5, 0.5]))
add(boom(2.0, 40, 70, 2.2), T0, 0.35, 0)
add(bell(mtof(74), 2.4, 1.2, 2.0), T0, 0.05, 0)

# ------------------------------------------------------------------ storytelling cues during the day
for c in ev["cuts"]:
    n = int(0.5 * SR); t = tt(n); add(norm(sweep(noise(n), "bp", np.interp(t, [0, 0.5], [2400, 500]), q=0.6) * np.sin(np.pi * t / 0.5) ** 2), c - 0.25, 0.05, 0)
for h, ht in enumerate(ev["hours"]):
    if h == 0 or ht > TE + 0.01: continue
    m = int(0.05 * SR); tk = np.sin(2 * np.pi * 3100 * tt(m)) * np.exp(-tt(m) * 120) + filt(noise(m), "high", 5000) * np.exp(-tt(m) * 200) * 0.4
    add(tk, ht, 0.06 if h % 6 else 0.10, 0)
NOTES = [74, 76, 78, 81, 83, 81, 78, 86, 74]
for i, t0 in enumerate(ev["toasts"]):
    f = mtof(NOTES[i % len(NOTES)]); add(bell(f), t0, 0.085, -0.15); add(bell(f * 1.5), t0 + 0.11, 0.055, 0.15)
for mt in ev["milestones"]:
    if mt is None: continue
    for k, m in enumerate((86, 90, 93)): add(bell(mtof(m), 1.2, 1.0, 2.0), mt + k * 0.06, 0.04, -0.3 + k * 0.3)
sw = ev["switchT"]
if sw > 0:
    m = int(0.16 * SR); sq = norm(filt(noise(m), "bp", (900, 3200)) * np.exp(-tt(m) * 12)); add(sq, sw, 0.10, 0.4)
for k in range(14):
    ts = ev["sunrise"] + rng.uniform(0, 2.2); m = int(rng.uniform(0.05, 0.12) * SR); tb = tt(m)
    f = np.interp(tb, [0, tb[-1]], [rng.uniform(3000, 4200), rng.uniform(4500, 6200)])
    add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tb / tb[-1]) ** 2, ts, 0.03, rng.uniform(-0.8, 0.8))
for t0, up in ((ev["sunrise"], True), (ev["sunset"], False)):
    n = int(2.0 * SR); t = tt(n); f0 = np.interp(t, [0, 2], [600, 1500] if up else [1500, 600])
    add(sum(np.sin(2 * np.pi * np.cumsum(f0 * r) / SR) for r in (1, 1.5, 2.0)) * np.sin(np.pi * t / 2) ** 2, t0 - 0.2, 0.012, 0)

# ------------------------------------------------------------------ kinetic-type word pops (subtle)
for i, wt in enumerate(ev.get("words", [])):
    m = int(0.06 * SR); tb = tt(m); f = 1900 + 260 * (i % 5)
    p = np.sin(2 * np.pi * f * tb * (1 + 0.6 * np.exp(-tb * 60))) * np.exp(-tb * 70) + filt(noise(m), "high", 4000) * np.exp(-tb * 150) * 0.3
    add(p, wt, 0.022, (-0.25, 0.25)[i % 2])

# ------------------------------------------------------------------ small airport sound layer
def radio_voice(dur):
    n = int(dur * SR); t = tt(n); out = np.zeros(n); pos = 0
    while pos < n - int(0.1 * SR):
        sl = int(rng.uniform(0.07, 0.17) * SR); f0 = rng.uniform(105, 170)
        ts = tt(sl); ph = np.cumsum(f0 * (1 + 0.04 * np.sin(2 * np.pi * 5 * ts))) / SR
        buzz = 2 * (ph % 1) - 1
        syl = sum(filt(buzz, "bp", (f * 0.85, f * 1.15)) * a for f, a in ((rng.uniform(450, 850), 1.0), (rng.uniform(1000, 1700), 0.7), (rng.uniform(2200, 2900), 0.35)))
        syl *= np.abs(np.sin(np.pi * ts / ts[-1])) ** 0.6
        out[pos:pos + sl] += syl[:max(0, min(sl, n - pos))]; pos += sl + int(rng.uniform(0.0, 0.07) * SR) + (int(0.18 * SR) if rng.random() < 0.15 else 0)
    out = filt(np.tanh(norm(out) * 2.2), "bp", (420, 2700))
    return norm(out + filt(noise(n), "bp", (500, 3000)) * 0.06)
def click(): m = int(0.035 * SR); return norm(filt(noise(m), "high", 1800) * np.exp(-tt(m) * 90))
# ATC chatter (faint, panned toward the radar side)
ts = T0 + 0.8
while ts < TE - 1.0:
    d = rng.uniform(0.9, 1.7); v = radio_voice(d)
    add(click(), ts - 0.04, 0.020, 0.45); add(v, ts, 0.022, 0.45); add(click(), ts + d, 0.016, 0.45)
    ts += d + rng.uniform(2.2, 4.6)
# terminal PA chime (ding-dong), every ~10 s
ts = T0 + 4.2
while ts < TE - 2:
    for f, dt in ((659.25, 0.0), (523.25, 0.42)):
        m = int(1.6 * SR); tb = tt(m); add((np.sin(2 * np.pi * f * tb) + 0.25 * np.sin(4 * np.pi * f * tb)) * np.exp(-tb * 2.4) * np.clip(tb / 0.01, 0, 1), ts + dt, 0.016, -0.35)
    ts += rng.uniform(9.0, 12.5)
# distant jet whine bed (daytime)
wh = filt(noise(N), "bp", (1900, 3600)) * 0.5 + np.sin(2 * np.pi * 3150 * TS + 0.3 * np.sin(2 * np.pi * 0.2 * TS)) * 0.02
add(wh * 0.006 * np.clip(rate / 80, 0, 1), 0, 1.0, 0.1)
# go-arounds: engine spool-up + short alert tone
for g in ev.get("ga", []):
    for k in range(2):
        m = int(0.12 * SR); add(np.sin(2 * np.pi * 1320 * tt(m)) * np.clip((0.12 - tt(m)) / 0.01, 0, 1) * np.clip(tt(m) / 0.005, 0, 1), g + 0.05 + k * 0.18, 0.035, 0.45)

# ------------------------------------------------------------------ finale
n = int(1.6 * SR); t = tt(n)
add(norm(sweep(noise(n), "bp", np.interp(t, [0, 1.6], [400, 6000]), q=0.5) * (t / 1.6) ** 2), TE - 1.6, 0.12, 0)
add(boom(3.0, 34, 70, 1.2), TE, 0.42, 0)
for i, ts in enumerate(ev["tag"]):
    add(boom(1.8, 40 + i * 4, 70, 2.0), ts, 0.38, 0)
    for k, m in enumerate([(62, 69, 74), (64, 71, 76), (66, 73, 78)][i]): add(bell(mtof(m + 12), 2.4, 1.2, 2.0, 1.8), ts + k * 0.015, 0.035, -0.3 + k * 0.3)
for i, ts in enumerate(ev["totals"]):
    n = int(0.45 * SR); t = tt(n)
    add(norm(sweep(noise(n), "bp", np.interp(t, [0, 0.45], [800, 4000]), q=0.6) * np.sin(np.pi * t / 0.45) ** 2), ts - 0.05, 0.05, 0.5)
    # counting ticks that slow down with the ease-out count-up
    for j in range(16):
        u = j / 16; tk_t = ts + 0.1 + 1.5 * (1 - (1 - u) ** (1 / 3))
        m = int(0.03 * SR); add(np.sin(2 * np.pi * (2600 + 60 * i) * tt(m)) * np.exp(-tt(m) * 160), tk_t, 0.035, 0.2)
    add(bell(mtof([74, 78, 81, 86][i]), 2.4, 1.3, 2.0), ts + 1.6, 0.075, (-0.3, -0.1, 0.1, 0.3)[i])

# ------------------------------------------------------------------ master
mix = np.stack([L, R], 1)
mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
fo = int(1.4 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
mix *= 10 ** (-17 / 20) / np.sqrt(np.mean(mix ** 2))
mix = np.tanh(mix * 1.15) / np.tanh(1.15); mix *= 0.93 / np.abs(mix).max()
print("peak", np.abs(mix).max(), "rms dBFS", 20 * np.log10(np.sqrt(np.mean(mix ** 2))))
print(" ".join("%d:%.0f" % (s, 20 * np.log10(np.sqrt((mix[s * SR:(s + 2) * SR] ** 2).mean()) + 1e-9)) for s in range(0, 60, 2)))
with wave.open(sys.argv[2] if len(sys.argv) > 2 else "soundtrack.wav", "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((mix * 32767).astype("<i2").tobytes())
