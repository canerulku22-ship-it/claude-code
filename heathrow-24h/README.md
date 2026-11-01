# 24 Hours at London Heathrow (in 60 seconds)

A vertical 1080×1920, 60 fps video with sound. A whole day of Heathrow departures
and arrivals is compressed into 60 seconds. The final render is `heathrow_24h_9x16.mp4`.

## What's on screen

| Time in video | What happens |
|---|---|
| 0 – 2.6 s | Night chase shot of a late arrival landing on runway 27R, with the title. |
| 2.6 – 5 s | The camera pulls out from the airport to the globe. The 3D airport shrinks into the "LIVE" panel and the panels fade in. |
| 5 – 56 s | The clock runs 00:00 → 24:00 (night hours go faster). |
| 56 – 60 s | End-of-day summary card. |

- **Globe:** shows every flight in the air, with a day/night line that moves with the
  real sun position for 1 November.
- **Route colours** (by block time, the same for departures and arrivals):
  - yellow: 0–2 h
  - orange: 2–4 h
  - red: 4–8 h
  - purple: 8 h or more

  The legend shows how many flights so far fall in each band.
- **Counters:** departures, arrivals, passengers (counting up), and planes in the air now.
  There is also an hourly movements bar chart along the time-of-day bar.
- **Most common flights:** a live leaderboard of the top routes.
- **Time cards:** first long-haul arrival, first departure, sunrise, busiest hour,
  showers, the 15:00 runway switch, sunset, the 200,000th passenger and the last departure.
- **3D Heathrow panel:** both runways, terminals, lighting and parked aircraft.
  - Planes land on the arrivals runway and take off from the departures runway.
  - Each plane's tail is painted in its route colour.
  - Lighting follows the time of day and the weather (mist, cloud, rain and wind
    streaks).
  - The runways swap roles at 15:00 (runway alternation).
- **Weather panel:** a compass with the wind direction, wind speed and gusts,
  temperature and conditions.
- **Sound:**
  - an ambient score;
  - take-off roars and touchdown tyre chirps with reverse thrust, synced to the 3D planes;
  - wind and rain that follow the weather;
  - hour ticks, chimes for the time cards, passenger-milestone sparkles,
    an ATC squelch at the runway switch, dawn birdsong and an end-of-day swell.

**About the data:** the schedule is a *representative* day, not a real one. It is
modelled on Heathrow's real route network, daily frequencies and block times, which
gives about 1,290 movements and about 230,000 passengers. Individual flight times and
flight numbers are synthetic.

## Rebuild

```bash
npm install                                   # three, world-atlas, topojson-client
python3 schedule.py                           # -> schedule.json
node render.js events events.json             # timing data for the soundtrack
python3 audio.py events.json soundtrack.wav   # needs numpy + scipy
# render the frames in parallel chunks (Playwright + headless Chromium/SwiftShader)
for i in 0 1 2 3; do node render.js chunk $((i*900)) $(((i+1)*900)) out/c$i.mp4 & done; wait
printf "file 'c0.mp4'\nfile 'c1.mp4'\nfile 'c2.mp4'\nfile 'c3.mp4'\n" > out/list.txt
ffmpeg -f concat -safe 0 -i out/list.txt -i soundtrack.wav -c:v copy -c:a aac -b:a 256k \
       -shortest -movflags +faststart heathrow_24h_9x16.mp4
```

`node render.js still <dir> 12 30 50` renders single PNG frames, which is useful for previews.
