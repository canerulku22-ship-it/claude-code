# HEATHROW: 24 HOURS IN THE SKY (v2)

A vertical 1080×1920, 60 fps, 60-second video with sound, rendered to
`heathrow_24h_in_the_sky_9x16.mp4`. It uses the same representative-day schedule as
v1: 644 departures, 647 arrivals, 229,801 passengers.

| Time | Section |
|---|---|
| 0 – 6.6 s | **Aerial opening.** A night aerial of Heathrow with a slow push-in while two arrivals land on 27R. "HEATHROW:" appears, then "24 HOURS IN THE SKY", then the subtitles one by one: "Every flight. Every arrival. Every departure." |
| 6.6 – 9 s | **Rise into the sky.** The camera climbs away from the airport and crossfades into the globe, which pulls back from London. |
| 9 – 52 s | **The day, 00:00 → 24:00.** Details below. |
| 52 – 60 s | **Finale.** "24 HOURS. ONE AIRPORT. THOUSANDS OF JOURNEYS." Then total arrivals, total departures, total passengers and total flights count up in turn over the full day's route network. |

## The day (9 – 52 s)

- **Globe**
  - Aircraft glyphs fly along their paths, leaving glowing trails. Departing flights are cyan and arriving flights are green.
  - Route arcs keep the flight-time colours: yellow 0–2 h, orange 2–4 h, red 4–8 h, purple 8 h+.
  - The busiest routes are drawn thick and pulsing, with live "× N" badges.
  - Origin and destination airports glow and send out pulse rings when flights leave or arrive.
  - Atmospheric lighting includes the day/night terminator, a sunset band, ocean glint and a sun-lit atmosphere.
  - The camera moves through four views: worldwide, across the Atlantic, Europe close-up, and Middle East & Asia.
- **Stats**
  - Large rolling-digit counters with their own colours: passengers in gold, departures in cyan, arrivals in green.
  - Each counter shows "last hour" figures.
- **Live airport cam**
  - Six camera angles, joined by dip-to-black cuts: aerial, approach 27R at sunrise, runway 27L lift-offs, tower view in the showers and sunset, Terminal 5 at dusk, and a night aerial orbit.
  - Daylight, sunset, night and weather change smoothly.
  - A weather chip shows wind direction and speed, temperature and conditions.

## Rebuild

The steps are the same as in v1 (see `../README.md`). Run them inside this folder:

```bash
npm install && node render.js events events.json && python3 audio.py events.json soundtrack.wav
for i in 0 1 2 3; do node render.js chunk $((i*900)) $(((i+1)*900)) out/c$i.mp4 & done; wait
# then concat out/c0..c3.mp4 and mux soundtrack.wav with ffmpeg
```
