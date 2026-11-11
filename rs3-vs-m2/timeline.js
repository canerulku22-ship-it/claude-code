// Script for the narration, shared by voiceover.py, film.html and audio.py.
// `text` is the on-screen caption, `say` is what the narrator pronounces,
// `gap` is the pause before the line (seconds), `check` (optional) is what
// Whisper should hear. voiceover.py lays the lines out back to back and
// writes the start times to out/vo/timing.js. Must stay valid JSON inside
// the braces.
window.TIMELINE = {
  "tail": 3.0,
  "voice": { "exaggeration": 0.8, "cfg": 0.35, "temperature": 0.85 },
  "vo": [
    { "id": "01", "gap": 0.3, "text": "Right then: Audi RS3 or BMW M2? Two absolute weapons, and honestly, they couldn’t be more different.", "say": "Right then. Audi R S three, or B M W M two? Two absolute weapons, and honestly, they couldn't be more different.", "check": "Right then. Audi RS3 or BMW M2? Two absolute weapons, and honestly, they couldn't be more different." },
    { "id": "02", "gap": 0.3, "text": "So before we get stuck in, let’s have a proper look at them both.", "say": "So before we get stuck in, let's have a proper look at them both." },
    { "id": "03", "gap": 0.5, "text": "The Audi’s a five-door hatch with a five-cylinder: 400 horsepower, and four-wheel drive.", "say": "The Audi's a five door hatch with a five cylinder. Four hundred horsepower, and four wheel drive.", "check": "The Audi's a five-door hatch with a five-cylinder. 400 horsepower and four-wheel drive." },
    { "id": "04", "gap": 0.4, "text": "The BMW? A two-door coupé with a twin-turbo straight-six. 480 horsepower, and it all goes to the rear wheels.", "say": "The B M W? A two door coo-pay with a twin turbo straight six. Four hundred and eighty horsepower, and it all goes to the rear wheels.", "check": "The BMW? A two-door coupe with a twin-turbo straight-six. 480 horsepower, and it all goes to the rear wheels." },
    { "id": "05", "gap": 0.5, "text": "Off the line, that four-wheel drive pays off: the RS3 does 0–62 in 3.8 seconds. The M2 auto? 4.0.", "say": "Off the line, that four wheel drive pays off. The R S three does nought to sixty-two in three point eight seconds. The M two auto? Four point oh.", "check": "Off the line, that four-wheel drive pays off. The RS3 does 0-62 in 3.8 seconds. The M2 auto? 4.0." },
    { "id": "06", "gap": 0.45, "text": "But here’s the M2’s party trick: you can still get it with a six-speed manual. Proper old school.", "say": "But here's the M two's party trick. You can still get it with a six speed manual. Proper old school.", "check": "But here's the M2's party trick. You can still get it with a six-speed manual. Proper old school." },
    { "id": "07", "gap": 0.45, "text": "Don’t write the Audi off for fun, though. RS Torque Rear mode can shove all the rear torque to the outside wheel. Drift mode, basically.", "say": "Don't write the Audi off for fun, though. R S Torque Rear mode can shove all the rear torque to the outside wheel. Drift mode, basically.", "check": "Don't write the Audi off for fun, though. RS Torque Rear mode can shove all the rear torque to the outside wheel. Drift mode, basically." },
    { "id": "08", "gap": 0.45, "text": "Practicality? Easy win for the Audi. Five doors, and a back seat adults can actually use.", "say": "Practicality? Easy win for the Audi. Five doors, and a back seat adults can actually use." },
    { "id": "09", "gap": 0.45, "text": "And price? The RS3 starts at around £60k. The M2’s closer to £69k.", "say": "And price? The R S three starts at around sixty grand. The M two's closer to sixty-nine.", "check": "And price? The RS3 starts at around 60 grand. The M2's closer to 69." },
    { "id": "10", "gap": 0.5, "text": "So here’s my take. Want an all-weather weapon for every day? RS3. Want an old-school, rear-drive hooligan? M2.", "say": "So here's my take. Want an all weather weapon for every day? R S three. Want an old school, rear drive hooligan? M two.", "check": "So here's my take. Want an all-weather weapon for every day? RS3. Want an old-school, rear-drive hooligan? M2." },
    { "id": "11", "gap": 0.45, "text": "Which one would you have? Let me know in the comments!", "say": "Which one would you have? Let me know in the comments!" }
  ]
};
