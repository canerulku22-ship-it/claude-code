// Script for the narration, shared by voiceover.py, film.html and audio.py.
// `text` is the on-screen caption, `say` is what the narrator pronounces,
// `gap` is the pause before the line (seconds), `check` (optional) is what
// Whisper should hear. voiceover.py lays the lines out back to back and
// writes the start times to out/vo/timing.js. `voice` tunes Chatterbox:
// higher exaggeration and lower cfg give a chattier, more animated read.
// Must stay valid JSON inside the braces.
window.TIMELINE = {
  "tail": 2.9,
  "voice": { "exaggeration": 0.8, "cfg": 0.35, "temperature": 0.85 },
  "vo": [
    { "id": "01", "gap": 0.3, "text": "Right, Golf R or Audi S3? Honestly, this one’s a proper head-scratcher.", "say": "Right, Golf R or Audi S three? Honestly, this one's a proper head-scratcher." },
    { "id": "02", "gap": 0.25, "text": "Same engine, same power, so which one actually deserves your money? Let’s find out.", "say": "Same engine, same power, so which one actually deserves your money? Let's find out." },
    { "id": "03", "gap": 0.45, "text": "Okay, so here’s the thing: under the skin, these two are basically twins.", "say": "Okay, so here's the thing. Under the skin, these two are basically twins." },
    { "id": "04", "gap": 0.2, "text": "Both get a 2.0-litre turbo with 333 horsepower, and clever four-wheel drive that can shove torque to either rear wheel.", "say": "Both get a two litre turbo with three hundred and thirty-three horsepower, and clever four wheel drive that can shove torque to either rear wheel." },
    { "id": "05", "gap": 0.45, "text": "So, 0–62? The Golf does it in 4.6 seconds. And the S3? 4.7. Literally a tenth apart!", "say": "So, nought to sixty-two? The Golf does it in four point six seconds. And the S three? Four point seven. Literally a tenth apart!", "check": "So, 0-62? The Golf does it in 4.6 seconds. And the S3? 4.7. Literally a tenth apart!" },
    { "id": "06", "gap": 0.4, "text": "But this is where it gets fun. The Golf’s the hooligan: spec the R-Performance pack and you get an actual Drift mode. Yes, really!", "say": "But this is where it gets fun. The Golf's the hooligan. Spec the R Performance pack, and you get an actual drift mode. Yes, really!" },
    { "id": "07", "gap": 1.2, "text": "The Audi? It’s the grown-up. A classier badge, and you can have it as a Sportback or a saloon.", "say": "The Audi? It's the grown-up. A classier badge, and you can have it as a Sportback, or a saloon." },
    { "id": "08", "gap": 0.4, "text": "Need space? The Golf’s got the bigger boot, and you can even get it as an estate. Dog owners, you’re welcome.", "say": "Need space? The Golf's got the bigger boot, and you can even get it as an estate. Dog owners, you're welcome." },
    { "id": "09", "gap": 0.4, "text": "And price? Honestly, it’s neck and neck. Both start at around £47k.", "say": "And price? Honestly, it's neck and neck. Both start at around forty-seven grand.", "check": "And price? Honestly, it's neck and neck. Both start at around 47 grand." },
    { "id": "10", "gap": 0.45, "text": "So here’s my take. Want the wilder drive? Get the Golf R. Want the badge? Get the S3.", "say": "So here's my take. Want the wilder drive? Get the Golf R. Want the badge? Get the S three." },
    { "id": "11", "gap": 0.4, "text": "But which one would you take? Let me know in the comments!", "say": "But which one would you take? Let me know in the comments!" }
  ]
};
