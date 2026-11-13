# Rizz Island 🌴

A pipeline that makes episodes of an animated TikTok reality show: absurd
brain rot creatures in a villa, coupling up, causing drama and getting voted
off by the comments. Output is 1080x1920, 30 fps H.264 + AAC, 65–80 s.

> **Status: steps 1–3 of 7.** Cast, placeholder art, art pipeline, voices,
> image prompts and the script writer work. Rendering and voting come next,
> and this README will grow with them.

## Setup

```bash
cd rizz-island
pip install -r requirements.txt     # plus ffmpeg on your PATH
python rizz_island.py --check       # shows anything missing (--install fixes Python packages)
export ANTHROPIC_API_KEY=...        # needed to write scripts (Claude API)
```

Piper voice models download automatically into `voices/` on first use.

## Commands so far

| command | what it does |
|---|---|
| `python rizz_island.py --art` | processes character art (or draws placeholders), writes `review/cast_sheet.jpg` and `review/lineup.jpg` |
| `python rizz_island.py --art --force` | rebuilds every sprite from scratch |
| `python rizz_island.py --auditions` | `review/auditions.mp3`: the narrator introduces each character, who says their catchphrase |
| `python rizz_island.py --prompts` | rewrites `image_prompts.md` from `cast.json` (do this after adding a bombshell) |
| `python rizz_island.py --script-only` | writes the next episode to `episodes/epNN/script.json` (+ a readable `script.md`) and stops so you can edit it |
| `... --script-only --brief "Discotto falls in the pool"` | same, with a note for the writer |
| `... --script-only --dry-run` | writes the prompt and JSON schema without calling Claude |
| `python rizz_island.py --new-season` | archives the current season to `seasons/` and resets `season_state.json` |

## Adding character art

Save images as `characters/<id>/<expression>.png`. The expressions are
`neutral`, `talking`, `shocked`, `angry`, `smug`, `in_love`, plus an optional
`blink`. Details are in [`characters/README.md`](characters/README.md). Then run
`python rizz_island.py --art`: backgrounds are removed with rembg, sprites are
trimmed and scaled to a shared body height, and the contact sheet shows the
result.

## Scripts

The writer sends Claude (`claude-opus-5-5`) the story bible, the full season
state (couples, rivalries, running jokes, eliminations, episode log) and the
latest vote result, and gets back JSON in a fixed schema: cold open, vote
result, "previously on", dialogue scenes and confessionals with an expression,
caption emphasis, camera move, effect, sound effect and reaction for every line,
the twist, the vote options and continuity updates. The pipeline then checks the
draft (estimated 65–80 s, everyone gets a line, PG wording, nobody speaks after
being dumped, valid couples) and sends any problems back for a fix.
`script.json` is the source of truth: edit it freely before rendering.
`season_state.json` only advances when an episode is fully rendered.

## Voices

Each character's `voice` in `cast.json` sets the engine, voice id, pitch
(semitones) and speed. Piper is the default (free, offline). To use
ElevenLabs instead, set `ELEVENLABS_API_KEY`, fill in `elevenlabs_voice_id` for
each character, and either set `"engine": "elevenlabs"` or run with
`RIZZ_TTS=elevenlabs`. Adding another provider means one class in `rizz/tts/`.

## Layout

```
cast.json          story bible: 8 characters, villa locations, storylines, running jokes
rizz_island.py     command-line entry point
rizz/              the pipeline (config, cast, placeholder_art, sprites, text, tts/, sheets, ...)
characters/        your AI character art          backgrounds/  your AI villa backgrounds
sfx/               royalty-free sound effects     music/        royalty-free beats
episodes/epNN/     script.json, script.md, renders  tests/  python -m pytest tests -q
review/            contact sheet, lineup, auditions (for you, not TikTok)
build/             caches (safe to delete)        voices/       downloaded Piper models
```
