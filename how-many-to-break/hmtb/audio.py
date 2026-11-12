"""Soundtrack: procedural sound effects placed from the render's events log.

Every sound is synthesised with numpy (no samples needed): impacts per drop object,
creaks, cracks and shatters per target material, debris hits from the physics sim,
whooshes, a counter tick, a tension riser before the last drop and a sub boom at the
break. Events inside the slow-motion shatter or the replay are pitched down and
stretched.

Royalty-free files can replace any sound: drop them in ``sfx/`` with the slot name (see
sfx/README.md). For example ``sfx/impact_bowling_ball.wav``, or ``impact_bowling_ball_1.wav``,
``_2`` and so on for variations. Any format ffmpeg reads works.
"""

import glob
import math
import os
import subprocess
import wave

import numpy as np

from . import PROJECT_DIR, catalog

SR = 48000
SFX_DIR = os.path.join(PROJECT_DIR, "sfx")


# ---------------------------------------------------------------------------
# Synthesis building blocks
# ---------------------------------------------------------------------------

def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _env(dur, attack=0.002, decay=0.2):
    t = _t(dur)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def _noise(rng, dur):
    return rng.standard_normal(int(dur * SR))


def _bandpass(x, lo, hi):
    """FFT band-pass with soft edges (fast for whole sounds)."""
    n = len(x)
    if n == 0:
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    w = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) * 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * w, n)


def _sweep(f0, f1, dur, decay=0.3, curve=3.0):
    t = _t(dur)
    f = f1 + (f0 - f1) * np.exp(-t * curve / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t / decay)


def _modes(freqs, decays, amps, dur, rng, detune=0.01):
    """Sum of decaying sine partials (bells, glass pings, metal)."""
    t = _t(dur)
    out = np.zeros_like(t)
    for f, d, a in zip(freqs, decays, amps):
        f *= 1 + rng.uniform(-detune, detune)
        out += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    return out


def _norm(x, peak=1.0):
    m = np.max(np.abs(x)) if len(x) else 0
    return x * (peak / m) if m > 0 else x


def _pad(x, dur):
    n = int(dur * SR)
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def _mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def _stretch(x, factor):
    """Slow down (factor < 1) by resampling: lower pitch, longer sound (tape-style)."""
    n = int(len(x) / factor)
    return np.interp(np.arange(n) * factor, np.arange(len(x)), x)


# ---------------------------------------------------------------------------
# Sound effects
# ---------------------------------------------------------------------------

def sfx_impact(sound, intensity, rng):
    """One drop object landing."""
    i = intensity
    if sound == "heavy_ball":
        thud = _sweep(140, 50, 0.5, decay=0.16) * 1.0
        clack = _bandpass(_noise(rng, 0.06), 900, 3500) * _env(0.06, 0.0005, 0.012) * 0.7
        tock = _modes([1150, 2380, 3900], [0.03, 0.02, 0.012], [0.5, 0.3, 0.15], 0.15, rng, 0.05)
        return _norm(_mix(thud, clack, tock * 0.6)) * (0.6 + 0.4 * i)
    if sound == "melon":
        thud = _sweep(110, 55, 0.45, decay=0.12)
        splat = _bandpass(_noise(rng, 0.25), 250, 1400) * _env(0.25, 0.004, 0.06) * 0.8
        return _norm(_mix(thud, splat)) * (0.6 + 0.4 * i)
    if sound == "brick":
        thud = _sweep(160, 70, 0.3, decay=0.08)
        clack = _bandpass(_noise(rng, 0.12), 500, 4000) * _env(0.12, 0.0005, 0.025)
        return _norm(_mix(thud * 0.9, clack)) * (0.55 + 0.45 * i)
    if sound == "phone":
        out = np.zeros(int(0.25 * SR))
        for k in range(int(rng.integers(2, 5))):
            off = int(rng.uniform(0, 0.06) * SR)
            click = _modes([rng.uniform(2200, 3800), rng.uniform(4500, 7000)], [0.02, 0.01], [0.6, 0.3], 0.08, rng)
            click += _bandpass(_noise(rng, 0.08), 2000, 9000) * _env(0.08, 0.0003, 0.006) * 0.6
            out[off:off + len(click)] += click * (1.0 if k == 0 else 0.5)
        return _norm(out) * (0.4 + 0.3 * i)
    if sound == "anvil":
        f0 = rng.uniform(380, 460)
        ring = _modes([f0, f0 * 2.32, f0 * 4.25, f0 * 6.63, f0 * 9.4], [1.1, 0.7, 0.45, 0.3, 0.2],
                      [0.5, 0.35, 0.25, 0.15, 0.1], 1.6, rng, 0.004)
        thud = _sweep(100, 40, 0.6, decay=0.2)
        hit = _bandpass(_noise(rng, 0.05), 1000, 8000) * _env(0.05, 0.0003, 0.008)
        return _norm(_mix(thud * 1.2, ring * 0.7, hit * 0.6)) * (0.7 + 0.3 * i)
    return _norm(_sweep(140, 60, 0.4, decay=0.12)) * i


def sfx_surface(material, intensity, rng):
    """The target answering each hit: glass rings, a trampoline boings, wood knocks."""
    if material == "glass":
        return _modes([rng.uniform(1700, 2100), rng.uniform(3600, 4300), rng.uniform(6200, 7400)],
                      [0.25, 0.15, 0.08], [0.25, 0.15, 0.08], 0.5, rng) * intensity
    if material == "fabric":
        t = _t(0.55)
        f = 140 + 90 * np.exp(-t * 6) * np.cos(2 * np.pi * 9 * t)
        boing = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
        springs = _modes([rng.uniform(2400, 2900), rng.uniform(4100, 4600)], [0.12, 0.08], [0.1, 0.06], 0.4, rng)
        return _mix(boing * 0.6, springs) * intensity
    if material == "wood":
        return _modes([rng.uniform(180, 220), rng.uniform(410, 470), rng.uniform(900, 1100)],
                      [0.09, 0.05, 0.03], [0.5, 0.3, 0.15], 0.3, rng) * intensity
    if material == "shell":
        return _modes([rng.uniform(1300, 1600)], [0.04], [0.15], 0.1, rng) * intensity
    return np.zeros(1)


def sfx_creak(material, intensity, rng):
    dur = rng.uniform(0.6, 1.0) * (0.7 + 0.5 * intensity)
    t = _t(dur)
    if material == "wood":
        rate = 35 + 40 * np.sin(np.pi * t / dur) + rng.uniform(-5, 5)
        phase = np.cumsum(rate) / SR
        pulses = (np.diff(np.floor(phase), prepend=0) > 0).astype(float)
        pulses *= 0.6 + 0.4 * rng.random(len(pulses))
        body = _bandpass(np.convolve(pulses, np.exp(-_t(0.01) / 0.002), "same"), 300, 1400)
        return _norm(body) * np.sin(np.pi * t / dur) ** 0.5 * 0.55 * intensity
    if material == "glass":
        f = 2200 + 900 * np.sin(np.pi * t / dur) + 120 * np.sin(2 * np.pi * 23 * t)
        squeal = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / dur) ** 2 * 0.18
        groan = _bandpass(_noise(rng, dur), 120, 600) * np.sin(np.pi * t / dur) * 0.25
        tick = np.zeros_like(t)
        for _ in range(int(6 * intensity) + 2):
            k = int(rng.uniform(0, dur - 0.03) * SR)
            ping = _modes([rng.uniform(3000, 8000)], [0.006], [1.0], 0.03, rng)
            tick[k:k + len(ping)] += ping * 0.3
        return (squeal + groan + tick) * intensity
    if material == "fabric":
        f = 90 + 40 * t / dur
        saw = 2 * ((np.cumsum(f) / SR) % 1.0) - 1
        stretch = _bandpass(saw, 150, 900) * np.sin(np.pi * t / dur) * 0.35
        squeak = np.sin(2 * np.pi * np.cumsum(1800 + 300 * t / dur) / SR) * np.sin(np.pi * t / dur) ** 4 * 0.1
        return (stretch + squeak) * intensity
    return _bandpass(_noise(rng, 0.2), 1500, 7000) * _env(0.2, 0.002, 0.04) * 0.3 * intensity


def sfx_crack(material, intensity, rng):
    dur = 0.12 + 0.2 * intensity
    out = np.zeros(int((dur + 0.15) * SR))
    n = int(5 + 14 * intensity)
    for k in range(n):
        off = int((k / n) ** 1.5 * dur * SR + rng.uniform(0, 0.01) * SR)
        if material == "glass":
            s = _modes([rng.uniform(2500, 9000), rng.uniform(5000, 11000)], [0.02, 0.01], [1, 0.6], 0.06, rng)
        elif material == "wood":
            s = _bandpass(_noise(rng, 0.04), 300, 3000) * _env(0.04, 0.0003, 0.006) * 1.5
        else:
            s = _bandpass(_noise(rng, 0.03), 1500, 9000) * _env(0.03, 0.0002, 0.004)
        out[off:off + len(s)] += s * rng.uniform(0.4, 1.0)
    snap = _bandpass(_noise(rng, 0.05), 800, 10000) * _env(0.05, 0.0002, 0.006)
    out[:len(snap)] += snap * 1.2
    return _norm(out) * (0.45 + 0.4 * intensity)


def sfx_shatter(material, rng):
    """The big moment. Long and layered; it gets stretched further in slow motion."""
    dur = 2.4
    if material == "glass":
        crash = _bandpass(_noise(rng, 0.6), 600, 14000) * _env(0.6, 0.001, 0.12) * 1.0
        out = np.zeros(int(dur * SR))
        for k in range(260):
            off = int(rng.random() ** 2.2 * (dur - 0.2) * SR)
            ping = _modes([rng.uniform(2500, 11000), rng.uniform(4000, 13000)], [0.05, 0.03],
                          [1, 0.5], 0.15, rng)
            out[off:off + len(ping)] += ping * rng.uniform(0.05, 0.25) * (1 - off / len(out))
        return _norm(_mix(crash, out * 0.9))
    if material == "wood":
        snap = _bandpass(_noise(rng, 0.4), 150, 6000) * _env(0.4, 0.0005, 0.07) * 1.2
        splinters = sfx_crack("wood", 1.0, rng)
        clunks = np.zeros(int(dur * SR))
        for k in range(10):
            off = int(rng.uniform(0.1, 1.6) * SR)
            c = _modes([rng.uniform(150, 260), rng.uniform(380, 520)], [0.08, 0.05], [0.6, 0.3], 0.25, rng)
            clunks[off:off + len(c)] += c * rng.uniform(0.2, 0.6)
        return _norm(_mix(snap, splinters, clunks))
    if material == "fabric":
        t = _t(0.9)
        rip = _bandpass(_noise(rng, 0.9), 400, 6000) * (np.sin(np.pi * t / 0.9) ** 0.5) * \
            (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 37 * t)))
        twangs = np.zeros(int(dur * SR))
        for k in range(8):
            off = int(rng.uniform(0.05, 1.2) * SR)
            tw = _sweep(rng.uniform(600, 1200), rng.uniform(200, 400), 0.4, decay=0.15)
            twangs[off:off + len(tw)] += tw * 0.3
        return _norm(_mix(rip, twangs))
    if material == "shell":
        crunch = sfx_crack("shell", 1.0, rng)
        splat = _bandpass(_noise(rng, 0.4), 200, 1500) * _env(0.4, 0.01, 0.1) * 0.8
        return _norm(_mix(crunch, np.concatenate([np.zeros(int(0.05 * SR)), splat])))
    return _norm(_bandpass(_noise(rng, 1.0), 200, 8000) * _env(1.0, 0.001, 0.2))


def sfx_boom(rng):
    t = _t(1.6)
    f = 34 + 40 * np.exp(-t * 5)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55) * np.clip(t / 0.005, 0, 1)


def sfx_whoosh(intensity, rng, dur=0.45):
    t = _t(dur)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    lo = _bandpass(_noise(rng, dur), 250, 1600)
    hi = _bandpass(_noise(rng, dur), 1600, 5000)
    mix_ = lo * (1 - t / dur) + hi * (t / dur) * 0.5
    return _norm(mix_ * env) * 0.18 * intensity


def sfx_tick(rng):
    return _modes([2400, 4800], [0.012, 0.006], [1, 0.4], 0.04, rng) * 0.15


def sfx_riser(dur, rng):
    t = _t(dur)
    u = t / dur
    noise = _bandpass(_noise(rng, dur), 400, 6000)
    tone = np.sin(2 * np.pi * np.cumsum(110 + 330 * u ** 2) / SR)
    return (noise * 0.25 + tone * 0.2) * u ** 2.5


def sfx_intro_hit(rng):
    """Frame-0 hit under the title: sub thump plus a bright ping."""
    return _norm(_mix(_sweep(90, 40, 0.8, decay=0.25), _modes([1568, 3136], [0.25, 0.12], [0.25, 0.1], 0.8, rng),
                      _bandpass(_noise(rng, 0.08), 2000, 9000) * _env(0.08, 0.0005, 0.01) * 0.3)) * 0.8


def sfx_pop(rng):
    t = _t(0.12)
    return np.sin(2 * np.pi * np.cumsum(500 + 900 * np.exp(-t * 40)) / SR) * np.exp(-t / 0.03) * 0.35


def sfx_outro(rng):
    """Bright plucked chord for the end card."""
    out = np.zeros(int(2.6 * SR))
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        t = _t(2.2)
        tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.7)
        off = int(k * 0.045 * SR)
        out[off:off + len(tone)] += tone * 0.25
    return out


def room_tone(n, rng):
    """Very quiet filtered noise so the track never drops to digital silence."""
    x = _bandpass(rng.standard_normal(n), 60, 1800)
    x /= np.sqrt(np.mean(x ** 2)) + 1e-12
    return np.stack([x, np.roll(x, 997)], axis=1) * 10 ** (-58 / 20)


def tension_bed(total_s, events, rng):
    """A quiet low drone that thickens as the pile grows, cut dead at the break."""
    n = int(total_s * SR)
    t = np.arange(n) / SR
    counts = [(e["frame"] / 30.0, e["count"]) for e in events if e["type"] == "impact" and not e.get("replay")]
    brk = next((e["frame"] / 30.0 for e in events if e["type"] == "break" and not e.get("replay")), total_s)
    if not counts:
        return np.zeros((n, 2))
    times = np.array([c[0] for c in counts])
    vals = np.array([c[1] for c in counts], dtype=float) / max(c[1] for c in counts)
    level = np.interp(t, times, vals, left=0.0)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.4 * t + 1.0)
             + 0.35 * np.sin(2 * np.pi * 110 * t * (1 + 0.002 * np.sin(2 * np.pi * 0.2 * t))))
    pulse = 0.75 + 0.25 * np.sin(2 * np.pi * (0.5 + 1.5 * level) * t)
    out = drone * pulse * (0.02 + 0.06 * level ** 1.5)
    out[t >= brk] = 0.0
    fade = np.clip((brk - t) / 0.05, 0, 1)
    out *= fade
    return np.stack([out, out * 0.95], axis=1)


# ---------------------------------------------------------------------------
# Custom SFX slots
# ---------------------------------------------------------------------------

_custom_cache = {}


def _decode(path):
    if path not in _custom_cache:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                             check=True, capture_output=True).stdout
        _custom_cache[path] = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return _custom_cache[path]


def custom_sound(slots, pick):
    """First matching file in sfx/ for the given slot names, or None."""
    for slot in slots:
        files = sorted(f for f in glob.glob(os.path.join(SFX_DIR, slot + ".*")) +
                       glob.glob(os.path.join(SFX_DIR, slot + "_[0-9]*.*"))
                       if not f.endswith((".md", ".txt")))
        if files:
            return _decode(files[pick % len(files)])
    return None


# ---------------------------------------------------------------------------
# Mixing
# ---------------------------------------------------------------------------

def _place(buf, sound, time_s, gain=1.0, pan=0.0):
    if sound is None or len(sound) == 0:
        return
    start = int(time_s * SR)
    if start >= len(buf):
        return
    end = min(len(buf), start + len(sound))
    s = sound[:end - start] * gain
    a = (pan + 1) * math.pi / 4
    buf[start:end, 0] += s * math.cos(a)
    buf[start:end, 1] += s * math.sin(a)


def _reverb(buf, rng, wet=0.12, length=0.7):
    t = _t(length)
    ir = rng.standard_normal((len(t), 2)) * np.exp(-t / (length / 5))[:, None]
    ir[: int(0.01 * SR)] = 0
    n = len(buf) + len(ir)
    size = 1 << (n - 1).bit_length()
    out = np.zeros_like(buf)
    for ch in range(2):
        y = np.fft.irfft(np.fft.rfft(buf[:, ch], size) * np.fft.rfft(ir[:, ch], size), size)[:len(buf)]
        out[:, ch] = y
    out *= wet / (np.max(np.abs(out)) + 1e-9) * np.max(np.abs(buf))
    return buf + out


def build_soundtrack(events, out_path, seed=1):
    """Synthesise and mix the episode's audio from events.json into a 48 kHz WAV."""
    cfg = events["config"]
    rng = np.random.default_rng(seed)
    prng = rng
    total_s = events["total_frames"] / float(events["fps"])
    buf = np.zeros((int(total_s * SR) + SR, 2))
    obj_key = cfg["drop_object"]
    sound = catalog.drop_object(obj_key)["sound"]
    material = catalog.target(cfg["target"])["material"]
    fps = float(events["fps"])

    for i, e in enumerate(events["events"]):
        t = e["frame"] / fps
        kind = e["type"]
        slow = e.get("slowmo") or e.get("replay")
        factor = 0.55 if slow else 1.0
        gain_mul = 0.8 if e.get("replay") else 1.0
        pan = e.get("pan", 0.0)
        if kind == "impact":
            s = custom_sound(["impact_" + obj_key, "impact"], i)
            if s is None:
                s = _mix(sfx_impact(sound, e["intensity"], prng), sfx_surface(material, 0.5 * e["intensity"], prng))
            if e.get("final"):
                s = _mix(s, sfx_boom(prng) * 0.6)
            if slow:
                s = _stretch(s, factor)
            _place(buf, s, t, 0.8 * gain_mul, pan)
            tick = custom_sound(["tick"], i)
            if not e.get("replay") and e["frame"] < events["segments"]["shatter"][0]:
                _place(buf, tick if tick is not None else sfx_tick(prng), t + 0.02, 1.0, 0.0)
        elif kind == "whoosh":
            s = custom_sound(["whoosh"], i)
            s = s if s is not None else sfx_whoosh(e["intensity"], prng)
            _place(buf, s, t, gain_mul)
        elif kind == "creak":
            s = custom_sound(["creak_" + material, "creak"], i)
            s = s if s is not None else sfx_creak(material, e["intensity"], prng)
            _place(buf, s, t, 0.9 * gain_mul, prng.uniform(-0.3, 0.3))
        elif kind == "crack":
            s = custom_sound(["crack_" + material, "crack"], i)
            s = s if s is not None else sfx_crack(material, e["intensity"], prng)
            _place(buf, s, t, 1.0 * gain_mul, prng.uniform(-0.2, 0.2))
        elif kind == "break":
            s = custom_sound(["shatter_" + material, "shatter"], i)
            s = s if s is not None else sfx_shatter(material, prng)
            s = _stretch(s, 0.7)    # the break always plays in slow motion
            _place(buf, s, t, 1.1 * gain_mul)
            b = custom_sound(["boom"], i)
            _place(buf, b if b is not None else sfx_boom(prng), t, 0.9 * gain_mul)
        elif kind == "debris":
            k = e.get("kind", "object")
            level = min(1.0, 0.25 + 0.15 * math.log1p(e["intensity"]))
            if k == "shard":
                s = custom_sound(["debris_" + material, "debris"], i)
                if s is None:
                    s = sfx_crack(material, 0.3, prng) if material != "fabric" else sfx_surface("fabric", 0.4, prng)
            elif k == "part":
                s = custom_sound(["debris_part", "debris"], i)
                s = s if s is not None else sfx_surface("wood", 1.0, prng)
            else:
                s = custom_sound(["impact_" + obj_key, "impact"], i)
                s = s if s is not None else sfx_impact(sound, 0.6, prng)
            if slow:
                s = _stretch(s, factor)
            _place(buf, s, t, 0.5 * level * gain_mul, pan)

    # Riser into the final drop, cut dead just before the impact.
    finals = [e for e in events["events"] if e["type"] == "impact" and e.get("final") and not e.get("replay")]
    if finals:
        fin = finals[0]["frame"] / fps
        dur = min(3.0, max(1.0, fin - 1.0))
        r = custom_sound(["riser"], 0)
        r = r[:int(dur * SR)] if r is not None else sfx_riser(dur, prng)
        _place(buf, r, fin - dur - 0.08, 0.5)

    # Hook, pill pop, end card.
    s = custom_sound(["intro"], 0)
    _place(buf, s if s is not None else sfx_intro_hit(prng), 0.0, 0.8)
    s = custom_sound(["pop"], 0)
    _place(buf, s if s is not None else sfx_pop(prng), 5 / fps, 0.8)
    outro_t = events["segments"]["outro"][0] / fps
    s = custom_sound(["whoosh"], 1)
    _place(buf, s if s is not None else sfx_whoosh(1.0, prng, dur=0.5) * 2.0, outro_t - 0.1, 1.0)
    s = custom_sound(["outro"], 0)
    _place(buf, s if s is not None else sfx_outro(prng), outro_t + 12 / fps, 0.7)
    # Whoosh under the diagonal swipe into the replay.
    replay_t = events["segments"]["replay"][0] / fps
    if events["segments"]["replay"][1] > events["segments"]["replay"][0]:
        s = custom_sound(["swipe", "whoosh"], 2)
        _place(buf, s if s is not None else sfx_whoosh(1.0, prng, dur=0.55) * 2.5, replay_t - 0.3, 1.0)
    buf += room_tone(len(buf), rng)

    music = custom_sound(["music"], 0)
    if music is not None:
        n = len(buf)
        m = np.tile(music, n // len(music) + 1)[:n]
        _place(buf, m, 0.0, 0.25)
    else:
        bed = tension_bed(total_s, events["events"], rng)
        buf[:len(bed)] += bed

    buf = _reverb(buf, rng)
    buf = buf[:int(total_s * SR)]
    # Gentle limiter, then normalise to -1 dBFS.
    peak = np.max(np.abs(buf)) + 1e-9
    buf = np.tanh(buf / peak * 1.6) / np.tanh(1.6)
    buf *= 10 ** (-1 / 20) / (np.max(np.abs(buf)) + 1e-9)
    pcm = (np.clip(buf, -1, 1) * 32767).astype("<i2")
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path
