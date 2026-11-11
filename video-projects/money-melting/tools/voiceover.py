"""Generate the voiceover (Kokoro TTS) and per-word timings (faster-whisper).

Usage: python tools/voiceover.py <models_dir>
  models_dir must hold kokoro-v1.0.onnx and voices-v1.0.bin
   or: python tools/voiceover.py --own-voice my_read.wav
  (your own recording of all the `tts` lines in order; it is aligned to the script instead of synthesized)
Writes: audio/vo.wav, web/timing.js (window.TIMING), audio/timing.json
"""
import difflib
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWN = sys.argv[2] if sys.argv[1] == "--own-voice" else None
MODELS = None if OWN else sys.argv[1]
SR = 24000
LEAD_IN = 0.08

script = json.load(open(os.path.join(ROOT, "script.json")))
tts = None if OWN else Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
asr = WhisperModel("small.en", device="cpu", compute_type="int8")


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def trim(x, thr=0.004, margin=0.03):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(margin * SR))
    b = min(len(x), idx[-1] + int(margin * SR))
    return x[a:b]


def resample_16k(x):
    n = int(len(x) * 16000 / SR)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def align(tts_words, asr_words, dur):
    """Give every scripted word a (start, end) using whisper words where they match."""
    a = [norm(w) for w in tts_words]
    b = [norm(w["w"]) for w in asr_words]
    times = [None] * len(a)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            w = asr_words[blk.b + k]
            times[blk.a + k] = [w["s"], w["e"]]
    # interpolate gaps proportionally to word length
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
        tot = sum(lens)
        acc = t0
        for k in range(i, j):
            d = (t1 - t0) * lens[k - i] / tot
            times[k] = [acc, acc + d]
            acc += d
        i = j
    for k in range(1, len(times)):  # keep monotonic
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




def own_voice(path):
    """Align a full human read to the script: one whisper pass, global word alignment."""
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(1)
    n = int(len(audio) * SR / sr)
    audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)
    segs, _ = asr.transcribe(resample_16k(audio), word_timestamps=True, beam_size=5, language="en")
    aw = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s_ in segs for w in s_.words]
    flat = [(si, li, wd) for si, seg in enumerate(script["segments"]) for li, line in enumerate(seg["lines"]) for wd in line["tts"].split()]
    times = align([f[2] for f in flat], aw, len(audio) / SR)
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
    for i, seg in enumerate(script["segments"]):
        mine = [l for l in lines_out if l["seg"] == seg["id"]]
        nxt = [l for l in lines_out if l["seg"] == script["segments"][i + 1]["id"]] if i + 1 < len(script["segments"]) else None
        start = max(0.0, mine[0]["start"] - 0.1)
        end = nxt[0]["start"] - 0.1 if nxt else max(len(audio) / SR, mine[-1]["end"] + seg["lines"][-1].get("pause", 1.5))
        segs_out[seg["id"]] = {"name": seg["name"], "start": round(start, 3), "end": round(end, 3)}
    dur = max(len(audio) / SR, segs_out[script["segments"][-1]["id"]]["end"])
    vo = np.zeros(int(dur * SR), np.float32)
    vo[:len(audio)] = audio
    return vo, {"duration": round(dur, 3), "segments": segs_out, "lines": lines_out}


if OWN:
    vo, timing = own_voice(OWN)
    vo = vo / max(1e-6, np.abs(vo).max()) * 0.89
    sf.write(os.path.join(ROOT, "audio", "vo.wav"), vo, SR, subtype="PCM_16")
    json.dump(timing, open(os.path.join(ROOT, "audio", "timing.json"), "w"), indent=1)
    with open(os.path.join(ROOT, "web", "timing.js"), "w") as f:
        f.write("window.TIMING = " + json.dumps(timing) + ";\n")
    print("aligned own voice, duration", timing["duration"])
    sys.exit(0)

chunks = [np.zeros(int(LEAD_IN * SR), np.float32)]
t = LEAD_IN
lines_out, segs_out = [], {}
for seg in script["segments"]:
    seg_start = t
    for li, line in enumerate(seg["lines"]):
        if "phon" in line:
            audio, sr = tts.create(line["phon"], voice=script["voice"], speed=script["speed"], is_phonemes=True)
        else:
            audio, sr = tts.create(line["tts"], voice=script["voice"], speed=script["speed"], lang="en-us")
        assert sr == SR
        audio = trim(audio.astype(np.float32))
        dur = len(audio) / SR
        segs, _ = asr.transcribe(resample_16k(audio), word_timestamps=True, beam_size=5, language="en")
        aw = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words]
        words = line["tts"].split()
        times = align(words, aw, dur)
        caps = parse_caption(line["cap"], len(words))
        for c in caps:
            c["s"] = round(t + times[c["w0"]][0], 3)
            c["e"] = round(t + times[c["w1"]][1], 3)
        lines_out.append({
            "seg": seg["id"], "idx": li, "start": round(t, 3), "end": round(t + dur, 3),
            "tts": line["tts"], "words": [{"w": w, "s": round(t + a, 3), "e": round(t + b, 3)} for w, (a, b) in zip(words, times)],
            "caps": caps,
        })
        print(f"{seg['id']}.{li} {t:6.2f}-{t + dur:6.2f}  {line['tts']}   | asr: {' '.join(x['w'] for x in aw)}")
        chunks.append(audio)
        t += dur
        gap = line.get("pause", 0.15)
        chunks.append(np.zeros(int(gap * SR), np.float32))
        t += gap
    segs_out[seg["id"]] = {"name": seg["name"], "start": round(seg_start, 3), "end": round(t, 3)}

vo = np.concatenate(chunks)
vo = vo / max(1e-6, np.abs(vo).max()) * 0.89
sf.write(os.path.join(ROOT, "audio", "vo.wav"), vo, SR, subtype="PCM_16")
timing = {"duration": round(len(vo) / SR, 3), "segments": segs_out, "lines": lines_out}
json.dump(timing, open(os.path.join(ROOT, "audio", "timing.json"), "w"), indent=1)
with open(os.path.join(ROOT, "web", "timing.js"), "w") as f:
    f.write("window.TIMING = " + json.dumps(timing) + ";\n")
print("total duration", timing["duration"])
