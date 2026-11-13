"""The battle clash card: split-colour card, both flags, HP bars, hits, sparks, KO.

Game-like visuals only: flags, shapes, sparks and numbers. The blow-by-blow
sequence comes straight from the simulation (``RoundTimes.exchanges``).
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .camera import ease_in_out, ease_out_back, ease_out_cubic
from .flags import flag_card
from .fx import burst_ring, circle, greyed, panel, paste, sparks, star_flash, tinted
from .maplayer import shade
from .text import TextStyle, flag_emoji, render_text

# Card layout in reference pixels, relative to the card's top-left corner.
CARD_H = 640
NAME_Y, FLAG_Y, BAR_Y = 78, 300, 505
FLAG_W, BAR_W, BAR_H = 320, 320, 40
SIDE_INSET = 215          # flag/name centre distance from the card's side edge


def _lerp(a, b, u):
    return a + (b - a) * u


class BattleCard:
    def __init__(self, renderer):
        self.r = renderer
        self.k = renderer.k
        sx0, sy0, sx1, sy1 = renderer.safe
        self.x0, self.x1 = sx0 + 8, sx1 - 8
        self.y0 = sy0 + 375
        self.cx = (self.x0 + self.x1) / 2
        self.w = self.x1 - self.x0

    # ---- static sprites -------------------------------------------------------
    @lru_cache(maxsize=8)
    def _half(self, code: str, side: str, col: tuple) -> Image.Image:
        """One colour half of the card (with the country name), card-sized RGBA."""
        k = self.k
        W, H = round(self.w * k), round(CARD_H * k)
        ss = 2
        base = shade(col, 0.68)
        big = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        slant = 70 * k * ss
        mid = W * ss / 2
        if side == "A":
            poly = [(0, 0), (mid + slant, 0), (mid - slant, H * ss), (0, H * ss)]
        else:
            poly = [(mid + slant, 0), (W * ss, 0), (W * ss, H * ss), (mid - slant, H * ss)]
        d.polygon(poly, fill=base + (255,))
        # Diagonal stripes for a game-card texture.
        stripe = shade(col, 0.78) + (255,)
        step = round(46 * k * ss)
        for off in range(-H * ss, W * ss, step):
            d.line((off, H * ss, off + H * ss, 0), fill=stripe, width=round(14 * k * ss))
        mask = Image.new("L", big.size, 0)
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        rounded = Image.new("L", big.size, 0)
        ImageDraw.Draw(rounded).rounded_rectangle((0, 0, W * ss - 1, H * ss - 1), round(44 * k * ss), fill=255)
        from PIL import ImageChops
        mask = ImageChops.multiply(mask, rounded)
        # Inner top highlight + bottom darkening.
        grad = np.linspace(1.18, 0.78, H * ss, dtype=np.float32)[:, None, None]
        arr = np.asarray(big, np.float32)
        arr[..., :3] = np.clip(arr[..., :3] * grad, 0, 255)
        big = Image.fromarray(arr.astype(np.uint8), "RGBA")
        big.putalpha(mask)
        half = big.resize((W, H), Image.LANCZOS)
        # Country name.
        name = self.r.name(code)
        size = 54
        txt = render_text(name, round(size * k), self.r.text_style)
        while txt.width > 390 * k and size > 26:
            size -= 4
            txt = render_text(name, round(size * k), self.r.text_style)
        nx = SIDE_INSET * k if side == "A" else W - SIDE_INSET * k
        paste(half, txt, nx, NAME_Y * k)
        return half

    @lru_cache(maxsize=4)
    def _frame(self) -> Image.Image:
        """White border + shadow drawn around the whole card."""
        k = self.k
        W, H = round(self.w * k), round(CARD_H * k)
        pad = round(30 * k)
        out = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
        sh = panel(W, H, round(44 * k), (0, 0, 0, 150))
        shl = Image.new("RGBA", out.size, (0, 0, 0, 0))
        shl.alpha_composite(sh, (pad, pad + round(12 * k)))
        out = Image.alpha_composite(out, shl.filter(ImageFilter.GaussianBlur(14 * k)))
        out.alpha_composite(panel(W, H, round(44 * k), (0, 0, 0, 0), (255, 255, 255, 255),
                                  max(2, round(6 * k))), (pad, pad))
        return out

    # ---- per-frame --------------------------------------------------------------
    def draw(self, canvas: Image.Image, rt, t: float) -> None:
        k = self.k
        b0, b1 = rt.battle
        lt = t - b0
        p = rt.plan
        A, B = p.battle.a, p.battle.b
        style = self.r.text_style
        seed = self.r.seed

        # Entry / exit envelope.
        slide = 1 - ease_out_back(min(1, lt / 0.36), 1.2)
        exit_u = ease_in_out(max(0.0, (t - (b1 - 0.32)) / 0.32))
        alpha = 1 - exit_u
        scale_out = 1 - 0.08 * exit_u

        # Shake from the most recent impacts (deterministic).
        shake_x = shake_y = 0.0
        for e in rt.exchanges:
            age = t - e["impact"]
            if 0 <= age < 0.32 and e["kind"] != "miss":
                amp = (22 if e["kind"] == "crit" else 10) * (1 - age / 0.32) ** 2
                shake_x += math.sin(age * 95 + e["impact"] * 7) * amp
                shake_y += math.cos(age * 83 + e["impact"] * 3) * amp * 0.6
        ko_age = t - rt.ko
        if 0 <= ko_age < 0.4:
            amp = 26 * (1 - ko_age / 0.4) ** 2
            shake_x += math.sin(ko_age * 90) * amp
            shake_y += math.cos(ko_age * 70) * amp * 0.6

        ox, oy = shake_x, shake_y
        card_cx = self.cx * k + ox * k
        card_cy = (self.y0 + CARD_H / 2) * k + oy * k

        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        travel = 700 * k
        frame = self._frame()
        paste(layer, frame, card_cx, card_cy, alpha=1 - slide if slide > 0 else 1)
        col = {"A": tuple(p.champion_color), "B": tuple(p.opponent_color)}
        paste(layer, self._half(A, "A", col["A"]), card_cx - travel * slide, card_cy)
        paste(layer, self._half(B, "B", col["B"]), card_cx + travel * slide, card_cy)

        # Flag positions.
        fy = (self.y0 + FLAG_Y) * k + oy * k
        fxa = (self.x0 + SIDE_INSET) * k + ox * k - travel * slide
        fxb = (self.x1 - SIDE_INSET) * k + ox * k + travel * slide
        offs = {"A": [0.0, 0.0], "B": [0.0, 0.0]}
        flash = {"A": 0.0, "B": 0.0}
        for e in rt.exchanges:
            atk, tgt = e["attacker"], ("B" if e["attacker"] == "A" else "A")
            u = (t - e["start"]) / max(0.2, e["spacing"] * 0.9)
            if 0 <= u <= 1:
                push = 48 * math.sin(math.pi * u)
                offs[atk][0] += push if atk == "A" else -push
            age = t - e["impact"]
            if e["kind"] == "miss":
                if 0 <= age + 0.06 < 0.32:
                    offs[tgt][1] -= 40 * math.sin(math.pi * (age + 0.06) / 0.32)
            elif 0 <= age < 0.16:
                flash[tgt] = max(flash[tgt], 1 - age / 0.16)
        # KO: loser tips over and greys out; winner bounces.
        loser = "B" if p.battle.winner == "A" else "A"
        winner = p.battle.winner
        ko_u = ease_out_cubic(min(1, max(0.0, ko_age) / 0.55)) if ko_age >= 0 else 0.0
        win_bounce = 1 + 0.10 * math.sin(min(1, max(0.0, ko_age - 0.15) / 0.45) * math.pi) if ko_age > 0.15 else 1

        for side, fx_, iso, code in (("A", fxa, self.r.world[A].iso2, A), ("B", fxb, self.r.world[B].iso2, B)):
            card = flag_card(iso, round(FLAG_W * k))
            if flash[side] > 0:
                card = tinted(card, (255, 255, 255), flash[side] * 0.85)
            ang, dy, a, sc = 0.0, 0.0, 1.0, 1.0
            if side == loser and ko_u > 0:
                card = greyed(card, ko_u * 0.85)
                ang = (14 if side == "A" else -14) * ko_u
                dy = 70 * ko_u
                a = 1 - 0.35 * ko_u
            if side == winner:
                sc = win_bounce
            paste(layer, card, fx_ + offs[side][0] * k, fy + offs[side][1] * k + dy * k, scale=sc,
                  alpha=a, angle=ang)

        # VS badge pops after the clash.
        vs_age = t - rt.clash
        if vs_age >= 0:
            s = ease_out_back(min(1, vs_age / 0.25), 2.2)
            badge = self._vs_badge()
            paste(layer, badge, card_cx, fy, scale=s * (1 - 0.15 * ko_u))

        # HP bars.
        fill_u = ease_out_cubic(min(1, max(0.0, lt - 0.45) / 0.35))
        for side, cx_ in (("A", fxa), ("B", fxb)):
            cur, ghost, top = self._hp(rt, side, t)
            self._bar(layer, cx_, (self.y0 + BAR_Y) * k + oy * k, cur * fill_u, ghost * fill_u, top,
                      col[side])

        # Impacts: sparks, stars, damage numbers, labels.
        for i, e in enumerate(rt.exchanges):
            age = t - e["impact"]
            if age < 0 or age > 0.8:
                continue
            tgt = "B" if e["attacker"] == "A" else "A"
            tx = fxb if tgt == "B" else fxa
            inner = -1 if tgt == "B" else 1           # spark source: the target's inner edge
            sxp = tx + inner * FLAG_W * 0.42 * k
            if e["kind"] != "miss":
                direction = 0 if tgt == "B" else 180
                crit = e["kind"] == "crit"
                star_flash(layer, sxp, fy, age, k, size=190 if crit else 120)
                sparks(layer, sxp, fy, direction, age, f"{seed}:{p.number}:{i}", k,
                       count=40 if crit else 22, power=1.3 if crit else 1.0)
                if crit:
                    burst_ring(layer, sxp, fy, age, k, max_r=170)
                dmg = render_text(f"-{e['damage']}", round((76 if crit else 60) * k),
                                  TextStyle(fill=(255, 92, 92) if not crit else (255, 210, 63)))
                rise = 70 * ease_out_cubic(min(1, age / 0.6))
                paste(layer, dmg, tx + 30 * k * -inner, fy - 50 * k - rise * k,
                      scale=ease_out_back(min(1, age / 0.12), 2.0),
                      alpha=1 - max(0.0, (age - 0.4) / 0.4))
            label = self._label(e)
            if label:
                pop = ease_out_back(min(1, age / 0.14), 2.0)
                txt = render_text(label[0], round(label[1] * k), TextStyle(accent=label[2]))
                paste(layer, txt, tx, fy + 92 * k, scale=pop, alpha=1 - max(0.0, (age - 0.45) / 0.35),
                      angle=-6 if tgt == "B" else 6)

        # Clash flash at the seam when the halves meet.
        clash_age = t - rt.clash
        star_flash(layer, card_cx, fy, clash_age, k, size=260, life=0.18)
        sparks(layer, card_cx, fy - 120 * k, 90, clash_age, f"{seed}:{p.number}:clash", k, count=30,
               spread=300, power=0.9)
        burst_ring(layer, card_cx, fy, clash_age, k, max_r=260, life=0.35)

        # ROUND ribbon on the card's top edge.
        rib_age = lt - 0.25
        if rib_age >= 0:
            rib = render_text(self.r.cfg["text"]["round"].format(round=p.number), round(62 * k),
                              TextStyle(fill=(255, 210, 63)))
            bg = panel(round(rib.width + 30 * k), round(rib.height * 0.86), round(28 * k),
                       self.r.panel_rgb + (235,), (255, 255, 255, 255), max(2, round(5 * k)))
            s = ease_out_back(min(1, rib_age / 0.25), 1.8)
            ry = self.y0 * k + oy * k
            paste(layer, bg, card_cx, ry, scale=s)
            paste(layer, rib, card_cx, ry + 3 * k, scale=s)

        # KO stamp and winner line.
        if ko_age >= 0.04:
            u = min(1, (ko_age - 0.04) / 0.25)
            stamp = render_text("K.O.!", round(170 * k), TextStyle(fill=(255, 210, 63)))
            paste(layer, stamp, card_cx, fy + 10 * k, scale=_lerp(2.2, 1.0, ease_out_back(u, 1.4)),
                  alpha=min(1, u * 2), angle=-8)
        if ko_age >= 0.3:
            wcode = p.winner
            line = f"{flag_emoji(self.r.world[wcode].iso2)} *{self.r.name(wcode)}* WINS!"
            if p.battle.comeback:
                line += "\nWHAT A COMEBACK!"
            elif p.battle.close:
                line += "\nCLOSE ONE!"
            txt = render_text(line, round(64 * k), style, max_width=round(820 * k))
            u = ease_out_back(min(1, (ko_age - 0.3) / 0.25), 1.6)
            paste(layer, txt, card_cx, (self.y0 + CARD_H + 30) * k + txt.height / 2, scale=u)

        paste(canvas, layer, canvas.width / 2, canvas.height / 2, scale=scale_out, alpha=alpha)

    def _label(self, e):
        tags = e["tags"]
        if e["kind"] == "miss":
            return ("*SO CLOSE!*", 66, (255, 210, 63)) if "near_miss" in tags else ("MISS!", 60, (255, 255, 255))
        if "rally" in tags:
            return ("*RALLY!*", 64, (120, 255, 140))
        if e["kind"] == "crit":
            return ("*CRIT!*", 70, (255, 210, 63))
        return None

    def _hp(self, rt, side: str, t: float):
        """(current HP, trailing 'ghost' HP, max HP) for one side at time t."""
        p = rt.plan.battle
        top = p.max_a if side == "A" else p.max_b
        key, before = ("hp_a", "hp_a_before") if side == "A" else ("hp_b", "hp_b_before")
        cur, ghost = top, top
        for e in rt.exchanges:
            if t < e["impact"]:
                break
            cur = e[key]
            u = ease_out_cubic(min(1, max(0.0, t - e["impact"] - 0.08) / 0.38))
            ghost = _lerp(e[before], e[key], u)
        return cur, max(cur, ghost), top

    def _bar(self, canvas, cx, cy, cur, ghost, top, colour):
        k = self.k
        w, h = round(BAR_W * k), round(BAR_H * k)
        x0, y0 = cx - w / 2, cy - h / 2
        paste(canvas, panel(w + round(10 * k), h + round(10 * k), round(h * 0.6), (10, 16, 36, 255)), cx, cy)
        paste(canvas, panel(w, h, round(h / 2), (40, 46, 66, 255)), cx, cy)
        gw = round(w * ghost / top)
        cw = round(w * cur / top)
        if gw > 2:
            g = panel(gw, h, round(h / 2), (255, 255, 255, 235))
            canvas.alpha_composite(g, (round(x0), round(y0)))
        if cw > 2:
            frac = cur / top
            col = colour if frac > 0.3 else (255, 70, 70)
            bar = panel(cw, h, round(h / 2), col + (255,))
            hi = panel(cw, max(2, h // 3), max(1, h // 6), (255, 255, 255, 70))
            canvas.alpha_composite(bar, (round(x0), round(y0)))
            canvas.alpha_composite(hi, (round(x0), round(y0 + h * 0.12)))
        num = render_text(f"{int(round(cur))}", round(30 * k), self.r.text_style)
        paste(canvas, num, cx, cy + 1 * k)

    @lru_cache(maxsize=2)
    def _vs_badge(self) -> Image.Image:
        k = self.k
        d = round(140 * k)
        img = circle(d, self.r.panel_rgb + (255,), (255, 255, 255, 255), max(2, round(6 * k))).copy()
        vs = render_text("VS", round(70 * k), TextStyle(fill=(255, 210, 63)))
        paste(img, vs, d / 2, d / 2 + 3 * k)
        return img
