"""Flag artwork from flag-icons: rasterised SVGs, rounded "flag cards" and team colours."""
from __future__ import annotations

import colorsys
import io
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..assets import flag_svg
from ..paths import CACHE

FLAG_CACHE = CACHE / "flags"


@lru_cache(maxsize=512)
def flag_image(iso2: str, width: int) -> Image.Image:
    """The 4:3 flag of ``iso2`` as an RGBA image ``width`` pixels wide (disk cached)."""
    width = max(8, int(width))
    height = round(width * 3 / 4)
    FLAG_CACHE.mkdir(parents=True, exist_ok=True)
    cached = FLAG_CACHE / f"{iso2.lower()}_{width}.png"
    if cached.exists():
        return Image.open(cached).convert("RGBA")
    svg = flag_svg(iso2)
    if svg is None:  # unknown flag: neutral placeholder with the code on it
        img = Image.new("RGBA", (width, height), (120, 128, 140, 255))
    else:
        import cairosvg  # imported lazily: needs the system cairo library
        png = cairosvg.svg2png(url=str(svg), output_width=width, output_height=height)
        img = Image.open(io.BytesIO(png)).convert("RGBA")
    img.save(cached)
    return img


def rounded_mask(size: tuple[int, int], radius: int, ss: int = 4) -> Image.Image:
    """Anti-aliased rounded-rectangle alpha mask."""
    w, h = size
    big = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius * ss, fill=255)
    return big.resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=256)
def flag_card(iso2: str, width: int, border: float = 0.035, shadow: bool = True) -> Image.Image:
    """A flag with rounded corners, a white rim and a soft drop shadow.

    The returned image is padded; the flag itself is centred in it."""
    width = max(12, int(width))
    rim = max(2, round(width * border))
    inner_w = width - 2 * rim
    flag = flag_image(iso2, inner_w)
    fw, fh = flag.size
    radius = max(3, round(width * 0.08))
    card_w, card_h = fw + 2 * rim, fh + 2 * rim

    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    inner_mask = rounded_mask((fw, fh), max(2, radius - rim))
    card.paste(flag, (rim, rim), ImageChops.multiply(inner_mask, flag.getchannel("A")))
    card.putalpha(rounded_mask((card_w, card_h), radius))

    pad = round(width * 0.10) if shadow else 0
    out = Image.new("RGBA", (card_w + 2 * pad, card_h + 2 * pad), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
        sh_mask = Image.new("L", out.size, 0)
        sh_mask.paste(card.getchannel("A"), (pad, pad + round(pad * 0.45)))
        sh_mask = sh_mask.filter(ImageFilter.GaussianBlur(pad * 0.45))
        sh.putalpha(sh_mask.point(lambda v: v * 0.55))
        out = Image.alpha_composite(out, sh)
    out.alpha_composite(card, (pad, pad))
    return out


def _bold(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Push a flag colour towards a bold, map-friendly version of itself."""
    s = min(max(s, 0.62), 0.92)
    v = min(max(v, 0.80), 0.96)
    if 0.53 <= h <= 0.72:          # blue: brighten so it pops against the sea
        s, v = min(s, 0.62), 1.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return round(r * 255), round(g * 255), round(b * 255)


def hue_distance(a, b) -> float:
    ha = colorsys.rgb_to_hsv(*(c / 255 for c in a))[0]
    hb = colorsys.rgb_to_hsv(*(c / 255 for c in b))[0]
    d = abs(ha - hb)
    return min(d, 1 - d)


def flag_palette(iso2: str) -> list[tuple[int, int, int]]:
    """Bold candidate team colours from the flag, most prominent first.

    White, black and greys are skipped; near-identical hues are merged."""
    arr = np.asarray(flag_image(iso2, 96).convert("RGBA"), dtype=np.int32)
    px = arr[..., :3][arr[..., 3] > 200]
    quant = (px // 24) * 24 + 12
    colours, counts = np.unique(quant, axis=0, return_counts=True)
    scored = []
    for (r, g, b), count in zip(colours, counts):
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.30 or v < 0.30 or count < 12:
            continue
        scored.append((count * (0.3 + s) * (0.5 + v), _bold(h, s, v)))
    scored.sort(key=lambda x: -x[0])
    palette: list[tuple[int, int, int]] = []
    for _, col in scored:
        if all(hue_distance(col, p) > 0.06 for p in palette):
            palette.append(col)
    if not palette:  # black/white flags: a stable hue from the code
        palette = [_bold((sum(map(ord, iso2)) * 0.137) % 1.0, 0.7, 0.85)]
    return palette


def team_color(iso2: str) -> tuple[int, int, int]:
    return flag_palette(iso2)[0]


def distinct_color(palette, avoid, min_hue: float = 0.09) -> tuple[int, int, int]:
    """First palette colour whose hue is clearly different from ``avoid``.

    Falls back to rotating the hue of the main colour (e.g. red vs red flags)."""
    for col in palette:
        if hue_distance(col, avoid) >= min_hue:
            return tuple(col)
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in palette[0]))
    return _bold((h + 0.33) % 1.0, max(s, 0.7), v)
