# How many ___ to break ___?

A config-driven pipeline for a vertical TikTok series. Objects drop one at a time onto a
target until it breaks. Each episode is a short JSON file. Blender builds and renders the
3D scene headless with Python, and ffmpeg adds the counters and the procedurally
generated sound. You never open Blender by hand.

Output: 1080x1920, 30 fps, H.264 + AAC MP4, 65-75 s. It has a title hook on the first
frame, counters that stay clear of TikTok's UI, slow-motion physics at the break, a
replay and an end card.

## Setup

You need Blender (free, 4.2 LTS or newer; tested with 5.3), ffmpeg and two Python packages.

```bash
pip install -r requirements.txt     # numpy, pillow
python make_episode.py --check      # checks Blender, ffmpeg and the packages
```

`--check` prints install commands for anything missing. In short:

| | Windows | macOS | Linux |
|---|---|---|---|
| Blender | `winget install BlenderFoundation.Blender` | `brew install --cask blender` | `sudo snap install blender --classic` |
| ffmpeg | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |

If Blender isn't on your PATH, set `BLENDER=/path/to/blender` or pass `--blender`.
Blender also works as a Python module: `pip install bpy` (Python 3.13 for bpy 5.x), then
set `BLENDER_PYTHON` to that Python. On a Linux server with no GPU, Eevee also needs Mesa:
`sudo apt install libegl1 libgl1-mesa-dri mesa-vulkan-drivers`.

## Make an episode

```bash
# Quick look: 540x960, low samples, first 10 seconds
python make_episode.py episodes/bowling_balls_glass_table.json --preview

# Full episode
python make_episode.py episodes/bowling_balls_glass_table.json

# Several episodes in a row (a failed one doesn't stop the rest)
python batch.py episodes/*.json
python batch.py --list my_batch.txt        # one config path per line
```

The video lands in `out/<config name>/<config name>.mp4` (previews in `out/<name>_preview/`).
Renders resume: if one stops halfway, run the same command again. Use `--fresh` to
start over, or `--skip-render` to rebuild only the sound and overlay from existing frames.

You can also run the 3D step on its own, exactly as Blender expects:

```bash
blender -b -P render.py -- --config episodes/bowling_balls_glass_table.json --preview
```

### Writing a new episode

Copy a file in `episodes/` and edit it. Only `title`, `drop_object`, `target` and
`break_at` are required:

```json
{
  "title": "How many bowling balls to break a glass table?",
  "drop_object": "bowling_ball",
  "drop_mass_kg": 7,
  "target": "glass_table",
  "break_at": 37,
  "drop_interval_start_s": 1.5,
  "drop_interval_end_s": 0.6,
  "crack_stages": [20, 28, 33, 36],
  "duration_s": 70
}
```

| Key | Meaning | Default |
|---|---|---|
| `title` | Hook text on the first frame. Words that name the object or target are highlighted. | required |
| `drop_object` | `bowling_ball`, `watermelon`, `brick`, `iphone`, `anvil` | required |
| `target` | `glass_table`, `trampoline`, `egg`, `wooden_chair` | required |
| `break_at` | The count that breaks it | required |
| `drop_mass_kg` | Weight per object (the bottom counter is count x mass) | from the catalogue |
| `drop_interval_start_s` / `_end_s` | Time between impacts at the start and the end | 1.5 / 0.6 |
| `crack_stages` | Counts where cracks spread and the camera pushes in | 4 stages, picked from `break_at` |
| `duration_s` | Total length (must be over 60) | 70 |
| `counter_label` / `counter_label_singular` | Top counter word, e.g. `BALLS` / `BALL` | from the catalogue |
| `seed` | Changes pile layout, colours and crack shapes | 1 |
| `replay` | Low-angle slow-motion replay of the break | true |
| `slowmo_factor` | Physics speed during the shatter (1 = real time) | 0.22 |
| `samples` / `preview_samples` | Eevee samples, final and preview | 16 / 6 |
| `intro_s`, `outro_s`, `crack_beat_s`, `suspense_s`, `shatter_s` | Timing of the beats below | 2 / 5 / 1 / 1.2 / 3.5 |

**How the duration is hit.** The intervals set the shape of the speed-up. The pause after
each crack stage, the suspense before the last drop, the slow-motion shatter, replay,
aftermath and end card are added around them. If the total still doesn't match
`duration_s`, the replay and aftermath stretch (within limits), then every drop interval
is scaled by the same factor. The render log prints that factor, e.g. *"Drop intervals
scaled x1.21 to fit the duration: 1.82s -> 0.73s"*. For pacing exactly as written, choose
intervals that give a factor near 1.0.

## Fill episodes: "How many ___ to fill ___?"

Set `"mode": "fill"` for a second format, for example `episodes/phones_burj_khalifa.json`
(52 s). The answer is arithmetic from facts in the config, printed at the start of the
render:

```
count  = container_volume_m3 x packing / (item_size_mm in m³)
weight = count x item_mass_kg
```

For the Burj Khalifa: 309,473 m² gross floor area (CTBUH) x 3.59 m average floor height
(584.5 m to the top occupied floor / 163 floors) = 1.11 million m³. One iPhone 16 is
147.6 x 71.6 x 7.8 mm = 82.4 cm³. Stacked with no gaps that's 13.46 billion phones,
weighing 2.29 million tonnes, or 1.6 phones for every person on Earth.

| Key | Meaning |
|---|---|
| `container_volume_m3` (+ `container_volume_note`) | Inside volume and where the number comes from |
| `item_size_mm`, `item_mass_kg` (+ `item_note`) | One item's size and weight |
| `packing` | 1.0 = stacked with no gaps; about 0.6 for items poured in loosely |
| `milestones` | `[{"count": 1.24e9, "text": "..."}]`: fact callouts that pop in as the counter passes them |
| `fact`, `footnote` | Comparison line and the maths shown on the answer card |
| `highlight` | Title words drawn in the accent colour |
| `duration_s` | 30-75 s (the example is 52 s) |

The beats are:

1. **Hook:** a worm's-eye view up the tower with the title.
2. **One item:** a single real-size phone lands on the plaza ("1 PHONE").
3. **Pull-back:** the camera rockets back to show the whole tower.
4. **Fill:** the glass tower fills from the bottom up while giant phones rain inside.
   - The camera tracks the fill level in medium shots and pulls out to show progress.
   - A height marker rides the level, and the counter races up through millions to billions.
5. **FULL!:** phones spray out of the top.
6. **Answer card:** the count, the weight, the comparison, the question and the maths.

The tower (`hmtb/skyline.py`) is a procedural Y-plan supertall with spiral setbacks, sized
so its model volume matches the real ~1.1 million m³. The counter follows how much of that
volume is below the fill line, so it races through the wide lower tiers and slows near the
top.

## What happens in an episode

| Time | What you see | What you hear |
|---|---|---|
| 0-2 s | Title pops in word by word on frame 1, close on the empty target, "Guess in the comments 👇" | Hit on frame 1, pill pop |
| build | Objects snap in one at a time, faster and faster. They stretch as they fall, squash and bounce on landing, and the whole pile (and a squashy target) jolts on each hit. Each impact gets a zoom punch, comic impact lines and a "+1" where it lands. Counters roll like an odometer, with "+X KG" floating off | Whoosh, impact, the target answering (glass ring, trampoline boing, wood knock), tick, a low tension drone that thickens |
| crack stages | A quick cut to a close-up of the target as cracks spread. The stress meter lights another segment, the counters shake red with a CRACK! stamp, a red vignette pulses, and the main camera pushes in | Crack and creak; random strain creaks between stages |
| before the last drop | A held beat | Riser, cut dead before the impact |
| break | The last object keeps its speed and smashes through. Pre-fractured pieces go to rigid-body physics in slow motion, with a camera shake, a white flash, a giant comic word (SMASH!, SPLAT!, RIIIP!), then a SLOW-MO tag | Slowed shatter, sub boom, then debris hits detected from the physics sim |
| replay | A yellow swipe covers the cut to a low side angle, in slow motion, with a REPLAY tag | Swipe whoosh, replay of the sounds, slower |
| last 5 s | Freeze-frame, dimmed. The counters slide to the middle and count up to the final numbers, then "What should we break next? 👇" | Whoosh, bright end chord |

## Signature style and safe zones

Every episode uses the same studio and graphics:

* **Studio:** an indigo cyclorama, a slate floor with a 25 cm grid, and a round test pad with a yellow/black hazard rim
* **Lighting:** warm key, cool rim
* **Cartoon finish:** ink outlines on every object (an inverted-hull outline, `scene3d/toon.py`), squash and stretch on the drops, and zoom punches on impacts
* **Counters:** Inter Display Black, white numbers with the yellow accent on dark rounded plates
* **Overlay:** laid out in 1080x1920 units, and nothing goes in the top 10% or the bottom 20%, or right of x = 900 (TikTok's buttons)
* **Framing:** the camera solves its framing so the action sits in the band between the two counters, whatever the target's size

## Adding objects and targets

1. Add an entry in `hmtb/catalog.py` (size, mass, labels, stacking mode, sound profile).
2. Add a builder with the same key:
   * Drop object: `build_<key>()` in `scene3d/drop_objects.py`. Model it from primitives, centred, long side along X.
   * Target: `build_<key>(rng)` in `scene3d/targets.py`, returning a `Target`. That lists the support surface for stacking, the crack surfaces and style, what shatters (Voronoi seeds, interior material, density), and what stays standing.
3. Run `--preview` and adjust.

Crack styles are `glass`, `wood`, `shell` and `fabric` (`scene3d/cracks.py`). Sound
profiles are in `hmtb/audio.py`.

## Sound

Everything is synthesised by `hmtb/audio.py` from the events log the render writes
(`out/<episode>/events.json`). That covers impacts per object, creaks, cracks and
shatters per material, and debris hits detected in the baked physics. To use real
royalty-free sounds instead, drop files into named slots in `sfx/` (see
[`sfx/README.md`](sfx/README.md)), then run `make_episode.py <config> --skip-render`.

## Render speed

Eevee is near real-time on a GPU, so a full episode takes a few minutes. On a CPU-only
machine (software OpenGL/Vulkan) it is several seconds per frame. To speed it up:

* `--scale 0.67` renders the 3D at 720x1280. It's upscaled when encoding, and the text stays sharp.
* `--samples 6` (or lower `samples` in the config). With the outlined cartoon look, 6 is hard to tell from 16.
* `--chunk 50` renders 50 frames per Blender process. Use it on CPU-only machines, where
  the software GPU driver can crash Blender after ~80 renders in one process. Crashed
  renders also resume automatically.
* Split one render across machines or processes:
  `blender -b -P render.py -- --config X.json --frames 0:1000`, and `--frames 1000:2100` on the other.
  Then run `make_episode.py X.json --skip-render`.

## How it works

```
episodes/*.json --> render.py (Blender, headless)
                     |- hmtb/config.py      defaults + validation
                     |- hmtb/timeline.py    drop schedule, beats, shot list (pure Python)
                     |- hmtb/stacking.py    where each object comes to rest
                     |- scene3d/            studio, assets, cracks, fracture, cameras, physics
                     '- writes out/<ep>/frames/*.png + events.json
                make_episode.py
                     |- hmtb/audio.py       procedural SFX from events.json -> audio.wav
                     '- hmtb/encode.py      overlay (hmtb/overlay.py) piped into ffmpeg -> MP4
```

* **The pile is laid out, not simulated.** Round objects would roll off a table and tall
  stacks can explode, so `hmtb/stacking.py` packs them: pyramids for balls and melons,
  bonded layers for bricks, a tower for phones. Their motion is keyframed: fall, bounce,
  wobble, squash, and the sag of the support. That keeps every episode stable and repeatable.
* **Real physics at the break.** The target is pre-fractured with a scripted Voronoi
  fracture (no add-on needed), so cut faces get an interior material and cracks line up.
  On the break frame the intact target swaps to its pieces, and every object goes from
  keyframed to rigid-body. The last object keeps its velocity. The physics time-scale is
  keyframed for the slow motion, and the sim is baked before rendering.
* **Cracks grow.** They're drawn into float textures where each pixel stores its crack
  stage plus progress along the crack, so one animated value per material makes each
  stage's cracks spread outward.
* **The events log** has every impact, crack, creak, break and physics hit in video
  frames. The replay re-uses scene frames around the break, so its events are mapped too.
  The audio and overlay read only this log.

## Credits

Fonts: Inter Display by The Inter Project Authors (SIL OFL 1.1). The 👇 graphic is
rendered from Noto Color Emoji (SIL OFL 1.1). See `fonts/NOTICE.txt`. Everything else
(models, materials, sounds) is generated by this code.
