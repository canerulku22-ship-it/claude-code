# Golf R vs Audi S3

A 69-second narrated comparison (1920×1080, 30 fps, stereo) of the Volkswagen
Golf R (Mk8.5) and the Audi S3 (8Y facelift). It's built from the
manufacturers' own press photos of the real cars plus real-time 3D renders of
both, with motion graphics and a chatty YouTuber-style voiceover on top. It opens on a split-screen hook that
names and shows both cars, then covers what they share, 0–62 mph, each car's
character, practicality and price, and ends with a verdict and a question for
the comments.

**Watch:** [`golf-r-vs-s3.mp4`](golf-r-vs-s3.mp4)

- **Cars:** 20 official press photos.
  - Volkswagen: the Golf R in Lapiz Blue on track, the Black Edition, the
    Estate, drift shots on snow, the engine bay and the driving-profile screen.
  - Audi: the S3 Sportback and saloon in the Dolomites, and both together.
  - `fetch_photos.sh` downloads them from the official URLs in `photos.tsv`.
    They are **not committed** (see *Photo terms*).
- **3D renders:** both cars are modelled from code with
  [three.js](https://threejs.org) and rendered frame by frame inside the film.
  - The body is lofted from cross-sections built from the published
    dimensions and tyre sizes.
  - The Golf was checked against Volkswagen's side-on press photo.
  - The S3 uses the same A3 Sportback shell as the RS3 in `../rs3-vs-m2`,
    with narrower arches and its own grille, quad exhausts and wheels.
  - Lights, grilles, glass, badges and UK plates are projected decals.
  - The models are close approximations, not manufacturer CAD.
  - The 3D code (`car3d.js`, `stage3d.js`, `decals.js`) is shared, unchanged,
    with the RS3 vs M2 and M5 films.
- **3D shots:**
  - the "twins" on one turntable as the studio lights clunk on
  - both cars from above, with drive flowing to all four wheels and torque
    shuffling between the rear two
  - the end card
- **Motion graphics:** drawn on an HTML canvas over the photos and 3D:
  - a virtual camera with push-ins, zoom punches and shake
  - flash cuts on the beats, and stripe wipes, whip pans and zoom-throughs between scenes
  - colour snapping in as each car is named
  - drag-race timers that land on 4.6 and 4.7 as they're spoken
  - labels pointing at the real saloon and Sportback
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

## Photo terms

The photos are press images from the [Volkswagen Newsroom](https://www.volkswagen-newsroom.com/en/the-new-golf-r-and-golf-r-variant-world-premiere-18466)
and Audi's [MediaCenter album](https://www.audi.com/en/images/album/audi-s3-performance-experience-2530).

- **Volkswagen:** its terms allow editorial use, including on social media,
  but not commercial use, and the images may not be passed on to third
  parties.
- **Audi:** its images are marked "use for editorial purposes free of charge".

So the photos stay out of the repository, and the end card credits Volkswagen
AG and AUDI AG. A review-style post fits these terms. Ads, sponsored posts or
other commercial use would need permission from Volkswagen and Audi first.

The 3D models carry simplified versions of each brand's badges, as you'd see
on any model car, and are labelled on the end card as approximate models built
for this film.

## Script

| Voiceover | On screen |
|---|---|
| "Right, Golf R or Audi S3? Honestly, this one's a proper head-scratcher." | Split screen of the real cars; each snaps into colour as it's named, then "VS". |
| "Same engine, same power, so which one actually deserves your money? Let's find out." | "WHICH ONE?" |
| "Okay, so here's the thing: under the skin, these two are basically twins." | Studio lights flicker on: both cars in 3D on one turntable, then "TWINS". |
| "Both get a 2.0-litre turbo with 333 horsepower, and clever four-wheel drive that can shove torque to either rear wheel." | Golf R engine bay with matching spec rows, then both 3D cars from above with torque flowing to the wheels. |
| "So, 0–62? The Golf does it in 4.6 seconds. And the S3? 4.7. Literally a tenth apart!" | Split-lane drag race; each timer lands as its number is said. |
| "But this is where it gets fun. The Golf's the hooligan: spec the R-Performance pack and you get an actual Drift mode. Yes, really!" | Golf R sliding on snow, the real driving-profile screen, then the drift shot with flying snow. |
| "The Audi? It's the grown-up. A classier badge, and you can have it as a Sportback or a saloon." | S3 saloon, a close-up of the grille, then both bodies with labels. |
| "Need space? The Golf's got the bigger boot, and you can even get it as an estate. Dog owners, you're welcome." | 341 vs 325 litres, then the Golf R Estate. |
| "And price? Honestly, it's neck and neck. Both start at around £47k." | A balance scale: £46,930 vs £47,550. |
| "So here's my take. Want the wilder drive? Get the Golf R. Want the badge? Get the S3." | Split-screen verdict. |
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

1. fetches the photos
2. installs three.js
3. records the narration (33 takes, about 25 minutes on four CPU cores)
4. renders the frames (about 20 minutes, most of it the 3D shots on
   Chromium's CPU WebGL renderer)
5. synthesises the soundtrack
6. writes `golf-r-vs-s3.mp4`

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
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The edit: photos, 3D, motion graphics and captions, timed from the narration. |
| `cars.js` | The 3D Golf R and S3: dimensions, silhouettes, and their lights, grilles and glass. |
| `car3d.js`, `stage3d.js`, `decals.js` | The shared 3D kit: body lofting, projected decals, wheels, studio, turntables and camera. |
| `test3d.html` | A test page that renders either car from any angle. |
| `render.mjs` | Serves the folder locally, steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, engines and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by Volkswagen AG or AUDI AG.*
