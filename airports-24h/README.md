# 24 Hours in the Sky: LAX and Gatwick

These are vertical 1080×1920, 60 fps, 60-second videos with sound. They use the same
engine as `heathrow-24h/v2`, rebuilt to be driven by a config file for each airport.

| Airport | Video | Config | Schedule |
|---|---|---|---|
| Los Angeles (LAX) | `lax_24h_in_the_sky_9x16.mp4` | `cfg_LAX.js` | `schedule_LAX.json` |
| London Gatwick (LGW) | `lgw_24h_in_the_sky_9x16.mp4` | `cfg_LGW.js` | `schedule_LGW.json` |

## What changed from Heathrow v2

- **TikTok-safe layout.** Everything is smaller and stays inside x 70–930, y 190–1510.
  This keeps it clear of TikTok's top bar, the like/comment/share buttons on the right,
  and the caption area at the bottom.
- **3D airport and ATC radar side by side.** The live 3D airport cam has a 2D radar scope
  next to it in the same row. The radar shows:
  - aircraft with callsign, altitude and origin/destination tags, plus trails and heading vectors;
  - arrival streams through the feeder fixes onto final approach;
  - departures turning toward their destinations;
  - holding patterns in busy hours, and go-arounds with a flashing alert;
  - the coastline, range rings, place names and a rotating sweep.

  Every radar blip is the same flight that lands or takes off in the 3D view.
- **Small airport sound layer.** Faint ATC radio chatter, terminal PA chimes and distant
  jet whine sit under the music, along with a spool-up and alert tone for each go-around.

## Rebuild

```bash
npm install
./build.sh                                   # assembles main.js from src/
python3 schedule_gen.py LAX                  # or LGW -> schedule_<code>.json
AP=LAX node render.js events events_LAX.json
python3 audio.py events_LAX.json soundtrack_LAX.wav
for i in 0 1 2 3; do AP=LAX node render.js chunk $((i*900)) $(((i+1)*900)) outLAX/c$i.mp4 & done; wait
# concat outLAX/c0..c3.mp4 and mux soundtrack_LAX.wav with ffmpeg
```

**About the data:** each schedule is a representative day, not a real one. Route
networks, daily frequencies and block times are modelled on the real airport. Individual
times, flight numbers, callsigns and loads are synthetic.
