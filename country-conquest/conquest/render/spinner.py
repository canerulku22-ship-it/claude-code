"""Optional ``"spinner_style": "wheel"``: a spinning wheel of candidate flags."""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw

from .camera import ease_in_out, ease_out_back
from .flags import flag_card
from .fx import circle, paste
from .maplayer import shade

RADIUS = 300  # reference px


class Wheel:
    def __init__(self, renderer):
        self.r = renderer
        self.k = renderer.k
        sx0, sy0, sx1, sy1 = renderer.safe
        self.cx = (sx0 + sx1) / 2
        self.cy = (sy0 + sy1) / 2 + 60

    @lru_cache(maxsize=8)
    def _wheel(self, segments: tuple[str, ...]) -> Image.Image:
        """Wheel artwork at angle 0 (segment 0 starts at the top, going clockwise)."""
        k, ss = self.k, 2
        R = round(RADIUS * k * ss)
        D = 2 * R
        img = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        n = len(segments)
        seg = 360 / n
        for i, code in enumerate(segments):
            col = self.r.world[code].color
            # Pillow angles start at 3 o'clock; -90 puts segment 0 at 12 o'clock.
            a0, a1 = -90 + i * seg, -90 + (i + 1) * seg
            fill = col if i % 2 == 0 else shade(col, 0.78)
            d.pieslice((0, 0, D - 1, D - 1), a0, a1, fill=fill + (255,), outline=(255, 255, 255, 255),
                       width=round(5 * k * ss))
        for i, code in enumerate(segments):
            mid = math.radians(-90 + (i + 0.5) * seg)
            fw = round(min(150, 520 / n + 40) * k * ss)
            card = flag_card(self.r.world[code].iso2, fw, shadow=False)
            card = card.rotate(-((i + 0.5) * seg), resample=Image.BICUBIC, expand=True)
            px = R + math.cos(mid) * R * 0.66
            py = R + math.sin(mid) * R * 0.66
            img.alpha_composite(card, (round(px - card.width / 2), round(py - card.height / 2)))
        ring = circle(D, (0, 0, 0, 0), (255, 255, 255, 255), round(12 * k * ss))
        img.alpha_composite(ring)
        return img

    def draw(self, canvas: Image.Image, rt, t: float) -> None:
        w = rt.wheel
        k = self.k
        s0 = rt.spin[0]
        appear = ease_out_back(min(1, max(0.0, t - s0) / 0.3), 1.4)
        leave = ease_in_out(max(0.0, (t - (rt.land + 0.35)) / 0.25))
        scale = appear * (1 - leave)
        if scale <= 0.01:
            return
        u = min(1, max(0.0, (t - w["t0"]) / (w["t1"] - w["t0"])))
        angle = w["final_angle"] * (1 - (1 - u) ** 3)
        art = self._wheel(tuple(w["segments"]))
        rotated = art.rotate(-angle, resample=Image.BICUBIC)
        paste(canvas, rotated, self.cx * k, self.cy * k, scale=0.5 * scale)
        hub = circle(round(110 * k), self.r.panel_rgb + (255,), (255, 255, 255, 255), max(2, round(6 * k)))
        paste(canvas, hub, self.cx * k, self.cy * k, scale=scale)
        champ = self.r.world[rt.plan.champion].iso2
        paste(canvas, flag_card(champ, round(80 * k), shadow=False), self.cx * k, self.cy * k, scale=scale)
        # Pointer at 12 o'clock, bouncing on each tick.
        bounce = 0.0
        for tt, _ in rt.ticks:
            if 0 <= t - tt < 0.08:
                bounce = 1 - (t - tt) / 0.08
        tip_y = (self.cy - RADIUS * scale + 18) * k
        size = 46 * k * scale
        pts = [(self.cx * k - size * 0.6, tip_y - size * 1.2 - bounce * 6 * k),
               (self.cx * k + size * 0.6, tip_y - size * 1.2 - bounce * 6 * k),
               (self.cx * k, tip_y + 10 * k * scale)]
        d = ImageDraw.Draw(canvas)
        d.polygon(pts, fill=(255, 210, 63, 255), outline=(10, 16, 36, 255), width=max(2, round(5 * k)))
