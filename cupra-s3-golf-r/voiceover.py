"""Narration with Chatterbox (Resemble AI, MIT licence), laid out automatically.

The voice is cloned from voice-reference.wav: nine seconds of the synthetic
Kokoro-82M British female voice `bf_emma`, not a real person. Each line is
generated a few times. Whisper checks every take, and the clearest, most
expressive take is kept. Lines are then laid out back to back using each
line's `gap`, so the film and the soundtrack follow the real speech timing.

Writes out/vo/<id>.wav, out/vo/durations.json and out/vo/timing.js.

    pip install chatterbox-tts==0.1.7 "setuptools<81"
    HF_HUB_DISABLE_XET=1 python voiceover.py        # ONLY=05,09 re-records selected lines; ONLY=layout only re-times
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
TAKES = int(os.environ.get('TAKES', 3))
ONLY = set(filter(None, os.environ.get('ONLY', '').split(',')))
LEAD = 0.25                                        # silence at the start of each file

src = open(os.path.join(HERE, 'timeline.js'), encoding='utf-8').read()
TL = json.loads(src[src.index('{'):src.rindex('}') + 1])
V = TL.get('voice', {})
EXAGGERATION, CFG, TEMPERATURE = V.get('exaggeration', 0.65), V.get('cfg', 0.45), V.get('temperature', 0.8)
os.makedirs(OUT, exist_ok=True)
torch.set_num_threads(os.cpu_count() or 4)
ref = os.path.join(HERE, 'voice-reference.wav')
tts = asr = None   # loaded only when a line needs recording (ONLY=layout just re-lays out the timing)


def norm(s):
    s = s.lower().replace('–', ' ').replace('-', ' ').replace('’', "'")
    return ' '.join(re.sub(r"[^a-z0-9.' ]", ' ', s).split())


def expressiveness(y, sr):
    f0, _, _ = librosa.pyin(librosa.resample(y, orig_sr=sr, target_sr=16000), fmin=70, fmax=450, sr=16000)
    f = f0[~np.isnan(f0)]
    return float(np.std(12 * np.log2(f / np.median(f)))) if len(f) > 10 else 0.0


lines = TL['vo']
info = {}
path = os.path.join(OUT, 'durations.json')
if ONLY and os.path.exists(path):
    info = json.load(open(path))['lines']
for n, line in enumerate(lines):
    if ONLY and line['id'] not in ONLY:
        continue
    if tts is None:
        tts = ChatterboxTTS.from_pretrained(device='cpu')
        asr = pipeline('automatic-speech-recognition', model='openai/whisper-base.en', device='cpu')
    best = None
    for k in range(TAKES):
        torch.manual_seed(1000 * n + k + (100 if ONLY else 0))
        y = tts.generate(line['say'], audio_prompt_path=ref, exaggeration=EXAGGERATION,
                         cfg_weight=CFG, temperature=TEMPERATURE).squeeze().numpy()
        y, _ = librosa.effects.trim(y, top_db=38)
        heard = asr(librosa.resample(y, orig_sr=tts.sr, target_sr=16000))['text']
        match = difflib.SequenceMatcher(None, norm(heard), norm(line.get('check', line['text']))).ratio()
        score = (match >= 0.88, round(match, 2), expressiveness(y, tts.sr))
        print(f"{line['id']} take {k}: {len(y) / tts.sr:.2f}s match {match:.2f} | {heard.strip()}", flush=True)
        if best is None or score > best[0]:
            best = (score, y, k)
    _, y, k = best
    y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 0.08
    y = np.concatenate([np.zeros(int(LEAD * tts.sr)), y, np.zeros(int(0.3 * tts.sr))]).astype(np.float32)
    sf.write(os.path.join(OUT, f"{line['id']}.wav"), y, tts.sr)
    info[line['id']] = {'dur': len(y) / tts.sr, 'on': LEAD, 'off': round(len(y) / tts.sr - 0.3, 3), 'take': k}
    print(f"  -> {line['id']} kept take {k}, speech {LEAD:.2f}-{info[line['id']]['off']:.2f}s", flush=True)
    json.dump({'lines': info}, open(path, 'w'), indent=2)

# lay the lines out back to back: each speech starts `gap` after the previous one ends
t, timing = 0.0, {}
for line in lines:
    d = info[line['id']]
    start = t + line['gap']
    at = round(start - d['on'], 3)
    timing[line['id']] = {**d, 'at': at}
    t = at + d['off']
duration = round(t + TL['tail'], 2)
json.dump({'lines': info, 'timing': timing, 'duration': duration}, open(path, 'w'), indent=2)
with open(os.path.join(OUT, 'timing.js'), 'w') as f:
    f.write(f'window.VO_TIMING = {json.dumps(timing)};\nwindow.VO_DURATION = {duration};\n')
print(f'laid out {len(lines)} lines, film length {duration}s')
