# Chef Whiskers

Turns a recipe JSON file into a ~20-second vertical (1080x1920) TikTok starring
**Chef Whiskers**: an original, 3D-animated orange tabby cat chef in a small white
chef hat and red apron, cooking hyper-realistic food in a cozy modern kitchen. It
suits a faceless channel: no human appears on camera.

```
recipe JSON ──► character reference image ──► one AI clip per shot ──► ffmpeg edit ──► MP4 + caption
                output/character_ref.png       output/clips/<recipe>/     crop, text,    output/final/<recipe>.mp4
                                                                          concat, music  output/final/<recipe>.txt
```

## Project layout

```
chef-whiskers/
├── generate.py              # the pipeline (run this)
├── providers/               # swappable AI providers
│   ├── base.py              # Provider interface, errors, retry logic
│   ├── __init__.py          # provider registry
│   └── placeholder.py       # offline test provider (test patterns, no API)
├── prompts/
│   ├── character.txt        # Chef Whiskers description, prepended to every shot
│   └── character_reference.txt  # prompt for the one-time reference image
├── recipes/
│   └── smash_burger.json    # sample recipe
├── output/
│   ├── clips/               # raw AI clips and edited 1080x1920 shots
│   └── final/               # finished videos and caption files
├── .env.example             # copy to .env; API keys go there, never in code
└── requirements.txt
```

## Setup

1. Python 3.9 or newer.
2. ffmpeg 5 or newer on your PATH: `brew install ffmpeg` (macOS),
   `sudo apt install ffmpeg` (Ubuntu/Debian) or `winget install ffmpeg` (Windows).
3. Copy the environment file and add the key for your provider:
   ```bash
   cp .env.example .env
   ```
   `.env` is git-ignored. Never hardcode keys in `generate.py` or commit them.

## Usage

```bash
# 1. Print every prompt, the on-screen text layout and the caption. Calls no API, writes nothing.
python generate.py smash_burger --dry-run

# 2. Free offline test of the whole edit (test-pattern clips, written to output/test/).
python generate.py smash_burger --provider placeholder

# 3. The real thing, once a provider is wired up.
python generate.py smash_burger --provider <name> --music path/to/licensed_track.mp3
```

The recipe argument is a name in `recipes/` or a path to any recipe JSON.

| Option | What it does |
| --- | --- |
| `--dry-run` | Print prompts, text layout and caption without calling any API or writing files. |
| `--provider NAME` | Provider to use. Defaults to `VIDEO_PROVIDER` in `.env`. |
| `--music FILE` | Optional soundtrack, looped if shorter than the video and faded out at the end. |
| `--music-volume 0-1` | Soundtrack level. Defaults to 0.35 under clip audio, 1.0 if the clips are silent. |
| `--mute-clips` | Drop audio the provider generated with the clips. |
| `--text-position` | `top` (default), `center` or `bottom` of the safe zone. |
| `--font FILE` | Bold `.ttf`/`.otf` for on-screen text. Also settable as `FONT_FILE` in `.env`. |
| `--regen-ref` | Regenerate `output/character_ref.png` even if it exists. |
| `--force` | Regenerate clips even when a cached clip matches. |
| `--retries N` | Attempts per API call for temporary errors (default 4). |

### Caching and resuming

Each raw clip is saved under a name derived from its provider, prompt, length and the
reference image. A rerun reuses every clip whose inputs did not change, so you can
edit one shot's prompt and regenerate only that shot. If a run fails or you stop it,
rerunning picks up at the shot that failed. The ffmpeg edit always reruns, since it is
fast and free.

## Recipe format

```json
{
  "title": "Crispy Double Smash Burger",
  "hook": "The smash burger that beats takeout",
  "shots": [
    { "seconds": 3.5, "visual_prompt": "Hero close-up of the finished burger ...", "on_screen_text": "Ready in 10 minutes" },
    { "seconds": 4,   "visual_prompt": "Chef Whiskers dices an onion ...",          "on_screen_text": "Dice half an onion super fine" }
  ],
  "caption": "The full recipe: ingredients and steps ...",
  "hashtags": ["#smashburger", "#easyrecipe"]
}
```

- **hook**: shown big, in yellow, over the first shot. Make the first shot the finished dish.
- **shots**: aim for about 20 s in total. `visual_prompt` describes only the action and
  framing: the character description is added automatically. `on_screen_text` should be
  short (under ~45 characters) so it can be read in a few seconds; it may be empty.
- **caption**: put the complete, real recipe here (quantities, times, temperatures),
  since the video only has room for highlights.
- **hashtags**: a `#` is added if missing.

The script validates the file before spending any credits and lists every problem it finds.

## The character

`prompts/character.txt` is prepended to every shot prompt and fixes Chef Whiskers'
design: fur colors and markings, amber eyes, white-tipped tail, the tilted chef hat
and the red apron with a paw-print pocket. Change it in one place and every shot follows.

On the first real run the script generates `output/character_ref.png` from
`prompts/character_reference.txt` and passes it to every video request so the cat
looks the same in every clip. Look at that image before generating clips: if it is
off, delete it or use `--regen-ref`. You can also drop in your own
`output/character_ref.png` and the script will use it instead of generating one.

Chef Whiskers must stay an original character. Check the reference image and clips
for resemblance to existing cartoon cats (for example, no boots, feathered hats or
swords, and no lasagna gags), and never put an existing character's name in a prompt.

## The edit

For every shot, ffmpeg:

1. scales the clip to cover 1080x1920 and center-crops the overflow,
2. trims it to the shot's `seconds`, or holds the last frame if the clip is shorter,
3. burns in the text in large bold type with a black outline, centered in TikTok's
   safe zone (240 px from the top, 480 px from the bottom, 60 px from the left and
   140 px from the right, clear of the app's buttons and caption), with a quick fade-in,
4. normalizes audio, adding a silent track if the clip has none.

It then joins the shots, mixes in the optional soundtrack, and writes
`output/final/<recipe>.mp4` (H.264/AAC, 30 fps) plus `output/final/<recipe>.txt`
with the caption and hashtags ready to paste.

The default font is a system bold sans (DejaVu Sans Bold, Liberation Sans Bold or
Arial Bold). For a more TikTok-like look, download a free bold font such as
Montserrat ExtraBold or Poppins Bold and set `FONT_FILE`. Emoji do not render in
burned-in text with these fonts; keep emoji in the caption.

## Plugging in a provider

The pipeline talks to AI services only through `providers/base.py`:

```python
class Provider(ABC):
    name = "myprovider"            # used with --provider / VIDEO_PROVIDER
    max_prompt_chars = None        # set if the API limits prompt length

    def generate_image(self, prompt: str) -> bytes: ...
    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0) -> bytes: ...
```

1. Create `providers/myprovider.py` with a subclass that implements both methods and
   returns the image or MP4 bytes. Read the key with `self.require_env("MY_API_KEY")`,
   which gives a clear error if it is missing.
2. Add one line to `PROVIDERS` in `providers/__init__.py`:
   `"myprovider": "myprovider:MyProvider"`.
3. Add the key name to `.env.example` and the SDK to `requirements.txt`.

Error contract: raise `TransientProviderError` for rate limits, timeouts and 5xx
responses (pass `retry_after=` if the API says how long to wait) and `ProviderError`
for anything retrying will not fix, such as a rejected prompt. `with_retries` backs off
exponentially with jitter. Plain `urllib` HTTP errors are classified automatically.

Ask the provider for **9:16** output. For consistency, send `ref_image` as the model's
character or subject reference if it has one. If the API can only use an image as the
first frame, every clip would open on the reference pose, so prefer a model with
reference support.

## Before you post

- **Label it as AI-generated.** When posting, turn on TikTok's **AI-generated content**
  setting (on the post screen, under *More options*; the exact wording can vary by
  app version). TikTok requires this label for realistic AI-generated content, and
  labeling is the honest thing to do for this format anyway.
- **Use only real, working recipes.** Cook the recipe yourself before you post it. The
  quantities, times and temperatures in the caption and on-screen text must be ones
  that actually work, and must match what the video shows. AI video can show
  impossible things, such as cheese melting in a second or the wrong technique, so
  watch every clip and reword the text or regenerate the shot if the visuals mislead.
- **Music**: use a track you have rights to, or skip `--music` and add a sound from
  TikTok's library in the app.
- **Check the clips** for warped paws or hands, stray human hands, gibberish text,
  and food that looks unsafe or undercooked.

## Troubleshooting

| Message | Fix |
| --- | --- |
| `ffmpeg and ffprobe not found` | Install ffmpeg (see Setup) and reopen the terminal. |
| `No provider selected` | Set `VIDEO_PROVIDER` in `.env` or pass `--provider`. |
| `... is not set` / `still has the placeholder value` | Put your real key in `.env`. |
| `HTTP 401` / `HTTP 403` | The key is wrong, or the account lacks access or credits. |
| `failed after 4 attempts` | The service is busy or rate-limiting you. Wait and rerun; finished clips are kept. |
| `No bold font found` | Pass `--font path/to/Bold.ttf` or set `FONT_FILE`. |
| `shot N is landscape` | The provider returned 16:9. Request 9:16 in the provider code. |
