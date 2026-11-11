# Golf R vs Audi S3

A narrated motion-graphics comparison (1920×1080, 30 fps, stereo) of the
Volkswagen Golf R (Mk8.5) and the Audi S3 (8Y facelift). It opens on a
split-screen hook that names and shows both cars. It then covers what they
share, 0–62 mph, each car's character, practicality and price, and ends with
a verdict and a question for the comments.

**Watch:** [`golf-r-vs-s3.mp4`](golf-r-vs-s3.mp4)

Everything is generated from code, as in the [BMW M5 film](../bmw-m5-video):

- **Visuals:** vector animation drawn on an HTML canvas, composited through a
  virtual camera (push-ins, zoom punches, shake) with stripe wipes, whip pans
  and zoom-throughs.
  - **Golf R:** Lapiz Blue; the light bar across the nose into the
    illuminated VW logo, matte chrome mirrors, R badges and blue calipers.
  - **S3:** Tango Red; the Singleframe grille with the four rings, segmented
    daytime lights, aluminium-look mirrors and blades, and the arch blisters.
  - Each car is drawn from the front and the side; the Golf also from above
    for the Drift-mode scene. No photos or stock footage.
- **Voiceover:** [Chatterbox](https://github.com/resemble-ai/chatterbox)
  (Resemble AI, MIT licence), run locally on the CPU. The voice is cloned
  from `voice-reference.wav`, nine seconds of the synthetic Kokoro-82M British
  female voice `bf_emma`, not a real person. Each line is generated three
  times, and Whisper picks the clearest take. Chatterbox adds Resemble's
  inaudible Perth watermark to its output.
- **Timing:** `voiceover.py` lays the lines out back to back. Every scene cut
  and beat in `film.html` and `audio.py` is keyed to that measured speech
  timing, so re-recording a line re-times the whole film.
- **Soundtrack:** music, two turbocharged four-cylinder engine models (blow-off
  valve, crackle on each upshift), tyre squeal and effects, synthesised with
  NumPy/SciPy. The music ducks about 11 dB under the voice, and the mix is
  mastered to −14 LUFS.

## Script and storyboard

| Voiceover | On screen |
|---|---|
| "Volkswagen Golf R, or Audi S3?" | Split screen: each car lights up as it's named, then "VS" slams in. |
| "Same engine. Same power. So which one should you buy?" | "WHICH ONE?" |
| "Under the skin, they're twins." | Blueprint outlines of both cars overlap almost exactly. |
| "Both get a 2.0-litre turbo with 333 horsepower, and four-wheel drive that can push torque to either rear wheel." | Matching spec rows, plus a drivetrain diagram that shifts torque between the rear wheels. |
| "0–62? Golf R: 4.6 seconds. S3: 4.7." | Drag race with timers. |
| "The Golf is the hooligan. Add the R-Performance pack and you even get a Drift mode." | Top-down Golf; the driving-profile selector clicks through to DRIFT, then smoke. |
| "The Audi is the smart one: a premium badge, and a choice of Sportback or saloon." | The rings catch the light, then the Sportback morphs into the saloon. |
| "The Golf has the bigger boot, and you can even get it as an estate." | 341 vs 325 litres filling up, then the Golf morphs into the Estate. |
| "And prices? Neck and neck, from around £47k." | A balance scale: £46,930 vs £47,550. |
| "Want the wilder drive? Golf R. Want the badge? Audi S3." | Split-screen verdict. |
| "Which one are you taking? Tell us in the comments." | Poll-style ending and end card. |

## Facts used and sources

| Claim | Source |
|---|---|
| Golf R: 2.0 TSI, 333 PS, 420 Nm, 7-speed DSG, 4MOTION with R-Performance Torque Vectoring (torque split between the rear wheels) | [Volkswagen newsroom](https://www.volkswagen-newsroom.com/en/the-new-golf-r-and-golf-r-variant-world-premiere-18466/the-turbocharged-engine-superior-333-ps-and-420-nm-18473), [Volkswagen newsroom (torque vectoring)](https://volkswagen-newsroom.com/en/press-releases/performance-of-new-golf-r-sets-new-standards-6897) |
| Golf R 0–62 mph 4.6 s; Drift and Special modes with the R-Performance pack; Golf R Estate | [Drive.co.uk](https://drive.co.uk/cars/volkswagen/golf/r/review), [PistonHeads (Estate)](https://www.pistonheads.com/news/ph-driven/2025-volkswagen-golf-r-estate-uk-review/49206), [Honest John](https://honestjohn.co.uk/volkswagen/golf/r) |
| Golf R UK price from £46,930 | [Drive.co.uk](https://drive.co.uk/cars/volkswagen/golf/r/review) |
| Audi S3: 333 PS, 420 Nm, standard torque splitter from the RS 3, Sportback or saloon | [Rush Magazine](https://www.rushmagazine.co.uk/post/2024-audi-s3-facelift-review), [CarExpert](https://carexpert.com.au/car-reviews/2025-audi-s3-review) |
| Audi S3 0–62 mph 4.7 s | [Top Gear](https://www.topgear.com/long-term-car-reviews/audi/a3/s3-tfsi-quattro-333-vorsprung-5dr-s-tronic/report-1) |
| Audi S3 Sportback UK price from £47,550 | [Car Enthusiast](https://www.carenthusiast.com/reviews/article/13839/-/2025-Audi-S3/Driven%3A+S3+Sportback+Vorsprung+TFSI+S+Tronic.html) |
| Boot space: Golf R 341 litres, S3 325 litres | [Motorpoint](https://www.motorpoint.co.uk/comparisons/volkswagen-golf-r-vs-audi-s3) |

"Hooligan", "smart one", "wilder drive" and the verdict are the film's
opinion. UK list prices move, so the film says "from around £47k" and
notes that they're 2025 figures.

## Rebuild

```bash
./build.sh
```

On four CPU cores, the narration (33 takes) takes about 20 minutes and the
render about two. `ONLY=05 TAKES=4 .venv/bin/python voiceover.py`
re-records selected lines. To preview the animation live, open `film.html` in
a browser after one build; add `?t=15` to the URL to start at 15 s.

| File | Purpose |
|---|---|
| `timeline.js` | Script: caption text, pronunciation and the pause before each line. |
| `voice-reference.wav` | Synthetic reference voice for Chatterbox. |
| `voiceover.py` | Narration: three takes per line, checked with Whisper, laid out into `out/vo/timing.js`. |
| `film.html` | All visuals, timed from the narration. |
| `render.mjs` | Steps through every frame in headless Chromium and pipes the frames to ffmpeg. |
| `audio.py` | Music, engines and effects, mixed with the narration. |
| `build.sh` | Runs everything and masters the result. |

*Independent film. Not affiliated with or endorsed by Volkswagen AG or AUDI AG.*
