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
import struct
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
TEXT_FADE_IN = 0.25  # seconds (static text style)
EMPHASIS_COLOR = "0xFFD84D"  # *words* in on-screen text are highlighted in this colour
TRANSITIONS = ["fadewhite", "zoomin", "smoothleft", "smoothup", "circleopen", "smoothright", "slideleft", "radial", "smoothdown"]

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
    scene: str = ""  # pre-built animation for the local "render" provider; AI providers ignore it


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
        scene = raw.get("scene", "")
        if not isinstance(scene, str):
            problems.append(f'{where}"scene" must be a string if present')
            scene = ""
        shots.append(
            Shot(
                seconds=float(seconds),
                visual_prompt=text(raw, "visual_prompt", where),
                on_screen_text=text(raw, "on_screen_text", where, required=False),
                scene=scene.strip(),
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
    words: list = None  # [(word, emphasized)] for animated text; *word* marks emphasis

    def __post_init__(self):
        if self.words is None:
            self.words = [(w, False) for w in self.text.split()]


def parse_emphasis(text: str) -> list[tuple[str, bool]]:
    """Split text into words, tracking *emphasized* runs (the asterisks are removed)."""
    words, on = [], False
    for token in text.split():
        starts, ends = token.startswith("*"), token.endswith("*") and len(token) > 1
        word = token.strip("*")
        if starts:
            on = True
        if word:
            words.append((word, on))
        if ends or (starts and token.endswith("*") and len(token) > 1):
            on = False
    return words


def wrap_block(text: str, size: int, color: str) -> list[TextLine]:
    """Wrap text to the safe-zone width, shrinking the font until it fits in a few lines."""
    words = parse_emphasis(text)
    if not words:
        return []
    # Emphasized phrases are joined with no-break spaces so they stay on one line.
    tokens: list[str] = []
    for j, (w, emph) in enumerate(words):
        if emph and j and words[j - 1][1]:
            tokens[-1] += "\u00a0" + w
        else:
            tokens.append(w)
    plain = " ".join(tokens)
    while True:
        max_chars = max(6, int(SAFE_W / (size * CHAR_WIDTH_EM)))
        lines = textwrap.wrap(plain, max_chars, break_long_words=False, break_on_hyphens=False)
        fits = len(lines) <= MAX_LINES_PER_BLOCK and all(len(line) <= max_chars for line in lines)
        if fits or size <= MIN_TEXT_SIZE:
            out, k = [], 0
            for line in lines:
                n = sum(len(t.split("\u00a0")) for t in line.split(" ") if t)
                out.append(TextLine(line.replace("\u00a0", " "), size, color, words=words[k:k + n]))
                k += n
            return out
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


def font_family(path: Path) -> str:
    """Family name (name ID 1) from a TrueType/OpenType font, so libass can find the font."""
    try:
        data = path.read_bytes()
        base = struct.unpack(">I", data[12:16])[0] if data[:4] == b"ttcf" else 0
        for i in range(struct.unpack(">H", data[base + 4:base + 6])[0]):
            rec = base + 12 + i * 16
            if data[rec:rec + 4] != b"name":
                continue
            table = struct.unpack(">I", data[rec + 8:rec + 12])[0]
            count, strings = struct.unpack(">HH", data[table + 2:table + 6])
            found = {}
            for k in range(count):
                pid, _eid, _lid, nid, length, off = struct.unpack(">6H", data[table + 6 + k * 12:table + 18 + k * 12])
                if nid != 1:
                    continue
                raw = data[table + strings + off:table + strings + off + length]
                found[pid] = raw.decode("utf-16-be" if pid in (0, 3) else "latin-1", "replace")
            return found.get(3) or found.get(0) or found.get(1) or "Sans"
    except (OSError, struct.error, IndexError):
        pass
    return "Sans"


def ass_color(color: str) -> str:
    hexrgb = "FFFFFF" if color == "white" else color.replace("0x", "").replace("#", "")
    return f"&H00{hexrgb[4:6]}{hexrgb[2:4]}{hexrgb[0:2]}&"


def ass_time(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def build_ass(lines: list[TextLine], family: str, clip_seconds: float, delay: float) -> str:
    """Kinetic captions: each line pops in with an overshoot and slides up, its words appear
    one after another, and *emphasized* words are highlighted."""
    cx = SAFE_LEFT + SAFE_W // 2
    out = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}", "WrapStyle: 2",
           "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
           "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           f"Style: Cap,{family},80,&H00FFFFFF&,&H000000FF&,&H00000000&,&H70000000&,-1,0,0,0,100,100,0,0,1,7,4,8,0,0,0,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    t = delay
    for k, line in enumerate(lines):
        is_hook = line.color == HOOK_COLOR
        if k and lines[k - 1].color != line.color:
            t += 0.18  # small beat between the hook and the shot text
        base = ass_color("white")
        size = round(line.size * 1.16)
        outline = max(5, line.size // 10)
        spin = r"\frz-6\t(0,240,\frz0)" if is_hook else ""
        head = (rf"{{\an8\fs{size}\bord{outline}\shad4\move({cx},{line.y + 36},{cx},{line.y},0,200){spin}"
                rf"\fscx20\fscy20\t(0,140,\fscx118\fscy118)\t(140,250,\fscx100\fscy100)}}")
        parts = []
        for j, (word, emph) in enumerate(line.words):
            d = 40 + j * 70
            word = word.replace("\\", "/").replace("{", "(").replace("}", ")")
            color = ass_color(EMPHASIS_COLOR) if emph else base
            parts.append(rf"{{\alpha&HFF&\c{color}\t({d},{d + 90},\alpha&H00&)}}{word}")
        out.append(f"Dialogue: 0,{ass_time(t)},{ass_time(clip_seconds)},Cap,,0,0,0,,{head}{' '.join(parts)}")
        t += 0.12
    return "\n".join(out) + "\n"


def libass_available() -> bool:
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return any(len(f := l.split()) > 1 and f[1] == "subtitles" for l in proc.stdout.splitlines())


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
                workdir: Path, prefix: str, keep_audio: bool, pad: float = 0.0, ass_file: Optional[str] = None) -> None:
    """Crop and scale to 1080x1920, set the exact length (+ `pad` for the transition into the next
    shot), burn in the captions, normalize audio."""
    info = probe(src)
    length = seconds + pad
    text = [f"subtitles=filename={ass_file}:fontsdir=fonts"] if ass_file else drawtext_filters(lines, font_name, workdir, prefix)
    vf = [
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={WIDTH}:{HEIGHT}",
        "setsar=1",
        f"fps={FPS}",
        f"tpad=stop_mode=clone:stop_duration={length}",  # hold the last frame if the clip is short
        *text,
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
        "-t", f"{length:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        str(dst.resolve()),
    ]
    run_ffmpeg(args, what=f"rendering {rel(dst)}", cwd=workdir)


def assemble(clips: list[Path], dest: Path, total: float, music: Optional[Path], music_volume: float,
             durations: Optional[list[float]] = None, transitions: Optional[list[str]] = None, overlap: float = 0.0) -> None:
    """Join the rendered shots (hard cuts, or xfade transitions of `overlap` seconds, for which every
    clip but the last was rendered `overlap` seconds long) and mix a soundtrack under them."""
    args: list[str] = []
    for clip in clips:
        args += ["-i", str(clip.resolve())]
    n = len(clips)
    if overlap > 0 and n > 1 and durations and transitions:
        graph = ";".join(f"[{i}:v:0]settb=AVTB,fps={FPS},format=yuv420p[v{i}]" for i in range(n))
        vprev, aprev, offset = "v0", "0:a:0", 0.0
        for i in range(1, n):
            offset += durations[i - 1]
            graph += f";[{vprev}][v{i}]xfade=transition={transitions[i - 1]}:duration={overlap}:offset={offset:.3f}[x{i}]"
            graph += f";[{aprev}][{i}:a:0]acrossfade=d={overlap}:c1=tri:c2=tri[y{i}]"
            vprev, aprev = f"x{i}", f"y{i}"
        graph += f";[{vprev}]null[v];[{aprev}]anull[a]"
    else:
        graph = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    audio_out = "[a]"
    if music:
        args += ["-stream_loop", "-1", "-i", str(music.resolve())]  # loop a short track
        fade_out = max(0.0, total - 1.5)
        graph += (
            f";[{n}:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={music_volume},"
            f"afade=t=in:d=0.03,afade=t=out:st={fade_out:.3f}:d=1.5[m]"
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


def raw_clip_path(paths: OutputPaths, index: int, provider: Provider, prompt: str, shot: Shot, ref_hash: str) -> Path:
    """Cache key: changing the prompt, scene, length, provider or reference image regenerates the clip."""
    parts = [provider.name, prompt, shot.seconds, shot.scene, ref_hash, provider.cache_key_extra()]
    key = hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:10]
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
    own_music = bool(provider_cls and provider_cls.soundtrack is not Provider.soundtrack) and not args.no_music
    print(f"Music     {args.music or ('made by the provider (skip with --no-music)' if own_music else 'none (add one with --music, or pick a sound in the TikTok app)')}")
    print(f"Output    {rel(paths.final_video)} and {rel(paths.caption)}")

    ref = paths.character_ref
    state = "exists, will be reused" if ref.is_file() and not args.regen_ref else "will be generated"
    print_header(f"Character reference -> {rel(ref)} ({state})")
    print(f"generate_image(prompt)  [{prompt_stats(ref_prompt)}]\n")
    print(ref_prompt)

    for i, shot in enumerate(recipe.shots, 1):
        prompt = shot_prompt(character, shot)
        print_header(f"Shot {i}/{len(recipe.shots)}  {shot.seconds:g} s" + (f"  scene: {shot.scene}" if shot.scene else ""))
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
        dest = raw_clip_path(paths, i, provider, prompt, shot, ref_hash)
        if dest.is_file() and not args.force:
            print(f"[{i}/{total}] cached {rel(dest)}")
        else:
            print(f"[{i}/{total}] generating {shot.seconds:g} s clip ...")
            data = call(lambda: provider.generate_video(prompt, ref, duration=shot.seconds, scene=shot.scene or None), f"shot {i} video")
            save_clip(data, dest, f"shot {i}")
            print(f"[{i}/{total}] saved {rel(dest)}")
        info = probe(dest)
        if info.width > info.height:
            print(f"  ! shot {i} is landscape ({info.width}x{info.height}); center-cropping to 9:16 loses the sides. Request 9:16 from the provider.")
        if info.duration and info.duration + 0.05 < shot.seconds:
            print(f"  ! shot {i} clip is {info.duration:.1f} s; holding its last frame to fill {shot.seconds:g} s.")
        raw_clips.append(dest)

    keep_audio = not args.mute_clips and any(probe(c).has_audio for c in raw_clips)
    music, music_volume = args.music, args.music_volume
    if music is None and not args.no_music:
        track = provider.soundtrack(recipe.duration)
        if track:
            music = paths.clips / "soundtrack.wav"
            music.write_bytes(track)
            print(f"[music] {rel(music)} (made by the {provider.name} provider)")
            music_volume = 1.0 if music_volume is None else music_volume
    if music_volume is None:
        music_volume = 0.35 if keep_audio else 1.0

    # 3-4. Edit: crop/scale, captions, transitions, soundtrack
    animated = args.text_style == "animated"
    if animated and not libass_available():
        print("  ! this ffmpeg has no libass, so captions will be static (install an ffmpeg built with libass for animated text)")
        animated = False
    n = len(recipe.shots)
    overlap = 0.0 if args.transition == "cut" or n < 2 else max(0.05, min(args.transition_seconds, min(s.seconds for s in recipe.shots) / 3))
    transitions = [args.transition if args.transition not in ("auto", "cut") else TRANSITIONS[i % len(TRANSITIONS)] for i in range(n - 1)]
    with tempfile.TemporaryDirectory(prefix="chef_whiskers_") as tmp:
        workdir = Path(tmp)
        font_name = "font" + font.suffix.lower()
        shutil.copyfile(font, workdir / font_name)
        (workdir / "fonts").mkdir()
        shutil.copyfile(font, workdir / "fonts" / font.name)
        family = font_family(font)
        rendered = []
        for i, (shot, raw) in enumerate(zip(recipe.shots, raw_clips), 1):
            dst = paths.clips / f"shot{i:02d}_{WIDTH}x{HEIGHT}.mp4"
            lines = layout_text(text_blocks(recipe, i, shot), args.text_position)
            pad = overlap if i < n else 0.0
            ass_file = None
            if animated and lines:
                ass_file = f"s{i:02d}.ass"
                delay = (overlap if i > 1 else 0.0) + 0.05
                (workdir / ass_file).write_text(build_ass(lines, family, shot.seconds + pad, delay), encoding="utf-8")
            render_shot(raw, dst, shot.seconds, lines, font_name, workdir, f"s{i:02d}", keep_audio, pad=pad, ass_file=ass_file)
            print(f"[edit] {rel(dst)}")
            rendered.append(dst)
        assemble(rendered, paths.final_video, recipe.duration, music, music_volume,
                 durations=[s.seconds for s in recipe.shots], transitions=transitions, overlap=overlap)

    # 5. Caption
    paths.caption.write_text(recipe.caption_file_text(), encoding="utf-8")

    final = probe(paths.final_video)
    print(f"\nDone: {rel(paths.final_video)} ({final.width}x{final.height}, {final.duration:.1f} s)")
    print(f"      {rel(paths.caption)} (caption and hashtags)")
    if provider.ai_generated:
        print("Before posting: watch every clip, and turn on TikTok's 'AI-generated content' label when you post.")
    else:
        print(f"Before posting: watch it through. The {provider.name} provider does not use generative AI, so TikTok's AI label does not apply.")


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
    parser.add_argument("--no-music", action="store_true", help="skip the music bed a provider would otherwise add (render provider)")
    parser.add_argument("--text-position", choices=["top", "center", "bottom"], default="top",
                        help="where on-screen text sits inside the safe zone (default: top)")
    parser.add_argument("--text-style", choices=["animated", "static"], default="animated",
                        help="animated: captions pop in word by word with *emphasis* highlighted (needs libass); static: plain text")
    parser.add_argument("--transition", default="auto",
                        help="transition between shots: auto (varied), cut, or an ffmpeg xfade name such as smoothleft or zoomin")
    parser.add_argument("--transition-seconds", type=float, default=0.25, help="length of each transition (default: 0.25)")
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
