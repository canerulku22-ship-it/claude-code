#!/usr/bin/env python3
"""Turn a recipe JSON into a ~20 s vertical (1080x1920) TikTok starring Chef Whiskers.

  1. Load or generate the character reference image  -> output/character_ref.png
  2. Generate one clip per shot: character description + shot prompt + reference image
  3. ffmpeg: crop and scale each clip to 1080x1920, trim it to the shot length, burn in text
  4. Concatenate the clips and optionally mix in a soundtrack -> output/final/<recipe>.mp4
  5. Write the caption and hashtags                           -> output/final/<recipe>.txt

Examples:
  python generate.py smash_burger --dry-run                 # print prompts, call nothing
  python generate.py smash_burger --provider placeholder    # free offline test render
  python generate.py recipes/smash_burger.json --music track.mp3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from providers import (
    Provider,
    ProviderConfigError,
    ProviderError,
    available_providers,
    get_provider,
    get_provider_class,
    with_retries,
)

ROOT = Path(__file__).resolve().parent
RECIPES_DIR = ROOT / "recipes"
PROMPTS_DIR = ROOT / "prompts"

WIDTH, HEIGHT, FPS = 1080, 1920, 30
TARGET_SECONDS = 20
CAPTION_LIMIT = 4000  # TikTok's caption limit at the time of writing

# TikTok safe zone for a 1080x1920 frame, in px from each edge. The top clears the
# Following / For You tabs, the right the like/comment/share column, and the
# bottom the username, caption and sound ticker.
SAFE_TOP, SAFE_RIGHT, SAFE_BOTTOM, SAFE_LEFT = 240, 140, 480, 60
SAFE_W = WIDTH - SAFE_LEFT - SAFE_RIGHT
SAFE_H = HEIGHT - SAFE_TOP - SAFE_BOTTOM

HOOK_SIZE, TEXT_SIZE, MIN_TEXT_SIZE = 96, 80, 56
HOOK_COLOR, TEXT_COLOR = "0xFFD84D", "white"
MAX_LINES_PER_BLOCK = 3
CHAR_WIDTH_EM = 0.62  # conservative average glyph width of a bold sans font, for wrapping
LINE_SPACING = 1.2
TEXT_FADE_IN = 0.25  # seconds

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Debian/Ubuntu
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",  # Arch
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",  # Fedora
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


class PipelineError(Exception):
    """A problem the user can fix: bad recipe, missing file, ffmpeg failure."""


# --------------------------------------------------------------------------- recipe


@dataclass
class Shot:
    seconds: float
    visual_prompt: str
    on_screen_text: str


@dataclass
class Recipe:
    path: Path
    slug: str
    title: str
    hook: str
    shots: list[Shot]
    caption: str
    hashtags: list[str]

    @property
    def duration(self) -> float:
        return sum(s.seconds for s in self.shots)

    def caption_file_text(self) -> str:
        return f"{self.caption.strip()}\n\n{' '.join(self.hashtags)}\n"


def rel(path: Path) -> str:
    """Show paths relative to the project folder when possible."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_recipe_path(arg: str) -> Path:
    candidates = [Path(arg), ROOT / arg, RECIPES_DIR / arg, RECIPES_DIR / f"{arg}.json"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    available = ", ".join(sorted(p.stem for p in RECIPES_DIR.glob("*.json"))) or "none"
    raise PipelineError(f"Recipe not found: {arg}. Recipes in recipes/: {available}.")


def load_recipe(arg: str) -> tuple[Recipe, list[str]]:
    """Load and validate a recipe. Returns the recipe and a list of non-fatal warnings."""
    path = resolve_recipe_path(arg)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineError(
            f"{rel(path)} is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})."
        ) from exc
    if not isinstance(data, dict):
        raise PipelineError(f"{rel(path)} must contain a JSON object.")

    problems: list[str] = []

    def text(obj: dict, key: str, where: str, required: bool = True) -> str:
        value = obj.get(key)
        if not isinstance(value, str) or (required and not value.strip()):
            kind = "a non-empty string" if required else "a string (it may be empty)"
            problems.append(f'{where}"{key}" must be {kind}')
            return ""
        return value.strip()

    title = text(data, "title", "")
    hook = text(data, "hook", "")
    caption = text(data, "caption", "")

    shots: list[Shot] = []
    raw_shots = data.get("shots")
    if not isinstance(raw_shots, list) or not raw_shots:
        problems.append('"shots" must be a non-empty list')
        raw_shots = []
    for i, raw in enumerate(raw_shots, 1):
        where = f"shot {i}: "
        if not isinstance(raw, dict):
            problems.append(f"{where}must be an object with seconds, visual_prompt and on_screen_text")
            continue
        seconds = raw.get("seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 < seconds <= 15:
            problems.append(f'{where}"seconds" must be a number above 0 and at most 15 (got {seconds!r})')
            seconds = 0
        shots.append(
            Shot(
                seconds=float(seconds),
                visual_prompt=text(raw, "visual_prompt", where),
                on_screen_text=text(raw, "on_screen_text", where, required=False),
            )
        )

    hashtags: list[str] = []
    raw_tags = data.get("hashtags")
    if not isinstance(raw_tags, list) or not all(isinstance(t, str) for t in raw_tags):
        problems.append('"hashtags" must be a list of strings')
    else:
        for tag in raw_tags:
            tag = "".join(tag.split()).lstrip("#")
            if tag:
                hashtags.append(f"#{tag}")

    if problems:
        raise PipelineError(f"{rel(path)} has problems:\n  - " + "\n  - ".join(problems))

    recipe = Recipe(path, path.stem, title, hook, shots, caption, hashtags)

    warnings: list[str] = []
    if not 15 <= recipe.duration <= 25:
        warnings.append(
            f"shots add up to {recipe.duration:g} s; this format is built for about {TARGET_SECONDS} s."
        )
    for i, shot in enumerate(shots, 1):
        if len(shot.on_screen_text) > 45:
            warnings.append(f"shot {i} on-screen text is {len(shot.on_screen_text)} characters; under ~45 reads better.")
    if not hashtags:
        warnings.append("no hashtags.")
    if len(recipe.caption_file_text()) > CAPTION_LIMIT:
        warnings.append(
            f"caption plus hashtags is {len(recipe.caption_file_text())} characters; TikTok allows {CAPTION_LIMIT}."
        )
    return recipe, warnings


# --------------------------------------------------------------------------- prompts


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.is_file():
        raise PipelineError(f"Missing prompt file: {rel(path)}")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")]
    prompt = "\n".join(lines).strip()
    if not prompt:
        raise PipelineError(f"{rel(path)} is empty.")
    return prompt


def shot_prompt(character: str, shot: Shot) -> str:
    """The character description goes first so every clip starts from the same design."""
    return f"{character}\n\nShot: {shot.visual_prompt}"


# --------------------------------------------------------------------------- text layout


@dataclass
class TextLine:
    text: str
    size: int
    color: str
    y: int = 0


def wrap_block(text: str, size: int, color: str) -> list[TextLine]:
    """Wrap text to the safe-zone width, shrinking the font until it fits in a few lines."""
    text = " ".join(text.split())
    if not text:
        return []
    while True:
        max_chars = max(6, int(SAFE_W / (size * CHAR_WIDTH_EM)))
        lines = textwrap.wrap(text, max_chars, break_long_words=False, break_on_hyphens=False)
        fits = len(lines) <= MAX_LINES_PER_BLOCK and all(len(line) <= max_chars for line in lines)
        if fits or size <= MIN_TEXT_SIZE:
            return [TextLine(line, size, color) for line in lines]
        size -= 4


def text_blocks(recipe: Recipe, index: int, shot: Shot) -> list[tuple[str, int, str]]:
    """The hook goes over the first shot, above that shot's own text."""
    blocks = []
    if index == 1 and recipe.hook:
        blocks.append((recipe.hook, HOOK_SIZE, HOOK_COLOR))
    if shot.on_screen_text:
        blocks.append((shot.on_screen_text, TEXT_SIZE, TEXT_COLOR))
    return blocks


def layout_text(blocks: list[tuple[str, int, str]], position: str) -> list[TextLine]:
    """Stack wrapped blocks and place them at the top, center or bottom of the safe zone."""
    out: list[TextLine] = []
    y = 0
    for text, size, color in blocks:
        block = wrap_block(text, size, color)
        if not block:
            continue
        if out:
            y += int(block[0].size * 0.35)  # gap between the hook and the shot text
        for line in block:
            line.y = y
            out.append(line)
            y += int(line.size * LINE_SPACING)
    if not out:
        return []
    height = out[-1].y + out[-1].size
    if position == "top":
        top = SAFE_TOP + 40
    elif position == "center":
        top = SAFE_TOP + (SAFE_H - height) // 2
    else:
        top = HEIGHT - SAFE_BOTTOM - 40 - height
    for line in out:
        line.y += top
    return out


def drawtext_filters(lines: list[TextLine], font_name: str, workdir: Path, prefix: str) -> list[str]:
    """One drawtext per line, each centered in the safe zone.

    The text and font are passed as files in ``workdir`` (ffmpeg runs there) so
    quotes, colons and % signs in the text need no filter escaping.
    """
    filters = []
    for i, line in enumerate(lines):
        textfile = f"{prefix}_line{i}.txt"
        (workdir / textfile).write_text(line.text, encoding="utf-8")
        filters.append(
            "drawtext="
            f"fontfile={font_name}:textfile={textfile}:expansion=none:"
            f"fontsize={line.size}:fontcolor={line.color}:"
            f"borderw={max(4, line.size // 11)}:bordercolor=black:"
            "shadowcolor=black@0.45:shadowx=0:shadowy=6:"
            f"x={SAFE_LEFT}+({SAFE_W}-text_w)/2:y={line.y}:"
            f"alpha='min(1,t/{TEXT_FADE_IN})'"
        )
    return filters


# --------------------------------------------------------------------------- ffmpeg


@dataclass
class MediaInfo:
    duration: float
    width: int
    height: int
    has_audio: bool


def require_ffmpeg() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise PipelineError(
            f"{' and '.join(missing)} not found on PATH. Install ffmpeg "
            "(macOS: brew install ffmpeg; Ubuntu/Debian: sudo apt install ffmpeg; "
            "Windows: winget install ffmpeg) and try again."
        )


def run_ffmpeg(args: list[str], *, what: str, cwd: Optional[Path] = None) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise PipelineError(f"ffmpeg failed while {what}:\n{tail}")


def probe(path: Path) -> MediaInfo:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", str(path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise PipelineError(f"{rel(path)} is not a readable video: {proc.stderr.strip()}")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise PipelineError(f"{rel(path)} has no video stream.")
    return MediaInfo(
        duration=float(data.get("format", {}).get("duration") or 0),
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
    )


def save_image_as_png(data: bytes, dest: Path) -> None:
    if not data:
        raise ProviderError("the provider returned an empty image.")
    tmp = dest.with_name(dest.stem + ".partial.png")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        tmp.write_bytes(data)
    else:  # JPEG/WebP etc.: convert so the file really is a PNG
        download = dest.with_name(dest.stem + ".download")
        download.write_bytes(data)
        try:
            run_ffmpeg(["-i", str(download), "-frames:v", "1", str(tmp)],
                       what="converting the reference image to PNG")
        finally:
            download.unlink(missing_ok=True)
    tmp.replace(dest)


def save_clip(data: bytes, dest: Path, what: str) -> MediaInfo:
    """Write a downloaded clip, keeping it only if ffprobe can read it as a video."""
    tmp = dest.with_suffix(".partial.mp4")
    tmp.write_bytes(data)
    try:
        info = probe(tmp)
    except PipelineError as exc:
        tmp.unlink(missing_ok=True)
        raise ProviderError(f"{what}: the provider returned {len(data)} bytes that are not a playable video.") from exc
    tmp.replace(dest)
    return info


def render_shot(src: Path, dst: Path, seconds: float, lines: list[TextLine], font_name: str,
                workdir: Path, prefix: str, keep_audio: bool) -> None:
    """Crop and scale to 1080x1920, set the exact shot length, burn in text, normalize audio."""
    info = probe(src)
    vf = [
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={WIDTH}:{HEIGHT}",
        "setsar=1",
        f"fps={FPS}",
        f"tpad=stop_mode=clone:stop_duration={seconds}",  # hold the last frame if the clip is short
        *drawtext_filters(lines, font_name, workdir, prefix),
        "format=yuv420p",
    ]
    args = ["-i", str(src.resolve())]
    if keep_audio and info.has_audio:
        audio = ["-map", "0:a:0", "-af", "aresample=48000,aformat=channel_layouts=stereo,apad"]
    else:  # silent track, so every clip has the same streams for the concat
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        audio = ["-map", "1:a:0"]
    args += [
        "-map", "0:v:0", *audio,
        "-vf", ",".join(vf),
        "-t", f"{seconds:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(dst.resolve()),
    ]
    run_ffmpeg(args, what=f"rendering {rel(dst)}", cwd=workdir)


def assemble(clips: list[Path], dest: Path, total: float, music: Optional[Path], music_volume: float) -> None:
    """Concatenate the rendered shots and optionally mix a soundtrack under them."""
    args: list[str] = []
    for clip in clips:
        args += ["-i", str(clip.resolve())]
    n = len(clips)
    graph = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    audio_out = "[a]"
    if music:
        args += ["-stream_loop", "-1", "-i", str(music.resolve())]  # loop a short track
        fade_out = max(0.0, total - 1.5)
        graph += (
            f";[{n}:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={music_volume},"
            f"afade=t=in:d=0.5,afade=t=out:st={fade_out:.3f}:d=1.5[m]"
            ";[a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]"
        )
        audio_out = "[mix]"
    tmp = dest.with_suffix(".partial.mp4")
    args += [
        "-filter_complex", graph, "-map", "[v]", "-map", audio_out,
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(tmp.resolve()),
    ]
    run_ffmpeg(args, what="assembling the final video")
    tmp.replace(dest)


# --------------------------------------------------------------------------- setup helpers


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=value lines). Real environment variables win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if value[:1] in "\"'" and value[-1:] == value[:1] and len(value) >= 2:
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        os.environ.setdefault(key, value)


def find_font(explicit: Optional[Path]) -> Optional[Path]:
    configured = explicit or (Path(os.environ["FONT_FILE"]) if os.environ.get("FONT_FILE", "").strip() else None)
    if configured:
        path = configured.expanduser()
        if not path.is_absolute() and not path.is_file():
            path = ROOT / path
        if not path.is_file():
            raise PipelineError(f"Font file not found: {configured} (from --font or FONT_FILE).")
        return path
    return next((Path(c) for c in FONT_CANDIDATES if Path(c).is_file()), None)


@dataclass
class OutputPaths:
    root: Path
    slug: str

    @property
    def character_ref(self) -> Path:
        return self.root / "character_ref.png"

    @property
    def clips(self) -> Path:
        return self.root / "clips" / self.slug

    @property
    def final_video(self) -> Path:
        return self.root / "final" / f"{self.slug}.mp4"

    @property
    def caption(self) -> Path:
        return self.root / "final" / f"{self.slug}.txt"


def output_paths(slug: str, test: bool) -> OutputPaths:
    return OutputPaths(ROOT / "output" / "test" if test else ROOT / "output", slug)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_clip_path(paths: OutputPaths, index: int, provider: str, prompt: str, seconds: float, ref_hash: str) -> Path:
    """Cache key: changing the prompt, length, provider or reference image regenerates the clip."""
    key = hashlib.sha256(json.dumps([provider, prompt, seconds, ref_hash]).encode()).hexdigest()[:10]
    return paths.clips / f"shot{index:02d}_raw_{key}.mp4"


# --------------------------------------------------------------------------- commands


def print_header(title: str) -> None:
    print(f"\n--- {title} " + "-" * max(3, 76 - len(title)))


def dry_run(recipe: Recipe, character: str, ref_prompt: str, provider_name: str,
            font: Optional[Path], args: argparse.Namespace) -> None:
    provider_cls: Optional[type[Provider]] = None
    provider_note = "(not called in a dry run)"
    if not provider_name:
        provider_note = "(none set: pass --provider or set VIDEO_PROVIDER in .env)"
    else:
        try:
            provider_cls = get_provider_class(provider_name)
        except ProviderError as exc:
            provider_note = f"(problem: {exc})"
    paths = output_paths(recipe.slug, bool(provider_cls and provider_cls.is_test_provider))
    max_chars = provider_cls.max_prompt_chars if provider_cls else None

    def prompt_stats(prompt: str) -> str:
        over = f", OVER the provider's {max_chars} limit" if max_chars and len(prompt) > max_chars else ""
        return f"{len(prompt)} chars{over}"

    print("=== Chef Whiskers: DRY RUN (no API calls, no files written) ===")
    print(f"Recipe    {rel(recipe.path)}  \"{recipe.title}\"")
    print(f"Length    {len(recipe.shots)} shots, {recipe.duration:g} s at {WIDTH}x{HEIGHT}, {FPS} fps")
    print(f"Provider  {provider_name or '-'} {provider_note}")
    if provider_cls and provider_cls.describe():
        print(f"          {provider_cls.describe()}")
    print(f"Font      {font or 'NOT FOUND: pass --font or set FONT_FILE'}")
    print(f"Music     {args.music or 'none (add one with --music, or pick a sound in the TikTok app)'}")
    print(f"Output    {rel(paths.final_video)} and {rel(paths.caption)}")

    ref = paths.character_ref
    state = "exists, will be reused" if ref.is_file() and not args.regen_ref else "will be generated"
    print_header(f"Character reference -> {rel(ref)} ({state})")
    print(f"generate_image(prompt)  [{prompt_stats(ref_prompt)}]\n")
    print(ref_prompt)

    for i, shot in enumerate(recipe.shots, 1):
        prompt = shot_prompt(character, shot)
        print_header(f"Shot {i}/{len(recipe.shots)}  {shot.seconds:g} s")
        print(f"generate_video(prompt, ref_image={rel(ref)}, duration={shot.seconds:g})  [{prompt_stats(prompt)}]\n")
        print(prompt)
        lines = layout_text(text_blocks(recipe, i, shot), args.text_position)
        print(f"\nOn-screen text ({args.text_position} of safe zone):")
        for line in lines or [TextLine("(none)", 0, "")]:
            label = "hook" if line.color == HOOK_COLOR else "text"
            print(f"  {label} {line.size}px y={line.y:<4}  {line.text}" if line.size else f"  {line.text}")

    caption = recipe.caption_file_text()
    print_header(f"Caption -> {rel(paths.caption)} ({len(caption)} chars)")
    print(caption)
    print("Dry run complete. Next, a free offline test render of the edit:")
    print(f"  python generate.py {recipe.slug} --provider placeholder")


def run(recipe: Recipe, character: str, ref_prompt: str, provider_name: str,
        font: Optional[Path], args: argparse.Namespace) -> None:
    # Check everything local before spending any API credits.
    require_ffmpeg()
    if font is None:
        raise PipelineError("No bold font found for the on-screen text. Pass --font path/to/Bold.ttf or set FONT_FILE in .env.")
    if args.music and not args.music.is_file():
        raise PipelineError(f"Soundtrack not found: {args.music}")
    provider = get_provider(provider_name)
    paths = output_paths(recipe.slug, provider.is_test_provider)
    paths.clips.mkdir(parents=True, exist_ok=True)
    paths.final_video.parent.mkdir(parents=True, exist_ok=True)

    print(f"Chef Whiskers: \"{recipe.title}\", {len(recipe.shots)} shots, {recipe.duration:g} s, provider '{provider.name}'")
    if provider.is_test_provider:
        print("  (test provider: makes test-pattern media in output/test/, not for posting)")

    def call(fn, what):
        return with_retries(fn, what=what, attempts=args.retries)

    def check_prompt(prompt: str, what: str) -> None:
        if provider.max_prompt_chars and len(prompt) > provider.max_prompt_chars:
            raise PipelineError(
                f"{what} prompt is {len(prompt)} characters; {provider.name} accepts at most "
                f"{provider.max_prompt_chars}. Shorten prompts/character.txt or the shot's visual_prompt."
            )

    # 1. Character reference image
    ref = paths.character_ref
    if ref.is_file() and not args.regen_ref:
        print(f"[ref] using existing {rel(ref)}")
    else:
        check_prompt(ref_prompt, "character reference")
        print(f"[ref] generating character reference -> {rel(ref)}")
        save_image_as_png(call(lambda: provider.generate_image(ref_prompt), "character reference image"), ref)
    ref_hash = file_sha256(ref)

    # 2. One clip per shot (cached, so a rerun only regenerates what changed)
    raw_clips: list[Path] = []
    total = len(recipe.shots)
    for i, shot in enumerate(recipe.shots, 1):
        prompt = shot_prompt(character, shot)
        check_prompt(prompt, f"shot {i}")
        dest = raw_clip_path(paths, i, provider.name, prompt, shot.seconds, ref_hash)
        if dest.is_file() and not args.force:
            print(f"[{i}/{total}] cached {rel(dest)}")
        else:
            print(f"[{i}/{total}] generating {shot.seconds:g} s clip ...")
            data = call(lambda: provider.generate_video(prompt, ref, duration=shot.seconds), f"shot {i} video")
            save_clip(data, dest, f"shot {i}")
            print(f"[{i}/{total}] saved {rel(dest)}")
        info = probe(dest)
        if info.width > info.height:
            print(f"  ! shot {i} is landscape ({info.width}x{info.height}); center-cropping to 9:16 loses the sides. Request 9:16 from the provider.")
        if info.duration and info.duration + 0.05 < shot.seconds:
            print(f"  ! shot {i} clip is {info.duration:.1f} s; holding its last frame to fill {shot.seconds:g} s.")
        raw_clips.append(dest)

    keep_audio = not args.mute_clips and any(probe(c).has_audio for c in raw_clips)
    music_volume = args.music_volume if args.music_volume is not None else (0.35 if keep_audio else 1.0)

    # 3-4. Edit: crop/scale, text, concat, soundtrack
    with tempfile.TemporaryDirectory(prefix="chef_whiskers_") as tmp:
        workdir = Path(tmp)
        font_name = "font" + font.suffix.lower()
        shutil.copyfile(font, workdir / font_name)
        rendered = []
        for i, (shot, raw) in enumerate(zip(recipe.shots, raw_clips), 1):
            dst = paths.clips / f"shot{i:02d}_{WIDTH}x{HEIGHT}.mp4"
            lines = layout_text(text_blocks(recipe, i, shot), args.text_position)
            render_shot(raw, dst, shot.seconds, lines, font_name, workdir, f"s{i:02d}", keep_audio)
            print(f"[edit] {rel(dst)}")
            rendered.append(dst)
        assemble(rendered, paths.final_video, recipe.duration, args.music, music_volume)

    # 5. Caption
    paths.caption.write_text(recipe.caption_file_text(), encoding="utf-8")

    final = probe(paths.final_video)
    print(f"\nDone: {rel(paths.final_video)} ({final.width}x{final.height}, {final.duration:.1f} s)")
    print(f"      {rel(paths.caption)} (caption and hashtags)")
    print("Before posting: watch every clip, and turn on TikTok's 'AI-generated content' label when you post.")


def parse_args(argv: Optional[list[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn a recipe JSON into a ~20 s vertical TikTok starring Chef Whiskers.",
        epilog="Examples:\n"
               "  python generate.py smash_burger --dry-run\n"
               "  python generate.py smash_burger --provider placeholder\n"
               "  python generate.py recipes/smash_burger.json --music track.mp3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("recipe", help="recipe name in recipes/ (e.g. smash_burger) or a path to a recipe JSON")
    parser.add_argument("--dry-run", action="store_true",
                        help="print every prompt, the on-screen text and the caption; call no API and write no files")
    parser.add_argument("--provider",
                        help=f"generation provider (default: VIDEO_PROVIDER from .env). Available: {', '.join(available_providers())}")
    parser.add_argument("--music", type=Path, help="optional soundtrack (mp3/wav/m4a), looped if shorter than the video")
    parser.add_argument("--music-volume", type=float, default=None,
                        help="soundtrack volume, 0-1 (default: 0.35 under clip audio, 1.0 if the clips are silent)")
    parser.add_argument("--mute-clips", action="store_true", help="drop any audio the provider generated with the clips")
    parser.add_argument("--text-position", choices=["top", "center", "bottom"], default="top",
                        help="where on-screen text sits inside the safe zone (default: top)")
    parser.add_argument("--font", type=Path, help="bold .ttf/.otf for on-screen text (default: FONT_FILE or a system bold font)")
    parser.add_argument("--regen-ref", action="store_true", help="regenerate output/character_ref.png even if it exists")
    parser.add_argument("--force", action="store_true", help="regenerate clips even when a cached clip matches")
    parser.add_argument("--retries", type=int, default=4, help="attempts per API call for temporary errors (default: 4)")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    load_dotenv(ROOT / ".env")
    try:
        recipe, warnings = load_recipe(args.recipe)
        character = load_prompt("character.txt")
        ref_prompt = load_prompt("character_reference.txt").replace("{character}", character)
        provider_name = (args.provider or os.environ.get("VIDEO_PROVIDER", "")).strip()
        font = find_font(args.font)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if args.dry_run:
            dry_run(recipe, character, ref_prompt, provider_name, font, args)
        else:
            run(recipe, character, ref_prompt, provider_name, font, args)
        return 0
    except ProviderConfigError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1
    except ProviderError as exc:
        print(f"\nerror: {exc}\nClips that finished are cached, so rerunning resumes from the failed shot.", file=sys.stderr)
        return 1
    except PipelineError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Finished clips are cached, so rerunning resumes where this stopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
