# Chef Whiskers

Turns a recipe JSON file into a ~20-second vertical (1080x1920) TikTok starring
**Chef Whiskers**: an original, 3D-animated orange tabby cat chef in a small white
chef hat and red apron, cooking in a cozy modern kitchen. It suits a faceless
channel: no human appears on camera.

There are three ways to make the clips, behind the same interface:

- **`render` (default): a local 3D animation.** The cat, the kitchen and the food are
  modeled in Three.js and rendered frame by frame in headless Chromium, with
  synthesized sound and music. Free, no API key, and the cat is the same 3D model in
  every shot.
- **`blender`: a Blender/Cycles 3D film.** Food-only shots built procedurally in
  Blender with Python: modeled food, geometry-node particles, 3D labels and titles,
  path-traced lighting. It looks much more realistic and renders much more slowly. See
  [Blender provider](#blender-provider).
- **`fal`: generative AI video** through fal.ai, from text prompts and a character
  reference image. Needs an API key and costs money per clip.

```
recipe JSON ──► character reference ──► one clip per shot ──► ffmpeg edit ──► MP4 + caption
                output/character_ref.png  output/clips/<recipe>/  crop, text,    output/final/<recipe>.mp4
                                                                   concat, music  output/final/<recipe>.txt
```

## Project layout

```
chef-whiskers/
├── generate.py              # the pipeline (run this)
├── providers/               # swappable clip providers
│   ├── base.py              # Provider interface, errors, retry logic
│   ├── __init__.py          # provider registry
│   ├── render.py            # local 3D render (default)
│   ├── blender.py           # Blender/Cycles 3D film
│   ├── fal.py               # fal.ai generative video
│   └── placeholder.py       # offline test provider (test patterns)
├── renderer/                # the 3D animation
│   ├── main.js              # Chef Whiskers, kitchen, smash burger food and scenes
│   ├── chicken.js           # chicken burger food and scenes
│   ├── fx2d.js              # 2D motion graphics drawn over the 3D (bursts, stickers, speed lines)
│   ├── render.js            # renders frames in headless Chromium, pipes them to ffmpeg
│   ├── audio.py             # synthesized sound effects and music bed (numpy)
│   ├── index.html
│   └── package.json
├── blender/                 # the Blender 3D film (chicken_burger_3d)
│   ├── lib.py               # materials, studio, cameras, food models, labels, particles
│   ├── shots.py             # the ten shots, their animation and sound cues
│   └── render_shot.py       # renders one shot to a resumable PNG sequence
├── prompts/
│   ├── character.txt        # Chef Whiskers description, prepended to every AI prompt
│   └── character_reference.txt  # prompt for the AI reference image
├── recipes/
│   ├── smash_burger.json    # sample recipe
│   ├── chicken_burger.json  # sample recipe with 8 quick shots
│   └── chicken_burger_3d.json  # the Blender film: 10 shots, 26 s
├── output/
│   ├── clips/               # raw clips and edited 1080x1920 shots
│   └── final/               # finished videos and caption files
├── .env.example             # copy to .env; API keys go there, never in code
└── requirements.txt
```

## Setup

1. Python 3.9 or newer, then `pip install -r requirements.txt`.
2. ffmpeg 5 or newer on your PATH: `brew install ffmpeg` (macOS),
   `sudo apt install ffmpeg` (Ubuntu/Debian) or `winget install ffmpeg` (Windows).
3. For the 3D render: Node.js 18 or newer, then
   ```bash
   cd renderer && npm install && npx playwright install chromium
   ```
4. Copy the environment file: `cp .env.example .env`. It selects the provider
   (`VIDEO_PROVIDER=render`) and holds API keys if you use an AI provider. `.env` is
   git-ignored. Never hardcode keys in `generate.py` or commit them.

## Usage

```bash
# Print every prompt, scene, on-screen text layout and the caption. Calls nothing, writes nothing.
python generate.py smash_burger --dry-run

# Render the video (local 3D render by default).
python generate.py smash_burger

# Generative AI clips instead (needs FAL_KEY in .env).
python generate.py smash_burger --provider fal --music path/to/licensed_track.mp3

# Free offline test of the edit (test-pattern clips, written to output/test/).
python generate.py smash_burger --provider placeholder
```

The recipe argument is a name in `recipes/` or a path to any recipe JSON.

| Option | What it does |
| --- | --- |
| `--dry-run` | Print prompts, scenes, text layout and caption without calling anything or writing files. |
| `--provider NAME` | `render`, `blender`, `fal` or `placeholder`. Defaults to `VIDEO_PROVIDER` in `.env`. |
| `--music FILE` | Your own soundtrack, looped if shorter than the video and faded out at the end. |
| `--no-music` | Skip the music bed the render provider adds when no `--music` is given. |
| `--music-volume 0-1` | Soundtrack level. Defaults to 1.0 for the render music bed and your own track over silent clips, 0.35 under clip audio. |
| `--mute-clips` | Drop the audio that came with the clips. |
| `--text-position` | `top` (default), `center` or `bottom` of the safe zone. |
| `--text-style` | `animated` (default): captions pop in line by line, words appear one after another, `*emphasis*` is highlighted. `static`: plain text. |
| `--transition` | `auto` (default, a varied set of whips, zooms and wipes), `cut`, or any ffmpeg xfade name such as `smoothleft` or `zoomin`. |
| `--transition-seconds` | Length of each transition (default 0.25). The video's total length doesn't change. |
| `--font FILE` | Bold `.ttf`/`.otf` for on-screen text. Also settable as `FONT_FILE` in `.env`. |
| `--regen-ref` | Make `output/character_ref.png` again even if it exists. |
| `--force` | Make clips again even when a cached clip matches. |
| `--retries N` | Attempts per API call for temporary errors (default 4). |

### Caching and resuming

Each raw clip is saved under a name derived from its provider, prompt, scene, length
and the reference image (and, for the render provider, the renderer's source code). A
rerun reuses every clip whose inputs did not change. If a run fails or you stop it,
rerunning picks up at the shot that failed. The ffmpeg edit always reruns, since it is
fast.

## Recipe format

```json
{
  "title": "Crispy Double Smash Burger",
  "hook": "The smash burger that beats takeout",
  "shots": [
    { "seconds": 3.5, "scene": "burger_hero", "visual_prompt": "Hero close-up of the finished burger ...", "on_screen_text": "Ready in 10 minutes" },
    { "seconds": 4,   "scene": "chop_onion",  "visual_prompt": "Chef Whiskers dices an onion ...",          "on_screen_text": "Dice half an onion super fine" }
  ],
  "caption": "The full recipe: ingredients and steps ...",
  "hashtags": ["#smashburger", "#easyrecipe"]
}
```

- **hook**: shown big over the first shot. Make the first shot the finished dish.
- **shots**: aim for about 20 s in total; quick 2–3 s shots feel snappier. `on_screen_text`
  should be short (under ~45 characters) so it can be read in a few seconds; it may be
  empty. Wrap words in asterisks to highlight them, for example `"Fry at *350°F*"`
  (also works in `hook`).
  - `scene` picks the animation for the render provider (see below). AI providers ignore it.
  - `visual_prompt` is what AI providers generate from; the character description is
    added automatically. The render provider ignores it.
- **caption**: put the complete, real recipe here (quantities, times, temperatures),
  since the video only has room for highlights.
- **hashtags**: a `#` is added if missing.

The script validates the file before rendering or spending credits, and lists every
problem it finds.

## Local 3D render provider

`providers/render.py` drives `renderer/`:

- `main.js` builds Chef Whiskers from 3D shapes: shell-textured fur with tabby stripes
  and cream markings, big amber eyes with eyelids and catchlights, ears, whiskers, the
  white-tipped tail, the small tilted chef hat and the red apron with a paw-print
  pocket. It also builds the kitchen and the food: buns, smash patties that morph
  from a raw ball to a lacy patty and brown as they cook, melting cheese, onion,
  pickles, the skillet, knife and spatula, plus steam, smoke, spatter and sparkles.
  The paws are posed with 2-bone IK onto the tools.
- Every frame is a pure function of the scene and the time, so `render.js` can render
  any frame range. It renders each frame in headless Chromium (software WebGL), with
  depth of field, and pipes the frames into ffmpeg.
- `audio.py` synthesizes each clip's sound from cues the scene exports (chops,
  sizzle, the smash, the bite, a happy "mrrp") and a cozy music bed for the whole
  video, all with numpy. No samples, so there is nothing to license.

Available scenes:

| Dish | Scenes |
| --- | --- |
| Smash burger (`main.js`) | `burger_hero`, `chop_onion`, `smash_patty`, `cheese_melt`, `stack_and_bite` |
| Chicken burger (`chicken.js`) | `chick_tease`, `chick_montage`, `chick_hero`, `chick_brine`, `chick_dredge`, `chick_fry`, `chick_golden`, `chick_sauce`, `chick_stack`, `chick_bite` |

`ref` is the pose used for `output/character_ref.png`.

The chicken burger opens with a hook built for the first seconds of a TikTok:
- `chick_tease` is a cold open that shows the payoff first: the bite at 0.2 s, a CRUNCH!
  burst, crumbs flying at the lens in slow motion, and a "SOUND ON" sticker.
- `chick_montage` is three hits in 1.5 s, each opened by a white flash.
- `chick_hero` has the cat wave and wink at the camera before the steps begin.

The chicken scenes also add more
cat-and-food action (tossing, flipping, tongs, a squeeze bottle, a sneeze from the
flour), squash-and-stretch, camera punches and shakes, and 2D motion graphics from
`fx2d.js` drawn over the 3D: impact rings and action lines, speed lines, comic bursts,
light rays, and stickers such as "350°F" with a thermometer icon.

A new dish needs its own scene module. Copy `chicken.js` as a template, register it in
`main.js` the same way (`Object.assign(SCENES, yourScenes(kit))`), and give each scene a
`setup()`, an `update(t, duration)` and an `events(duration)` for the sound. Preview
frames with `node render.js stills <scene> <seconds> <outdir> 0.5 2.0`.

**Render time.** Software rendering takes about 4–8 s per frame on 4 CPU cores
depending on the scene, so a 20-second video at 30 fps takes roughly 40–80 minutes. Rendering happens once: clips are
cached until the renderer's code changes. `RENDER_WORKERS=2` in `.env` splits each
clip across parallel browser processes, which helps only on machines with many cores.

## Blender provider

`providers/blender.py` renders `recipes/chicken_burger_3d.json` as a food-only 3D film in
Blender 4.2 or newer (tested with 5.2), with Cycles:

```bash
python generate.py chicken_burger_3d --provider blender
```

The ten shots in `blender/shots.py`, in recipe order:

| Scene | What happens |
| --- | --- |
| `b_intro` | The finished burger floats and spins while the camera pushes in. |
| `b_ingredients` | Chicken, flour, seasoning, sauce, lettuce, cheese and buns fly in, each with a 3D label. |
| `b_season` | Spices rain onto the raw chicken and stick. |
| `b_dip` | Buttermilk dip with a splash and drips. |
| `b_coat` | Flour puffs up, flakes stick and the crust forms. |
| `b_fry` | Macro shot in the oil: bubbles, spits, steam, the crust turning golden. |
| `b_crisp` | Out of the oil, probe thermometer, a 165°F / 74°C tag. |
| `b_assemble` | Bun, sauce swirl, lettuce, chicken, melting cheese and the top bun land in turn. |
| `b_exploded` | The layers float apart with labels while the camera orbits, then snap back. |
| `b_reveal` | Hero spin with the 3D title THE ULTIMATE CRISPY CHICKEN BURGER. |

How it is built:
- `lib.py` models everything from code: lathed buns with a glossy gradient crust, a
  chicken thigh whose "crust" shape key grows a ridged, craggy coating, cupped and
  ruffled lettuce, cheese with a "melt" shape key, a sauce swirl that draws itself
  along a curve, bowls, a pot, and oil and buttermilk that ripple with a Wave modifier.
  The chicken's material blends from raw to wet, floured and fried.
- Particles (flour flakes, spices, oil bubbles, crumbs, drops, dust) are geometry-node
  instances on points, moved by a small ballistic simulation in Python. Steam and flour
  clouds are camera-facing sprites. Labels are extruded 3D text on rounded plates with
  leader lines.
- Each frame is a pure function of the time, so any frame can be rendered alone, and
  finished frames in `output/blender_frames/` are skipped when you run again: an
  interrupted render picks up where it stopped. Sound comes from the same `audio.py`
  as the render provider.

**Setup.** Either install the Blender app and put `blender` on your PATH, or
`pip install bpy` (the Blender Python module; it has wheels only for the Python version
that Blender bundles, such as 3.13 for Blender 5.x) and set `BLENDER_PYTHON` in `.env`
to that Python. Without a GPU it renders on the CPU.

**Render time.** At the defaults (`BLENDER_SCALE=75`, i.e. 810x1440 upscaled to 1080x1920,
and `BLENDER_SAMPLES=12` with denoising) a frame takes about 20–40 s on 4 CPU cores, so
the 26-second film (780 frames) takes 5–8 hours. A GPU is much faster. For a quick look,
render single frames:

```bash
cd blender
python render_shot.py b_fry 3.0 /tmp/fry --only 45 --preview   # one rough frame
python render_shot.py b_fry 3.0 /tmp/fry --only 45              # full quality
python render_shot.py b_fry 3.0 /tmp/fry --save-blend fry.blend # open the shot in Blender
```

## fal.ai provider

`providers/fal.py` sends everything through [fal.ai](https://fal.ai), so one
`FAL_KEY` covers both calls:

| Call | Default model | What is sent |
| --- | --- | --- |
| Character reference | `fal-ai/flux-pro/v1.1-ultra` | the reference prompt, 9:16, PNG |
| Each shot | `fal-ai/vidu/q2/reference-to-video` | the full shot prompt, `character_ref.png` as a reference image, 9:16, the shot length rounded up |

The reference image is uploaded to fal's storage once per run. Vidu Q2 uses it as a
*reference* for the character, not as the first frame, so each shot can open on its
own composition. The script shows each job's progress (queued, then generating) and
polls the same job through network drops, so a flaky connection doesn't make you pay
for a clip twice. If a model rejects a clip length, the script retries once with the
model's default length and the edit trims or extends the clip.

**Cost.** fal bills per image and per second of video; check current prices on each
model's page on fal.ai. A run makes the reference image (first run only) plus one
clip per shot. Cached clips are not generated or paid for again.

**Other models.** Set `FAL_IMAGE_MODEL` or `FAL_VIDEO_MODEL` in `.env`. A model
works without code changes if it takes the same fields: `prompt` and `aspect_ratio`,
plus `reference_image_urls` and `duration` for video. Add any extra fields a model
needs as JSON, for example `FAL_VIDEO_ARGS={"resolution": "1080p"}`. A model with a
different input schema needs a few lines in `providers/fal.py`.

For AI clips, `prompts/character.txt` fixes Chef Whiskers' design in words and is
prepended to every shot prompt, and `output/character_ref.png` is generated once from
`prompts/character_reference.txt`. Look at that image before generating clips: if it
is off, use `--regen-ref`, or drop in your own `output/character_ref.png`.

## The edit

For every shot, ffmpeg:

1. scales the clip to cover 1080x1920 and center-crops the overflow,
2. trims it to the shot's `seconds`, or holds the last frame if the clip is shorter,
3. burns in the captions in large bold type with a black outline, centered in TikTok's
   safe zone (240 px from the top, 480 px from the bottom, 60 px from the left and
   140 px from the right, clear of the app's buttons and caption). Animated captions are
   rendered as ASS subtitles by libass: each line pops in with an overshoot and slides
   up, its words appear one by one, and `*emphasized*` words turn yellow. Captions on
   later shots wait for the transition to finish. If your ffmpeg lacks libass, the
   script falls back to static text and says so.
4. normalizes audio, adding a silent track if the clip has none.

It then joins the shots with short transitions (or hard cuts), crossfading the audio,
mixes in the soundtrack, and writes
`output/final/<recipe>.mp4` (H.264/AAC, 30 fps) plus `output/final/<recipe>.txt`
with the caption and hashtags ready to paste.

The default font is a system bold sans (DejaVu Sans Bold, Liberation Sans Bold or
Arial Bold). For a more TikTok-like look, download a free bold font such as
Montserrat ExtraBold or Poppins Bold and set `FONT_FILE`. Emoji do not render in
burned-in text with these fonts; keep emoji in the caption.

## Plugging in another provider

The pipeline talks to clip makers only through `providers/base.py`:

```python
class Provider(ABC):
    name = "myprovider"            # used with --provider / VIDEO_PROVIDER
    max_prompt_chars = None        # set if the API limits prompt length
    ai_generated = True            # False for non-AI renderers (affects the posting reminder)

    def generate_image(self, prompt: str) -> bytes: ...
    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0, scene: str | None = None) -> bytes: ...
```

1. Create `providers/myprovider.py` with a subclass that implements both methods and
   returns the image or MP4 bytes. Read keys with `self.require_env("MY_API_KEY")`,
   which gives a clear error if one is missing.
2. Add one line to `PROVIDERS` in `providers/__init__.py`:
   `"myprovider": "myprovider:MyProvider"`.
3. Add the key name to `.env.example` and any SDK to `requirements.txt`.

Error contract: raise `TransientProviderError` for rate limits, timeouts and 5xx
responses (pass `retry_after=` if the API says how long to wait) and `ProviderError`
for anything retrying will not fix, such as a rejected prompt. `with_retries` backs off
exponentially with jitter. Plain `urllib` HTTP errors are classified automatically.

Ask an AI provider for **9:16** output, and send `ref_image` as the model's character
or subject reference if it has one, so clips don't all open on the reference pose.

## Before you post

- **Label AI-generated videos.** If the clips came from an AI provider such as `fal`,
  turn on TikTok's **AI-generated content** setting when posting (on the post screen,
  under *More options*; the exact wording can vary by app version). TikTok requires
  this label for realistic AI-generated content. Videos from the local `render`
  and `blender` providers are scripted 3D animation, not generative AI, so the label does
  not apply to them.
- **Use only real, working recipes.** Cook the recipe yourself before you post it. The
  quantities, times and temperatures in the caption and on-screen text must be ones
  that actually work, and must match what the video shows. Animation and AI video can
  both show impossible things, such as cheese melting in a second, so watch the whole
  video and reword the text if the visuals mislead.
- **Music**: the render provider's music bed is synthesized and yours to use. With
  `--music`, use a track you have rights to, or skip it and add a sound from
  TikTok's library in the app.
- **Originality**: Chef Whiskers must stay an original character. If you change the
  design or the prompts, check for resemblance to existing cartoon cats (no boots,
  feathered hats or swords, and no lasagna gags), and never put an existing
  character's name in a prompt.

## Troubleshooting

| Message | Fix |
| --- | --- |
| `ffmpeg and ffprobe not found` | Install ffmpeg (see Setup) and reopen the terminal. |
| `Node.js was not found` / `renderer is not installed` | Install Node.js 18+, then run `cd renderer && npm install && npx playwright install chromium`. |
| `Blender was not found` | Install Blender and put `blender` on your PATH, or `pip install bpy` and set `BLENDER_PYTHON` (see [Blender provider](#blender-provider)). |
| `needs a package that is not installed` | Run `pip install -r requirements.txt`. |
| `needs a "scene" on every shot` | Add a `scene` to each shot (see the render provider section), or use an AI provider. |
| `No provider selected` | Set `VIDEO_PROVIDER` in `.env` or pass `--provider`. |
| `... is not set` / `still has the placeholder value` | Put your real key in `.env`. |
| `HTTP 401` / `HTTP 403` | The key is wrong, or the fal account is out of credits. |
| `HTTP 422` | fal rejected the request. The message names the field, or says the prompt was flagged; reword the shot's `visual_prompt` or fix the field in `FAL_VIDEO_ARGS`. |
| `failed after 4 attempts` | The service is busy or rate-limiting you. Wait and rerun; finished clips are kept. |
| `No bold font found` | Pass `--font path/to/Bold.ttf` or set `FONT_FILE`. |
| `shot N is landscape` | The provider returned 16:9. Request 9:16 in the provider code. |
