"""Re-time vo.wav to the pauses in script.json without regenerating speech (cuts existing line clips, re-joins)."""
import json, os, numpy as np, soundfile as sf
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sc = json.load(open(R + 'script.json')); tm = json.load(open(R + 'audio/timing.json'))
vo, sr = sf.read(R + 'audio/vo.wav', dtype='float32')
pause = {f"{seg['id']}.{i}": l.get('pause', 0.15) for seg in sc['segments'] for i, l in enumerate(seg['lines'])}
t = tm['lines'][0]['start']; out = [vo[:int(t * sr)]]; lines = []; segs = {}
for l in tm['lines']:
    a, b = int(l['start'] * sr), int(l['end'] * sr); clip = vo[a:b]; sh = t - l['start']
    L = dict(l); L['start'] = round(t, 3); L['end'] = round(t + len(clip) / sr, 3)
    L['words'] = [dict(w, s=round(w['s'] + sh, 3), e=round(w['e'] + sh, 3)) for w in l['words']]
    L['caps'] = [dict(c, s=round(c['s'] + sh, 3), e=round(c['e'] + sh, 3)) for c in l['caps']]
    lines.append(L); segs.setdefault(l['seg'], [t, None])
    gap = pause[f"{l['seg']}.{l['idx']}"]; out += [clip, np.zeros(int(gap * sr), np.float32)]
    t += len(clip) / sr + gap; segs[l['seg']][1] = t
new = np.concatenate(out); sf.write(R + 'audio/vo.wav', new, sr, subtype='PCM_16')
timing = {"duration": round(len(new) / sr, 3), "segments": {k: {"name": tm['segments'][k]['name'], "start": round(v[0], 3), "end": round(v[1], 3)} for k, v in segs.items()}, "lines": lines}
json.dump(timing, open(R + 'audio/timing.json', 'w'), indent=1); open(R + 'web/timing.js', 'w').write("window.TIMING = " + json.dumps(timing) + ";\n")
print('duration', timing['duration'])
