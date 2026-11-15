"""Regenerate specific voiceover lines (e.g. a take with a stray word) and splice them into vo.wav,
shifting every later timing. Usage: python tools/redo_lines.py s10.1 [s07.0 ...] [--takes 6]"""
import json
import os
import sys

import numpy as np
import soundfile as sf

sys.argv, ids = [sys.argv[0]] + [a for a in sys.argv[1:] if a.startswith("--") or a.isdigit()], [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("vo", os.path.join(ROOT, "tools", "voiceover.py"))
# reuse helpers without running the full generation: exec only the helper section
src = open(os.path.join(ROOT, "tools", "voiceover.py")).read().split("if args.own_voice:")[0]
ns = {"__file__": os.path.join(ROOT, "tools", "voiceover.py")}
exec(compile(src, "voiceover_helpers", "exec"), ns)
SR, align, transcribe, trim, norm, parse_caption, write_out, args = ns["SR"], ns["align"], ns["transcribe"], ns["trim"], ns["norm"], ns["parse_caption"], ns["write_out"], ns["args"]
script = ns["script"]

import torch  # noqa: E402
from chatterbox.tts import ChatterboxTTS  # noqa: E402

torch.set_num_threads(os.cpu_count() or 4)
tts = ChatterboxTTS.from_pretrained(device="cpu")
tts.prepare_conditionals(os.path.join(ROOT, "audio", "voice_prompt.wav"), exaggeration=args.exaggeration)

timing = json.load(open(os.path.join(ROOT, "audio", "timing.json")))
vo, sr = sf.read(os.path.join(ROOT, "audio", "vo.wav"), dtype="float32")
assert sr == SR
lines = timing["lines"]
# cut existing audio into per-line clips + gaps
pieces = []
for i, l in enumerate(lines):
    a, b = int(l["start"] * SR), int(l["end"] * SR)
    nxt = int(lines[i + 1]["start"] * SR) if i + 1 < len(lines) else len(vo)
    pieces.append({"line": l, "audio": vo[a:b], "gap": vo[b:nxt]})
lead = vo[:int(lines[0]["start"] * SR)]
cfg = {f"{s['id']}.{i}": ln for s in script["segments"] for i, ln in enumerate(s["lines"])}

for lid in ids:
    ln = cfg[lid]
    words = ln["tts"].split()
    want = [norm(w) for w in words]
    best = None
    for take in range(max(args.takes, 6)):
        torch.manual_seed(777 + take)
        x = trim(tts.generate(ln.get("say", ln["tts"]), exaggeration=args.exaggeration, cfg_weight=args.cfg, temperature=0.7).squeeze(0).numpy().astype(np.float32))
        aw = transcribe(x)
        got = [norm(w["w"]) for w in aw]
        exact = got == want
        print(lid, take, "exact" if exact else "", " ".join(w["w"] for w in aw), flush=True)
        if exact and (best is None or len(x) < len(best[0])):
            best = (x, aw)
        if exact and take >= 2:
            break
    if best is None:
        print("no exact take for", lid, "- keeping original"); continue
    x, aw = best
    x = x * (0.1 / (np.sqrt(np.mean(x ** 2)) + 1e-9)) * (np.abs(vo).max() / 0.89 if False else 1)
    piece = next(p for p in pieces if f"{p['line']['seg']}.{p['line']['idx']}" == lid)
    # match level of the surrounding narration
    ref_rms = np.sqrt(np.mean(piece["audio"] ** 2)) + 1e-9
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * ref_rms
    piece["audio"], piece["aw"] = x, aw

# rebuild audio + timings
t = len(lead) / SR
chunks = [lead]
new_lines = []
seg_bounds = {}
for p in pieces:
    l = dict(p["line"])
    dur = len(p["audio"]) / SR
    shift = t - l["start"]
    if "aw" in p:
        words = l["tts"].split()
        times = align(words, p["aw"], dur)
        caps = parse_caption(cfg[f"{l['seg']}.{l['idx']}"]["cap"], len(words))
        for c in caps:
            c["s"], c["e"] = round(t + times[c["w0"]][0], 3), round(t + times[c["w1"]][1], 3)
        l["words"] = [{"w": w, "s": round(t + a, 3), "e": round(t + b, 3)} for w, (a, b) in zip(words, times)]
        l["caps"] = caps
    else:
        l["words"] = [dict(w, s=round(w["s"] + shift, 3), e=round(w["e"] + shift, 3)) for w in l["words"]]
        l["caps"] = [dict(c, s=round(c["s"] + shift, 3), e=round(c["e"] + shift, 3)) for c in l["caps"]]
    l["start"], l["end"] = round(t, 3), round(t + dur, 3)
    new_lines.append(l)
    seg_bounds.setdefault(l["seg"], [t, None])
    chunks += [p["audio"], p["gap"]]
    t += dur + len(p["gap"]) / SR
    seg_bounds[l["seg"]][1] = t
segs = {k: {"name": timing["segments"][k]["name"], "start": round(v[0] if k != "s01" else timing["segments"]["s01"]["start"], 3), "end": round(v[1], 3)} for k, v in seg_bounds.items()}
new_vo = np.concatenate(chunks)
write_out(new_vo / 0.89 * np.abs(vo).max(), {"duration": round(len(new_vo) / SR, 3), "segments": segs, "lines": new_lines})
