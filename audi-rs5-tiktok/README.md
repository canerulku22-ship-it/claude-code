# Audi RS5 (2026): 50-second TikTok review

A vertical (1080×1920, 9:16, 30 fps, stereo) review of the brand-new Audi RS5,
Audi Sport's first plug-in hybrid RS. The car is a real-time 3D render; there
are no photos. The captions and graphics are deliberately small, and they're
kept inside TikTok's safe area: nothing important sits under the like,
comment and share buttons on the right, or under the caption bar at the
bottom.

**Watch:** [`audi-rs5-tiktok.mp4`](audi-rs5-tiktok.mp4)

- **Design:**
  - The car sits in the middle of the frame, small mono labels and data sit at
    the top left, and word-by-word captions sit just above the bottom bar.
  - Type is small: 42 px captions, 16–20 px mono labels, numbers no bigger
    than 96 px.
  - Graphics use thin 1.5–3 px rules and leader lines, small pills, a slim
    battery gauge, a tiny scope trace and a short checklist.
- **3D model:** the 2026 RS5 saloon, built with [three.js](https://threejs.org)
  from Audi's dimensions (4,896 mm long, 1,952 mm wide, 1,428 mm tall,
  2,903 mm wheelbase) and matched to Audi's press photos of the Progressive
  red launch car. Details:
  - fastback roof with a ducktail and black lip
  - slim headlights with checkered-flag pixel daytime lights
  - wide black mask joining the honeycomb Singleframe and air curtains
  - black rings
  - full-width rear light with checkered segments
  - finned diffuser with central oval tailpipes
  - black wheels

  The press photos were only a modelling reference and aren't in the film or
  the repository. The 3D code (`car3d.js`, `stage3d.js`, `decals.js`) is
  shared with the other films; it now takes the frame size from the film, so
  the same stage renders vertical video.
- **Shots:**
  - head-on in the dark as the lights snap on
  - a top-down x-ray of the V6, electric motor and battery, with power flowing
    to the wheels
  - flat out on a night road for 639 PS, 825 Nm and 3.6 s
  - top-down cornering as torque shifts between the rear wheels
  - silent electric cruising
  - the weight reveal
  - the rear light bar for the price
  - a turntable verdict
- **Voiceover:** [Chatterbox](https://github.com/resemble-ai/chatterbox)
  (Resemble AI, MIT licence), run locally, with the same chatty settings as the
  other films.
  - The voice is cloned from `voice-reference.wav`, a synthetic Kokoro-82M
    voice, not a real person.
  - Each line is generated three times, and Whisper picks the clearest take.
  - Chatterbox adds Resemble's inaudible Perth watermark.
- **Soundtrack:** synthesised with NumPy/SciPy and mastered to −14 LUFS:
  - music
  - a twin-turbo V6 engine model
  - the electric motor's whine
  - a heavy thud for the weight, and ticks for the counters

## Script

| Voiceover | On screen |
|---|---|
| "This is the brand-new Audi RS5, and it's the first ever plug-in hybrid RS." | Head-on in the dark; the checkered-flag lights snap on. "AUDI RS 5", "FIRST PLUG-IN HYBRID RS". |
| "Under the bonnet: a 2.9-litre twin-turbo V6, plus an electric motor." | Top-down x-ray: V6 (510 PS), electric motor (177 PS, 460 Nm), battery (25.9 kWh). |
| "Together? 639 horsepower, 825 newton metres, and 0–62 in 3.6 seconds." | Flat out on a night road; three small data rows roll up. |
| "The clever bit? A world-first rear axle that shuffles torque between the back wheels every five milliseconds." | Top-down cornering; torque bars swap between the rear wheels; a "5 ms" scope trace. |
| "And it'll do around 50 miles on electric power alone." | Silent cruising in blue; a slim battery gauge and "50 miles". |
| "The catch? It weighs almost 2.4 tonnes." | 2,355 kg rolls up over the car. |
| "And it starts at £89,400 for the saloon." | The rear light bar lit; "FROM £89,400", Avant from £91,300. |
| "My verdict? Ridiculously fast, seriously clever, but that weight is hard to ignore." | A three-line checklist: + fast, + clever, – heavy. |
| "Would you have one? Let me know in the comments!" | A yes/no poll bar and the end card. |

## Facts used and sources

| Claim | Source |
|---|---|
| Audi Sport's first high-performance plug-in hybrid; 2.9 twin-turbo V6 375 kW (510 PS) plus a 130 kW (177 PS), 460 Nm electric motor; 470 kW (639 PS) and 825 Nm combined; 0–100 km/h 3.6 s; 25.9 kWh battery (22 kWh net) | [Audi MediaCenter](https://www.audi-mediacenter.com/en/press-releases/the-new-audi-rs-5-high-performance-in-a-hybrid-17012) |
| quattro with Dynamic Torque Control: electromechanical torque vectoring at the rear, a world first, recalculated every 5 ms (200 Hz) | [Audi MediaCenter](https://www.audi-mediacenter.com/en/press-releases/the-new-audi-rs-5-high-performance-in-a-hybrid-17012) |
| Kerb weight 2,355 kg (saloon), 2,370 kg (Avant) | [Audi MediaCenter](https://www.audi-mediacenter.com/en/press-releases/the-new-audi-rs-5-high-performance-in-a-hybrid-17012) |
| Around 50 miles of electric range (Audi quotes more than 80 km in town) | [What Car?](https://www.whatcar.com/news/new-audi-rs5-goes-plug-in-hybrid-for-the-first-time-with-630bhp/n28701), [Honest John](https://www.honestjohn.co.uk/news/new-cars/2026-05/2026-audi-rs5/) |
| UK prices from £89,400 (saloon) and £91,300 (Avant) | [Motoring Research](https://www.motoringresearch.com/car-news/2026-audi-rs5-uk-pricing/), [Honest John](https://www.honestjohn.co.uk/news/new-cars/2026-05/2026-audi-rs5/) |
| Dimensions for the 3D model: 4,896 × 1,952 × 1,428 mm, 2,903 mm wheelbase | [Parkers](https://www.parkers.co.uk/audi/a5/saloon-2024/rs-5-tfsi-e-quattro-5dr-tiptronic/specs/), [Encycarpedia](https://www.encycarpedia.com/audi/26-rs-5-saloon) |

- **Opinion:** the verdict ("ridiculously fast, seriously clever", "hard to
  ignore" weight) is the presenter's opinion.
- **Disagreements:** some outlets quote other torque figures and a few UK
  prices slightly higher than £89,400. The film uses Audi's own 825 Nm and the
  most widely reported UK starting prices.

## Rebuild

```bash
./build.sh
```

The script:

1. installs three.js
2. records the narration (27 takes, about 25 minutes on four CPU cores)
3. renders the frames on Chromium's CPU WebGL renderer (about an hour)
4. synthesises the soundtrack
5. writes `audi-rs5-tiktok.mp4`

- `ONLY=layout` re-times the film without recording anything.
- To preview live, serve the folder over HTTP after one build (for example
  `python3 -m http.server`) and open `film.html`; it fills a portrait window.
  Add `?t=15` to start at 15 s.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation, pauses and voice settings. |
| `cars.js` | The 3D RS5: dimensions, silhouette, lights, grille and glass. |
| `car3d.js`, `stage3d.js`, `decals.js` | The shared 3D kit; the stage reads `FRAME_W` × `FRAME_H` from the film. |
| `test3d.html` | A test page that renders the car from any angle. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The vertical edit: 3D shots, small-type graphics and captions, timed from the narration. |
| `render.mjs` | Serves the folder locally, steps through every frame in headless Chromium at the film's frame size, and pipes the frames to ffmpeg. |
| `audio.py` | Music, the V6 and electric-motor sounds and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by AUDI AG.*
