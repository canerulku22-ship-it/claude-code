"""Write rough text-length timings to web/timing.js so visuals can be previewed before the voice exists."""
import json, re, os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sc = json.load(open(R + 'script.json')); STY = {"*": "hl", "!": "bad", "+": "good", "#": "swear"}
def ss(tok):
    for ch, st in STY.items():
        if len(tok) >= 2 and tok.startswith(ch) and tok.endswith(ch): return tok[1:-1], st
    return tok, ""
t = 0.06; lines = []; segs = {}
for seg in sc['segments']:
    s0 = t
    for li, l in enumerate(seg['lines']):
        ws = []; tt = t
        for wd in l['tts'].split():
            d = 0.05 * len(wd) + 0.1 + (0.15 if re.search(r'[.,?!:]$', wd) else 0); ws.append({"w": wd, "s": round(tt, 3), "e": round(tt + d - 0.03, 3)}); tt += d
        caps = []; wi = 0
        for tok in l['cap'].split():
            m = re.fullmatch(r"\{(.+):(\d+)\}(.*)", tok)
            if m: text, st = ss(m.group(1)); text += m.group(3); n = int(m.group(2))
            else: text, st = ss(tok); n = 1
            caps.append({"text": text, "style": st, "w0": wi, "w1": wi + n - 1, "s": ws[wi]['s'], "e": ws[wi + n - 1]['e']}); wi += n
        lines.append({"seg": seg['id'], "idx": li, "start": round(t, 3), "end": round(tt, 3), "tts": l['tts'], "words": ws, "caps": caps}); t = tt + l.get('pause', 0.15)
    segs[seg['id']] = {"name": seg['name'], "start": round(s0, 3), "end": round(t, 3)}
open(R + 'web/timing.js', 'w').write("window.TIMING = " + json.dumps({"duration": round(t, 3), "segments": segs, "lines": lines}) + ";\n")
print(' '.join(str(round(v['start'] + f * (v['end'] - v['start']), 2)) for v in segs.values() for f in (0.3, 0.85)))
