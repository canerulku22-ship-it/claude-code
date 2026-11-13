# Folding it 1 to 42 times

A config-driven animation pipeline for the TikTok series. One JSON file per
episode goes in; a 1080x1920, 30 fps, H.264 + AAC MP4 comes out. Blender
(Eevee) builds and renders the scene from Python, and ffmpeg adds the
counters and the procedurally generated sound. You never need to open
Blender.

## Install

- **Blender 4.0 or newer** (free): https://www.blender.org/download/
- **ffmpeg** with libass and libx264 (the standard builds have both):
  `brew install ffmpeg` / `winget install Gyan.FFmpeg` / `sudo apt install ffmpeg`
- Headless Linux only: `sudo apt install xvfb` (gives Eevee an OpenGL context)

Check everything is found:

```bash
python run.py --check
```

## Make an episode

```bash
python run.py episodes/paper.json --preview          # 540x960, first ~10 s, low samples
python run.py episodes/paper.json --preview --stills # + one still per landmark beat
python run.py episodes/paper.json --preview --stills-only  # just the beat stills (a minute)
python run.py episodes/paper.json                    # full 58 s render with audio
```

`run.py` only finds Blender for you. The underlying command is:

```bash
blender -b -P render_episode.py -- --config episodes/paper.json [--preview]
```

Results go to `output/<episode>/`:

| File | What it is |
|------|------------|
| `<episode>.mp4` | the finished video (`_preview.mp4` for previews) |
| `<episode>_preview_beats.png` | landmark stills with the overlay (`--stills`) |
| `full/frames/` | rendered PNG frames; `--resume` skips the ones that exist |
| `full/events.json` | the events log: every timed beat plus per-frame camera and label positions |
| `full/overlay.ass`, `full/audio.wav` | the counter layer and the soundtrack |

To change the text or sounds without re-rendering, run
`python post.py --events output/<episode>/full/events.json`.
To check pacing and audio in seconds, add `--dry-run`: it skips rendering and
builds only the events log and the soundtrack.

## Render several episodes

```bash
python batch.py episodes/*.json --plan       # check every config, print its beats
python batch.py episodes/*.json              # render them all, one after another
python batch.py episodes/ --preview          # a folder works too; so does a .txt list
python batch.py episodes/*.json --parts 2    # 2 Blender processes per episode
```

`batch.py` checks every config before it renders anything, so a mistake in
the last file shows up straight away. Other options (`--resume`,
`--samples 32`, `--stills`, ...) are passed on to every episode. A failed
episode does not stop the rest (add `--stop-on-error` if it should), and a
summary is printed at the end. On a machine without a GPU, `--parts 2` is
about 10% faster.

Example episodes are in `episodes/`: paper, pizza dough, a bedsheet and a
banknote.

## Make a new episode

Copy `episodes/paper.json` and edit it:

```json
{
  "title": "What if you fold paper 42 times?",
  "material": "paper",
  "thickness_mm": 0.1,
  "colour": "#f5f2ea",
  "folds": 42,
  "duration_s": 58
}
```

| Field | Meaning |
|-------|---------|
| `title` | the hook, on screen from the first frame (numbers are highlighted) |
| `material` | name of the material; `paper`, `banknote`, `pizza dough` and `bedsheet` have presets |
| `thickness_mm` | thickness of one sheet. Layers = 2^n, thickness = `thickness_mm` x 2^n |
| `colour` | the material's colour, exactly as it appears on screen |
| `folds` | how many folds (1-60) |
| `duration_s` | video length in seconds; must be under 60 (default 58) |

Optional fields (defaults come from the material preset):

| Field | Default | Meaning |
|-------|---------|---------|
| `sheet_size_mm` | A4 `[210, 297]` | size of the flat sheet before folding |
| `physical_folds` | `10` (banknote 8, pizza dough 5) | folds shown as a real fold animation before the column takes over |
| `sound` | `paper` | fold sound style: `paper`, `cloth` or `dough` |
| `roughness`, `sheen` | per preset | surface finish of the material |
| `cta` | `What should we fold next?` | closing line |
| `landmarks` | `auto` | or a list of landmark ids to allow |
| `sfx_dir` | none | your own sound folder (see `assets/sfx/README.md`) |
| `seed` | `7` | varies the procedural sounds |

**Landmark beats are recalculated for each material.** A landmark lands on the
first fold where the stack reaches it (for size comparisons such as notebook,
phone and person, it lands once the stack reaches 65% of the object's size).
For 0.1 mm paper that gives 7 notebook, 10 phone, 14 person, 20 Big Ben,
23 Burj Khalifa, 27 Everest & planes, 32 Space Station and 42 the Moon.
Run `python batch.py your.json --plan` to see an episode's beats.
Props stand clear of the stack whatever the sheet size, and a comparison
is skipped if the stack has already outgrown it (a bedsheet is wider than a
notebook by the time it is notebook-thick). The library lives in
`foldlib/landmarks.py`.
Pacing is automatic too: folds speed up between landmarks and the video holds
at each one, all scaled to fit `duration_s`.

## The signature look

Every episode shares one style, defined in `foldlib/style.py`: the counter
font (Inter Display, bundled under the OFL licence), colours, panel layout,
TikTok-safe margins, camera, and the environment palette from desk to space.
Change it there and it changes for the whole series. Text never goes in the
top 10%, the bottom 20% or the right-hand button rail.

## Sound

`foldlib/audio.py` synthesises everything: paper flips and crisp creases,
whooshes on each doubling, a landmark chime that climbs the scale, a riser
whose pitch follows the camera's pull-back, and the finale hit. Each sound is
timed from `events.json`. To use your own royalty-free files, see
`assets/sfx/README.md`. The mix is normalised to -14 LUFS.

## How it works

- `foldlib/timeline.py`: pacing, fold timings, camera framing and the event list (plain Python)
- `foldlib/blender/`: scene, procedural landmark models, per-frame animation
- `foldlib/overlay.py`: counters and labels as an ASS subtitle file, burned in by ffmpeg
- `foldlib/audio.py` and `foldlib/compose.py`: soundtrack, loudness and the final encode

The story spans 0.1 mm to 440,000 km, which is too much for one 3D scene. So
the camera stays put and the whole world is rescaled about the foot of the
stack each frame. That is exactly equivalent to pulling the camera back.
Objects that would be invisible at true scale, such as the plane, the Space
Station, the Moon and the Earth from far away, are enlarged, and a small
on-screen note says so.

## Render times

Eevee is fast on a GPU (well under a second per full-HD frame). On a machine
without a GPU it falls back to software OpenGL, which takes a few seconds per
frame. Use `--preview` while iterating, and `--resume` to continue an
interrupted render. To split a render across processes or machines that
share the output folder, run `--frames-only --part 0/2` and
`--frames-only --part 1/2` (and so on), then run once more with `--resume`.
That last run fills any gaps and encodes the video.
