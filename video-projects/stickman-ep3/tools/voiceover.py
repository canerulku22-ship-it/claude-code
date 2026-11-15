"""Expressive voiceover with Chatterbox TTS (best-of-N takes per line) + Whisper word timings.

Usage: python tools/voiceover.py [--takes 2] [--own-voice my_read.wav]
Needs: chatterbox-tts, faster-whisper, soundfile. Voice timbre comes from audio/voice_prompt.wav
(a synthetic Kokoro 'am_onyx' clip, so no real person's voice is cloned).
Writes audio/vo.wav, audio/timing.json, web/timing.js
"""
import argparse
import difflib
import json
import os
import re

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 24000
LEAD_IN = 0.06
ap = argparse.ArgumentParser()
ap.add_argument("--takes", type=int, default=2)
ap.add_argument("--own-voice")
ap.add_argument("--exaggeration", type=float, default=0.65)
ap.add_argument("--cfg", type=float, default=0.4)
args = ap.parse_args()

script = json.load(open(os.path.join(ROOT, "script.json")))
asr = WhisperModel("small.en", device="cpu", compute_type="int8")


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def to16k(x, sr=SR):
    n = int(len(x) * 16000 / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def transcribe(x, sr=SR):
    segs, _ = asr.transcribe(to16k(x, sr), word_timestamps=True, beam_size=5, language="en")
    return [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words]


def trim(x, thr=0.01, margin=0.04):
    idx = np.where(np.abs(x) > thr * np.abs(x).max())[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(margin * SR)):min(len(x), idx[-1] + int(margin * SR))]


def align(tts_words, asr_words, dur):
    a = [norm(w) for w in tts_words]
    b = [norm(w["w"]) for w in asr_words]
    times = [None] * len(a)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            w = asr_words[blk.b + k]
            times[blk.a + k] = [w["s"], w["e"]]
    i = 0
    while i < len(a):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(a) and times[j] is None:
            j += 1
        t0 = times[i - 1][1] if i > 0 else 0.0
        t1 = times[j][0] if j < len(a) else dur
        if t1 <= t0:
            t1 = t0 + 0.05 * (j - i)
        lens = [max(1, len(x)) for x in a[i:j]]
        acc = t0
        for k in range(i, j):
            d = (t1 - t0) * lens[k - i] / sum(lens)
            times[k] = [acc, acc + d]
            acc += d
        i = j
    for k in range(1, len(times)):
        if times[k][0] < times[k - 1][0]:
            times[k][0] = times[k - 1][1]
        times[k][1] = max(times[k][1], times[k][0] + 0.04)
    return times


STYLE = {"*": "hl", "!": "bad", "+": "good"}


def strip_style(tok):
    for ch, st in STYLE.items():
        if len(tok) >= 2 and tok.startswith(ch) and tok.endswith(ch):
            return tok[1:-1], st
    return tok, ""


def parse_caption(cap, n_words):
    out, wi = [], 0
    for tok in cap.split():
        m = re.fullmatch(r"\{(.+):(\d+)\}(.*)", tok)
        if m:
            text, st = strip_style(m.group(1))
            text += m.group(3)
            n = int(m.group(2))
        else:
            text, st = strip_style(tok)
            n = 1
        out.append({"text": text, "style": st, "w0": wi, "w1": wi + n - 1})
        wi += n
    assert wi == n_words, f"caption consumes {wi} words, tts has {n_words}: {cap}"
    return out


def score(words, aw):
    ratio = difflib.SequenceMatcher(None, [norm(w) for w in words], [norm(w["w"]) for w in aw]).ratio()
    return ratio


def write_out(vo, timing):
    vo = vo / max(1e-6, np.abs(vo).max()) * 0.89
    sf.write(os.path.join(ROOT, "audio", "vo.wav"), vo, SR, subtype="PCM_16")
    json.dump(timing, open(os.path.join(ROOT, "audio", "timing.json"), "w"), indent=1)
    with open(os.path.join(ROOT, "web", "timing.js"), "w") as f:
        f.write("window.TIMING = " + json.dumps(timing) + ";\n")
    print("total duration", timing["duration"])


def own_voice(path):
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(1)
    audio = np.interp(np.linspace(0, len(audio) - 1, int(len(audio) * SR / sr)), np.arange(len(audio)), audio).astype(np.float32)
    aw = transcribe(audio)
    flat = [wd for seg in script["segments"] for line in seg["lines"] for wd in line["tts"].split()]
    times = align(flat, aw, len(audio) / SR)
    lines_out, segs_out, k = [], {}, 0
    for seg in script["segments"]:
        for li, line in enumerate(seg["lines"]):
            words = line["tts"].split()
            tt = times[k:k + len(words)]
            k += len(words)
            caps = parse_caption(line["cap"], len(words))
            for c in caps:
                c["s"], c["e"] = round(tt[c["w0"]][0], 3), round(tt[c["w1"]][1], 3)
            lines_out.append({"seg": seg["id"], "idx": li, "start": round(tt[0][0], 3), "end": round(tt[-1][1], 3), "tts": line["tts"],
                              "words": [{"w": w, "s": round(a, 3), "e": round(b, 3)} for w, (a, b) in zip(words, tt)], "caps": caps})
    ids = [s["id"] for s in script["segments"]]
    for i, seg in enumerate(script["segments"]):
        mine = [l for l in lines_out if l["seg"] == seg["id"]]
        nxt = [l for l in lines_out if i + 1 < len(ids) and l["seg"] == ids[i + 1]]
        end = nxt[0]["start"] - 0.1 if nxt else max(len(audio) / SR, mine[-1]["end"] + seg["lines"][-1].get("pause", 1.5))
        segs_out[seg["id"]] = {"name": seg["name"], "start": round(max(0, mine[0]["start"] - 0.1), 3), "end": round(end, 3)}
    dur = max(len(audio) / SR, segs_out[ids[-1]]["end"])
    vo = np.zeros(int(dur * SR), np.float32)
    vo[:len(audio)] = audio
    write_out(vo, {"duration": round(dur, 3), "segments": segs_out, "lines": lines_out})


if args.own_voice:
    own_voice(args.own_voice)
    raise SystemExit

import torch  # noqa: E402
from chatterbox.tts import ChatterboxTTS  # noqa: E402

torch.set_num_threads(os.cpu_count() or 4)
tts = ChatterboxTTS.from_pretrained(device="cpu")
prompt = os.path.join(ROOT, "audio", "voice_prompt.wav")
tts.prepare_conditionals(prompt, exaggeration=args.exaggeration)

chunks = [np.zeros(int(LEAD_IN * SR), np.float32)]
t = LEAD_IN
lines_out, segs_out = [], {}
for seg in script["segments"]:
    seg_start = t
    for li, line in enumerate(seg["lines"]):
        words = line["tts"].split()
        best = None
        for take in range(args.takes):
            torch.manual_seed(1000 * len(lines_out) + take)
            wav = tts.generate(line.get("say", line["tts"]), exaggeration=args.exaggeration, cfg_weight=args.cfg, temperature=0.75)
            x = trim(wav.squeeze(0).numpy().astype(np.float32))
            aw = transcribe(x)
            sc = score(words, aw) - 0.02 * max(0, len(x) / SR / max(1, len(words)) - 0.42) * 10  # prefer accurate, not draggy
            if best is None or sc > best[0]:
                best = (sc, x, aw)
        sc, x, aw = best
        rms = np.sqrt(np.mean(x ** 2)) + 1e-9
        x = x * (0.1 / rms)  # even loudness line to line
        dur = len(x) / SR
        times = align(words, aw, dur)
        caps = parse_caption(line["cap"], len(words))
        for c in caps:
            c["s"] = round(t + times[c["w0"]][0], 3)
            c["e"] = round(t + times[c["w1"]][1], 3)
        lines_out.append({"seg": seg["id"], "idx": li, "start": round(t, 3), "end": round(t + dur, 3), "tts": line["tts"],
                          "words": [{"w": w, "s": round(t + a, 3), "e": round(t + b, 3)} for w, (a, b) in zip(words, times)], "caps": caps})
        print(f"{seg['id']}.{li} {t:6.2f}-{t + dur:6.2f} score={sc:.2f}  {line['tts']}  | {' '.join(w['w'] for w in aw)}", flush=True)
        chunks.append(x)
        t += dur
        gap = line.get("pause", 0.15)
        chunks.append(np.zeros(int(gap * SR), np.float32))
        t += gap
    segs_out[seg["id"]] = {"name": seg["name"], "start": round(seg_start, 3), "end": round(t, 3)}

vo = np.concatenate(chunks)
write_out(vo, {"duration": round(len(vo) / SR, 3), "segments": segs_out, "lines": lines_out})
