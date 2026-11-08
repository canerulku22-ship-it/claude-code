# BMW M5: "Electric on Monday. V8 on Saturday."

A 1 min 43 s motion-graphics film (1920×1080, 30 fps, stereo) about the
seventh-generation BMW M5 (G90/G99): its history, how the hybrid drivetrain
works, the headline numbers, and why it suits British drivers. The story
follows one week of British driving.

**Watch:** [`bmw-m5.mp4`](bmw-m5.mp4)

Everything is generated from code. The visuals are vector animation drawn on
an HTML canvas, and the soundtrack (music, V8 engine model, electric whine,
rain, birds, UI sounds) is synthesised with NumPy. No stock footage, photos or
logos are used.

## Storyboard

| Time | Scene | What happens |
|---|---|---|
| 0:00 | Cold open | "Some cars are fast. Some cars are practical. Very few are both." A V8 idles on an oscilloscope line. |
| 0:06 | Title | The car arrives on the overrun, a light sweep crosses the paint, and a giant "M5" appears behind it. It then launches out of frame. |
| 0:13 | 01 · The Origin | 1984: BMW Motorsport puts the M1 supercar's straight-six into a family saloon. An animated chart shows launch power across all seven generations (286 → 727 PS). |
| 0:28 | 02 · The Heart | X-ray blueprint: V8, gearbox-mounted electric motor and 18.6 kWh battery light up in turn, then power flows to all four wheels. |
| 0:45 | 03 · The Numbers | A speedometer runs 0–62 mph in 3.5 s, up to 190 mph, then back to 87 mph on electric power. Stat cards show 727 PS, 1,000 Nm, 3.5 s, 190 mph and 87 mph. |
| 0:57 | 04 · A Day in Britain | 06:40: a silent electric exit from a Cotswold village. 07:55: the commute there and back on battery. 18:45: plug in at home. Saturday: wet hairpins on the Black Mountain Pass. Sunday: the saloon becomes a Touring. |
| 1:25 | 05 · Why it works in Britain | Five animated checkmarks: electric range, low-CO₂ tax band, ULEZ, all-wheel drive for British weather, and right-hand-drive saloon or Touring. |
| 1:36 | Outro | The car launches into the night. "Electric on Monday. V8 on Saturday." End card. |

## Facts used and sources

| Claim in the film | Source |
|---|---|
| 727 PS (717 bhp) combined; 4.4 V8 585 PS plus a 197 PS electric motor; 1,000 Nm (738 lb ft); 18.6 kWh battery | [BMW Group press release](https://www.press.bmwgroup.com/ireland/article/detail/T0443366EN/the-all-new-bmw-m5), [CAR magazine](https://carmagazine.co.uk/car-news/first-official-pictures/bmw/m5) |
| 0–62 mph in 3.5 s; 155 mph limited, 190 mph (305 km/h) with M Driver's Package; 87 mph (140 km/h) on electric power | [BMW technical data](https://press.bmwgroup.com/global/article/attachment/T0443252EN/621216), [What Car?](https://whatcar.com/news/2024-bmw-m5-revealed-performance-car-gets-plug-in-hybrid-power/n26919) |
| Up to 43 miles electric range (WLTP 67–69 km, saloon) | [BMW Group press release](https://www.press.bmwgroup.com/ireland/article/detail/T0443366EN/the-all-new-bmw-m5), [What Car?](https://whatcar.com/news/2024-bmw-m5-revealed-performance-car-gets-plug-in-hybrid-power/n26919) |
| 37–39 g/km CO₂ (WLTP, saloon) | [BMW Group press release](https://www.press.bmwgroup.com/ireland/article/detail/T0443366EN/the-all-new-bmw-m5) |
| UK launch prices around £110,500 (saloon) and £112,500 (Touring) | [Fleet News](https://www.fleetnews.co.uk/news/2024-bmw-m5-plug-in-hybrid), [electrifying.com](https://www.electrifying.com/blog/article/m5-touring-gets-a-plug-to-boost-power) |
| Generations and launch power: E28 286, E34 315, E39 400, E60 507, F10 560, F90 600 PS | [BMW M: generations of the M5](https://www.bmw-m.com/en/topics/magazine-article-pool/the-generations-of-the-bmw-m5-an-overview.html), [BMWBlog](https://www.bmwblog.com/2024/09/04/bmw-m5-full-history-e28-to-g90) |
| Average British commuting trip is under 10 miles (8.6 miles in the National Travel Survey) | [DfT commuting factsheet](https://assets.publishing.service.gov.uk/media/5a7b98c0e5274a7202e18326/Commuting_and_business_travel_factsheet___April_2011.pdf) |

Two claims are worded loosely on purpose:

- **Company-car tax.** Published BiK percentages for plug-in hybrids in the 40–69 mile band disagree from source to source, so the film doesn't quote a percentage. It only says the tax band is far lower than any petrol-only M5's.
- **Prices.** They have risen since launch, so the film says "from around £110,000 at UK launch".

## Rebuild

```bash
./build.sh            # renders frames, synthesises audio, writes bmw-m5.mp4
```

Requirements: Node with Playwright and Chromium, Python 3 with NumPy and
SciPy, and ffmpeg. To preview the animation live, open `film.html` in a
browser; add `?t=45` to the URL to start at 45 s.

| File | Purpose |
|---|---|
| `film.html` | All visuals. `drawFrame(t)` draws the frame at time `t`. |
| `render.mjs` | Steps through every frame in headless Chromium and pipes the frames to ffmpeg, using parallel workers. |
| `audio.py` | Soundtrack synthesis, timed to the same scene timeline. |
| `build.sh` | Runs everything and masters the result to −14 LUFS. |

*Independent fan film. Not affiliated with or endorsed by BMW AG. Real-world
electric range varies with conditions.*
