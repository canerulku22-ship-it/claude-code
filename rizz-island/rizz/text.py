"""Text rendering with colour emoji support.

Pillow has no font fallback, so a caption like "I GOT A TEXT! 📱" needs two
fonts: a heavy display font for letters and Noto Color Emoji for the emoji.
This module splits strings into runs, measures them, and draws them with a
thick outline (the TikTok caption look).

Noto Color Emoji is a bitmap font that only renders at size 109, so emoji are
drawn once at that size, cached, and scaled to the text size.
"""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import config

_BOLD = config.find_font(config.FONT_CANDIDATES_BOLD, "RIZZ_FONT_BOLD")
_EMOJI = config.find_font(config.FONT_CANDIDATES_EMOJI, "RIZZ_FONT_EMOJI")


@lru_cache(maxsize=64)
def font(size: int) -> ImageFont.FreeTypeFont:
    if _BOLD:
        return ImageFont.truetype(_BOLD, size)
    return ImageFont.load_default(size)


def _is_emoji_cp(cp: int) -> bool:
    return (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF
            or 0x1F1E6 <= cp <= 0x1F1FF or cp in (0x2194, 0x2195, 0x21A9, 0x21AA, 0x231A, 0x231B, 0x23F0, 0x00A9, 0x00AE))


def split_runs(text: str) -> list[tuple[str, bool]]:
    """Split into [(chunk, is_emoji)]. Emoji clusters keep their ZWJ/VS16/skin-tone parts."""
    runs: list[tuple[str, bool]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if _is_emoji_cp(ord(ch)):
            j = i + 1
            while j < len(text):
                cp = ord(text[j])
                if cp in (0xFE0F, 0x20E3) or 0x1F3FB <= cp <= 0x1F3FF:
                    j += 1
                elif cp == 0x200D and j + 1 < len(text):
                    j += 2
                else:
                    break
            runs.append((text[i:j], True))
            i = j
        else:
            j = i + 1
            while j < len(text) and not _is_emoji_cp(ord(text[j])):
                j += 1
            chunk = text[i:j].replace("️", "")
            if chunk:
                if runs and not runs[-1][1]:
                    runs[-1] = (runs[-1][0] + chunk, False)
                else:
                    runs.append((chunk, False))
            i = j
    return runs


@lru_cache(maxsize=256)
def _emoji_tile(cluster: str) -> Image.Image | None:
    if not _EMOJI:
        return None
    try:
        f = ImageFont.truetype(_EMOJI, 109)
    except OSError:
        return None
    tile = Image.new("RGBA", (180, 150), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((90, 75), cluster, font=f, embedded_color=True, anchor="mm")
    bbox = tile.getbbox()
    return tile.crop(bbox) if bbox else None


def emoji_image(cluster: str, height: int) -> Image.Image | None:
    tile = _emoji_tile(cluster)
    if tile is None:
        return None
    w = max(1, round(tile.width * height / tile.height))
    return tile.resize((w, height), Image.LANCZOS)


def measure(text: str, size: int, stroke: int = 0) -> tuple[int, int]:
    """(width, height) of a single line including its outline."""
    f = font(size)
    w = 0
    for chunk, is_emoji in split_runs(text):
        if is_emoji:
            im = emoji_image(chunk, int(size * 0.95))
            w += (im.width if im else 0) + int(size * 0.08)
        else:
            w += int(f.getlength(chunk))
    asc, desc = f.getmetrics()
    return w + 2 * stroke, asc + desc + 2 * stroke


def draw_text(img: Image.Image, xy: tuple[float, float], text: str, size: int, fill=(255, 255, 255),
              stroke: int = 0, stroke_fill=(0, 0, 0), anchor: str = "lt") -> tuple[int, int, int, int]:
    """Draw one line of text (with emoji) onto img. anchor: 'lt', 'mt', 'mm' or 'mb'.

    Returns the bounding box that was drawn.
    """
    f = font(size)
    w, h = measure(text, size, stroke)
    x, y = xy
    if anchor[0] == "m":
        x -= w / 2
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    d = ImageDraw.Draw(img)
    asc, _ = f.getmetrics()
    cx = x + stroke
    for chunk, is_emoji in split_runs(text):
        if is_emoji:
            em = emoji_image(chunk, int(size * 0.95))
            if em is not None:
                ey = int(y + stroke + asc - em.height * 0.9)
                img.alpha_composite(em, (int(cx), max(0, ey)))
                cx += em.width + int(size * 0.08)
        else:
            d.text((cx, y + stroke), chunk, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            cx += f.getlength(chunk)
    return int(x), int(y), int(x + w), int(y + h)


def wrap(text: str, size: int, max_w: int, stroke: int = 0) -> list[str]:
    """Greedy word wrap to fit max_w pixels."""
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = f"{cur} {wd}".strip()
        if cur and measure(trial, size, stroke)[0] > max_w:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines
