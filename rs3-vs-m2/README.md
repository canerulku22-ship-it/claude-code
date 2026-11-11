# Audi RS3 vs BMW M2

A 70-second narrated comparison (1920×1080, 30 fps, stereo) of the Audi RS3
Sportback (8Y facelift) and the BMW M2 (G87, 2025 model year). It mixes the
manufacturers' own press photos with real-time 3D renders of both cars, plus
motion graphics and a chatty YouTuber-style voiceover.

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
  - The M2's silhouette was matched against BMW's side-profile press photo.
  - The RS3's was matched against Audi's three-quarter shots, since there is
    no side-on press photo.
  - Lights, grilles, glass, badges and UK number plates are drawn as decals
    projected onto the body. Wheels, brake callipers, mirrors, spoilers and
    exhausts are separate parts.
  - The models are close approximations, not manufacturer CAD.
- **3D shots:**
  - both cars on a turntable as the studio lights clunk on
  - an orbit around each car with callouts that track the bodywork: doors,
    engine and driven wheels
  - a top-down RS3 sliding as the torque bars swing to the outside rear wheel
  - the two cars nose to tail with their doors outlined
  - the end card
- **Photos:** 24 official press images.
  - Audi: the RS3 Sportback in Kyalami Green on the road, in the studio and
    drifting on snow.
  - BMW: the M2 on the Portuguese coast, its kidney grille, quad exhausts and
    the six-speed manual.
  - `fetch_photos.sh` downloads them from the official URLs in `photos.tsv`.
    They are **not committed** (see *Photo terms*).
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

## Photo terms

The photos are press images from [Audi](https://www.audi.com/en/photos/detail/audi-rs-3-sportback-125917)
and the [BMW Group PressClub](https://newsroom.bmwgroup.com/emea/en-ie/the-new-bmw-m2-en-ie).

- **Audi:** its images are marked "use for editorial purposes free of charge".
- **BMW:** its images are "copyright free for editorial use", © BMW AG.

So the photos stay out of the repository, and the end card credits AUDI AG and
BMW AG. A review-style post fits these terms. Ads, sponsored posts or other
commercial use would need permission from Audi and BMW first.

The 3D models carry simplified versions of each brand's badges, as you'd see
on any model car, and are labelled on the end card as approximate models built
for this film.

## Script

| Voiceover | On screen |
|---|---|
| "Right then: Audi RS3 or BMW M2? Two absolute weapons, and honestly, they couldn't be more different." | Split screen of the real cars; each snaps into colour as it's named, then "VS", "TWO ABSOLUTE WEAPONS" and 5 doors ≠ 2, AWD ≠ RWD, 5 cyl ≠ 6. |
| "So before we get stuck in, let's have a proper look at them both." | Studio lights flicker on: both 3D cars on a turntable. |
| "The Audi's a five-door hatch with a five-cylinder: 400 horsepower, and four-wheel drive." | 3D RS3 walk-round: "5-DOOR HATCH", "2.5 FIVE-CYLINDER", 400 PS counter, all four wheels glowing. |
| "The BMW? A two-door coupé with a twin-turbo straight-six. 480 horsepower, and it all goes to the rear wheels." | 3D M2 walk-round: "2-DOOR COUPÉ", "3.0 TWIN-TURBO STRAIGHT-SIX", 480 PS, rear wheels spinning up in smoke. |
| "Off the line, that four-wheel drive pays off: the RS3 does 0–62 in 3.8 seconds. The M2 auto? 4.0." | Split-lane drag race on the real cars; each timer lands as its number is said. |
| "But here's the M2's party trick: you can still get it with a six-speed manual. Proper old school." | M2 on the coast road, the real gear lever with an animated H-pattern, then a sepia side shot. |
| "Don't write the Audi off for fun, though. RS Torque Rear mode can shove all the rear torque to the outside wheel. Drift mode, basically." | RS3 on snow, a top-down 3D RS3 sliding as the torque bars swing to 100% outside, then "DRIFT MODE". |
| "Practicality? Easy win for the Audi. Five doors, and a back seat adults can actually use." | Both 3D cars nose to tail, doors outlined: 5 vs 2; the camera pushes in on the RS3's back door. |
| "And price? The RS3 starts at around £60k. The M2's closer to £69k." | A balance scale tipping toward the M2: around £60K vs around £69K. |
| "So here's my take. Want an all-weather weapon for every day? RS3. Want an old-school, rear-drive hooligan? M2." | Split-screen verdict. |
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

1. fetches the photos
2. installs three.js
3. records the narration (33 takes, about 25 minutes on four CPU cores)
4. renders the frames, 3D included, on Chromium's CPU WebGL renderer
5. synthesises the soundtrack
6. writes `rs3-vs-m2.mp4`

- `ONLY=07 TAKES=4 .venv/bin/python voiceover.py` re-records selected lines.
- `ONLY=layout` re-times the film without recording anything.
- To preview live, serve the folder over HTTP after one build (for example
  `python3 -m http.server`) and open `film.html`. Add `?t=15` to start at
  15 s. ES modules don't load from `file://`.
- Open `test3d.html` the same way to look at the 3D cars on their own.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation, pauses and voice settings. |
| `photos.tsv`, `fetch_photos.sh` | The press photos used, with their official URLs, and the script that downloads them. |
| `car3d.js` | The 3D car generator: lofted body, projected decals, wheels, and the studio. |
| `cars.js` | The RS3 and M2: dimensions, silhouettes, and their lights, grilles and glass. |
| `stage3d.js` | The 3D stage used by the film: turntables, rim lights, cameras, and screen positions for callouts. |
| `test3d.html` | A test page that renders either car from any angle. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The edit: photos, 3D, motion graphics and captions, timed from the narration. |
| `render.mjs` | Serves the folder locally, steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, the five-cylinder and straight-six engines and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by AUDI AG or BMW AG.*
