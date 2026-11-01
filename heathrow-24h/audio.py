"""Synthesise the full 60 s soundtrack from events.json (exported by the page)."""
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

SR = 48000
DUR = 60.0
N = int(SR * DUR)
ev = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "events.json"))
rng = np.random.default_rng(1101)
L = np.zeros(N); R = np.zeros(N)

def tt(n): return np.arange(n) / SR
def noise(n): return rng.standard_normal(n)
def filt(x, kind, f, order=2):
    nyq = SR / 2
    if kind == "bp": sos = butter(order, [f[0] / nyq, f[1] / nyq], "band", output="sos")
    else: sos = butter(order, min(f, nyq * 0.95) / nyq, kind, output="sos")
    return sosfilt(sos, x)
def sweep(x, kind, fc, blk=512, q=0.5):
    """time-varying filter; fc = array of cutoffs (per sample) """
    out = np.zeros_like(x); zi = None; sos_prev = None
    for i in range(0, len(x), blk):
        c = float(np.clip(fc[min(i, len(fc) - 1)], 30, SR * 0.45))
        if kind == "bp": sos = butter(1, [c * (1 - q) / (SR / 2), min(0.98, c * (1 + q) / (SR / 2))], "band", output="sos")
        else: sos = butter(2, c / (SR / 2), kind, output="sos")
        if zi is None: zi = sosfilt_zi(sos) * 0
        out[i:i + blk], zi = sosfilt(sos, x[i:i + blk], zi=zi)
    return out
def env_adsr(n, a, d_hold, r):
    t = tt(n); e = np.ones(n)
    e *= np.clip(t / max(a, 1e-4), 0, 1)
    rel_start = a + d_hold
    e *= np.where(t > rel_start, np.exp(-(t - rel_start) / max(r, 1e-4)), 1)
    return e
def add(sig, t0, gain=1.0, pan=0.0):
    """pan: scalar or per-sample array in [-1,1] (equal-power)"""
    i0 = int(round(t0 * SR)); n = len(sig)
    if i0 >= N: return
    if i0 < 0: sig = sig[-i0:]; n = len(sig); i0 = 0
    if isinstance(pan, np.ndarray):
        pan = pan[-len(sig):] if len(pan) > len(sig) else pan
    n = min(n, N - i0)
    p = pan[:n] if isinstance(pan, np.ndarray) else pan
    th = (np.clip(p, -1, 1) + 1) * np.pi / 4
    L[i0:i0 + n] += sig[:n] * gain * np.cos(th)
    R[i0:i0 + n] += sig[:n] * gain * np.sin(th)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def bell(f, dur=2.2, idx=2.2, ratio=3.5):
    t = tt(int(dur * SR))
    mod = np.sin(2 * np.pi * f * ratio * t) * idx * np.exp(-t * 3.0)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 2.2) * np.clip(t / 0.004, 0, 1)

# -------------------------------------------------------------- per-time control curves
S = ev["samples"]
st = np.array([s["t"] for s in S])
def curve(key):
    return np.interp(np.arange(N) / SR, st, np.array([s[key] for s in S], dtype=float))
kt = curve("kt"); rain = curve("rain"); rate = curve("rate"); night = curve("night")
TE = ev["TE"]

# -------------------------------------------------------------- music (pads + arp + pulse)
CH = {
    "Bm": [35, 47, 54, 61, 62, 69], "G": [31, 43, 50, 59, 61, 66], "D": [38, 50, 57, 64, 66, 73],
    "A": [33, 45, 52, 57, 61, 64], "Dend": [26, 38, 50, 57, 62, 66, 69, 74],
}
PROG = [(0, "Bm"), (4, "G"), (8, "D"), (12, "Bm"), (16, "G"), (20, "A"), (24, "D"), (28, "Bm"), (32, "G"), (36, "A"),
        (40, "D"), (44, "Bm"), (48, "G"), (52, "A"), (56, "Dend")]
pad = np.zeros(N)
for i, (t0, name) in enumerate(PROG):
    t1 = PROG[i + 1][0] if i + 1 < len(PROG) else 60.0
    length = (t1 - t0) + 1.6
    n = int(length * SR); t = tt(n); seg = np.zeros(n)
    for m in CH[name]:
        f = mtof(m)
        for det in (-0.0045, 0.0045):
            for h in range(1, 9):
                if f * h > 7000: break
                seg += np.sin(2 * np.pi * f * (1 + det) * h * t + h * 1.3 + det * 900) / h * (0.5 if m < 40 else 1.0)
    e = np.clip(t / 0.9, 0, 1) * np.where(t > (t1 - t0), np.exp(-(t - (t1 - t0)) / 0.5), 1)
    if name == "Dend": e = np.clip(t / 0.25, 0, 1) * np.exp(-t / 3.2)
    i0 = int(t0 * SR); n2 = min(n, N - i0); pad[i0:i0 + n2] += (seg * e)[:n2]
bright = 500 + 2600 * (1 - night) + 900 * np.clip((np.arange(N) / SR - TE) / 0.3, 0, 1) * (np.arange(N) / SR > TE)
bright[: int(2.4 * SR)] = np.linspace(380, 700, int(2.4 * SR))
pad = sweep(pad, "low", bright, blk=1024)
pad *= 0.030
# slow stereo movement
lfo = np.sin(np.arange(N) / SR * 2 * np.pi * 0.07) * 0.35
add(pad, 0, 1.0, lfo)

# arpeggio plucks (from 05:00 to end of day)
BEAT = 0.5
arp = np.zeros(N)
for i, (t0, name) in enumerate(PROG):
    if t0 < 8 or name == "Dend": continue
    tones = [m + 12 for m in CH[name][2:]] + [CH[name][3] + 24]
    order = [0, 2, 1, 3, 2, 4, 3, 1]
    for k in range(16):
        ts = t0 + k * BEAT / 2
        if ts < ev["TN"] - 0.5 or ts >= TE: continue
        f = mtof(tones[order[k % 8] % len(tones)])
        n = int(0.6 * SR); t = tt(n)
        s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) * np.exp(-t * 9)) * np.exp(-t * 6.5) * np.clip(t / 0.003, 0, 1)
        g = 0.055 * (0.55 + 0.45 * (1 - night[int(ts * SR)])) * (1.0 if k % 2 == 0 else 0.7)
        add(s, ts, g, 0.35 if k % 2 else -0.35)

# soft pulse: kick on each beat after 05:00, shaker on off-beats in daytime
for k in range(int((TE - 8.0) / BEAT)):
    ts = 8.0 + k * BEAT
    if ts < ev["TN"]: continue
    n = int(0.35 * SR); t = tt(n)
    f = 46 + 40 * np.exp(-t * 30)
    kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)
    add(kick, ts, 0.16 if k % 2 == 0 else 0.10, 0)
    d = 1 - night[int(ts * SR)]
    if d > 0.2:
        sh = filt(noise(int(0.06 * SR)), "high", 6000) * np.exp(-tt(int(0.06 * SR)) * 60)
        add(sh, ts + BEAT / 2, 0.035 * d, 0.25)

# -------------------------------------------------------------- airport ambience, wind, rain
amb = filt(np.cumsum(noise(N)) * 0.02, "low", 220)
amb = amb / (np.abs(amb).max() + 1e-9)
add(amb * (0.035 + 0.045 * np.clip(rate / 90, 0, 1)), 0, 1.0, 0)
w = filt(noise(N), "bp", (260, 1100))
gl = np.interp(np.arange(N) / SR, np.arange(0, 61, 0.7), rng.uniform(0.55, 1.0, len(np.arange(0, 61, 0.7))))
wl = filt(noise(N), "bp", (300, 1300))
add(w * gl * (np.clip(kt / 20, 0, 1.4) ** 1.6) * 0.055, 0, 1.0, -0.3)
add(wl * gl[::-1] * (np.clip(kt / 20, 0, 1.4) ** 1.6) * 0.055, 0, 1.0, 0.3)
rn_l = filt(noise(N), "high", 2600); rn_r = filt(noise(N), "high", 2600)
drops = (rng.random(N) < 0.0009) * rng.uniform(0.3, 1.0, N)
drops = filt(drops, "bp", (1800, 6000))
add((rn_l * 0.022 + drops * 0.3) * rain, 0, 1.0, -0.5)
add((rn_r * 0.022 + drops[::-1] * 0.3) * rain, 0, 1.0, 0.5)

# -------------------------------------------------------------- aircraft templates
def tpl_departure(wide):
    d = 3.4; n = int(d * SR); t = tt(n)
    nz = noise(n)
    fc = np.interp(t, [0, 0.4, 1.2, 2.2, 3.4], [260, 700, 1700, 1300, 600])
    roar = sweep(nz, "low", fc, blk=512)
    rumble = filt(noise(n), "low", 140) * 1.6
    e = np.interp(t, [0, 0.25, 0.95, 1.9, 3.4], [0, 0.35, 1.0, 0.75, 0])
    whf = np.interp(t, [0, 1.0, 3.4], [1500, 2500, 2100]) * (0.9 if wide else 1.0)
    whine = np.sin(2 * np.pi * np.cumsum(whf) / SR) * 0.05 * np.interp(t, [0, 0.4, 1.4, 3.0], [0, 1, 0.7, 0])
    crk = filt((rng.random(n) < 0.004) * rng.uniform(-1, 1, n), "bp", (150, 900)) * 6 * np.interp(t, [0, 0.8, 1.5, 2.8, 3.4], [0, 0, 1, 0.4, 0])
    s = (roar * 1.0 + rumble * (1.3 if wide else 1.0)) * e + whine + crk * e
    pan = np.interp(t, [0, 0.9, 2.4, 3.4], [0.55, 0.3, -0.5, -0.85])
    return s / (np.abs(s).max() + 1e-9), pan
def tpl_arrival(wide, td=1.4):
    d = 2.9; n = int(d * SR); t = tt(n) - td
    fc = np.interp(t, [-td, -0.2, 0.2, 1.5], [1400, 650, 500, 400])
    wh = sweep(noise(n), "bp", fc, blk=512, q=0.6) * np.interp(t, [-td, -0.15, 0.1, 0.4], [0, 0.8, 0.45, 0.2])
    chirp = np.zeros(n)
    for k, dt in enumerate((0.0, 0.075)):
        i0 = int((td + dt) * SR); m = int(0.05 * SR)
        b = filt(noise(m), "bp", (1700, 3800)) * np.exp(-tt(m) * 70) * (1.0 if k == 0 else 0.6)
        chirp[i0:i0 + m] += b * 3.2
    rev = filt(noise(n), "low", 650) * np.interp(t, [0, 0.15, 0.35, 0.8, 1.5], [0, 0, 1.0, 0.6, 0]) * (1.25 if wide else 1.0)
    s = wh + chirp + rev * 0.9
    pan = np.interp(t, [-td, 0, 1.5], [0.85, 0.1, -0.35])
    return s / (np.abs(s).max() + 1e-9), pan
TPL = {("D", w): [tpl_departure(w) for _ in range(3)] for w in (False, True)}
TPL.update({("A", w): [tpl_arrival(w) for _ in range(3)] for w in (False, True)})

def pitch(sig, ratio):
    if abs(ratio - 1) < 1e-3: return sig
    idx = np.arange(0, len(sig) - 1, ratio)
    return np.interp(idx, np.arange(len(sig)), sig)

for e in ev["inset"]:
    if e["intro"]: continue
    s, pan = TPL[(e["type"], e["wide"])][rng.integers(3)]
    r = rng.uniform(0.9, 1.08) * (0.9 if e["wide"] else 1.0)
    s2 = pitch(s, r); p2 = pitch(pan, r)
    near = e["rw"] == ("27L" if e["type"] == "D" else "27L")
    g = 0.11 * rng.uniform(0.8, 1.15) * (1.25 if e["wide"] else 1.0) * (1.2 if near else 0.85)
    start = e["t"] - (0 if e["type"] == "D" else 1.4 / r)
    if e["t"] > TE + 0.5: continue
    add(s2, start, g, p2)

# intro plane: close chase-cam landing, touchdown at 2.3 s
n = int(4.8 * SR); t = tt(n)
eng = filt(noise(n), "low", 900) * 0.9 + filt(noise(n), "bp", (1800, 3200)) * 0.25
eng += np.sin(2 * np.pi * np.cumsum(np.interp(t, [0, 2.3, 4.8], [2300, 2200, 1700])) / SR) * 0.06
env = np.interp(t, [0, 0.6, 2.2, 2.4, 3.3, 4.8], [0.0, 0.55, 0.75, 0.5, 0.95, 0.0])
rev = filt(noise(n), "low", 520) * np.interp(t, [0, 2.4, 2.65, 3.6, 4.8], [0, 0, 1.0, 0.55, 0]) * 1.2
intro = eng * env + rev
add(intro / np.abs(intro).max(), 0.0, 0.62, np.interp(t, [0, 2.3, 4.8], [0.2, 0.0, -0.3]))
for k, dt in enumerate((0.0, 0.08)):
    m = int(0.07 * SR); b = filt(noise(m), "bp", (1500, 3600)) * np.exp(-tt(m) * 55)
    add(b / np.abs(b).max(), 2.3 + dt, 0.45 if k == 0 else 0.28, 0.05)

# -------------------------------------------------------------- UI / storytelling cues
# title shimmer + transition whoosh
n = int(1.6 * SR); t = tt(n)
sh = sweep(noise(n), "bp", np.interp(t, [0, 1.6], [2500, 7000]), q=0.4) * np.interp(t, [0, 1.1, 1.6], [0, 1, 0])
add(sh / np.abs(sh).max(), 0.05, 0.06, 0)
add(bell(mtof(74), 2.5, 1.2, 2.0), 0.85, 0.05, -0.2); add(bell(mtof(81), 2.5, 1.2, 2.0), 1.0, 0.04, 0.2)
n = int(2.4 * SR); t = tt(n)
wh = sweep(noise(n), "bp", np.interp(t, [0, 1.0, 2.4], [300, 2600, 500]), q=0.7) * np.interp(t, [0, 1.0, 2.4], [0, 1, 0])
add(wh / np.abs(wh).max(), 2.25, 0.20, np.interp(t, [0, 2.4], [-0.6, 0.6]))

# hour ticks
for h, ht in enumerate(ev["hours"]):
    if h == 0 or ht > TE + 0.01: continue
    m = int(0.05 * SR); tk = np.sin(2 * np.pi * 3100 * tt(m)) * np.exp(-tt(m) * 120) + filt(noise(m), "high", 5000) * np.exp(-tt(m) * 200) * 0.4
    add(tk, ht, 0.07 if h % 6 else 0.11, 0.0)
# toast chimes (pentatonic, ascending through the day)
NOTES = [74, 76, 78, 81, 83, 81, 78, 86, 74]
for i, tt0 in enumerate(ev["toasts"]):
    f = mtof(NOTES[i % len(NOTES)])
    add(bell(f), tt0, 0.09, -0.15); add(bell(f * 1.5), tt0 + 0.11, 0.06, 0.15)
# passenger milestones: sparkle
for mt in ev["milestones"]:
    if mt is None: continue
    for k, m in enumerate((86, 90, 93)):
        add(bell(mtof(m), 1.2, 1.0, 2.0), mt + k * 0.06, 0.045, -0.3 + k * 0.3)
# runway switch: ATC squelch + double beep
sw = ev["switchT"]
m = int(0.16 * SR); sq = filt(noise(m), "bp", (900, 3200)) * np.exp(-tt(m) * 12)
add(sq / np.abs(sq).max(), sw, 0.10, 0.4)
for k in range(2):
    m = int(0.07 * SR); add(np.sin(2 * np.pi * 1050 * tt(m)) * np.clip(tt(m) / 0.003, 0, 1) * np.clip((0.07 - tt(m)) / 0.005, 0, 1), sw + 0.2 + k * 0.12, 0.05, 0.4)
add(sq[::-1] / np.abs(sq).max(), sw + 0.5, 0.08, 0.4)
# sunrise birds + shimmer, sunset shimmer
for k in range(14):
    ts = ev["sunrise"] + rng.uniform(0, 2.2)
    m = int(rng.uniform(0.05, 0.12) * SR); tb = tt(m)
    f = np.interp(tb, [0, tb[-1]], [rng.uniform(3000, 4200), rng.uniform(4500, 6200)])
    ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tb / tb[-1]) ** 2
    add(ch, ts, 0.03, rng.uniform(-0.8, 0.8))
for tt0, up in ((ev["sunrise"], True), (ev["sunset"], False)):
    n = int(2.0 * SR); t = tt(n)
    f0 = np.interp(t, [0, 2], [600, 1500] if up else [1500, 600])
    s = sum(np.sin(2 * np.pi * np.cumsum(f0 * r) / SR) for r in (1, 1.5, 2.0)) * np.sin(np.pi * t / 2) ** 2
    add(s, tt0 - 0.2, 0.012, 0)

# end of day: riser + impact + chime
n = int(1.4 * SR); t = tt(n)
riser = sweep(noise(n), "bp", np.interp(t, [0, 1.4], [400, 6000]), q=0.5) * (t / 1.4) ** 2
add(riser / np.abs(riser).max(), TE - 1.4, 0.12, 0)
n = int(2.5 * SR); t = tt(n)
boom = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-t * 8)) / SR) * np.exp(-t * 1.6)
add(boom, TE, 0.30, 0)
for k, m in enumerate((74, 78, 81, 86)):
    add(bell(mtof(m), 3.5, 1.4, 2.0), TE + 0.05 + k * 0.09, 0.07, -0.3 + k * 0.2)

# -------------------------------------------------------------- master
mix = np.stack([L, R], 1)
# gentle fade in/out
mix[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
fo = int(1.6 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
rms = np.sqrt(np.mean(mix ** 2)); mix *= 10 ** (-17 / 20) / rms
mix = np.tanh(mix * 1.15) / np.tanh(1.15)
mix *= 0.93 / np.abs(mix).max()
print("peak", np.abs(mix).max(), "rms dBFS", 20 * np.log10(np.sqrt(np.mean(mix ** 2))))
with wave.open(sys.argv[2] if len(sys.argv) > 2 else "soundtrack.wav", "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((mix * 32767).astype("<i2").tobytes())
