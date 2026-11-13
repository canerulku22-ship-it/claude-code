"""Review images: a cast contact sheet (every expression) and a vertical lineup poster.

These are for you, not for TikTok: they make it quick to approve the cast and
to check that AI art came out consistent after background removal.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config
from .cast import Cast
from .sprites import SpriteBank
from .text import draw_text, measure, wrap

BG = (248, 244, 255)
INK = (30, 20, 40)


def _thumb(im: Image.Image, w: int, h: int) -> Image.Image:
    """Fit a sprite into w x h, keeping the bottom-centre anchor."""
    k = min(w / im.width, h / im.height)
    return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)


def contact_sheet(cast: Cast, out: Path) -> Path:
    bank = SpriteBank(cast)
    cols = config.EXPRESSIONS
    info_w, cell_w, cell_h, head_h = 520, 300, 400, 190
    W = info_w + cell_w * len(cols)
    H = head_h + cell_h * len(cast.characters)
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    draw_text(sheet, (30, 28), f"{cast.show.get('title', 'Rizz Island').upper()} — CAST 🌴", 64, fill=(255, 90, 160),
              stroke=6, stroke_fill=INK)
    for i, e in enumerate(cols):
        draw_text(sheet, (info_w + i * cell_w + cell_w / 2, 130), e.replace("_", "-"), 34, fill=INK, anchor="mt")

    for r, c in enumerate(cast.characters.values()):
        y0 = head_h + r * cell_h
        if r % 2 == 0:
            d.rectangle([0, y0, W, y0 + cell_h], fill=(238, 232, 252))
        d.rectangle([0, y0, 16, y0 + cell_h], fill=c.rgb)
        draw_text(sheet, (36, y0 + 20), f"{c.emoji} {c.name}", 36, fill=c.rgb, stroke=4, stroke_fill=INK)
        yy = y0 + 80
        for line in wrap(c.raw.get("role", ""), 26, info_w - 60):
            draw_text(sheet, (36, yy), line, 26, fill=INK)
            yy += 34
        yy += 6
        for line in wrap(f"“{c.raw['catchphrase']}”", 26, info_w - 60)[:3]:
            draw_text(sheet, (36, yy), line, 26, fill=(120, 60, 160))
            yy += 34
        rel = c.raw["relationship"]
        partner = cast.characters.get(rel.get("partner") or "")
        status = f"💞 coupled with {partner.short_name}" if partner else "💔 single"
        draw_text(sheet, (36, yy + 8), status, 24, fill=(90, 90, 110))
        v = c.voice
        draw_text(sheet, (36, y0 + cell_h - 44), f"🎙 {v['voice_id']}  pitch {v['pitch']:+}  speed {v['speed']}",
                  20, fill=(120, 120, 140))
        for i, e in enumerate(cols):
            im = bank.get(c.id, e)
            if im is None:
                continue
            t = _thumb(im, cell_w - 10, cell_h - 10)
            sheet.alpha_composite(t, (info_w + i * cell_w + (cell_w - t.width) // 2, y0 + cell_h - t.height - 4))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out, quality=92)
    return out


def villa_gradient(w: int, h: int) -> Image.Image:
    """Quick sunset-and-pool backdrop for the lineup poster."""
    y = np.linspace(0, 1, h)[:, None, None]
    top, mid, low = np.array([255, 120, 170]), np.array([255, 200, 120]), np.array([60, 200, 230])
    col = np.where(y < 0.55, top + (mid - top) * (y / 0.55), mid + (low - mid) * ((y - 0.55) / 0.45))
    img = np.broadcast_to(col, (h, w, 3)).astype(np.uint8)
    im = Image.fromarray(img, "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse([w * 0.6, h * 0.12, w * 0.95, h * 0.12 + w * 0.35], fill=(255, 240, 180, 255))   # sun
    return im.filter(ImageFilter.GaussianBlur(2))


def lineup(cast: Cast, out: Path) -> Path:
    """1080x1920 poster: everyone side by side in two rows with name tags."""
    W, H = config.VIDEO_W, config.VIDEO_H
    im = villa_gradient(W, H)
    bank = SpriteBank(cast)
    chars = list(cast.characters.values())
    per_row = (len(chars) + 1) // 2
    l, t, r, b = config.safe_rect(W, H)
    draw_text(im, ((l + r) / 2, t + 10), "MEET THE SINGLES 💘", 76, fill=(255, 255, 255), stroke=8,
              stroke_fill=INK, anchor="mt")
    row_h = (b - t - 140) / 2
    cw = (r - l) / per_row
    # One shared scale (so relative sizes stay true) that fits the widest/tallest figure.
    sprites = {c.id: bank.get(c.id, "neutral") for c in chars}
    k = min(min(cw * 1.3 / (sp.getbbox()[2] - sp.getbbox()[0]),
                (row_h - 70) / (config.SPRITE_BASELINE - sp.getbbox()[1])) for sp in sprites.values())
    for idx, c in enumerate(chars):
        row, col = divmod(idx, per_row)
        sp = sprites[c.id]
        s = sp.resize((round(sp.width * k), round(sp.height * k)), Image.LANCZOS)
        cx = l + cw * (col + 0.5)
        base_y = t + 140 + row_h * (row + 1) - 50
        shadow = Image.new("RGBA", (int(cw * 0.8), 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse([0, 0, shadow.width, 40], fill=(0, 0, 0, 70))
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)), (int(cx - shadow.width / 2), int(base_y - 25)))
        im.alpha_composite(s, (int(cx - s.width / 2), int(base_y - config.SPRITE_BASELINE * k)))
        tag = c.short_name.upper()
        size = 34
        while measure(tag, size, 4)[0] > cw - 6 and size > 18:
            size -= 2
        draw_text(im, (cx, base_y + 2), tag, size, fill=c.rgb, stroke=5, stroke_fill=(255, 255, 255), anchor="mt")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out, quality=92)
    return out
