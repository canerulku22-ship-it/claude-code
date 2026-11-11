# Golf R vs Audi S3

A 69-second narrated comparison (1920×1080, 30 fps, stereo) of the Volkswagen
Golf R (Mk8.5) and the Audi S3 (8Y facelift). It's built from the
manufacturers' own press photos of the real cars, with motion graphics and a
chatty YouTuber-style voiceover on top. It opens on a split-screen hook that
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
- **Motion graphics:** drawn on an HTML canvas over the photos:
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

## Script

| Voiceover | On screen |
|---|---|
| "Right, Golf R or Audi S3? Honestly, this one's a proper head-scratcher." | Split screen of the real cars; each snaps into colour as it's named, then "VS". |
| "Same engine, same power, so which one actually deserves your money? Let's find out." | "WHICH ONE?" |
| "Okay, so here's the thing: under the skin, these two are basically twins." | A grey Golf R and a grey S3 Sportback side by side: "TWINS". |
| "Both get a 2.0-litre turbo with 333 horsepower, and clever four-wheel drive that can shove torque to either rear wheel." | Golf R engine bay, matching spec rows, and a torque-split diagram. |
| "So, 0–62? The Golf does it in 4.6 seconds. And the S3? 4.7. Literally a tenth apart!" | Split-lane drag race; each timer lands as its number is said. |
| "But this is where it gets fun. The Golf's the hooligan: spec the R-Performance pack and you get an actual Drift mode. Yes, really!" | Golf R sliding on snow, the real driving-profile screen, then the drift shot with flying snow. |
| "The Audi? It's the grown-up. A classier badge, and you can have it as a Sportback or a saloon." | S3 saloon, a close-up of the grille, then both bodies with labels. |
| "Need space? The Golf's got the bigger boot, and you can even get it as an estate. Dog owners, you're welcome." | 341 vs 325 litres, then the Golf R Estate. |
| "And price? Honestly, it's neck and neck. Both start at around £47k." | A balance scale: £46,930 vs £47,550. |
| "So here's my take. Want the wilder drive? Get the Golf R. Want the badge? Get the S3." | Split-screen verdict. |
| "But which one would you take? Let me know in the comments!" | Poll-style ending and end card. |

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

The script fetches the photos, records the narration (33 takes, about 25
minutes on four CPU cores), renders the frames (about 2 minutes) and the
soundtrack, and writes `golf-r-vs-s3.mp4`.

- `ONLY=07 TAKES=4 .venv/bin/python voiceover.py` re-records selected lines.
- `ONLY=layout` re-times the film without recording anything.
- To preview live, open `film.html` in a browser after one build; add `?t=15`
  to the URL to start at 15 s.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation, pauses and voice settings. |
| `photos.tsv`, `fetch_photos.sh` | The press photos used, with their official URLs, and the script that downloads them. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | The edit: photos, motion graphics and captions, timed from the narration. |
| `render.mjs` | Steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, engines and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by Volkswagen AG or AUDI AG.*
