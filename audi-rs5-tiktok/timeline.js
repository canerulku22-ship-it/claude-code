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
    { "id": "01", "gap": 0.8, "text": "This is the brand-new Audi RS5, and it’s the first ever plug-in hybrid RS.", "say": "This is the brand new Audi R S five, and it's the first ever plug in hybrid R S.", "check": "This is the brand new Audi RS5, and it's the first ever plug-in hybrid RS." },
    { "id": "02", "gap": 0.55, "text": "Under the bonnet: a 2.9-litre twin-turbo V6, plus an electric motor.", "say": "Under the bonnet, a two point nine litre twin turbo V six, plus an electric motor.", "check": "Under the bonnet, a 2.9 litre twin turbo V6, plus an electric motor." },
    { "id": "03", "gap": 0.6, "text": "Together? 639 horsepower, 825 newton metres, and 0–62 in 3.6 seconds.", "say": "Together? Six hundred and thirty-nine horsepower, eight hundred and twenty-five newton metres, and nought to sixty-two in three point six seconds.", "check": "Together? 639 horsepower, 825 newton metres, and 0 to 62 in 3.6 seconds." },
    { "id": "04", "gap": 0.6, "text": "The clever bit? A world-first rear axle that shuffles torque between the back wheels every five milliseconds.", "say": "The clever bit? A world first rear axle that shuffles torque between the back wheels every five milliseconds.", "check": "The clever bit? A world first rear axle that shuffles torque between the back wheels every five milliseconds." },
    { "id": "05", "gap": 0.6, "text": "And it’ll do around 50 miles on electric power alone.", "say": "And it'll do around fifty miles on electric power alone.", "check": "And it'll do around 50 miles on electric power alone." },
    { "id": "06", "gap": 0.6, "text": "The catch? It weighs almost 2.4 tonnes.", "say": "The catch? It weighs almost two point four tonnes.", "check": "The catch? It weighs almost 2.4 tonnes." },
    { "id": "07", "gap": 0.6, "text": "And it starts at £89,400 for the saloon.", "say": "And it starts at eighty-nine thousand four hundred pounds for the saloon.", "check": "And it starts at 89,400 pounds for the saloon." },
    { "id": "08", "gap": 0.65, "text": "My verdict? Ridiculously fast, seriously clever, but that weight is hard to ignore.", "say": "My verdict? Ridiculously fast, seriously clever, but that weight is hard to ignore." },
    { "id": "09", "gap": 0.6, "text": "Would you have one? Let me know in the comments!", "say": "Would you have one? Let me know in the comments!" }
  ]
};
