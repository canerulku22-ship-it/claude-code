// Script for the narration, shared by voiceover.py, film.html and audio.py.
// `text` is the on-screen caption, `say` is what the narrator pronounces,
// `gap` is the pause before the line (seconds), `check` (optional) is what
// Whisper should hear. voiceover.py lays the lines out back to back and
// writes the start times to out/vo/timing.js. Must stay valid JSON inside
// the braces.
window.TIMELINE = {
  "tail": 2.6,
  "voice": { "exaggeration": 0.8, "cfg": 0.35, "temperature": 0.85 },
  "vo": [
    { "id": "01", "gap": 1.3, "text": "Three hot hatches, one question. Cupra 290, Audi S3, or Golf R?", "say": "Three hot hatches. One question. Cupra two ninety, Audi S three, or Golf R?", "check": "Three hot hatches. One question. Cupra 290, Audi S3, or Golf R?" },
    { "id": "02", "gap": 0.35, "text": "All three run a 2.0-litre turbo, but they couldn’t be more different. Let’s go!", "say": "All three run a two litre turbo, but they couldn't be more different. Let's go!", "check": "All three run a 2-litre turbo, but they couldn't be more different. Let's go!" },
    { "id": "03", "gap": 0.45, "text": "The Cupra’s the old-school one: 290 horsepower, all through the front wheels.", "say": "The Cupra's the old school one. Two hundred and ninety horsepower, all through the front wheels.", "check": "The Cupra's the old-school one. 290 horsepower, all through the front wheels." },
    { "id": "04", "gap": 0.4, "text": "The S3 and Golf R? 333 horsepower each, and four-wheel drive.", "say": "The S three and Golf R? Three hundred and thirty-three horsepower each, and four wheel drive.", "check": "The S3 and Golf R? 333 horsepower each, and four-wheel drive." },
    { "id": "05", "gap": 0.45, "text": "Off the line, that grip pays off. Golf R, 4.6. S3, 4.7. The Cupra? 5.7.", "say": "Off the line, that grip pays off. Golf R, four point six. S three, four point seven. The Cupra? Five point seven.", "check": "Off the line, that grip pays off. Golf R, 4.6. S3, 4.7. The Cupra? 5.7." },
    { "id": "06", "gap": 0.45, "text": "And the Golf R even gets a proper Drift mode, with the R-Performance pack.", "say": "And the Golf R even gets a proper drift mode, with the R Performance pack.", "check": "And the Golf R even gets a proper drift mode, with the R-Performance pack." },
    { "id": "07", "gap": 0.45, "text": "But here’s the kicker. A used Cupra 290? Under £20k. The other two? Over £46k, new.", "say": "But here's the kicker. A used Cupra two ninety? Under twenty grand. The other two? Over forty-six grand, new.", "check": "But here's the kicker. A used Cupra 290? Under 20 grand. The other two? Over 46 grand, new." },
    { "id": "08", "gap": 0.45, "text": "So: want a bargain? Cupra. Want the badge? S3. Want the best all-rounder? Golf R.", "say": "So. Want a bargain? Cupra. Want the badge? S three. Want the best all rounder? Golf R.", "check": "So, want a bargain? Cupra. Want the badge? S3. Want the best all-rounder? Golf R." },
    { "id": "09", "gap": 0.4, "text": "Which one are you taking? Let me know in the comments!", "say": "Which one are you taking? Let me know in the comments!" }
  ]
};
