"""On-screen motion graphics: title hook, counters, pop-ups, stress meter and end card.

One signature style for every episode: Inter Display Black, white numbers with a yellow
accent, on dark rounded plates, with comic-book energy:

* the title pops in word by word (all of it within the first third of a second)
* counters roll like an odometer and squash-pop on every impact
* "+1" pops up where each object lands, with impact lines around it, and "+X KG"
  floats off the weight counter
* a segmented stress meter lights up stage by stage, with a red vignette pulse and a
  CRACK! stamp
* a giant comic word (SMASH! / SPLAT! / RIIIP!) explodes onto the break, then a
  SLOW-MO tag shows
* a diagonal swipe hides the cut into the replay
* the end card counts the final numbers up

Everything is laid out in 1080x1920 "design pixels" and scaled to the output size.
TikTok safe zones are respected: nothing in the top 10% (y < 192) or bottom 20%
(y > 1536), and nothing right of x = 900, where the like/comment/share buttons sit.

``Overlay.frame_bytes(f)`` returns raw RGBA bytes for video frame ``f``. make_episode.py
pipes them straight into ffmpeg, which composites them over the 3D render.
"""

import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import PROJECT_DIR, catalog
from .config import format_weight

FONT_BLACK = os.path.join(PROJECT_DIR, "fonts", "InterDisplay-Black.otf")
FONT_BOLD = os.path.join(PROJECT_DIR, "fonts", "InterDisplay-ExtraBold.otf")
EMOJI_POINT_DOWN = os.path.join(PROJECT_DIR, "overlay_assets", "point_down.png")

WHITE = (255, 255, 255, 255)
ACCENT = (255, 206, 28, 255)     # signature yellow, same as the hazard stripes
INK = (10, 11, 20, 255)
PLATE = (10, 11, 20, 215)
ALERT = (255, 58, 58, 255)
STAGE_COLOURS = [(255, 206, 28), (255, 150, 30), (255, 95, 40), (255, 50, 50)]

SAFE_X0, SAFE_X1 = 64, 900       # right edge kept clear of TikTok's buttons
SAFE_Y0, SAFE_Y1 = 208, 1520     # top 10% and bottom 20% kept clear
CENTER_X = (SAFE_X0 + SAFE_X1) // 2

# End card layout (design px): big counters in the middle, the question below them.
OUTRO_TOP_Y = 500
OUTRO_BOT_Y = 830
OUTRO_CARD_Y = 1230

TAG_WORD = {"glass": "CRACK!", "wood": "CRACK!", "shell": "CRACK!", "fabric": "RIP!"}
BREAK_WORD = {"glass": "SMASH!", "wood": "CRACK!", "shell": "SPLAT!", "fabric": "RIIIP!"}

POPUP_LIFE = 20      # frames a "+1" stays on screen
BURST_LIFE = 9       # frames the impact lines last
ROLL_FRAMES = 6      # odometer roll duration


def _ease_out_back(t, s=1.7):
    t = min(max(t, 0.0), 1.0) - 1.0
    return t * t * ((s + 1) * t + s) + 1.0


def _ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return 3 * t * t - 2 * t * t * t


def _pop(t, amount=0.28, decay=2.6, freq=0.55):
    """Scale multiplier for a counter tick ``t`` frames after it changed."""
    if t is None or t < 0 or t > 14:
        return 1.0
    return 1.0 + amount * math.exp(-t / decay) * math.cos(t * freq)


@lru_cache(maxsize=512)
def _font(path, size):
    return ImageFont.truetype(path, max(4, int(round(size))))


class Overlay:
    def __init__(self, events, width, height):
        self.ev = events
        self.cfg = events["config"]
        self.W, self.H = width, height
        self.k = width / 1080.0
        self.fps = events["fps"]
        self.total = events["total_frames"]
        seg = events["segments"]
        self.intro_end = seg["intro"][1]
        self.break_f = seg["shatter"][0]
        self.shatter = seg["shatter"]
        self.replay = seg["replay"]
        self.outro_f = seg["outro"][0]
        self.counter = events["counter"]
        self.n_stages = max(1, len(self.cfg["crack_stages"]))
        self.crack_frames = [c["frame"] for c in self.counter if c["crack_stage"]]
        self.impacts = [e for e in events["events"]
                        if e["type"] == "impact" and not e.get("replay") and not e.get("final")]
        tgt = catalog.target(self.cfg["target"])
        self.tag_word = TAG_WORD.get(tgt["material"], "CRACK!")
        self.break_word = BREAK_WORD.get(tgt["material"], "SMASH!")
        self.emoji = Image.open(EMOJI_POINT_DOWN).convert("RGBA") if os.path.exists(EMOJI_POINT_DOWN) else None
        self._vignette = None
        self._layout()
        self._last_key = None
        self._last_bytes = None

    # ------------------------------------------------------------------ layout
    def _layout(self):
        """Fix font sizes and plate widths once per episode so nothing jumps around."""
        n_max = self.cfg["break_at"]
        label = self.cfg["counter_label"]
        widest_num = "8" * len(str(n_max))
        w_kg = format_weight(n_max * self.cfg["drop_mass_kg"])
        widest_kg = "".join("8" if ch.isdigit() else ch for ch in w_kg)
        inner = (SAFE_X1 - SAFE_X0) - 2 * 40
        size = 150
        while size > 60:
            w = (_font(FONT_BLACK, size).getlength(widest_num + " ")
                 + _font(FONT_BLACK, size * 0.62).getlength(label))
            if w <= inner:
                break
            size -= 4
        self.top_size = size
        self.top_w = w + 2 * 40
        bsize = 124
        while bsize > 50 and _font(FONT_BLACK, bsize).getlength(widest_kg) > inner:
            bsize -= 4
        self.bot_size = bsize
        self.bot_w = _font(FONT_BLACK, bsize).getlength(widest_kg) + 2 * 40
        self.plate_w = max(self.top_w, self.bot_w, 520)
        self.meter_h = 30                                   # stress meter strip in the top plate
        self.top_h = self.top_size * 1.12 + 44 + self.meter_h
        self.bot_h = self.bot_size * 1.02 + 46 + 52
        self.top_y = SAFE_Y0 + 8
        self.bot_y = SAFE_Y1 - self.bot_h

    # ------------------------------------------------------------------ state
    def _count_at(self, f):
        n, prev, changed, stage = 0, 0, -999, 0
        stages_lit, lit_at = 0, -999
        for c in self.counter:
            if c["frame"] <= f:
                prev, n, changed, stage = n, c["count"], c["frame"], c["crack_stage"]
                if c["crack_stage"]:
                    stages_lit, lit_at = c["crack_stage"], c["frame"]
        if f >= self.break_f:
            n = self.counter[-1]["count"]
        return n, prev, changed, stage, stages_lit, lit_at

    def _state(self, f):
        """Everything that decides how frame f looks, as a hashable tuple."""
        n, prev, changed, stage, lit, lit_at = self._count_at(f)
        t_tick = f - changed
        tick = t_tick if 0 <= t_tick <= 14 and f < self.break_f else None
        crack = next((f - cf for cf in self.crack_frames if 0 <= f - cf < 26), None)
        intro = f if f < self.intro_end + 12 else None
        counters_in = min(1.0, max(0.0, (f - (self.intro_end - 2)) / 9.0))
        brk = f - self.break_f if 0 <= f - self.break_f < 30 else None
        slowmo = (f - self.shatter[0]) // 12 % 2 if self.shatter[0] + 22 <= f < self.shatter[1] else None
        rep = (f - self.replay[0]) // 15 % 2 if self.replay[0] <= f < self.replay[1] else None
        swipe = f - (self.replay[0] - 8) if -1 < f - (self.replay[0] - 8) < 16 else None
        outro = f - self.outro_f if f >= self.outro_f else None
        if outro is not None and outro > 40:
            outro = 40 + (outro // 2) % 20      # only the emoji keeps bobbing
        pops = tuple(i for i, e in enumerate(self.impacts) if 0 <= f - e["frame"] < POPUP_LIFE)
        pop_t = tuple(f - self.impacts[i]["frame"] for i in pops)
        lit_t = f - lit_at if 0 <= f - lit_at < 10 else None
        return (n, prev, tick, stage, lit, lit_t, crack, intro, round(counters_in, 3), brk, slowmo, rep,
                swipe, outro, pops, pop_t)

    # ------------------------------------------------------------------ helpers
    def _s(self, v):
        return v * self.k

    def _layer(self):
        return Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def _plate(self, img, cx, y, w, h, scale=1.0, border=None, alpha=1.0, dx=0.0):
        """Dark rounded plate centred on cx, top at y (design px). Returns its pixel box."""
        w2, h2 = w * scale, h * scale
        x0 = cx - w2 / 2 + dx
        box = [self._s(x0), self._s(y), self._s(x0 + w2), self._s(y + h2)]
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        fill = (PLATE[0], PLATE[1], PLATE[2], int(PLATE[3] * alpha))
        d.rounded_rectangle(box, radius=self._s(30 * scale), fill=fill,
                            outline=border if border else None,
                            width=int(round(self._s(6 * scale))) if border else 0)
        img.alpha_composite(layer)
        return box

    def _rolling(self, img, box, old, new, t_roll, font, colour, anchor_x, base_y, align="right"):
        """Draw a number that rolls from ``old`` to ``new`` like an odometer, clipped to box."""
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        clip = Image.new("RGBA", (max(1, x1 - x0), max(1, y1 - y0)), (0, 0, 0, 0))
        d = ImageDraw.Draw(clip)
        anchor = {"right": "rs", "center": "ms", "left": "ls"}[align]
        if t_roll is None or t_roll >= ROLL_FRAMES or old == new:
            d.text((anchor_x - x0, base_y - y0), new, font=font, fill=colour, anchor=anchor, features=["tnum"])
        else:
            e = _ease_out(t_roll / float(ROLL_FRAMES))
            travel = font.size * 1.15
            fade = colour[:3] + (int(colour[3] * (1 - e)),)
            d.text((anchor_x - x0, base_y - y0 - e * travel), old, font=font, fill=fade, anchor=anchor,
                   features=["tnum"])
            d.text((anchor_x - x0, base_y - y0 + (1 - e) * travel), new, font=font, fill=colour, anchor=anchor,
                   features=["tnum"])
        img.alpha_composite(clip, (x0, y0))

    # ------------------------------------------------------------------ counters
    def _top_counter(self, img, n, prev, top_y, scale, pop, border, alpha, dx, red, tick, lit, lit_t,
                     meter=True):
        box = self._plate(img, CENTER_X, top_y, self.plate_w, self.top_h, scale, border, alpha, dx)
        size = self.top_size * scale
        label = self.cfg["counter_label_singular"] if n == 1 else self.cfg["counter_label"]
        f_num = _font(FONT_BLACK, self._s(size * pop))
        f_lab = _font(FONT_BLACK, self._s(size * 0.62))
        gap = _font(FONT_BLACK, self._s(size)).getlength(" ")
        w_num = f_num.getlength(str(n), features=["tnum"])
        total = w_num + gap + f_lab.getlength(label)
        content_h = (self.top_h - self.meter_h) * scale
        base_y = self._s(top_y) + self._s(content_h / 2 + size * 0.36)
        x = self._s(CENTER_X + dx) - total / 2
        a = int(255 * alpha)
        col = (ALERT if red else WHITE)[:3] + (a,)
        inner = [box[0], box[1] + self._s(6 * scale), box[2], box[1] + self._s(content_h)]
        self._rolling(img, inner, str(prev), str(n), tick, f_num, col, x + w_num, base_y)
        d = ImageDraw.Draw(img)
        d.text((x + w_num + gap, base_y), label, font=f_lab, fill=ACCENT[:3] + (a,), anchor="ls")
        if meter:
            self._meter(img, box, scale, lit, lit_t, alpha)

    def _meter(self, img, box, scale, lit, lit_t, alpha):
        """Segmented stress meter along the bottom of the top plate."""
        d = ImageDraw.Draw(img)
        pad = self._s(26 * scale)
        y1 = box[3] - self._s(14 * scale)
        y0 = y1 - self._s(14 * scale)
        x0, x1 = box[0] + pad, box[2] - pad
        n = self.n_stages
        gap = self._s(8 * scale)
        seg_w = (x1 - x0 - gap * (n - 1)) / n
        for i in range(n):
            sx = x0 + i * (seg_w + gap)
            if i < lit:
                c = STAGE_COLOURS[min(3, int(i * 4 / n))]
                grow = 0.0
                if i == lit - 1 and lit_t is not None:
                    grow = self._s(6) * math.exp(-lit_t / 3.0)
                    if lit_t < 3:
                        c = (255, 255, 255)
                d.rounded_rectangle([sx - grow, y0 - grow, sx + seg_w + grow, y1 + grow], radius=self._s(5),
                                    fill=c + (int(255 * alpha),))
            else:
                d.rounded_rectangle([sx, y0, sx + seg_w, y1], radius=self._s(5),
                                    fill=(255, 255, 255, int(40 * alpha)))

    def _bottom_counter(self, img, n, prev, y, scale, pop, border, alpha, dx, red, tick):
        box = self._plate(img, CENTER_X, y, self.plate_w, self.bot_h, scale, border, alpha, dx)
        d = ImageDraw.Draw(img)
        a = int(255 * alpha)
        lab_size = 40 * scale
        cx = self._s(CENTER_X + dx)
        d.text((cx, self._s(y + 30 * scale + lab_size * 0.75)), "W E I G H T", font=_font(FONT_BOLD, self._s(lab_size)),
               fill=ACCENT[:3] + (a,), anchor="ms")
        f_num = _font(FONT_BLACK, self._s(self.bot_size * scale * pop))
        col = (ALERT if red else WHITE)[:3] + (a,)
        base_y = self._s(y + self.bot_h * scale - 30 * scale)
        inner = [box[0], self._s(y + 30 * scale + lab_size), box[2], box[3] - self._s(4)]
        new = format_weight(n * self.cfg["drop_mass_kg"])
        old = format_weight(prev * self.cfg["drop_mass_kg"])
        self._rolling(img, inner, old, new, tick, f_num, col, cx, base_y, align="center")

    # ------------------------------------------------------------------ comic bits
    def _impact_fx(self, img, idx, t):
        """Impact lines and a "+1" pop-up where an object lands."""
        e = self.impacts[idx]
        sx, sy = e.get("screen", [0.5, 0.5])
        x = min(max(sx * 1080, SAFE_X0 + 70), SAFE_X1 - 70)
        y = min(max(sy * 1920, self.top_y + self.top_h + 60), self.bot_y - 60)
        big = e["count"] in self.cfg["crack_stages"]
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        if t < BURST_LIFE:
            u = t / float(BURST_LIFE)
            r_in = (40 + 70 * _ease_out(u)) * (1.5 if big else 1.0)
            r_out = r_in + (34 if big else 24) * (1 - u)
            alpha = int(255 * (1 - u ** 2))
            rot = (e["frame"] * 0.7) % (math.pi * 2)
            for i in range(10):
                a = rot + i * math.pi * 2 / 10
                p0 = (self._s(x + math.cos(a) * r_in), self._s(y + math.sin(a) * r_in * 0.8))
                p1 = (self._s(x + math.cos(a) * r_out), self._s(y + math.sin(a) * r_out * 0.8))
                d.line([p0, p1], fill=INK[:3] + (alpha,), width=int(self._s(12)))
                d.line([p0, p1], fill=(ACCENT if not big else ALERT)[:3] + (alpha,), width=int(self._s(6)))
        # "+1" rising and fading.
        s = 0.5 + 0.5 * _ease_out_back(t / 5.0)
        rise = 120 * _ease_out(t / float(POPUP_LIFE))
        fade = 1.0 if t < POPUP_LIFE - 6 else (POPUP_LIFE - t) / 6.0
        f = _font(FONT_BLACK, self._s((96 if big else 76) * s))
        a = int(255 * fade)
        d.text((self._s(x), self._s(y - 50 - rise)), "+1", font=f, fill=(ACCENT if not big else ALERT)[:3] + (a,),
               anchor="ms", stroke_width=int(self._s(9)), stroke_fill=INK[:3] + (a,))
        img.alpha_composite(layer)

    def _kg_popup(self, img, idx, t, alpha):
        """Small "+X KG" floating up off the weight counter."""
        kg = format_weight(self.cfg["drop_mass_kg"])
        rise = 70 * _ease_out(t / float(POPUP_LIFE))
        fade = (1.0 if t < POPUP_LIFE - 6 else (POPUP_LIFE - t) / 6.0) * alpha
        d = ImageDraw.Draw(img)
        x = CENTER_X + self.plate_w / 2 - 40
        y = self.bot_y - 10 - rise
        a = int(255 * fade)
        d.text((self._s(x), self._s(y)), "+" + kg, font=_font(FONT_BLACK, self._s(44)), fill=ACCENT[:3] + (a,),
               anchor="rs", stroke_width=int(self._s(6)), stroke_fill=INK[:3] + (a,))

    def _vignette_pulse(self, img, t):
        if self._vignette is None:
            yy, xx = np.mgrid[0:self.H, 0:self.W]
            nx = (xx / self.W - 0.5) * 2
            ny = (yy / self.H - 0.5) * 2
            r = np.sqrt(nx ** 2 * 0.9 + ny ** 2 * 0.6)
            self._vignette = np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6
        strength = 0.55 * math.exp(-t / 4.0)
        a = (self._vignette * 255 * strength).astype(np.uint8)
        layer = Image.new("RGBA", (self.W, self.H), ALERT[:3] + (0,))
        layer.putalpha(Image.fromarray(a, "L"))
        img.alpha_composite(layer)

    def _tag(self, img, text, cx, y, t, fill=ALERT, life=26):
        """Small tilted stamp (CRACK!) that pops in and fades."""
        if t < 0 or t >= life:
            return
        s = 0.55 + 0.45 * _ease_out_back(t / 6.0)
        alpha = 1.0 if t < life - 6 else (life - t) / 6.0
        size = 58 * s
        f = _font(FONT_BLACK, self._s(size))
        tw = f.getlength(text)
        pad = self._s(size * 0.45)
        w, h = int(tw + 2 * pad), int(self._s(size * 1.45))
        tag = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(tag)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=self._s(14), fill=fill[:3] + (int(255 * alpha),),
                            outline=INK[:3] + (int(255 * alpha),), width=int(self._s(4)))
        d.text((w / 2, h / 2), text, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
        tag = tag.rotate(-7, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(tag, (int(self._s(cx) - tag.width / 2), int(self._s(y))))

    def _break_word(self, img, t):
        """Giant comic word exploding onto the break."""
        if t >= 28:
            return
        s = 0.25 + 0.85 * _ease_out_back(t / 7.0, s=2.4)
        fade = 1.0 if t < 20 else (28 - t) / 8.0
        shake = 14 * math.exp(-t / 5.0)
        size = int(self._s(190))
        f = _font(FONT_BLACK, size)
        tw = f.getlength(self.break_word)
        cw, ch = int(tw + size * 1.2), int(size * 2.4)
        spr = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        d = ImageDraw.Draw(spr)
        cx, cy = cw / 2, ch / 2
        pts = []
        for i in range(28):
            a = i * math.pi * 2 / 28
            r = (0.5 if i % 2 else 0.36) * (1 + 0.12 * math.sin(i * 7.3))
            pts.append((cx + math.cos(a) * r * cw, cy + math.sin(a) * r * ch * 0.85))
        d.polygon(pts, fill=ALERT[:3] + (255,), outline=INK[:3] + (255,), width=int(self._s(8)))
        d.text((cx, cy), self.break_word, font=f, fill=ACCENT, anchor="mm", stroke_width=int(self._s(14)),
               stroke_fill=INK)
        spr = spr.rotate(-8 + 3 * math.sin(t * 0.9), resample=Image.BICUBIC, expand=True)
        w2, h2 = max(1, int(spr.width * s)), max(1, int(spr.height * s))
        spr = spr.resize((w2, h2), Image.BICUBIC)
        if fade < 1.0:
            spr.putalpha(spr.getchannel("A").point(lambda v: int(v * fade)))
        x = self._s(CENTER_X) - w2 / 2 + self._s(shake * math.sin(t * 2.7))
        y = self._s(700) - h2 / 2 + self._s(shake * math.cos(t * 3.1))
        img.alpha_composite(spr, (int(x), int(y)))

    def _side_tag(self, img, y, text, dot_on, dot_colour=ALERT):
        f = _font(FONT_BLACK, self._s(40))
        tw = f.getlength(text)
        pad, dot = self._s(22), self._s(18)
        w, h = tw + dot + pad * 3, self._s(64)
        x0, y0 = self._s(SAFE_X0 + 4), self._s(y)
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h / 2, fill=PLATE)
        if dot_on:
            cy = y0 + h / 2
            d.ellipse([x0 + pad, cy - dot / 2, x0 + pad + dot, cy + dot / 2], fill=dot_colour)
        d.text((x0 + pad * 2 + dot, y0 + h / 2), text, font=f, fill=WHITE, anchor="lm")
        img.alpha_composite(layer)

    def _swipe(self, img, t):
        """Diagonal accent band sweeping across the screen to cover the cut to the replay."""
        u = t / 15.0
        cx = -700 + 2500 * _ease_in_out(u)
        band = 760
        slant = 260
        pts = [(cx - band / 2 + slant, 0), (cx + band / 2 + slant, 0), (cx + band / 2 - slant, 1920),
               (cx - band / 2 - slant, 1920)]
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        d.polygon([(self._s(px), self._s(py)) for px, py in pts], fill=ACCENT[:3] + (255,))
        for off in (-band / 2, band / 2):
            d.line([(self._s(cx + off + slant), 0), (self._s(cx + off - slant), self._s(1920))], fill=INK,
                   width=int(self._s(18)))
        d.text((self._s(cx), self._s(960)), "REPLAY", font=_font(FONT_BLACK, self._s(130)), fill=INK, anchor="mm")
        img.alpha_composite(layer)

    def _wrap(self, words, font, max_w):
        lines, cur = [], []
        for w in words:
            trial = " ".join([x for x, _ in cur] + [w[0]])
            if cur and font.getlength(trial) > max_w:
                lines.append(cur)
                cur = []
            cur.append(w)
        if cur:
            lines.append(cur)
        return lines

    def _title_words(self):
        """Title words, with the drop object and target highlighted in the accent colour."""
        obj = catalog.drop_object(self.cfg["drop_object"])
        tgt = catalog.target(self.cfg["target"])
        hl = set()
        for phrase in (obj["plural"], obj["singular"], tgt["name"], self.cfg["counter_label"]):
            for w in phrase.upper().split():
                hl.add(w.strip("?!.,"))
        return [(w, ACCENT if w.strip("?!.,") in hl else WHITE) for w in self.cfg["title"].upper().split()]

    def _title(self, img, t):
        """The hook: words pop in one by one (all on screen by frame ~10), then fly out."""
        words = self._title_words()
        size = 96
        while True:
            f = _font(FONT_BLACK, self._s(size))
            lines = self._wrap(words, f, self._s(SAFE_X1 - SAFE_X0 - 20))
            if len(lines) <= 4 or size <= 56:
                break
            size -= 4
        leave = _ease_in_out((t - (self.intro_end - 4)) / 12.0) if t >= self.intro_end - 4 else 0.0
        if leave >= 1.0:
            return
        alpha = int(255 * (1.0 - leave))
        f_full = _font(FONT_BLACK, self._s(size))
        lh = size * 1.08
        y = SAFE_Y0 + 30 - 140 * leave
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        k = 0
        for line in lines:
            text = " ".join(w for w, _ in line)
            x = self._s(CENTER_X) - f_full.getlength(text) / 2
            yy = self._s(y + lh * 0.82)
            for w, col in line:
                ww = f_full.getlength(w)
                appear = t - k * 1.2                       # stagger: a word every 1.2 frames
                s = 0.45 + 0.55 * _ease_out_back(appear / 6.0, s=1.3) if appear >= 0 else 0.0
                if s > 0:
                    fw = _font(FONT_BLACK, self._s(size * s))
                    cxw = x + ww / 2
                    sw = int(self._s(10))
                    d.text((cxw + self._s(6), yy + self._s(8)), w, font=fw, anchor="ms",
                           fill=INK[:3] + (int(alpha * 0.8),), stroke_width=sw,
                           stroke_fill=INK[:3] + (int(alpha * 0.8),))
                    d.text((cxw, yy), w, font=fw, fill=col[:3] + (alpha,), anchor="ms", stroke_width=sw,
                           stroke_fill=INK[:3] + (alpha,))
                x += f_full.getlength(w + " ")
                k += 1
            y += lh
        img.alpha_composite(layer)
        if t >= 8:
            pt = _ease_out_back((t - 8) / 8.0)
            self._pill(img, CENTER_X, SAFE_Y1 - 150 + 60 * leave, "GUESS IN THE COMMENTS",
                       58 * (0.7 + 0.3 * pt), t, alpha=(1.0 - leave))

    def _pill(self, img, cx, y, text, size, t, alpha=1.0, fill=ACCENT, color=INK, emoji=True):
        # Shrink to fit the safe width (the pill must stay clear of TikTok's buttons).
        while True:
            f = _font(FONT_BLACK, self._s(size))
            tw = f.getlength(text)
            em = self._s(size * 1.5) if (emoji and self.emoji) else 0
            pad = self._s(size * 0.55)
            w = tw + em + pad * 2 + (pad * 0.4 if em else 0)
            if w <= self._s(SAFE_X1 - SAFE_X0) or size < 20:
                break
            size *= 0.95
        h = self._s(size * 1.6)
        x0 = self._s(cx) - w / 2
        y0 = self._s(y)
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        a = int(255 * alpha)
        d.rounded_rectangle([x0 + self._s(6), y0 + self._s(8), x0 + w + self._s(6), y0 + h + self._s(8)],
                            radius=h / 2, fill=INK[:3] + (int(a * 0.7),))
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h / 2, fill=fill[:3] + (a,))
        d.text((x0 + pad, y0 + h / 2), text, font=f, fill=color[:3] + (a,), anchor="lm")
        img.alpha_composite(layer)
        if em:
            bob = math.sin(t * 0.45) * self._s(6)
            e = self.emoji.resize((int(em * self.emoji.width / self.emoji.height), int(em)), Image.LANCZOS)
            if alpha < 1.0:
                e.putalpha(e.getchannel("A").point(lambda v: int(v * alpha)))
            img.alpha_composite(e, (int(x0 + pad + tw + pad * 0.4), int(y0 + (h - em) / 2 + bob)))

    def _end_card(self, img, t):
        pt = _ease_out_back(t / 9.0)
        words = [(w, WHITE) for w in "WHAT SHOULD WE BREAK NEXT?".split()]
        size = 84 * (0.85 + 0.15 * pt)
        f = _font(FONT_BLACK, self._s(size))
        lines = self._wrap(words, f, self._s(SAFE_X1 - SAFE_X0 - 40))
        y = OUTRO_CARD_Y
        d = ImageDraw.Draw(img)
        a = int(255 * min(1.0, t / 5.0))
        for line in lines:
            text = " ".join(w for w, _ in line)
            d.text((self._s(CENTER_X + 5), self._s(y + 7)), text, font=f, fill=INK[:3] + (int(a * 0.8),),
                   anchor="ms", stroke_width=int(self._s(10)), stroke_fill=INK[:3] + (int(a * 0.8),))
            d.text((self._s(CENTER_X), self._s(y)), text, font=f, fill=WHITE[:3] + (a,), anchor="ms",
                   stroke_width=int(self._s(10)), stroke_fill=INK[:3] + (a,))
            y += size * 1.1
        if self.emoji is not None and t >= 6:
            em = self._s(110)
            e = self.emoji.resize((int(em * self.emoji.width / self.emoji.height), int(em)), Image.LANCZOS)
            bob = math.sin(t * 0.32) * self._s(10)
            img.alpha_composite(e, (int(self._s(CENTER_X) - e.width / 2), int(self._s(y - 34) + bob)))

    # ------------------------------------------------------------------ frame
    def render(self, f):
        (n, prev, tick, stage, lit, lit_t, crack, intro, counters_in, brk, slowmo, rep, swipe, outro,
         pops, pop_t) = self._state(f)
        img = self._layer()

        if intro is not None:
            self._title(img, intro)

        if crack is not None and crack < 12:
            self._vignette_pulse(img, crack)

        for idx, t in zip(pops, pop_t):
            self._impact_fx(img, idx, t)

        o = 0.0
        if outro is not None:
            o = _ease_in_out(outro / 14.0)
            img.alpha_composite(Image.new("RGBA", img.size, INK[:3] + (int(120 * o),)))

        if counters_in > 0:
            slide = (1.0 - _ease_out_back(counters_in)) * -60
            pop = _pop(tick)
            border, red, dx = None, False, 0.0
            if tick is not None and tick < 5:
                border = ALERT if stage else ACCENT
            if crack is not None and crack < 12:
                dx = math.sin(crack * 2.1) * 10 * math.exp(-crack / 5.0)
                red = crack < 8
            if brk is not None and brk < 12:
                border, red = ALERT, True
            top_y, bot_y = self.top_y + slide, self.bot_y - slide
            scale_t = scale_b = 1.0
            shown, shown_prev, roll = n, prev, tick
            if outro is not None:
                top_y += (OUTRO_TOP_Y - top_y) * o
                bot_y += (OUTRO_BOT_Y - bot_y) * o
                scale_t, scale_b = 1.0 + 0.30 * o, 1.0 + 0.15 * o
                # Final tally: count up from zero as the counters slide to the middle.
                c = _ease_out(min(outro, 22) / 22.0)
                shown, shown_prev, roll = int(round(n * c)), int(round(n * c)), None
                pop = _pop(outro - 22) if outro >= 22 else 1.0
            self._top_counter(img, shown, shown_prev, top_y, scale_t, pop, border, counters_in, dx, red, roll,
                              lit if outro is None else self.n_stages, lit_t, meter=outro is None)
            self._bottom_counter(img, shown, shown_prev, bot_y, scale_b, pop if (tick is not None or outro) else 1.0,
                                 border, counters_in, dx, red, roll)
            for idx, t in zip(pops, pop_t):
                self._kg_popup(img, idx, t, counters_in)
            if crack is not None:
                self._tag(img, self.tag_word, CENTER_X + 230, self.top_y + self.top_h - 12, crack)
            side_y = self.top_y + self.top_h + 24
            if slowmo is not None:
                self._side_tag(img, side_y, "SLOW-MO", slowmo == 0, ACCENT)
            if rep is not None:
                self._side_tag(img, side_y, "REPLAY", rep == 0)

        if brk is not None:
            if brk < 6:
                img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, int(150 * (1 - brk / 6.0)))))
            self._break_word(img, brk)

        if swipe is not None:
            self._swipe(img, swipe)

        if outro is not None:
            a = _ease_in_out((outro - 8) / 10.0)
            if a > 0:
                d = ImageDraw.Draw(img)
                d.text((self._s(CENTER_X), self._s(OUTRO_TOP_Y - 40)), "IT BROKE AT",
                       font=_font(FONT_BOLD, self._s(50)), fill=ACCENT[:3] + (int(255 * a),), anchor="ms")
            if outro >= 12:
                self._end_card(img, outro - 12)
        return img

    def frame_bytes(self, f):
        """RGBA bytes for frame f, reusing the previous frame when nothing changed."""
        key = self._state(f)
        if key != self._last_key:
            self._last_bytes = self.render(f).tobytes()
            self._last_key = key
        return self._last_bytes
