# Cupra 290 vs Audi S3 vs Golf R

A three-way hot-hatch comparison under a minute long (1920×1080, 30 fps, stereo):
the SEAT Leon Cupra 290 (2016), the Audi S3 Sportback (8Y facelift) and the
Volkswagen Golf R (Mk8.5). Every car on screen is a real-time 3D render; there
are no photos. Motion graphics and a chatty YouTuber-style voiceover go on top.

**Watch:** [`cupra-s3-golf-r.mp4`](cupra-s3-golf-r.mp4)

- **The intro:**
  1. A light bar sweeps across the dark studio.
  2. The three cars' headlights snap on one at a time, on "Three", "hot" and
     "hatches".
  3. "ONE QUESTION."
  4. The screen splits into three slanted panels, each bursting into colour
     with its name as it's said.
  5. "WHICH ONE?"
- **3D renders:** the cars are modelled from code with
  [three.js](https://threejs.org) and rendered frame by frame inside the film.
  - The Golf R and S3 are the same models as in `../golf-r-vs-s3`.
  - The Leon Cupra 290 is new. It is built on the Golf's MQB proportions from
    SEAT's published length, width, height, wheelbase and 235/35 R19 tyres.
  - It has its own lower roof, black roof spoiler, angular LED headlights,
    trapezoid honeycomb grille with the SEAT "S", "Leon line" creases,
    side-mounted LED tail lights and twin exhausts, in Desire Red.
  - The Leon was drawn from its known design rather than matched to a photo,
    so it is the loosest of the three.
  - The models are close approximations, not manufacturer CAD.
  - The 3D code (`car3d.js`, `stage3d.js`, `decals.js`) is shared, unchanged,
    with the other films.
- **3D shots**, in a dark studio or on a night road whose markings, lamp
  posts and marker posts scroll past:
  - the intro line-up and the three-panel reveal
  - all three on one turntable as the studio lights clunk on
  - an orbit of the Cupra spinning its front wheels
  - the S3 and Golf R together, all eight wheels lighting up
  - a three-lane drag race off the start lights; the Cupra lights up its
    front tyres while the four-wheel-drive pair pull away
  - the Golf R sideways in its own smoke for "Drift mode"
  - a price chart in front of the three cars
  - a three-panel verdict
  - the end card with a three-way poll
- **Motion graphics:** drawn on an HTML canvas:
  - a virtual camera with push-ins, zoom punches and shake
  - flash cuts, three-colour stripe wipes, whip pans and zoom-throughs
  - labels that track the cars
  - rolling 290 / 333 PS counters
  - race timers that land on 4.6, 4.7 and 5.7 as they're said
  - a "BARGAIN" stamp
- **Voiceover:** [Chatterbox](https://github.com/resemble-ai/chatterbox)
  (Resemble AI, MIT licence), run locally, with the same chatty settings as
  the other comparisons.
  - The voice is cloned from `voice-reference.wav`, a synthetic Kokoro-82M
    British female voice, not a real person.
  - Each line is generated three times, and Whisper picks the clearest take.
  - Chatterbox adds Resemble's inaudible Perth watermark.
- **Soundtrack:** synthesised with NumPy/SciPy and mastered to −14 LUFS:
  - music
  - three turbo four-cylinder engine models
  - hits as each car lights up, start-light beeps, tyre squeal and other
    effects

## Script

| Voiceover | On screen |
|---|---|
| "Three hot hatches, one question. Cupra 290, Audi S3, or Golf R?" | The intro: headlights snap on in the dark, then a three-panel reveal on each name. |
| "All three run a 2.0-litre turbo, but they couldn't be more different. Let's go!" | All three on a turntable: "2.0 TURBO" over each, then 2016 · FWD / 2025 · AWD. |
| "The Cupra's the old-school one: 290 horsepower, all through the front wheels." | 3D Cupra orbit, 290 PS counter, front wheels glowing and smoking. |
| "The S3 and Golf R? 333 horsepower each, and four-wheel drive." | The S3 and Golf R together: two 333 PS counters, all eight wheels lighting up. |
| "Off the line, that grip pays off. Golf R, 4.6. S3, 4.7. The Cupra? 5.7." | Start lights, a three-lane drag race; each timer lands as its time is said. |
| "And the Golf R even gets a proper Drift mode, with the R-Performance pack." | The Golf R sideways in smoke: "DRIFT MODE". |
| "But here's the kicker. A used Cupra 290? Under £20k. The other two? Over £46k, new." | A price chart over the dimmed cars: under £20K used vs £46,930 and £47,550 new. |
| "So: want a bargain? Cupra. Want the badge? S3. Want the best all-rounder? Golf R." | Three-panel verdict; each panel snaps into colour as it's picked. |
| "Which one are you taking? Let me know in the comments!" | All three turning, a three-way poll bar and the end card. |

## Facts used and sources

| Claim | Source |
|---|---|
| Leon Cupra 290: 2.0 TSI, 290 PS, 350 Nm, front-wheel drive, 0–62 mph 5.7 s (DSG; 5.8–6.0 s manual) | [evo](https://www.evo.co.uk/seat/leon-cupra/17432/seat-leon-cupra-290-review-does-power-boost-put-cupra-into-golf-r-territory), [Top Gear](https://www.topgear.com/car-reviews/seat/leon-cupra/20-tsi-cupra-290-5dr/first-drive), [Car Enthusiast](https://www.carenthusiast.com/reviews/article/11110/-/2016-SEAT-Leon+Cupra/First+drive+-+five-door+290hp+DSG.html), [Auto Express](https://www.autoexpress.co.uk/seat/leon/94590/seat-leon-cupra-290-2016-review) |
| Used Cupra 290 asking prices about £13k–£23k (AutoUncle average about £18k) | [Autotrader](https://www.autotrader.co.uk/cars/used/seat/leon/cupra-290), [AutoUncle](https://www.autouncle.co.uk/en-gb/used-cars/Seat/Leon/t-Cupra%20290) |
| Golf R: 2.0 TSI, 333 PS, 4MOTION, 0–62 mph 4.6 s; Drift mode with the R-Performance pack; from £46,930 | [Volkswagen newsroom](https://www.volkswagen-newsroom.com/en/the-new-golf-r-and-golf-r-variant-world-premiere-18466/the-turbocharged-engine-superior-333-ps-and-420-nm-18473), [Drive.co.uk](https://drive.co.uk/cars/volkswagen/golf/r/review) |
| Audi S3: 333 PS, quattro, 0–62 mph 4.7 s; Sportback from £47,550 | [Motor1](https://www.motor1.com/news/715275/2025-audi-s3-debut-specs/), [Top Gear](https://www.topgear.com/long-term-car-reviews/audi/a3/s3-tfsi-quattro-333-vorsprung-5dr-s-tronic/report-1), [Car Enthusiast](https://www.carenthusiast.com/reviews/article/13839/-/2025-Audi-S3/Driven%3A+S3+Sportback+Vorsprung+TFSI+S+Tronic.html) |

- **Drift mode:** reports conflict on whether the facelifted S3 has a drift
  mode, so the film says only that the Golf R gets one and doesn't claim the
  S3 lacks it. Motor1 and CarThrottle say it doesn't; Audi describes its
  Dynamic Plus mode as encouraging oversteer.
- **Opinion and prices:** "old-school", "bargain", "badge" and "best
  all-rounder" are the presenter's opinion. Used prices are asking prices and
  vary with age and mileage, so the film says "under £20k" and labels the
  figure as typical asking prices.
- **Cupra 290 years:** the 290 PS Cupra was sold in 2016–17 and again in
  2019–20 (after the 300 PS Cupra 300); the model is the 2016 car.

## Rebuild

```bash
./build.sh
```

The script:

1. installs three.js
2. records the narration (27 takes, about 25 minutes on four CPU cores)
3. renders the frames on Chromium's CPU WebGL renderer (about 40 minutes)
4. synthesises the soundtrack
5. writes `cupra-s3-golf-r.mp4`

- `ONLY=05 TAKES=4 .venv/bin/python voiceover.py` re-records selected lines.
- `ONLY=layout` re-times the film without recording anything.
- To preview live, serve the folder over HTTP after one build (for example
  `python3 -m http.server`) and open `film.html`. Add `?t=15` to start at
  15 s.
- Open `test3d.html` the same way to look at the 3D cars on their own.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation, pauses and voice settings. |
| `cars.js` | The 3D Leon Cupra 290, Golf R and S3: dimensions, silhouettes, and their lights, grilles and glass. |
| `car3d.js`, `stage3d.js`, `decals.js` | The shared 3D kit: body lofting, projected decals, wheels, studio, night road, turntables and camera. |
| `test3d.html` | A test page that renders any of the cars from any angle. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The edit: 3D shots, motion graphics and captions, timed from the narration. |
| `render.mjs` | Serves the folder locally, steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, three engine models and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by SEAT, CUPRA, AUDI AG or
Volkswagen AG.*
