# Audi RS3 vs BMW M2

A 70-second narrated comparison (1920×1080, 30 fps, stereo) of the Audi RS3
Sportback (8Y facelift) and the BMW M2 (G87, 2025 model year). Every car on
screen is a real-time 3D render; there are no photos. Motion graphics and a
chatty YouTuber-style voiceover go on top.

- It opens on a split-screen hook that names and shows both cars.
- The lights then come on in a 3D studio with the two cars on a turntable.
- Each car gets a 3D walk-round with callouts.
- After that: 0–62 mph, the M2's manual gearbox, the RS3's drift mode,
  practicality, price, a verdict, and a question for the comments.

**Watch:** [`rs3-vs-m2.mp4`](rs3-vs-m2.mp4)

- **3D renders:** both cars are modelled from code with
  [three.js](https://threejs.org) and rendered frame by frame inside the film.
  - The body is lofted from cross-sections built from each car's published
    length, width, height, wheelbase and tyre sizes.
  - The M2's silhouette was matched against BMW's side-profile press photo,
    and the RS3's against Audi's three-quarter shots. The photos were only
    modelling references and aren't in the film or the repository.
  - Lights, grilles, glass, badges and UK number plates are drawn as decals
    projected onto the body. Wheels, brake callipers, mirrors, spoilers and
    exhausts are separate parts.
  - The models are close approximations, not manufacturer CAD.
  - The 3D code (`car3d.js`, `stage3d.js`, `decals.js`) is shared, unchanged,
    with the M5 and Golf R vs S3 films.
- **3D shots**, in a dark studio or on a night road whose markings, lamp
  posts and marker posts scroll past:
  - a split-screen hook, each car turning as it's named
  - both cars on a turntable as the studio lights clunk on
  - an orbit around each car with callouts that track the bodywork: doors,
    engine and driven wheels
  - a drag race off the start lights, with the noses lifting and the M2
    spinning its rear tyres
  - the M2 chased down the road, close up while the gearlever graphic runs
    through the gate, then in sepia for "old school"
  - the RS3 sideways in its own tyre smoke, a top-down view as the torque
    bars swing to the outside rear wheel, then full lock from behind
  - the two cars nose to tail with their doors outlined
  - 3D portraits on the price scale
  - a split-screen verdict: the RS3 in falling snow, the M2 sliding
  - the end card
- **Motion graphics:** drawn on an HTML canvas:
  - a virtual camera with push-ins, zoom punches and shake
  - flash cuts, stripe wipes, whip pans and zoom-throughs
  - colour snapping in as each car is named
  - rolling 400 / 480 PS counters
  - drag-race timers that land on 3.8 and 4.0 as they're said
  - an animated H-pattern gate
  - a sepia "old school" shot
  - a price balance that tips toward the dearer car
  - a poll-style ending
- **Voiceover:** [Chatterbox](https://github.com/resemble-ai/chatterbox)
  (Resemble AI, MIT licence), run locally, with the same chatty settings as
  the Golf R vs S3 film.
  - The voice is cloned from `voice-reference.wav`, a synthetic Kokoro-82M
    British female voice, not a real person.
  - Each line is generated three times, and Whisper picks the clearest take.
  - Chatterbox adds Resemble's inaudible Perth watermark.
- **Timing:** `voiceover.py` lays the lines out back to back. Every scene cut,
  beat and sound cue is keyed to the measured speech.
- **Soundtrack:** synthesised with NumPy/SciPy and mastered to −14 LUFS:
  - music
  - a five-cylinder engine model for the RS3, with the half-order warble
  - a straight-six for the M2
  - a manual gearchange synced to the gate graphic
  - a burnout, tyre squeal, door thunks, a film-projector clatter and other
    effects

## No photos

The film contains no photos or footage. The 3D models were shaped against
press photos from [Audi](https://www.audi.com/en/photos/detail/audi-rs-3-sportback-125917)
and the [BMW Group PressClub](https://newsroom.bmwgroup.com/emea/en-ie/the-new-bmw-m2-en-ie),
but those images aren't in the film or the repository.

The 3D models carry simplified versions of each brand's badges, as you'd see
on any model car, and are labelled on the end card as approximate models built
for this film.

## Script

| Voiceover | On screen |
|---|---|
| "Right then: Audi RS3 or BMW M2? Two absolute weapons, and honestly, they couldn't be more different." | 3D split screen; each car snaps into colour as it's named, then "VS", "TWO ABSOLUTE WEAPONS" and 5 doors ≠ 2, AWD ≠ RWD, 5 cyl ≠ 6. |
| "So before we get stuck in, let's have a proper look at them both." | Studio lights flicker on: both 3D cars on a turntable. |
| "The Audi's a five-door hatch with a five-cylinder: 400 horsepower, and four-wheel drive." | 3D RS3 walk-round: "5-DOOR HATCH", "2.5 FIVE-CYLINDER", 400 PS counter, all four wheels glowing. |
| "The BMW? A two-door coupé with a twin-turbo straight-six. 480 horsepower, and it all goes to the rear wheels." | 3D M2 walk-round: "2-DOOR COUPÉ", "3.0 TWIN-TURBO STRAIGHT-SIX", 480 PS, rear wheels spinning up in smoke. |
| "Off the line, that four-wheel drive pays off: the RS3 does 0–62 in 3.8 seconds. The M2 auto? 4.0." | Start lights, then a 3D drag race down a night road; the RS3 edges ahead and each timer lands as its number is said. |
| "But here's the M2's party trick: you can still get it with a six-speed manual. Proper old school." | The 3D M2 chased down the road, an animated H-pattern beside it, then a sepia side shot. |
| "Don't write the Audi off for fun, though. RS Torque Rear mode can shove all the rear torque to the outside wheel. Drift mode, basically." | The 3D RS3 sideways in tyre smoke, a top-down view as the torque bars swing to 100% outside, then "DRIFT MODE". |
| "Practicality? Easy win for the Audi. Five doors, and a back seat adults can actually use." | Both 3D cars nose to tail, doors outlined: 5 vs 2; the camera pushes in on the RS3's back door. |
| "And price? The RS3 starts at around £60k. The M2's closer to £69k." | A balance scale with 3D portraits, tipping toward the M2: around £60K vs around £69K. |
| "So here's my take. Want an all-weather weapon for every day? RS3. Want an old-school, rear-drive hooligan? M2." | 3D split-screen verdict: the RS3 in falling snow, the M2 sliding in smoke. |
| "Which one would you have? Let me know in the comments!" | The 3D cars turning, a poll bar and the end card. |

## Facts used and sources

| Claim | Source |
|---|---|
| RS3: 2.5-litre five-cylinder, 400 PS, 500 Nm, quattro, 0–62 mph 3.8 s | [Motor1 (first drive)](https://www.motor1.com/reviews/738871/audi-rs3-2025-first-drive/), [Motor1 (reveal)](https://www.motor1.com/news/730604/2025-audi-rs3-reveal-specs/), [evo](https://www.evo.co.uk/audi/rs3/207305/audi-rs3-2024-review-can-it-topple-amgs-a45-s) |
| RS3: RS Torque Splitter; RS Torque Rear mode can send all the rear torque to the outside rear wheel | [Audi MediaCenter (chassis)](https://www.audi-mediacenter.com/en/high-performance-redefined-audi-rs-3-sportback-and-rs-3-sedan-14310/the-chassis-a-new-level-of-driving-dynamics-14314), [Motor1 (first drive)](https://www.motor1.com/reviews/738871/audi-rs3-2025-first-drive/) |
| RS3 Sportback UK price from £59,510 at launch | [Motor1](https://www.motor1.com/news/730688/audi-rs3-facelift-2024-revealed-price/) |
| M2: 3.0 twin-turbo straight-six, 480 PS, rear-wheel drive, eight-speed auto or six-speed manual | [BMW Group PressClub](https://newsroom.bmwgroup.com/emea/en-ie/the-new-bmw-m2-en-ie) |
| M2: 0–62 mph 4.0 s (auto), 4.2 s (manual) | [BMW Group PressClub](https://newsroom.bmwgroup.com/emea/en-ie/the-new-bmw-m2-en-ie), [evo](https://www.evo.co.uk/bmw/m2/204894/bmw-m2-2024-review-an-m4-with-attitude) |
| M2 UK price from £68,705 (auto) | [Autocar](https://www.autocar.co.uk/car-review/bmw/m2), [evo](https://www.evo.co.uk/bmw/m2/204894/bmw-m2-2024-review-an-m4-with-attitude) |
| Dimensions for the 3D models (length, width, height, wheelbase, tyres) | Audi and BMW technical data |

"Absolute weapons", "party trick", "hooligan" and the verdict are the
presenter's opinion. UK prices move (the RS3 Sportback has since been listed
from £61,525), so the film says "around £60k" and "closer to £69k" and shows
the 2025 list prices in small print.

## Rebuild

```bash
./build.sh
```

The script:

1. installs three.js
2. records the narration (33 takes, about 25 minutes on four CPU cores)
3. renders the frames on Chromium's CPU WebGL renderer (about 45 minutes, as
   every shot is 3D)
4. synthesises the soundtrack
5. writes `rs3-vs-m2.mp4`

- `ONLY=07 TAKES=4 .venv/bin/python voiceover.py` re-records selected lines.
- `ONLY=layout` re-times the film without recording anything.
- To preview live, serve the folder over HTTP after one build (for example
  `python3 -m http.server`) and open `film.html`. Add `?t=15` to start at
  15 s. ES modules don't load from `file://`.
- Open `test3d.html` the same way to look at the 3D cars on their own.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation, pauses and voice settings. |
| `car3d.js` | The 3D car generator: lofted body, projected decals, wheels, and the studio. |
| `cars.js` | The RS3 and M2: dimensions, silhouettes, and their lights, grilles and glass. |
| `decals.js` | Drawing helpers for the decals: plates, badges, honeycomb, slats, glass outlines. |
| `stage3d.js` | The 3D stage used by the film: studio and night road, turntables, rim lights, cameras, and screen positions for callouts. |
| `test3d.html` | A test page that renders either car from any angle. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The edit: 3D shots, motion graphics and captions, timed from the narration. |
| `render.mjs` | Serves the folder locally, steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, the five-cylinder and straight-six engines and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by AUDI AG or BMW AG.*
