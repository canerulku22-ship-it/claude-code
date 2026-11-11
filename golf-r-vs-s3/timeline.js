// Script for the narration, shared by voiceover.py, film.html and audio.py.
// `text` is the on-screen caption, `say` is what the narrator pronounces,
// `gap` is the pause before the line (seconds). voiceover.py lays the lines
// out back to back and writes the resulting start times to out/vo/timing.js.
// Must stay valid JSON inside the braces.
window.TIMELINE = {
  "tail": 2.9,
  "vo": [
    { "id": "01", "gap": 0.35, "text": "Volkswagen Golf R, or Audi S3?", "say": "Volkswagen Golf R, or Audi S three?" },
    { "id": "02", "gap": 0.3, "text": "Same engine. Same power. So which one should you buy?", "say": "Same engine. Same power. So which one should you buy?" },
    { "id": "03", "gap": 0.5, "text": "Under the skin, they’re twins.", "say": "Under the skin, they're twins." },
    { "id": "04", "gap": 0.2, "text": "Both get a 2.0-litre turbo with 333 horsepower, and four-wheel drive that can push torque to either rear wheel.", "say": "Both get a two litre turbo with three hundred and thirty-three horsepower, and four wheel drive that can push torque to either rear wheel." },
    { "id": "05", "gap": 0.5, "text": "0–62? Golf R: 4.6 seconds. S3: 4.7.", "say": "Nought to sixty-two? Golf R, four point six seconds. S three, four point seven.", "check": "0-62? Golf R, 4.6 seconds. S3, 4.7." },
    { "id": "06", "gap": 0.45, "text": "The Golf is the hooligan. Add the R-Performance pack and you even get a Drift mode.", "say": "The Golf is the hooligan. Add the R Performance pack, and you even get a drift mode." },
    { "id": "07", "gap": 0.45, "text": "The Audi is the smart one: a premium badge, and a choice of Sportback or saloon.", "say": "The Audi is the smart one. A premium badge, and a choice of Sportback or saloon." },
    { "id": "08", "gap": 0.45, "text": "The Golf has the bigger boot, and you can even get it as an estate.", "say": "The Golf has the bigger boot, and you can even get it as an estate." },
    { "id": "09", "gap": 0.45, "text": "And prices? Neck and neck, from around £47k.", "say": "And prices? Neck and neck, from around forty-seven grand.", "check": "And prices? Neck and neck, from around 47 grand." },
    { "id": "10", "gap": 0.5, "text": "Want the wilder drive? Golf R. Want the badge? Audi S3.", "say": "Want the wilder drive? Golf R. Want the badge? Audi S three." },
    { "id": "11", "gap": 0.45, "text": "Which one are you taking? Tell us in the comments.", "say": "Which one are you taking? Tell us in the comments." }
  ]
};
