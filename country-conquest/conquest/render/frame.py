"""Composes a complete video frame for any time ``t`` from the timeline.

Layer order: animated sea -> land (countries, owned territory, roulette
highlight) -> paint spread -> flag pins / labels -> battle dim + clash card or
wheel -> HUD counters -> titles and banners.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from ..timeline import Timeline, safe_rect
from ..world import World
from .battle import BattleCard
from .camera import Camera, ease_in_out, ease_out_back, ease_out_cubic
from .fx import burst_ring, panel, paste, pin_sprite
from .hud import draw_hud
from .maplayer import MapRenderer, hex_rgb, shade
from .sea import Sea
from .spinner import Wheel
from .text import TextStyle, flag_emoji, render_text


class FrameRenderer:
    def __init__(self, world: World, timeline: Timeline, width: int, height: int, supersample: int,
                 guides: bool = False):
        self.world = world
        self.tl = timeline
        self.cfg = cfg = timeline.cfg
        self.W, self.H = width, height
        self.k = width / 1080.0
        style = cfg["style"]
        self.map = MapRenderer(world, width, height, supersample, style)
        self.sea = Sea(width, height, style)
        self.highlight_rgb = hex_rgb(style["highlight"])
        self.panel_rgb = hex_rgb(style["panel"])
        self.text_style = TextStyle(font=style["font"], fill=hex_rgb(style["text"]),
                                    accent=hex_rgb(style["accent"]), stroke=hex_rgb(style["text_stroke"]))
        self.safe = safe_rect(cfg)
        self.seed = timeline.plan.seed
        self.battle = BattleCard(self)
        self.wheel = Wheel(self)
        self._land_cache: dict = {}
        self.guides = guides
        # Smooth value noise (half res) that makes the paint front look organic.
        rng = np.random.default_rng(int(self.seed) % (2**32))
        hw, hh = width // 2, height // 2
        small = rng.random((hh // 24 + 2, hw // 24 + 2)).astype(np.float32)
        noise = Image.fromarray((small * 255).astype(np.uint8)).resize((hw, hh), Image.BICUBIC)
        self.paint_noise = np.asarray(noise, np.float32) / 127.5 - 1.0
        yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32)
        self.grid = (xx * 2, yy * 2)

    def name(self, code: str) -> str:
        return self.cfg.get("names", {}).get(code, self.world[code].name).upper()

    # ------------------------------------------------------------------------
    def render(self, t: float) -> Image.Image:
        tl, k, world = self.tl, self.k, self.world
        scene, rt, lt = tl.scene_at(t)
        cam = tl.camera_at(t)
        hold = tl.holdings_at(t)
        champ = hold["champion"]
        owned = set(hold["territory"])
        fills = {c: hold["color"] for c in owned}
        highlight = None
        painting = None

        if scene == "spin" and rt.wheel is None:
            code = self._roulette_country(rt, t)
            if code:
                highlight = code
                if t >= rt.land:   # landed: pulse from highlight into the opponent's colour
                    u = min(1, (t - rt.land) / 0.5)
                    pulse = 0.5 + 0.5 * math.cos((t - rt.land) * 14)
                    base = _mix(self.highlight_rgb, rt.plan.opponent_color, u)
                    fills[code] = _mix(base, (255, 255, 255), 0.35 * pulse * (1 - u))
                else:
                    fills[code] = self.highlight_rgb
        if rt is not None and scene in ("battle", "takeover"):
            fills.setdefault(rt.plan.opponent, rt.plan.opponent_color)
        if scene == "takeover" and rt.paint[0] <= t < rt.plant:
            painting = rt
            # Until the paint dries, the old champion keeps its colour.
            for c in rt.plan.territory:
                fills[c] = rt.plan.champion_color
            fills[rt.plan.opponent] = rt.plan.opponent_color

        land = self._land(cam, fills, owned)
        if highlight:
            land = self.map._outline(land, self.map.mask(cam, [highlight]), (255, 255, 255))
        frame = self.sea.render(t, land.getchannel("A")).convert("RGBA")
        frame.alpha_composite(land)
        if painting is not None:
            self._paint(frame, cam, painting, t)

        self._pins(frame, cam, hold, t)
        if scene == "spin":
            self._spin_overlays(frame, cam, rt, t)
        if scene == "battle":
            dim = min(1, (t - rt.battle[0]) / 0.3) * (1 - max(0.0, (t - (rt.battle[1] - 0.32)) / 0.32))
            self._dim(frame, 0.62 * dim)
            self.battle.draw(frame, rt, t)

        self._hud(frame, hold, t)
        if scene == "intro":
            self._intro(frame, t)
        elif scene == "takeover" and rt.plan.new_champion:
            self._new_champion(frame, rt, t)
        elif scene == "outro":
            self._outro(frame, t)
        if self.guides:
            self._draw_guides(frame)
        return frame.convert("RGB")

    def _draw_guides(self, frame: Image.Image) -> None:
        """Shade the areas TikTok's own UI covers (for checking layouts only)."""
        from PIL import ImageDraw
        k = self.k
        x0, y0, x1, y1 = (v * k for v in self.safe)
        layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        red = (255, 0, 60, 90)
        d.rectangle((0, 0, frame.width, y0), fill=red)
        d.rectangle((0, y1, frame.width, frame.height), fill=red)
        d.rectangle((x1, y0, frame.width, y1), fill=red)
        d.rectangle((0, y0, x0, y1), fill=(255, 0, 60, 40))
        frame.alpha_composite(layer)

    # ---- map layers ---------------------------------------------------------------
    def _land(self, cam: Camera, fills: dict, owned: set) -> Image.Image:
        key = (round(cam.cx, 1), round(cam.cy, 1), round(cam.scale * 1e9, 3), cam.ax, cam.ay,
               tuple(sorted(fills.items())), tuple(sorted(owned)))
        hit = self._land_cache.get(key)
        if hit is None:
            hit = self.map.land_layer(cam, fills, owned)
            if len(self._land_cache) > 3:
                self._land_cache.clear()
            self._land_cache[key] = hit
        return hit

    def _roulette_country(self, rt, t: float) -> str | None:
        current = None
        for i, (tt, code) in enumerate(rt.ticks):
            if t >= tt:
                current = (i, code)
        if current is None:
            return None
        i, code = current
        if len(rt.plan.candidates) == 1 and t < rt.land and i % 2 == 1:
            return None     # a single candidate blinks on and off
        return code

    def _paint(self, frame: Image.Image, cam: Camera, rt, t: float) -> None:
        """Winner's colour spreading across the conquered land like paint."""
        k = self.k
        p0, p1 = rt.paint
        u = ease_out_cubic((t - p0) / (p1 - p0))
        colour = tuple(rt.plan.color_after)
        mask = self.map.mask(cam, rt.paint_targets)
        ox, oy = cam.to_screen(*rt.paint_origin)
        ox, oy = ox * k, oy * k
        r_max = rt.paint_radius_m * cam.scale * k * 1.08 + 30 * k
        radius = u * r_max
        xx, yy = self.grid
        amp = 38 * k
        d = np.hypot(xx - ox, yy - oy) + self.paint_noise * amp * min(1.0, radius / (60 * k))
        front = radius - d
        reveal = np.clip(front / (5 * k) + 0.5, 0, 1)
        wet = np.clip(1 - np.abs(front) / (16 * k), 0, 1) * (u < 0.999)
        half = (frame.width // 2, frame.height // 2)
        m_half = np.asarray(mask.resize(half, Image.BILINEAR), np.float32) / 255.0
        a_fill = Image.fromarray((reveal * m_half * 255).astype(np.uint8)).resize(frame.size, Image.BILINEAR)
        a_wet = Image.fromarray((wet * m_half * 200).astype(np.uint8)).resize(frame.size, Image.BILINEAR)
        a_fill = ImageChops.multiply(a_fill, mask)
        layer = Image.new("RGBA", frame.size, colour + (0,))
        layer.putalpha(a_fill)
        frame.alpha_composite(layer)
        rim = Image.new("RGBA", frame.size, shade(colour, 1.45) + (0,))
        rim.putalpha(ImageChops.multiply(a_wet, mask))
        frame.alpha_composite(rim)

    def _pin_width(self, cam: Camera, code: str, home: bool) -> float:
        extent = math.sqrt(self.world[code].area_km2) * 1000 * cam.scale   # reference px
        if home:
            return min(96, max(48, extent * 0.55))
        return min(70, max(34, extent * 0.42)) if extent > 12 else 0

    def _pins(self, frame: Image.Image, cam: Camera, hold: dict, t: float) -> None:
        """Champion flags planted on owned countries; the newest one drops in."""
        k, world = self.k, self.world
        champ = hold["champion"]
        iso = world[champ].iso2
        phase = int(t * 10) % 10
        planted = []
        # Which pin is mid-animation (dropping in)?
        dropping = {}
        intro_drop = (0.30, champ) if t < 0.9 else None
        if intro_drop:
            dropping[champ] = intro_drop[0] - 0.12
        for rt in self.tl.rounds:
            if rt.plant - 0.12 <= t < rt.plant + 0.6:
                for c in ([rt.plan.opponent] if not rt.plan.new_champion else rt.plan.territory_after):
                    dropping[c] = rt.plant - 0.12
        order = sorted(hold["territory"], key=lambda c: (c != champ, -world[c].area_km2))
        boxes = []
        for code in order:
            home = code == champ
            w = self._pin_width(cam, code, home)
            if w <= 0:
                continue
            ax, ay = cam.to_screen(*world[code].anchor)
            sprite, (bx, by) = pin_sprite(iso, max(8, round(w * k)), phase)
            x, y = ax * k - bx, ay * k - by
            box = (x, y, x + sprite.width, y + sprite.height)
            if not home and any(_overlap(box, b) > 0.35 for b in boxes):
                continue
            if x > frame.width or y > frame.height or x + sprite.width < 0 or y + sprite.height < 0:
                continue
            drop_t = dropping.get(code)
            if drop_t is not None:
                age = t - drop_t
                if age < 0:
                    continue
                u = min(1, age / 0.24)
                fall = (1 - ease_out_back(u, 2.0)) * 140 * k
                s = 1 + 0.35 * (1 - u)
                burst_ring(frame, ax * k, ay * k, age - 0.18, k, colour=(255, 255, 255), max_r=70)
                img = sprite if s == 1 else sprite.resize((round(sprite.width * s), round(sprite.height * s)),
                                                          Image.BILINEAR)
                frame.alpha_composite(img, (max(0, round(ax * k - bx * s)), max(0, round(ay * k - by * s - fall))))
            else:
                frame.alpha_composite(sprite, (max(0, round(x)), max(0, round(y))))
            boxes.append(box)
            planted.append(code)

    def _spin_overlays(self, frame: Image.Image, cam: Camera, rt, t: float) -> None:
        k = self.k
        if rt.wheel is not None:
            self.wheel.draw(frame, rt, t)
        # "WHO'S NEXT?" banner while the spinner runs.
        s0 = rt.spin[0]
        if s0 + 0.05 <= t < rt.land + 0.1:
            age = t - s0 - 0.05
            pop = ease_out_back(min(1, age / 0.25), 1.8)
            fade = 1 - max(0.0, (t - rt.land) / 0.1)
            txt = render_text(self.tl.texts["spin"], round(70 * k), self.text_style)
            wob = 1 + 0.03 * math.sin(age * 10)
            paste(frame, txt, self._cx() * k, (self.safe[1] + 300) * k, scale=pop * wob, alpha=fade)
        # Opponent name tag after landing (after the wheel has gone, in wheel mode).
        tag_t = rt.land + (0.55 if rt.wheel is not None else 0.0)
        if t >= tag_t:
            opp = rt.plan.opponent
            age = t - tag_t
            ax, ay = cam.to_screen(*self.world[opp].anchor)
            tag = render_text(f"{flag_emoji(self.world[opp].iso2)} {self.name(opp)}", round(52 * k),
                              self.text_style)
            bg = panel(round(tag.width + 16 * k), round(tag.height * 0.92), round(tag.height * 0.4),
                       self.panel_rgb + (210,))
            pop = ease_out_back(min(1, age / 0.22), 2.0)
            x = min(max(ax * k, (self.safe[0] * k) + tag.width / 2), self.safe[2] * k - tag.width / 2)
            y = ay * k + 85 * k      # below the country: pins stand above their anchor
            y = min(y, self.safe[3] * k - tag.height / 2)
            paste(frame, bg, x, y, scale=pop)
            paste(frame, tag, x, y + 2 * k, scale=pop)
            burst_ring(frame, ax * k, ay * k, age, k, colour=self.highlight_rgb, max_r=160, life=0.4, width=14)

    def _dim(self, frame: Image.Image, amount: float) -> None:
        if amount <= 0.01:
            return
        overlay = Image.new("RGBA", frame.size, (4, 10, 30, int(255 * amount)))
        frame.alpha_composite(overlay)

    # ---- overlays -----------------------------------------------------------------
    def _cx(self) -> float:
        return (self.safe[0] + self.safe[2]) / 2

    def _hud(self, frame: Image.Image, hold: dict, t: float) -> None:
        tpl = self.cfg["text"]
        count = len(hold["territory"])
        terr = tpl["territory"].format(count=count, COUNTRIES="COUNTRY" if count == 1 else "COUNTRIES",
                                       countries="country" if count == 1 else "countries")
        streak = tpl["streak"].format(streak=hold["streak"]) if hold["streak"] >= 1 else None
        bump, swap = 0.0, 1.0
        for rt in self.tl.rounds:
            age = t - (rt.plant + 0.15)
            if 0 <= age < 0.45:
                bump = math.sin(age / 0.45 * math.pi)
                if rt.plan.new_champion:
                    swap = min(1, age / 0.35)
        alpha = min(1, t / 0.25)
        draw_hud(frame, self.k, self.safe[0] + 6, self.safe[1] + 12, self.world[hold["champion"]].iso2,
                 terr, streak, self.text_style, self.panel_rgb, bump, alpha, swap)

    def _title(self, frame: Image.Image, text: str, cy: float, age: float, size: int = 88,
               alpha: float = 1.0) -> None:
        k = self.k
        txt = render_text(text, round(size * k), self.text_style, max_width=round(840 * k))
        pop = ease_out_back(min(1, max(0.0, age) / 0.35), 1.7)
        if age >= 0:
            paste(frame, txt, self._cx() * k, cy * k, scale=pop, alpha=alpha)

    def _intro(self, frame: Image.Image, t: float) -> None:
        d = self.tl.intro[1]
        fade = 1 - ease_in_out(max(0.0, (t - (d - 0.2)) / 0.2))
        self._title(frame, self.tl.texts["intro"], self.safe[1] + 390, t - 0.15, alpha=fade)

    def _outro(self, frame: Image.Image, t: float) -> None:
        o0 = self.tl.outro[0]
        self._title(frame, self.tl.texts["outro"], self.safe[3] - 170, t - o0 - 0.35, size=86)

    def _new_champion(self, frame: Image.Image, rt, t: float) -> None:
        w = rt.plan.winner
        text = self.cfg["text"]["new_champion"].format(flag=flag_emoji(self.world[w].iso2), name=self.name(w))
        age = t - (rt.takeover[0] + 0.25)
        fade = 1 - max(0.0, (t - (rt.takeover[1] - 0.15)) / 0.15)
        self._title(frame, text, self.safe[1] + 330, age, size=78, alpha=fade)


def _mix(a, b, u: float):
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))


def _overlap(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = (a[2] - a[0]) * (a[3] - a[1])
    return ix * iy / area if area else 0.0
