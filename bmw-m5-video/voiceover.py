"""Narration with Chatterbox (Resemble AI, MIT licence).

The voice is cloned from a synthetic reference, not a real person: about
nine seconds of the Kokoro British female voice that voiceover.mjs writes
to out/vo_ref/. Chatterbox keeps that timbre and accent and adds a more
expressive delivery. Each line is generated a few times. Whisper checks
every take, and the clearest take that fits its slot in timeline.js is kept.

Writes out/vo/<id>.wav, out/vo/durations.json and out/vo/timing.js
(speech onset/offset, used by film.html for captions).

    node voiceover.mjs            # reference voice (and a lightweight fallback narration)
    python voiceover.py           # needs: pip install chatterbox-tts "setuptools<81"
"""
import difflib
import json
import os
import re

import librosa
import numpy as np
import soundfile as sf
import torch
from chatterbox.tts import ChatterboxTTS
from transformers import pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'vo')
REF = os.path.join(HERE, 'out', 'vo_ref')
TAKES = int(os.environ.get('TAKES', 3))
ONLY = set(filter(None, os.environ.get('ONLY', '').split(',')))   # e.g. ONLY=08 regenerates just that line
EXAGGERATION, CFG, TEMPERATURE = 0.65, 0.45, 0.8   # lively ad read
LEAD = 0.25                                        # silence before each line, seconds

src = open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read()
TL = json.loads(src[src.index('{'):src.rindex('}') + 1])
os.makedirs(OUT, exist_ok=True)
torch.set_num_threads(os.cpu_count() or 4)

# synthetic reference voice: two Kokoro lines, trimmed and joined
parts = []
for i in ('02', '07'):
    y, _ = librosa.load(os.path.join(REF, f'{i}.wav'), sr=24000)
    parts += [librosa.effects.trim(y, top_db=35)[0], np.zeros(int(0.35 * 24000))]
ref_path = os.path.join(OUT, 'reference.wav')
sf.write(ref_path, np.concatenate(parts), 24000)

tts = ChatterboxTTS.from_pretrained(device='cpu')
asr = pipeline('automatic-speech-recognition', model='openai/whisper-base.en', device='cpu')


def norm(s):
    s = s.lower().replace('–', ' ').replace('-', ' ').replace('’', "'")
    s = re.sub(r'\bhp\b', 'horsepower', s)
    return ' '.join(re.sub(r"[^a-z0-9.' ]", ' ', s).split())


def expressiveness(y, sr):
    f0, _, _ = librosa.pyin(librosa.resample(y, orig_sr=sr, target_sr=16000), fmin=70, fmax=450, sr=16000)
    f = f0[~np.isnan(f0)]
    return float(np.std(12 * np.log2(f / np.median(f)))) if len(f) > 10 else 0.0


lines = TL['vo']
durations = {}
if ONLY and os.path.exists(os.path.join(OUT, 'durations.json')):
    durations = json.load(open(os.path.join(OUT, 'durations.json')))
for n, line in enumerate(lines):
    if ONLY and line['id'] not in ONLY:
        continue
    end = lines[n + 1]['at'] if n + 1 < len(lines) else TL['duration'] - 0.6
    slot = end - line['at'] - LEAD - 0.2        # speech must finish before the next line
    text = line['say'].replace('B M W', 'BMW')
    best = None
    for k in range(TAKES):
        torch.manual_seed(1000 * n + k + (100 if ONLY else 0))
        y = tts.generate(text, audio_prompt_path=ref_path, exaggeration=EXAGGERATION,
                         cfg_weight=CFG, temperature=TEMPERATURE).squeeze().numpy()
        y, _ = librosa.effects.trim(y, top_db=38)
        heard = asr(librosa.resample(y, orig_sr=tts.sr, target_sr=16000))['text']
        match = difflib.SequenceMatcher(None, norm(heard), norm(line['text'])).ratio()
        dur = len(y) / tts.sr
        score = (match >= 0.85, dur <= slot, match, expressiveness(y, tts.sr))
        print(f"{line['id']} take {k}: {dur:.2f}s (slot {slot:.2f}) match {match:.2f} | {heard.strip()}", flush=True)
        if best is None or score > best[0]:
            best = (score, y, k)
    score, y, k = best
    if not score[1]:   # still too long: tighten slightly rather than overlap the next line
        y = librosa.effects.time_stretch(y, rate=min(1.12, len(y) / tts.sr / slot))
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 0.08
    y = np.concatenate([np.zeros(int(LEAD * tts.sr)), y, np.zeros(int(0.3 * tts.sr))]).astype(np.float32)
    sf.write(os.path.join(OUT, f"{line['id']}.wav"), y, tts.sr)
    speech = len(y) / tts.sr - 0.3
    durations[line['id']] = {'dur': len(y) / tts.sr, 'on': LEAD, 'off': round(speech, 3), 'take': k}
    json.dump(durations, open(os.path.join(OUT, 'durations.json'), 'w'), indent=2)
    print(f"  -> {line['id']} kept take {k}, speech {LEAD:.2f}-{speech:.2f}s", flush=True)

with open(os.path.join(OUT, 'timing.js'), 'w') as f:
    f.write(f'window.VO_TIMING = {json.dumps(durations)};\n')
