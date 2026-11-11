# BMW M5: "This is why the BMW M5 is the best car on British roads."

A 41-second narrated motion-graphics film (1920×1080, 30 fps, stereo) about
the seventh-generation BMW M5 (G90). It opens on a hook, runs through history,
the hybrid drivetrain, performance and why the car suits British drivers, and
ends on "Electric on Monday. V8 on Saturday."

**Watch:** [`bmw-m5.mp4`](bmw-m5.mp4)

Everything is generated from code:

- **Visuals:** vector animation drawn on an HTML canvas. The car is drawn as
  the G90 M5 from the front, side and rear: the kidney grille with the
  illuminated "Iconic Glow" outline and M double slats, the light signature,
  carbon roof, Hofmeister kink, flared arches, quad tailpipes and blue M
  calipers, in Isle of Man Green. No photos or stock footage.
- **Motion graphics:** every scene is drawn into an off-screen buffer and
  composited through a virtual camera. That gives a slow push-in per scene,
  plus zoom punches and shake on the big beats. Scenes change with M-stripe
  wipes, whip pans with motion blur, and zoom-throughs. Other elements:
  rolling-digit counters, ring bursts, scan bars, drifting outlined type, a
  gear and RPM readout synced to the engine sound, sparks, lightning,
  raindrops on the lens, a viewfinder frame and a shine across the logo.
- **Voiceover:** [Chatterbox](https://github.com/resemble-ai/chatterbox)
  (Resemble AI, MIT licence), run locally on the CPU with an expressive ad
  read. The voice is cloned from a synthetic reference, not a real person:
  about nine seconds of the British female voice `bf_emma` from
  [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0, run
  with [kokoro-js](https://www.npmjs.com/package/kokoro-js)). Each line is
  generated three times; Whisper checks every take, and the clearest take
  that fits its slot is kept. Chatterbox adds Resemble's inaudible Perth
  watermark to its output. Captions follow the measured speech timing.
- **Soundtrack:** music, a V8 engine model, EV whine and sound effects,
  synthesised with NumPy/SciPy. The music ducks about 11 dB under the voice.
  The mix is mastered to −14 LUFS.

## Script and storyboard

| Time | Voiceover | On screen |
|---|---|---|
| 0:00 | "This is why the BMW M5 is the best car on British roads." | Darkness. The kidney grille's light outline traces on, the headlights snap on and the engine starts. |
| 0:05 | "Since 1984, it's put supercar power in a family saloon." | A 1980s saloon outline. The year rolls through every generation to 2024, and the new M5 appears. |
| 0:09 | "The new one? A twin-turbo V8 and an electric motor." / "727 horsepower." | X-ray view: V8, gearbox-mounted motor and battery light up, power flows to all four wheels, then "727" slams in. |
| 0:15 | "0–62 in 3.5 seconds." | Speedometer and stopwatch with the car flat out. |
| 0:19 | "But here's the clever bit: it plugs in." | Charge flap opens and the cable plugs in at home. |
| 0:22 | "Up to 43 miles on electric alone. Most commutes, there and back, with no petrol." | Home-to-work route with the electric range draining. |
| 0:27 | "Lower company-car tax. All-wheel drive for British weather." | 37 g/km CO₂ against a petrol-only rival's top tax band, then the car in rain past dry-stone walls with an all-wheel-drive torque display. |
| 0:32 | "Saloon, or Touring." | The saloon morphs into the Touring. |
| 0:34 | "Electric on Monday. V8 on Saturday." | Rear view: silent in EV mode, then the tail lights flare and it launches into the night. |
| 0:37 | "The BMW M5." | End card. |

Lines can be edited in `timeline.js`: `text` is the caption and `say` is the
pronunciation. Re-run `build.sh` after editing.

## Facts used and sources

| Claim in the film | Source |
|---|---|
| 727 PS (717 bhp) combined; 4.4 twin-turbo V8 585 PS plus a 197 PS electric motor; 1,000 Nm; 18.6 kWh battery | [BMW Group press release](https://www.press.bmwgroup.com/ireland/article/detail/T0443366EN/the-all-new-bmw-m5), [CAR magazine](https://carmagazine.co.uk/car-news/first-official-pictures/bmw/m5) |
| 0–62 mph in 3.5 s | [BMW technical data](https://press.bmwgroup.com/global/article/attachment/T0443252EN/621216), [What Car?](https://whatcar.com/news/2024-bmw-m5-revealed-performance-car-gets-plug-in-hybrid-power/n26919) |
| Up to 43 miles electric range (WLTP 67–69 km, saloon) | [BMW Group press release](https://www.press.bmwgroup.com/ireland/article/detail/T0443366EN/the-all-new-bmw-m5), [What Car?](https://whatcar.com/news/2024-bmw-m5-revealed-performance-car-gets-plug-in-hybrid-power/n26919) |
| 37–39 g/km CO₂ (WLTP, saloon) | [BMW Group press release](https://www.press.bmwgroup.com/ireland/article/detail/T0443366EN/the-all-new-bmw-m5) |
| Touring version available | [BMW Group press release (Touring)](https://www.press.bmwgroup.com/ireland/article/detail/T0444474EN/the-all-new-bmw-m5-touring?language=en) |
| First M5 in 1984; generations E28 → G90 | [BMW M: generations of the M5](https://www.bmw-m.com/en/topics/magazine-article-pool/the-generations-of-the-bmw-m5-an-overview.html), [BMWBlog](https://www.bmwblog.com/2024/09/04/bmw-m5-full-history-e28-to-g90) |
| A typical commute is well within the range (average commuting trip 8.6 miles each way) | [DfT commuting factsheet](https://assets.publishing.service.gov.uk/media/5a7b98c0e5274a7202e18326/Commuting_and_business_travel_factsheet___April_2011.pdf) |

"Best car on British roads" is the film's opinion, used as a hook. The tax
comparison is qualitative: published plug-in-hybrid company-car tax
percentages disagree between sources, so the film shows tax bands without
quoting a rate.

## Rebuild

```bash
./build.sh
```

The script installs `kokoro-js` and Chatterbox (PyTorch, a few GB, into
`.venv`). It then synthesises the narration, renders the frames and
soundtrack, and writes `bmw-m5.mp4`. On four CPU cores the narration takes
about 20 minutes (33 takes); the rest takes about two minutes.
`VOICE=kokoro ./build.sh` skips Chatterbox and uses the lighter Kokoro voice.

It needs Node with Playwright and Chromium, Python 3 with NumPy and SciPy, and
ffmpeg. The first run downloads the voice models from Hugging Face. To preview
the animation live, open `film.html` in a browser after one build; add `?t=15`
to the URL to start at 15 s.

| File | Purpose |
|---|---|
| `timeline.js` | Script and timing for each voiceover line, shared by every step. |
| `voiceover.mjs` | Kokoro lines: the reference voice for Chatterbox, and the fallback narration. |
| `voiceover.py` | Chatterbox narration: three takes per line, checked with Whisper; writes the speech timing for the captions. |
| `film.html` | All visuals. `drawFrame(t)` draws the frame at time `t`. |
| `render.mjs` | Steps through every frame in headless Chromium and pipes the frames to ffmpeg, using parallel workers. |
| `audio.py` | Music, engine and effects, mixed with the voiceover. |
| `build.sh` | Runs everything and masters the result. |

*Independent fan film. Not affiliated with or endorsed by BMW AG. Real-world
electric range varies with conditions.*
