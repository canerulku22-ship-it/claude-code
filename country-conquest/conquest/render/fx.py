"""Small drawing helpers shared by the scenes: sprites, panels, sparks, pins."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .flags import flag_card


def paste(canvas: Image.Image, img: Image.Image, cx: float, cy: float,
          scale: float = 1.0, alpha: float = 1.0, angle: float = 0.0) -> None:
    """Alpha-composite ``img`` centred on (cx, cy) with optional scale/opacity/rotation."""
    if alpha <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1.0) > 1e-3:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                         Image.BILINEAR)
    if abs(angle) > 0.05:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 0.999:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    x, y = round(cx - img.width / 2), round(cy - img.height / 2)
    if x >= canvas.width or y >= canvas.height or x + img.width <= 0 or y + img.height <= 0:
        return  # entirely off screen
    canvas.alpha_composite(img, dest=(max(0, x), max(0, y)),
                           source=(max(0, -x), max(0, -y)))


@lru_cache(maxsize=64)
def panel(w: int, h: int, radius: int, fill: tuple, border: tuple | None = None,
          border_w: int = 0, ss: int = 3) -> Image.Image:
    """Anti-aliased rounded rectangle sprite."""
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius * ss, fill=fill,
                        outline=border, width=border_w * ss if border else 0)
    return big.resize((w, h), Image.LANCZOS)


@lru_cache(maxsize=32)
def circle(d: int, fill: tuple, border: tuple | None = None, border_w: int = 0, ss: int = 3) -> Image.Image:
    big = Image.new("RGBA", (d * ss, d * ss), (0, 0, 0, 0))
    ImageDraw.Draw(big).ellipse((0, 0, d * ss - 1, d * ss - 1), fill=fill, outline=border,
                                width=border_w * ss if border else 0)
    return big.resize((d, d), Image.LANCZOS)


def tinted(img: Image.Image, colour=(255, 255, 255), amount: float = 1.0) -> Image.Image:
    """Blend an RGBA sprite towards ``colour`` (hit flash), keeping its alpha."""
    if amount <= 0.01:
        return img
    solid = Image.new("RGBA", img.size, colour + (255,))
    solid.putalpha(img.getchannel("A"))
    return Image.blend(img, solid, min(1.0, amount))


def greyed(img: Image.Image, amount: float) -> Image.Image:
    if amount <= 0.01:
        return img
    grey = img.convert("LA").convert("RGBA")
    grey.putalpha(img.getchannel("A"))
    return Image.blend(img, grey, min(1.0, amount))


def sparks(canvas: Image.Image, x: float, y: float, direction: float, age: float, seed: str,
           k: float, count: int = 22, spread: float = 150.0, colours=None, power: float = 1.0) -> None:
    """Deterministic spark burst: streaks flying out from (x, y), affected by gravity.

    ``direction`` is in degrees (0 = right, 90 = down); ``age`` is seconds since impact."""
    if age < 0 or age > 0.7:
        return
    rng = random.Random(seed)
    colours = colours or [(255, 255, 255), (255, 226, 120), (255, 170, 60), (255, 240, 200)]
    d = ImageDraw.Draw(canvas)
    g = 1500.0 * k
    for _ in range(count):
        ang = math.radians(direction + rng.uniform(-spread / 2, spread / 2))
        speed = rng.uniform(450, 1250) * k * power
        life = rng.uniform(0.25, 0.55)
        if age > life:
            continue
        vx, vy = math.cos(ang) * speed, math.sin(ang) * speed
        px, py = x + vx * age, y + vy * age + 0.5 * g * age * age
        tail = 0.035
        qx, qy = px - vx * tail, py - (vy + g * age) * tail
        fade = 1 - age / life
        width = max(1, round(rng.uniform(3, 7) * k * fade + 0.5))
        col = rng.choice(colours)
        d.line((qx, qy, px, py), fill=col + (int(255 * fade),), width=width)


def burst_ring(canvas: Image.Image, x: float, y: float, age: float, k: float,
               colour=(255, 255, 255), max_r: float = 120.0, life: float = 0.28, width: float = 10) -> None:
    """Expanding ring (impact / landing shockwave)."""
    if age < 0 or age > life:
        return
    u = age / life
    r = max_r * k * (1 - (1 - u) ** 2)
    w = max(1, round(width * k * (1 - u)))
    ImageDraw.Draw(canvas).ellipse((x - r, y - r, x + r, y + r), outline=colour + (int(255 * (1 - u)),),
                                   width=w)


def star_flash(canvas: Image.Image, x: float, y: float, age: float, k: float, size: float = 150,
               life: float = 0.14, colour=(255, 255, 255)) -> None:
    """A quick spiky impact star."""
    if age < 0 or age > life:
        return
    u = age / life
    r_out = size * k * (0.6 + 0.6 * u)
    r_in = r_out * 0.32
    pts = []
    for i in range(16):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * 2 * i / 16 + 0.3
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    ImageDraw.Draw(canvas).polygon(pts, fill=colour + (int(235 * (1 - u)),))


@lru_cache(maxsize=256)
def waving_flag(iso2: str, width: int, phase_idx: int, phases: int = 10) -> Image.Image:
    """A flag card with a gentle wave (cached per animation phase)."""
    card = flag_card(iso2, width, shadow=False)
    arr = np.asarray(card)
    h, w = arr.shape[:2]
    pad = max(2, round(h * 0.08))
    out = np.zeros((h + 2 * pad, w, 4), np.uint8)
    phase = 2 * math.pi * phase_idx / phases
    for x in range(w):
        # Wave grows away from the pole (left edge).
        amp = pad * (x / w)
        dy = int(round(math.sin(x / w * 2 * math.pi * 1.2 - phase) * amp))
        out[pad + dy:pad + dy + h, x] = arr[:, x]
    img = Image.fromarray(out, "RGBA")
    # Subtle light/dark banding sells the wave.
    shade = np.array([1.0 + 0.10 * math.sin(x / w * 2 * math.pi * 1.2 - phase + 1.2) for x in range(w)],
                     np.float32)
    rgb = np.asarray(img, np.float32)
    rgb[..., :3] = np.clip(rgb[..., :3] * shade[None, :, None], 0, 255)
    return Image.fromarray(rgb.astype(np.uint8), "RGBA")


@lru_cache(maxsize=128)
def pin_sprite(iso2: str, width: int, phase_idx: int) -> tuple[Image.Image, tuple[int, int]]:
    """A flag on a pole. Returns (sprite, (base_x, base_y)) where base is the pole foot."""
    flag = waving_flag(iso2, width, phase_idx)
    pole_h = round(flag.height * 1.9)
    pole_w = max(2, round(width * 0.07))
    W = flag.width + pole_w + 4
    H = pole_h + 6
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    px = 2
    d.rounded_rectangle((px, 0, px + pole_w, pole_h), radius=pole_w // 2, fill=(245, 245, 250, 255),
                        outline=(20, 24, 40, 255), width=max(1, pole_w // 3))
    ball = pole_w + 2
    d.ellipse((px + pole_w / 2 - ball / 2, -1, px + pole_w / 2 + ball / 2, ball - 1), fill=(255, 210, 63, 255),
              outline=(20, 24, 40, 255), width=1)
    img.alpha_composite(flag, (px + pole_w, max(0, round(pole_w * 0.6))))
    # Contact shadow at the foot.
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, H - 8, pole_w * 4 + 4, H - 1), fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(1.5))
    out = Image.alpha_composite(sh, img)
    return out, (px + pole_w // 2, pole_h)
