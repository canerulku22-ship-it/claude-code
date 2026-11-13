"""Soundtrack for 'kaiju' episodes: voiceover, a procedural score and monster-movie SFX.

Three buses, mixed at the end:

* voice   the Piper TTS lines (hmtb/voice.py), placed at their ``at_s`` times
* music   a news sting, a creeping drone, a driving minor-key monster theme, a comic
          pineapple cue and a little tarantella under the end card; it ducks under the voice
* sfx     Big Ben bongs, bubbles, the geyser, the roar, stomps, flung buses, the bite, the
          rolling Eye, slices, pineapples and the splash, all timed from the events log

Any sound can be replaced by a file in sfx/ (see sfx/README.md): music.wav replaces the
score, and slots such as roar.wav, stomp.wav, splash.wav or bong.wav replace those effects.
"""

import math
import wave

import numpy as np

from .audio import (SR, _bandpass, _env, _mix, _modes, _noise, _norm, _place, _reverb, _sweep, _t, custom_sound,
                    room_tone, sfx_boom, sfx_crack, sfx_riser, sfx_shatter, sfx_whoosh)

# Note frequencies (Hz).
N = {"A1": 55.0, "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.0, "A2": 110.0, "Bb2": 116.54,
     "C3": 130.81, "C#3": 138.59, "D3": 146.83, "E3": 164.81, "F3": 174.61, "F#3": 185.0, "G3": 196.0,
     "A3": 220.0, "Bb3": 233.08, "C4": 261.63, "C#4": 277.18, "D4": 293.66, "E4": 329.63, "F#4": 369.99,
     "G4": 392.0, "A4": 440.0, "B4": 493.88, "D5": 587.33}


# ---------------------------------------------------------------------------
# Instruments (additive synthesis, all mono)
# ---------------------------------------------------------------------------

def _harmonics(f, t, n, rolloff, vib=0.0, vib_rate=5.5):
    phase = 2 * np.pi * f * t + vib * np.sin(2 * np.pi * vib_rate * t)
    out = np.zeros_like(t)
    for k in range(1, n + 1):
        if f * k > 9000:
            break
        out += np.sin(k * phase) / k ** rolloff
    return out


def brass(f, dur, rng):
    """Bright brass stab: a few detuned saw-like voices with a soft attack."""
    t = _t(dur)
    env = np.clip(t / 0.035, 0, 1) * np.exp(-t / (dur * 0.6))
    out = sum(_harmonics(f * (1 + d), t, 14, 1.15, vib=0.002 * f / 5.5) for d in (-0.004, 0.0, 0.005))
    return out * env / 3.0


def bass(f, dur):
    t = _t(dur)
    env = np.clip(t / 0.006, 0, 1) * np.exp(-t / 0.22)
    return _harmonics(f, t, 10, 1.7) * env


def pad(freqs, dur):
    t = _t(dur)
    env = np.clip(t / 0.8, 0, 1) * np.clip((dur - t) / 0.8, 0, 1)
    out = np.zeros_like(t)
    for f in freqs:
        for d in (-0.006, 0.006):
            out += _harmonics(f * (1 + d), t, 6, 2.0)
    return out * env / (2 * len(freqs))


def pluck(f, dur=0.5):
    """Mandolin-ish pluck: bright partials that decay faster the higher they are."""
    t = _t(dur)
    out = np.zeros_like(t)
    for k in range(1, 9):
        out += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (3 + 2.2 * k))
    return out * np.clip(t / 0.002, 0, 1)


def taiko(rng, big=1.0):
    t = _t(0.7)
    body = np.sin(2 * np.pi * np.cumsum(55 + 75 * np.exp(-t * 18)) / SR) * np.exp(-t / (0.28 * big))
    skin = _bandpass(_noise(rng, 0.7), 150, 1200) * _env(0.7, 0.001, 0.03)
    return body + skin * 0.35


def snare(rng):
    return _bandpass(_noise(rng, 0.2), 900, 7000) * _env(0.2, 0.001, 0.05) * 0.6 + \
        np.sin(2 * np.pi * 190 * _t(0.2)) * _env(0.2, 0.001, 0.04) * 0.4


def hat(rng):
    return _bandpass(_noise(rng, 0.05), 6000, 14000) * _env(0.05, 0.0005, 0.012) * 0.5


def timpani_roll(rng, dur, f=N["D2"]):
    out = np.zeros(int(dur * SR) + SR)
    k = 0
    while k * 0.055 < dur:
        g = 0.3 + 0.7 * (k * 0.055 / dur) ** 2
        hit = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.3 * np.exp(-_t(0.6) * 30))) / SR) * _env(0.6, 0.002, 0.25)
        i = int(k * 0.055 * SR)
        out[i:i + len(hit)] += hit * g * rng.uniform(0.8, 1.0)
        k += 1
    return out


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

def _put(bus, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(bus) or i < 0:
        return
    n = min(len(x), len(bus) - i)
    bus[i:i + n] += x[:n] * g


def build_score(events, rng):
    """The music bus (mono), following the beats and moments of the episode."""
    fps = float(events["fps"])
    total = events["total_frames"] / fps
    seg = {k: (a / fps, b / fps) for k, (a, b) in events["segments"].items()}
    mo = {k: v / fps for k, v in events["moments"].items()}
    bus = np.zeros(int((total + 2) * SR))
    beat = 0.5                                                   # 120 BPM

    # Hook: brass stab + timpani, then a newsroom pulse (bass on D, ticking hats).
    for f in (N["D3"], N["F3"], N["A3"], N["E4"]):
        _put(bus, brass(f, 1.6, rng), 0.0, 0.5)
    _put(bus, taiko(rng, 1.4), 0.0, 1.0)
    t = 0.0
    while t < seg["hook"][1]:
        _put(bus, bass(N["D2"], 0.4), t, 0.45)
        for k in range(2):
            _put(bus, hat(rng), t + k * beat / 2, 0.5 if k == 0 else 0.3)
        t += beat

    # Erupt: low drone that swells, timpani roll into the geyser, heartbeat thumps after.
    a, b = seg["erupt"]
    _put(bus, pad([N["D2"], N["A2"], N["D3"]], b - a + 1.5), a, 0.9)
    _put(bus, timpani_roll(rng, mo["geyser"] - a - 0.4), a + 0.4, 0.35)
    _put(bus, sfx_riser(2.4, rng), mo["geyser"] - 2.4, 1.0)
    for f in (N["D3"], N["F3"], N["A3"]):
        _put(bus, brass(f, 1.2, rng), mo["geyser"], 0.55)
    t = mo["geyser"] + 0.9
    while t < seg["rise"][0]:
        _put(bus, taiko(rng, 0.8), t, 0.7)
        _put(bus, taiko(rng, 0.6), t + 0.28, 0.45)
        t += 0.85

    # Rise: hit + held minor chord under the roar.
    for f in (N["D2"], N["D3"], N["F3"], N["A3"]):
        _put(bus, brass(f, 2.4, rng), mo["rise_start"], 0.55)
    _put(bus, pad([N["D2"], N["F2"], N["A2"]], mo["name_card"] - mo["rise_start"] + 1.0), mo["rise_start"], 0.8)

    # Main theme: ostinato bass in 8ths, taiko, brass stabs (i - VI - iv - V), until the pineapple beat.
    start, end = mo["name_card"], seg["pineapple"][0]
    bars = [["D2", "D2", "F2", "D2", "G2", "D2", "F2", "E2"], ["D2", "D2", "F2", "D2", "A2", "G2", "F2", "C3"]]
    chords = [["D3", "F3", "A3"], ["Bb2", "D3", "F3"], ["G2", "Bb2", "D3"], ["A2", "C#3", "E3"]]
    bar = 0
    t = start
    while t < end - 0.05:
        full = bar >= 2
        for k, note in enumerate(bars[bar % 2]):
            tt = t + k * beat / 2
            if tt < end:
                _put(bus, bass(N[note], 0.3), tt, 0.55)
                if full:
                    _put(bus, hat(rng), tt, 0.25)
        for q in range(4):
            tt = t + q * beat
            if tt >= end:
                break
            if q in (0, 2):
                _put(bus, taiko(rng, 1.0), tt, 0.85)
            elif full:
                _put(bus, snare(rng), tt, 0.4)
        if bar % 4 == 3:                                         # a fill into the next phrase
            for k in range(4):
                _put(bus, taiko(rng, 0.6), t + 3 * beat + k * beat / 4, 0.4 + 0.1 * k)
        if bar % 2 == 0 or full:
            for n in chords[bar % 4]:
                _put(bus, brass(N[n], 0.9 if full else 1.4, rng), t, 0.32)
        bar += 1
        t += 4 * beat

    # Pineapple: suspense (pad + ticking), then a comic cue for the gag and a hit on the splash.
    a = seg["pineapple"][0]
    _put(bus, pad([N["D3"], N["A3"]], mo["pineapples"] - a + 0.5), a, 0.7)
    t = a
    while t < mo["pineapples"]:
        _put(bus, hat(rng), t, 0.6)
        t += beat / 2
    for k, n in enumerate(("D4", "B4", "G4", "D5")):              # bright plinks as pineapples land
        _put(bus, pluck(N[n], 0.4), mo["pineapples"] + k * 0.18, 0.5)
    for k, f in enumerate((N["F3"], N["E3"], N["D3"] * 1.0)):     # sad wah-wah-waaah on the gag
        dur = 0.45 if k < 2 else 1.1
        tt = _t(dur)
        x = _harmonics(f, tt, 10, 1.3, vib=0.0) * np.clip(tt / 0.04, 0, 1) * np.exp(-tt / (dur * 0.8))
        if k == 2:
            x = _harmonics(f, tt, 10, 1.3, vib=0.01 * f / 6.0, vib_rate=6.0) * np.clip(tt / 0.04, 0, 1) * \
                np.clip((dur - tt) / 0.3, 0, 1)
        _put(bus, x, mo["gag"] + 0.15 + k * 0.48, 0.3)
    for f in (N["D2"], N["A2"], N["D3"], N["F#3"]):
        _put(bus, brass(f, 1.5, rng), mo["splash"], 0.45)
    _put(bus, taiko(rng, 1.5), mo["splash"], 1.0)

    # End card: a little tarantella in D major (it's a pizza, after all), fading out.
    a = seg["end"][0] + 0.25
    melody = ["A4", "F#4", "D4", "F#4", "A4", "F#4", "G4", "E4", "C#4", "E4", "G4", "E4",
              "A4", "F#4", "D4", "F#4", "A4", "D5", "B4", "G4", "E4", "C#4", "D4", "D4"]
    step = 60.0 / 150 / 2                                        # triplet-ish 6/8 feel
    t = a
    k = 0
    while t < total - 0.6:
        n = melody[k % len(melody)]
        fade = min(1.0, (total - t) / 3.0)
        _put(bus, pluck(N[n], 0.35), t, 0.45 * fade)
        _put(bus, pluck(N[n] * 1.003, 0.35), t + step / 3, 0.2 * fade)         # mandolin tremolo
        if k % 3 == 0:
            root = N["D3"] if (k // 6) % 2 == 0 else N["A2"]
            _put(bus, pluck(root, 0.5), t, 0.5 * fade)
        t += step
        k += 1
    return bus[:int(total * SR)]


# ---------------------------------------------------------------------------
# Sound effects
# ---------------------------------------------------------------------------

def sfx_bong(rng):
    """A big hour bell: hum, prime, minor-third tierce, quint, nominal and upper partials."""
    f0 = 164.8
    ratios = [0.5, 1.0, 1.19, 1.5, 2.0, 2.52, 3.0, 4.07]
    decays = [5.0, 3.5, 2.8, 2.2, 2.4, 1.2, 0.9, 0.5]
    amps = [0.5, 0.6, 0.45, 0.25, 0.4, 0.2, 0.12, 0.08]
    tone = _modes([f0 * r for r in ratios], decays, amps, 4.5, rng, detune=0.002)
    strike = _bandpass(_noise(rng, 0.06), 800, 5000) * _env(0.06, 0.0005, 0.01)
    return _norm(_mix(tone, strike * 0.6)) * 0.9


def sfx_bloop(rng):
    dur = rng.uniform(0.08, 0.16)
    t = _t(dur)
    f0 = rng.uniform(120, 260)
    f = f0 * (1 + 2.5 * (1 - np.exp(-t * 35)))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur * 0.4)) * np.clip(t / 0.004, 0, 1)


def sfx_geyser(rng, dur=3.4):
    """Liquid roar: a burst of filtered noise that slowly closes down, over a boom."""
    t = _t(dur)
    roar = _bandpass(_noise(rng, dur), 60, 2500)
    hiss = _bandpass(_noise(rng, dur), 2000, 8000) * 0.3
    env = np.clip(t / 0.05, 0, 1) * np.exp(-t / 1.6)
    gurgle = np.sin(2 * np.pi * 7 * t) * 0.3 + 1.0
    return _norm(_mix((roar + hiss) * env * gurgle, sfx_boom(rng) * 1.2)) * 0.9


def sfx_roar(rng, dur=2.6, pitch=1.0):
    """Monster roar: a distorted, formant-filtered growl with a rasp and a sub layer."""
    t = _t(dur)
    env = np.clip(t / 0.18, 0, 1) * np.clip((dur - t) / 0.9, 0, 1)
    f0 = (78 + 22 * np.sin(2 * np.pi * 0.6 * t)) * pitch * (1 + 0.25 * np.exp(-t * 2.5))
    phase = 2 * np.pi * np.cumsum(f0 * (1 + 0.03 * np.sin(2 * np.pi * 6.3 * t))) / SR
    saw = sum(np.sin(k * phase) / k for k in range(1, 24))
    growl = saw * (1 + 0.6 * np.sin(2 * np.pi * 31 * t))
    voice = _bandpass(growl, 180, 900) + 0.6 * _bandpass(growl, 900, 2600)
    rasp = _bandpass(_noise(rng, dur), 400, 3200) * (0.6 + 0.4 * np.sin(2 * np.pi * 44 * t))
    x = np.tanh((_norm(voice) + 0.4 * _norm(rasp)) * 2.5)
    sub = np.sin(2 * np.pi * np.cumsum(f0 * 0.5) / SR) * 0.5
    return _norm((x + sub) * env) * 0.95


def sfx_stomp(rng, big=False):
    """Giant footstep: sub thump, ground crunch and a rattle of debris."""
    dur = 2.4 if big else 1.4
    sub = _sweep(75 if big else 65, 26, dur, decay=0.6 if big else 0.35)
    crunch = _bandpass(_noise(rng, 0.6), 80, 900) * _env(0.6, 0.002, 0.14)
    rattle = np.zeros(int(0.9 * SR))
    for _ in range(14 if big else 7):
        i = int(rng.uniform(0.04, 0.8) * SR)
        c = _bandpass(_noise(rng, 0.03), 1200, 5000) * _env(0.03, 0.0005, 0.008)
        rattle[i:i + len(c)] += c[:len(rattle) - i] * rng.uniform(0.2, 0.5)
    out = _mix(sub * 1.2, crunch * 0.6, rattle * 0.5)
    if big:
        out = _mix(out, sfx_boom(rng), _bandpass(_noise(rng, 3.0), 30, 200) * _env(3.0, 0.05, 1.0) * 0.8)
    return _norm(out) * (1.0 if big else 0.8)


def sfx_clang(rng, heavy=True):
    """A bus (or cab) kicked: metal clang plus a crunch."""
    base = 160 if heavy else 260
    tone = _modes([base, base * 2.43, base * 4.9, base * 7.6], [0.5, 0.35, 0.2, 0.12], [1, 0.6, 0.4, 0.2],
                  0.9, rng, detune=0.03)
    crunch = _bandpass(_noise(rng, 0.3), 300, 4000) * _env(0.3, 0.001, 0.06)
    return _norm(_mix(tone, crunch * 0.8)) * 0.6


def sfx_splash(rng, big=False):
    dur = 2.8 if big else 0.9
    t = _t(dur)
    body = _bandpass(_noise(rng, dur), 200, 6000) * np.clip(t / 0.01, 0, 1) * np.exp(-t / (dur * 0.3))
    low = _bandpass(_noise(rng, dur), 40, 300) * np.exp(-t / (dur * 0.25))
    out = _mix(body, low * 0.8)
    if big:
        out = _mix(out, sfx_boom(rng) * 0.9)
        for _ in range(25):                                     # drips falling back
            i = int(rng.uniform(0.5, 2.6) * SR)
            d = sfx_bloop(rng) * 0.2
            out[i:i + len(d)] += d[:len(out) - i]
    return _norm(out) * (0.95 if big else 0.55)


def sfx_crunch(rng, dur=0.7, n=5):
    """Stone crunching: a cluster of noise grains."""
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        i = int(rng.uniform(0, dur * 0.6) * SR)
        g = _bandpass(_noise(rng, 0.12), rng.uniform(150, 400), rng.uniform(2000, 5000)) * _env(0.12, 0.001, 0.035)
        out[i:i + len(g)] += g[:len(out) - i] * rng.uniform(0.5, 1.0)
    return _norm(out)


def sfx_groan(rng, dur=1.1):
    """Twisting steel: a slow, wobbling, distorted tone."""
    t = _t(dur)
    f = 95 + 30 * np.sin(2 * np.pi * 1.3 * t) + 15 * rng.standard_normal() * t
    x = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.04 * np.sin(2 * np.pi * 11 * t))) / SR)
    return np.tanh(x * 3) * np.clip(t / 0.1, 0, 1) * np.clip((dur - t) / 0.3, 0, 1) * 0.5


def sfx_roll(rng, dur):
    """The wheel rolling: low rumble pulsing with each turn, and a metal squeal."""
    t = _t(dur)
    rumble = _bandpass(_noise(rng, dur), 30, 350)
    rumble *= 0.7 + 0.3 * np.sin(2 * np.pi * (0.6 + 1.6 * t / dur) * t)
    squeal = np.sin(2 * np.pi * np.cumsum(1300 + 120 * np.sin(2 * np.pi * 3 * t)) / SR) * 0.05
    env = np.clip(t / 0.3, 0, 1) * np.clip((dur - t) / 0.5, 0, 1) * (0.5 + 0.5 * t / dur)
    return _norm((_norm(rumble) + squeal) * env) * 0.7


def sfx_slice(rng):
    """Cutting through a building: a metallic 'shing' and a crumble."""
    t = _t(0.45)
    shing = _bandpass(_noise(rng, 0.45), 3000, 10000) * np.exp(-t / 0.12)
    ring = np.sin(2 * np.pi * np.cumsum(2400 - 900 * t) / SR) * np.exp(-t / 0.15) * 0.4
    return _norm(_mix(shing + ring, sfx_crunch(rng, 0.9, 7) * 0.7)) * 0.7


def sfx_whistle(dur, rng):
    """Cartoon falling whistle."""
    t = _t(dur)
    f = 2200 * (600 / 2200.0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(t / 0.05, 0, 1) * 0.25


def sfx_boing(rng):
    t = _t(0.6)
    f = 240 + 140 * np.sin(2 * np.pi * 13 * t) * np.exp(-t * 4) + 120 * (1 - np.exp(-t * 6))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.22) * 0.5


def sfx_thud(rng):
    return _norm(_mix(_sweep(110, 45, 0.5, decay=0.12), _bandpass(_noise(rng, 0.2), 100, 1200) *
                      _env(0.2, 0.001, 0.04) * 0.5)) * 0.6


def sfx_gag(rng, dur=1.3):
    """A monster-sized 'bleurgh': falling pitch, wet gurgle."""
    t = _t(dur)
    f = 150 * (55 / 150.0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f * (1 + 0.08 * np.sin(2 * np.pi * 9 * t))) / SR
    voice = sum(np.sin(k * phase) / k for k in range(1, 16))
    wet = _bandpass(_noise(rng, dur), 200, 1500) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 13 * t)))
    x = np.tanh((_bandpass(voice, 150, 1400) * 2 + wet * 0.5) * 2)
    return _norm(x * np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)) * 0.8


# ---------------------------------------------------------------------------
# Mix
# ---------------------------------------------------------------------------

def _envelope(x, block=480, release=0.15):
    """Smoothed peak envelope (fast attack, exponential release), per sample."""
    nb = len(x) // block + 1
    peaks = np.array([np.max(np.abs(x[i * block:(i + 1) * block])) if i * block < len(x) else 0.0
                      for i in range(nb)])
    k = math.exp(-block / (release * SR))
    env = np.zeros(nb)
    cur = 0.0
    for i, p in enumerate(peaks):
        cur = max(p, cur * k)
        env[i] = cur
    return np.interp(np.arange(len(x)), np.arange(nb) * block + block / 2, env)


def build_kaiju_soundtrack(events, vo_lines, out_path, seed=1):
    """Mix voice, music and effects for a kaiju episode; writes a 48 kHz stereo WAV."""
    rng = np.random.default_rng(seed)
    fps = float(events["fps"])
    total = events["total_frames"] / fps
    n = int(total * SR) + SR
    mo = {k: v / fps for k, v in events["moments"].items()}
    cfg = events["config"]

    # Voice.
    voice = np.zeros((n, 2))
    for line, x in zip(cfg["voiceover"], vo_lines):
        _place(voice, _norm(x) * 0.9, line["at_s"], 1.0, 0.0)
    v_env = _envelope(voice[:, 0], release=0.25)
    duck = np.clip(v_env / 0.25, 0, 1)                     # 1 while someone is talking

    # Music.
    custom = custom_sound(["music"], 0)
    music = np.tile(custom, n // len(custom) + 1)[:n] if custom is not None else build_score(events, rng)
    music = _norm(np.pad(music, (0, max(0, n - len(music))))[:n])
    mus = np.zeros((n, 2))
    mus[:, 0] = mus[:, 1] = music * 0.34 * (1 - 0.6 * duck)

    # Effects.
    fx = np.zeros((n, 2))

    def put(slot, synth, t, gain=1.0, pan=0.0, pick=0):
        s = custom_sound([slot], pick)
        _place(fx, s if s is not None else synth(), t, gain, pan)

    for e in events["events"]:
        t = e["frame"] / fps
        kind = e["type"]
        if kind == "bong":
            put("bong", lambda: sfx_bong(rng), t, 0.8)
        elif kind == "bubbles":
            a, b = t, mo.get("geyser", t + 2.6)
            k = 0
            while a < b:
                _place(fx, sfx_bloop(rng), a, rng.uniform(0.15, 0.35), rng.uniform(-0.6, 0.6))
                a += rng.exponential(0.22 - 0.15 * min(1.0, (a - t) / max(0.1, b - t)))
                k += 1
            rumble = _bandpass(_noise(rng, b - t + 0.5), 30, 250) * np.clip(_t(b - t + 0.5) / (b - t), 0, 1)
            _place(fx, _norm(rumble) * 0.35, t, 1.0)
        elif kind == "geyser":
            put("geyser", lambda: sfx_geyser(rng), t, 1.0)
        elif kind == "rise":
            put("rise", lambda: sfx_splash(rng, big=True), t, 0.8)
            _place(fx, sfx_whoosh(1.0, rng, dur=1.2) * 3, t, 0.8)
        elif kind == "roar":
            small = e.get("small", False)
            put("roar", lambda: sfx_roar(rng, 1.4 if small else 2.2, 1.1 if small else 1.0), t,
                0.6 if small else 1.0, pick=1 if small else 0)
        elif kind == "stomp":
            put("stomp", lambda: sfx_stomp(rng), t, 0.75, rng.uniform(-0.3, 0.3))
        elif kind == "stomp_big":
            put("stomp_big", lambda: sfx_stomp(rng, big=True), t, 1.0)
            _place(fx, sfx_whoosh(1.0, rng, dur=0.9) * 3, t + 0.05, 0.7)
        elif kind == "fling":
            put("clang", lambda: sfx_clang(rng, e.get("heavy", True)), t, 0.7, rng.uniform(-0.5, 0.5))
            _place(fx, sfx_whoosh(1.0, rng, dur=0.7) * 2, t + 0.05, 0.6, rng.uniform(-0.5, 0.5))
        elif kind == "water_hit":
            put("splash_small", lambda: sfx_splash(rng), t, 0.6, rng.uniform(-0.6, 0.6))
        elif kind == "bite":
            put("bite", lambda: _mix(sfx_crunch(rng, 1.0, 9), sfx_thud(rng), sfx_bong(rng) * 0.35), t, 1.0)
            _place(fx, sfx_shatter("glass", rng) * 0.5, t + 0.02, 0.6)
        elif kind == "chew":
            _place(fx, sfx_crunch(rng, 0.3, 3), t, 0.35, rng.uniform(-0.2, 0.2))
        elif kind == "eye_detach":
            put("groan", lambda: _mix(sfx_groan(rng), sfx_crack("glass", 1.0, rng) * 0.6), t, 0.8)
        elif kind == "eye_roll":
            put("roll", lambda: sfx_roll(rng, max(0.5, e["until"] / fps - t)), t, 0.8)
        elif kind == "slice":
            put("slice", lambda: sfx_slice(rng), t, 0.7, rng.uniform(-0.4, 0.4))
        elif kind == "pineapple_land":
            put("pineapple", lambda: _mix(sfx_thud(rng), sfx_boing(rng)), t, 0.6, rng.uniform(-0.6, 0.6))
        elif kind == "gag":
            put("gag", lambda: sfx_gag(rng), t, 0.9)
        elif kind == "dive":
            _place(fx, sfx_whoosh(1.0, rng, dur=1.1) * 3, t, 0.9)
        elif kind == "splash":
            put("splash", lambda: sfx_splash(rng, big=True), t, 1.0)
    if "pineapples" in mo:                                    # the cartoon whistle as they fall
        _place(fx, sfx_whistle(1.1, rng), mo["pineapples"] - 1.15, 0.8, 0.2)
    fx += room_tone(n, rng)
    fx *= (1 - 0.25 * duck)[:, None]

    bed = _reverb(mus + fx, rng, wet=0.14, length=1.2)
    mix = bed + _reverb(voice, rng, wet=0.05, length=0.5)
    mix = mix[:int(total * SR)]
    # Compressor (so booms don't bury the voice), soft clip, then -1 dBFS.
    env = _envelope(np.max(np.abs(mix), axis=1), release=0.12)
    thr = 0.5 * np.max(env)
    gain = np.minimum(1.0, (thr / np.maximum(env, 1e-9)) ** 0.6)
    mix *= gain[:, None]
    peak = np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(mix / peak * 1.4) / np.tanh(1.4)
    mix *= 10 ** (-1 / 20) / (np.max(np.abs(mix)) + 1e-9)
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_path
