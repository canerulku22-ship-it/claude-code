# Country Conquest

A config-driven pipeline that renders the vertical TikTok series *Country Conquest*:
a champion country spins for a neighbouring opponent, battles it, paints the map in
its colour, and the empire carries over from episode to episode.

- 1080x1920, 30 fps, H.264 MP4, 57 s by default (configurable, always under 60 s)
- Every result comes from a seeded simulation, and every episode is a JSON config,
  so any video can be re-rendered exactly.

> **Status:** map, rules, simulation, preview and video rendering are done.
> Procedural audio (step 3) comes next, once the look is approved.

## Setup

```bash
pip install -r requirements.txt        # Python 3.10+, plus ffmpeg on your PATH
python conquest.py fetch-assets        # one-off download (~6 MB), also runs automatically
```

The assets are pinned npm packages, checked against their sha512 hashes:

- Natural Earth 1:50m countries (public domain)
- flag-icons (MIT)
- Lilita One font (OFL)

## Make a new episode

```bash
python conquest.py episode --preview   # quick 540x960 check of intro + round 1 (~10 s to render)
python conquest.py render episodes/s01e01.json   # full episode from that same config
```

`episode` freezes the next episode into `episodes/sXXeYY.json`. That file holds:

- the merged config,
- a fresh random seed,
- the series state it starts from.

Rendering it fully writes `out/sXXeYY.mp4` plus `out/sXXeYY.events.json`, a log of
every timed moment (ticks, ding, hits, KO, paint, plant…) that the audio is built from.
Then `state.json` advances, so the next episode continues from that point.

Other ways to run it:

- `python conquest.py episode`: create and fully render the next episode in one go.
- `python conquest.py episode --seed 12345`: pin the seed.
- `python conquest.py render <file> --stills 1.0,6.5`: save PNG frames instead of a video.
- `python conquest.py render <file> --preview --guides`: shade TikTok's UI zones to check the layout.
- `python conquest.py batch 3`: render 3 episodes in a row, each continuing from the last.
- `python conquest.py status`: show the current champion, territory and streak.

Re-rendering an old episode config gives the identical video and never touches
`state.json`. Previews never touch it either.

## Start a new season

```bash
python conquest.py reset               # archives state.json to seasons/, restarts from start_country
python conquest.py episode --reset     # same, then renders episode 1
```

## Config (`configs/default.json`)

Edit the defaults, or pass your own file with `--base my.json`. It only needs the
keys you change.

| key | meaning |
| --- | --- |
| `start_country` | ISO alpha-3 code that starts a season (`"TUR"`) |
| `rounds` | rounds per episode (5) |
| `neighbours_only` | spinner only picks countries bordering the empire; sea neighbours within `sea_neighbour_km` count (the gap must be open water) |
| `strength_mode` | `"equal"` (pure chance) or `"territory_bonus"` (+3 HP per extra country, capped at +18) |
| `exclude_pairs` | pairs that are never matched, also when the empire *holds* one side (`exclude_pairs_cover_territory`) |
| `min_area_km2` | skip microstates that are invisible on the map |
| `spinner_style` | `"map_roulette"` or `"wheel"` |
| `seed` | `null` = new random seed per episode (saved into the episode file) |
| `video.target_duration` | total length; rounds share what's left after intro (2 s) and outro (3 s) |
| `colors` / `names` | per-country colour or display-name overrides, e.g. `{"TUR": "#E30A17"}` |
| `text` | every on-screen line. `*word*` is drawn in the accent colour, and flag emoji render as real flags |
| `safe_area` | screen margins kept clear of TikTok's UI |

## How it works

`conquest/sim.py` plays the episode:

- The spinner pick uses the neighbour graph and the exclusion rules.
- Battles are blow by blow: miss, hit or crit, with a rally/comeback mechanic
  applied equally to both sides.
- It produces the ownership changes.

`conquest/timeline.py` turns that into timed scenes, camera moves and the events log.

`conquest/render/` draws each frame with Pillow:

- animated sea
- countries from the projected Natural Earth polygons
- paint spread, flag pins, the clash card, the HUD

`conquest/encode.py` renders frames in parallel and pipes them into ffmpeg.
Team colours come from each flag. An opponent always fights in a flag colour that
contrasts with the champion's, and keeps that colour if it wins.
