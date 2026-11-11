# Golf R vs Audi S3

A 69-second narrated comparison (1920×1080, 30 fps, stereo) of the Volkswagen
Golf R (Mk8.5) and the Audi S3 (8Y facelift). Every car on screen is a
real-time 3D render; there are no photos. Motion graphics and a chatty
YouTuber-style voiceover go on top.

It opens on a split-screen hook that names and shows both cars. It then covers
what they share, 0–62 mph, each car's character, practicality and price, and
ends with a verdict and a question for the comments.

**Watch:** [`golf-r-vs-s3.mp4`](golf-r-vs-s3.mp4)

- **3D renders:** the cars are modelled from code with
  [three.js](https://threejs.org) and rendered frame by frame inside the film.
  - Four models: the Golf R, the Golf R Estate, and the S3 as a Sportback
    and a saloon.
  - The body is lofted from cross-sections built from the published
    dimensions and tyre sizes.
  - The Golf was checked against Volkswagen's side-on press photo. That photo
    was only a modelling reference and isn't in the film or the repository.
  - The S3 uses the same A3 Sportback shell as the RS3 in `../rs3-vs-m2`,
    with narrower arches and its own grille, quad exhausts and wheels.
  - The saloon and the Estate share their hatchbacks' front halves, with their
    own roofs, glass and tails.
  - Lights, grilles, glass, badges and UK plates are projected decals.
  - The models are close approximations, not manufacturer CAD.
  - The 3D code (`car3d.js`, `stage3d.js`, `decals.js`) is shared, unchanged,
    with the RS3 vs M2 and M5 films.
- **3D shots**, in a dark studio or on a night road whose markings, lamp
  posts and marker posts scroll past:
  - a split-screen hook, each car turning as it's named
  - the "twins" on one turntable as the studio lights clunk on, then nose to
    nose with their engines glowing through the bonnets
  - both cars from above, with drive flowing to all four wheels and torque
    shuffling between the rear two
  - a drag race off the start lights, the noses lifting
  - the Golf chased through the snow, the drive-mode menu stepping down to
    Drift, then sideways in its own tyre smoke
  - the S3 cruising, a close-up of its grille, then the Sportback and saloon
    on one turntable
  - both tailgates behind the boot-space bars, then the Golf R Estate
  - 3D portraits on the price scale
  - a split-screen verdict: the Golf sliding, the S3 saloon composed
  - the end card
- **Motion graphics:** drawn on an HTML canvas over the 3D:
  - a virtual camera with push-ins, zoom punches and shake
  - flash cuts on the beats, and stripe wipes, whip pans and zoom-throughs between scenes
  - colour snapping in as each car is named
  - start lights, and drag-race timers that land on 4.6 and 4.7 as they're spoken
  - labels pointing at the Sportback and the saloon
  - flying snow, ring bursts and rolling counters
  - a poll-style ending
- **Voiceover:** [Chatterbox](https://github.com/resemble-ai/chatterbox)
  (Resemble AI, MIT licence), run locally, with a chatty, animated delivery:
  higher exaggeration and lower CFG, set in `timeline.js`.
  - The voice is cloned from `voice-reference.wav`, a synthetic Kokoro-82M
    British female voice, not a real person.
  - Each line is generated three times, and Whisper picks the clearest take.
  - Chatterbox adds Resemble's inaudible Perth watermark.
- **Timing:** `voiceover.py` lays the lines out back to back. Every scene cut,
  beat and sound cue is keyed to the measured speech.
- **Soundtrack:** music, two turbo four-cylinder engine models (blow-off valve,
  crackle on each upshift), tyre squeal and effects, synthesised with
  NumPy/SciPy, mastered to −14 LUFS.

## No photos

The film contains no photos or footage. The 3D models were shaped against
press photos from the [Volkswagen Newsroom](https://www.volkswagen-newsroom.com/en/the-new-golf-r-and-golf-r-variant-world-premiere-18466)
and Audi's [MediaCenter](https://www.audi.com/en/images/album/audi-s3-performance-experience-2530),
but those images aren't in the film or the repository.

The 3D models carry simplified versions of each brand's badges, as you'd see
on any model car, and are labelled on the end card as approximate models built
for this film.

## Script

| Voiceover | On screen |
|---|---|
| "Right, Golf R or Audi S3? Honestly, this one's a proper head-scratcher." | 3D split screen; each car snaps into colour as it's named, then "VS". |
| "Same engine, same power, so which one actually deserves your money? Let's find out." | "WHICH ONE?" |
| "Okay, so here's the thing: under the skin, these two are basically twins." | Studio lights flicker on: both cars in 3D on one turntable, then "TWINS". |
| "Both get a 2.0-litre turbo with 333 horsepower, and clever four-wheel drive that can shove torque to either rear wheel." | Both cars nose to nose, engines glowing, with matching spec rows; then both from above with torque flowing to the wheels. |
| "So, 0–62? The Golf does it in 4.6 seconds. And the S3? 4.7. Literally a tenth apart!" | Start lights, then a 3D drag race down a night road; each timer lands as its number is said. |
| "But this is where it gets fun. The Golf's the hooligan: spec the R-Performance pack and you get an actual Drift mode. Yes, really!" | The 3D Golf chased through the snow, the drive-mode menu stepping down to Drift, then sideways in tyre smoke. |
| "The Audi? It's the grown-up. A classier badge, and you can have it as a Sportback or a saloon." | The 3D S3 cruising, a close-up of its grille, then the Sportback and saloon on a turntable with labels. |
| "Need space? The Golf's got the bigger boot, and you can even get it as an estate. Dog owners, you're welcome." | 341 vs 325 litres beside both tailgates, then the 3D Golf R Estate. |
| "And price? Honestly, it's neck and neck. Both start at around £47k." | A balance scale with 3D portraits: £46,930 vs £47,550. |
| "So here's my take. Want the wilder drive? Get the Golf R. Want the badge? Get the S3." | 3D split-screen verdict: the Golf sliding, the S3 saloon composed. |
| "But which one would you take? Let me know in the comments!" | Both 3D cars turning, a poll bar and the end card. |

## Facts used and sources

| Claim | Source |
|---|---|
| Golf R: 2.0 TSI, 333 PS, 420 Nm, 4MOTION with R-Performance Torque Vectoring (torque split between the rear wheels) | [Volkswagen newsroom](https://www.volkswagen-newsroom.com/en/the-new-golf-r-and-golf-r-variant-world-premiere-18466/the-turbocharged-engine-superior-333-ps-and-420-nm-18473), [Volkswagen newsroom (torque vectoring)](https://volkswagen-newsroom.com/en/press-releases/performance-of-new-golf-r-sets-new-standards-6897) |
| Golf R 0–62 mph 4.6 s; Drift mode with the R-Performance pack; Golf R Estate | [Drive.co.uk](https://drive.co.uk/cars/volkswagen/golf/r/review), [PistonHeads (Estate)](https://www.pistonheads.com/news/ph-driven/2025-volkswagen-golf-r-estate-uk-review/49206), [Honest John](https://honestjohn.co.uk/volkswagen/golf/r) |
| Golf R UK price from £46,930 | [Drive.co.uk](https://drive.co.uk/cars/volkswagen/golf/r/review) |
| Audi S3: 333 PS, 420 Nm, standard torque splitter, Sportback or saloon | [Rush Magazine](https://www.rushmagazine.co.uk/post/2024-audi-s3-facelift-review), [CarExpert](https://carexpert.com.au/car-reviews/2025-audi-s3-review) |
| Audi S3 0–62 mph 4.7 s | [Top Gear](https://www.topgear.com/long-term-car-reviews/audi/a3/s3-tfsi-quattro-333-vorsprung-5dr-s-tronic/report-1) |
| Audi S3 Sportback UK price from £47,550 | [Car Enthusiast](https://www.carenthusiast.com/reviews/article/13839/-/2025-Audi-S3/Driven%3A+S3+Sportback+Vorsprung+TFSI+S+Tronic.html) |
| Boot space: Golf R 341 litres, S3 325 litres | [Motorpoint](https://www.motorpoint.co.uk/comparisons/volkswagen-golf-r-vs-audi-s3) |

"Hooligan", "grown-up", "classier badge" and the verdict are the
presenter's opinion. UK prices move, so the film says "around £47k" and
labels them as 2025 list prices.

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
5. writes `golf-r-vs-s3.mp4`

- `ONLY=07 TAKES=4 .venv/bin/python voiceover.py` re-records selected lines.
- `ONLY=layout` re-times the film without recording anything.
- To preview live, serve the folder over HTTP after one build (for example
  `python3 -m http.server`) and open `film.html`. Add `?t=15` to start at
  15 s. ES modules don't load from `file://`.
- Open `test3d.html` the same way to look at the 3D cars on their own.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation, pauses and voice settings. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The edit: 3D shots, motion graphics and captions, timed from the narration. |
| `cars.js` | The 3D Golf R, Golf R Estate, S3 Sportback and S3 saloon: dimensions, silhouettes, and their lights, grilles and glass. |
| `car3d.js`, `stage3d.js`, `decals.js` | The shared 3D kit: body lofting, projected decals, wheels, studio, turntables and camera. |
| `test3d.html` | A test page that renders either car from any angle. |
| `render.mjs` | Serves the folder locally, steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, engines and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by Volkswagen AG or AUDI AG.*
