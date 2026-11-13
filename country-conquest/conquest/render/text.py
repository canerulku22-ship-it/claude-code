"""Signature text style: bold font, thick dark stroke, soft shadow, accent spans.

Strings may contain:
* ``*accent*`` spans (drawn in the accent colour),
* flag emoji such as 🇹🇷 (drawn with the flag-icons artwork so flags look the
  same everywhere in the video),
* other emoji such as 👇 🔥 (drawn from a colour emoji font, outlined to match).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from ..assets import emoji_font_path, font_path
from .flags import flag_image, rounded_mask

RI_BASE = 0x1F1E6  # regional indicator "A"


@dataclass(frozen=True)
class TextStyle:
    font: str = "LilitaOne"
    fill: tuple = (255, 255, 255)
    accent: tuple = (255, 210, 63)
    stroke: tuple = (10, 16, 36)
    stroke_ratio: float = 0.13       # stroke width as a fraction of the font size
    shadow: bool = True


@lru_cache(maxsize=64)
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path(name), size)


@lru_cache(maxsize=1)
def _emoji_font():
    path = emoji_font_path()
    if path is None:
        return None
    try:
        return ImageFont.truetype(path, 109)   # Noto Color Emoji's bitmap strike size
    except OSError:
        return None


@lru_cache(maxsize=64)
def _emoji_image(ch: str, size: int) -> Image.Image | None:
    font = _emoji_font()
    if font is None:
        return None
    canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((10, 10), ch, font=font, embedded_color=True)
    box = canvas.getbbox()
    if box is None:
        return None
    glyph = canvas.crop(box)
    scale = size / max(glyph.size)
    return glyph.resize((max(1, round(glyph.width * scale)), max(1, round(glyph.height * scale))),
                        Image.LANCZOS)


def _is_emoji(cp: int) -> bool:
    return (0x1F300 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF
            or 0x1F000 <= cp <= 0x1F2FF)


def tokenize(text: str):
    """Split into words; each word is a list of (kind, value, accent) pieces."""
    words, word, accent = [], [], False
    run = ""

    def flush_run():
        nonlocal run
        if run:
            word.append(("text", run, accent))
            run = ""

    i = 0
    while i < len(text):
        ch = text[i]
        cp = ord(ch)
        nxt = ord(text[i + 1]) if i + 1 < len(text) else 0
        if ch == "*":
            flush_run()
            accent = not accent
        elif ch == " ":
            flush_run()
            if word:
                words.append(word)
            word = []
        elif ch == "\n":
            flush_run()
            if word:
                words.append(word)
            words.append("\n")
            word = []
        elif RI_BASE <= cp <= RI_BASE + 25 and RI_BASE <= nxt <= RI_BASE + 25:
            flush_run()
            word.append(("flag", chr(cp - RI_BASE + 65) + chr(nxt - RI_BASE + 65), accent))
            i += 1
        elif _is_emoji(cp):
            flush_run()
            word.append(("emoji", ch, accent))
        elif cp in (0xFE0F, 0x200D):
            pass  # variation selector / joiner
        else:
            run += ch
        i += 1
    flush_run()
    if word:
        words.append(word)
    return words


def flag_emoji(iso2: str) -> str:
    """'TR' -> '🇹🇷' (so templates can say {flag})."""
    return "".join(chr(RI_BASE + ord(c) - 65) for c in iso2.upper())


class _Layout:
    def __init__(self, size: int, style: TextStyle):
        self.size = size
        self.style = style
        self.font = _font(style.font, size)
        self.space = self.font.getlength(" ")
        cap = self.font.getbbox("H")
        self.cap_h = cap[3] - cap[1]
        self.ascent, self.descent = self.font.getmetrics()

    def piece_width(self, piece) -> float:
        kind, value, _ = piece
        if kind == "text":
            return self.font.getlength(value)
        if kind == "flag":
            return self.cap_h * 1.25 * 1.12 + self.size * 0.08
        return self.size * 0.86 + self.size * 0.08

    def word_width(self, word) -> float:
        return sum(self.piece_width(p) for p in word)


def _wrap(words, layout: _Layout, max_width: float | None):
    lines, line, width = [], [], 0.0
    for word in words:
        if word == "\n":
            lines.append(line)
            line, width = [], 0.0
            continue
        ww = layout.word_width(word)
        add = ww + (layout.space if line else 0)
        if max_width and line and width + add > max_width:
            lines.append(line)
            line, width = [word], ww
        else:
            line.append(word)
            width += add
    if line:
        lines.append(line)
    return lines


@lru_cache(maxsize=512)
def render_text(text: str, size: int, style: TextStyle = TextStyle(),
                max_width: int | None = None, align: str = "center",
                line_gap: float = 0.08) -> Image.Image:
    """Render ``text`` as a tightly padded RGBA image."""
    size = max(6, int(size))
    layout = _Layout(size, style)
    words = tokenize(text)
    lines = _wrap(words, layout, max_width)
    if max_width and len(lines) > 1:
        # Balance line lengths: shrink the width while the line count stays the same.
        lo, hi = max_width * 0.4, float(max_width)
        for _ in range(12):
            mid = (lo + hi) / 2
            if len(_wrap(words, layout, mid)) <= len(lines):
                hi = mid
            else:
                lo = mid
        lines = _wrap(words, layout, hi)

    stroke = max(1, round(size * style.stroke_ratio))
    line_h = round((layout.ascent + layout.descent) * (1 + line_gap))
    widths = [sum(layout.word_width(w) for w in ln) + layout.space * max(0, len(ln) - 1) for ln in lines]
    pad = stroke + round(size * 0.12)
    W = int(max(widths or [1]) + 2 * pad)
    H = int(line_h * len(lines) + 2 * pad)

    fill_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    stroke_mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(fill_layer)
    sdraw = ImageDraw.Draw(stroke_mask)

    for li, (ln, lw) in enumerate(zip(lines, widths)):
        if align == "center":
            x = pad + (max(widths) - lw) / 2
        elif align == "right":
            x = pad + max(widths) - lw
        else:
            x = pad
        baseline = pad + li * line_h + layout.ascent
        mid_y = baseline - layout.cap_h / 2
        for wi, word in enumerate(ln):
            if wi:
                x += layout.space
            for piece in word:
                kind, value, accent = piece
                pw = layout.piece_width(piece)
                if kind == "text":
                    colour = style.accent if accent else style.fill
                    draw.text((x, baseline), value, font=layout.font, fill=colour + (255,), anchor="ls")
                    sdraw.text((x, baseline), value, font=layout.font, fill=255, anchor="ls",
                               stroke_width=stroke, stroke_fill=255)
                elif kind == "flag":
                    fh = round(layout.cap_h * 1.12)
                    fw = round(fh * 4 / 3)
                    fx, fy = round(x + size * 0.04), round(mid_y - fh / 2)
                    flag = flag_image(value, fw).resize((fw, fh), Image.LANCZOS)
                    mask = ImageChops.multiply(rounded_mask((fw, fh), max(2, fh // 7)), flag.getchannel("A"))
                    fill_layer.paste(flag, (fx, fy), mask)
                    sdraw.rounded_rectangle((fx - stroke, fy - stroke, fx + fw + stroke, fy + fh + stroke),
                                            radius=max(2, fh // 7) + stroke, fill=255)
                else:
                    em = _emoji_image(value, round(size * 0.86))
                    if em is not None:
                        ex, ey = round(x + size * 0.03), round(mid_y - em.height / 2)
                        fill_layer.alpha_composite(em, (ex, ey))
                        grown = Image.new("L", (W, H), 0)
                        grown.paste(em.getchannel("A"), (ex, ey))
                        grown = grown.filter(ImageFilter.MaxFilter(_odd(stroke * 2 + 1)))
                        stroke_mask = ImageChops.lighter(stroke_mask, grown)
                        sdraw = ImageDraw.Draw(stroke_mask)
                x += pw

    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if style.shadow:
        sh = Image.new("L", (W, H), 0)
        sh.paste(stroke_mask, (0, round(size * 0.07)))
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.05)).point(lambda v: v * 0.6)
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow.putalpha(sh)
        out = Image.alpha_composite(out, shadow)
    stroke_img = Image.new("RGBA", (W, H), style.stroke + (0,))
    stroke_img.putalpha(stroke_mask)
    out = Image.alpha_composite(out, stroke_img)
    return Image.alpha_composite(out, fill_layer)


def _odd(n: int) -> int:
    n = max(3, int(n))
    return n if n % 2 else n + 1
