"""On-screen graphics: title hook, counters, crack tags, replay tag and the end card.

One signature style for every episode: Inter Display Black, white numbers with a yellow
accent, on dark rounded plates. Everything is laid out in 1080x1920 "design pixels" and
scaled to the output size, so the preview looks the same, only smaller.

TikTok safe zones are respected: nothing in the top 10% (y < 192) or bottom 20%
(y > 1536), and nothing right of x = 900, where the like/comment/share buttons sit.

``Overlay.frame_bytes(f)`` returns raw RGBA bytes for video frame ``f``. make_episode.py
pipes them straight into ffmpeg, which composites them over the 3D render.
"""

import math
import os
from functools import lru_cache

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

SAFE_X0, SAFE_X1 = 64, 900       # right edge kept clear of TikTok's buttons
SAFE_Y0, SAFE_Y1 = 208, 1520     # top 10% and bottom 20% kept clear
CENTER_X = (SAFE_X0 + SAFE_X1) // 2

# End card layout (design px): big counters in the middle, the question below them.
OUTRO_TOP_Y = 500
OUTRO_BOT_Y = 810
OUTRO_CARD_Y = 1210

TAG_WORD = {"glass": "CRACK!", "wood": "CRACK!", "shell": "CRACK!", "fabric": "RIP!"}


def _ease_out_back(t, s=1.7):
    t = min(max(t, 0.0), 1.0) - 1.0
    return t * t * ((s + 1) * t + s) + 1.0


def _ease_in_out(t):
    t = min(max(t, 0.0), 1.0)
    return 3 * t * t - 2 * t * t * t


def _pop(t, amount=0.28, decay=2.6, freq=0.55):
    """Scale multiplier for a counter tick ``t`` frames after it changed."""
    if t < 0 or t > 14:
        return 1.0
    return 1.0 + amount * math.exp(-t / decay) * math.cos(t * freq)


@lru_cache(maxsize=256)
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
        self.replay = seg["replay"]
        self.outro_f = seg["outro"][0]
        self.counter = events["counter"]
        self.crack_frames = [c["frame"] for c in self.counter if c["crack_stage"]]
        tgt = catalog.target(self.cfg["target"])
        self.tag_word = TAG_WORD.get(tgt["material"], "CRACK!")
        self.emoji = Image.open(EMOJI_POINT_DOWN).convert("RGBA") if os.path.exists(EMOJI_POINT_DOWN) else None
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
        self.top_h = self.top_size * 1.12 + 44
        self.bot_h = self.bot_size * 1.02 + 46 + 52
        self.top_y = SAFE_Y0 + 8
        self.bot_y = SAFE_Y1 - self.bot_h

    # ------------------------------------------------------------------ state
    def _count_at(self, f):
        n, changed, stage = 0, -999, 0
        for c in self.counter:
            if c["frame"] <= f:
                n, changed, stage = c["count"], c["frame"], c["crack_stage"]
        if f >= self.break_f:
            n = self.counter[-1]["count"]
        return n, changed, stage

    def _state(self, f):
        """Everything that decides how frame f looks, as a hashable tuple."""
        n, changed, stage = self._count_at(f)
        t_tick = f - changed
        tick = t_tick if t_tick <= 14 else None
        crack = None
        for cf in self.crack_frames:
            if 0 <= f - cf < 26:
                crack = f - cf
        intro = f if f < self.intro_end + 12 else None
        counters_in = min(1.0, max(0.0, (f - (self.intro_end - 2)) / 9.0))
        brk = f - self.break_f if 0 <= f - self.break_f < 18 else None
        rep = None
        if self.replay[0] <= f < self.replay[1]:
            rep = (f - self.replay[0]) // 15 % 2
        outro = f - self.outro_f if f >= self.outro_f else None
        if outro is not None and outro > 40:
            outro = 40 + (outro // 2) % 20      # only the emoji keeps bobbing
        return (n, tick, stage if tick is not None else 0, crack, intro, round(counters_in, 3), brk, rep, outro)

    # ------------------------------------------------------------------ drawing helpers
    def _s(self, v):
        return v * self.k

    def _text(self, draw, xy, text, size, fill, font=FONT_BLACK, anchor="ls", stroke=0, stroke_fill=INK,
              features=None):
        draw.text((self._s(xy[0]), self._s(xy[1])), text, font=_font(font, self._s(size)), fill=fill,
                  anchor=anchor, stroke_width=int(round(self._s(stroke))), stroke_fill=stroke_fill,
                  features=features)

    def _plate(self, img, cx, y, w, h, scale=1.0, border=None, alpha=1.0, dx=0.0):
        """Dark rounded plate centred on cx, top at y (design px). Returns its box."""
        w2, h2 = w * scale, h * scale
        x0 = cx - w2 / 2 + dx
        box = [self._s(x0), self._s(y), self._s(x0 + w2), self._s(y + h2)]
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        fill = (PLATE[0], PLATE[1], PLATE[2], int(PLATE[3] * alpha))
        d.rounded_rectangle(box, radius=self._s(30 * scale), fill=fill,
                            outline=border if border else None,
                            width=int(round(self._s(6 * scale))) if border else 0)
        img.alpha_composite(layer)
        return box

    def _top_counter(self, img, n, cy_top, scale, pop, border, alpha, dx=0.0, red=False):
        self._plate(img, CENTER_X, cy_top, self.plate_w, self.top_h, scale, border, alpha, dx)
        d = ImageDraw.Draw(img)
        size = self.top_size * scale
        label = self.cfg["counter_label_singular"] if n == 1 else self.cfg["counter_label"]
        num = str(n)
        f_num = _font(FONT_BLACK, self._s(size * pop))
        f_lab = _font(FONT_BLACK, self._s(size * 0.62))
        gap = _font(FONT_BLACK, self._s(size)).getlength(" ")
        w_num = f_num.getlength(num, features=["tnum"])
        w_lab = f_lab.getlength(label)
        total = w_num + gap + w_lab
        base_y = self._s(cy_top + (self.top_h * scale) / 2 + size * 0.36)
        x = self._s(CENTER_X + dx) - total / 2
        a = int(255 * alpha)
        col = ALERT if red else WHITE
        d.text((x, base_y), num, font=f_num, fill=col[:3] + (a,), anchor="ls", features=["tnum"])
        d.text((x + w_num + gap, base_y), label, font=f_lab, fill=ACCENT[:3] + (a,), anchor="ls")

    def _bottom_counter(self, img, n, y, scale, pop, border, alpha, dx=0.0, red=False):
        self._plate(img, CENTER_X, y, self.plate_w, self.bot_h, scale, border, alpha, dx)
        d = ImageDraw.Draw(img)
        a = int(255 * alpha)
        lab_size = 40 * scale
        cx = self._s(CENTER_X + dx)
        f_lab = _font(FONT_BOLD, self._s(lab_size))
        d.text((cx, self._s(y + 30 * scale + lab_size * 0.75)), "W E I G H T", font=f_lab,
               fill=ACCENT[:3] + (a,), anchor="ms")
        kg = format_weight(n * self.cfg["drop_mass_kg"])
        f_num = _font(FONT_BLACK, self._s(self.bot_size * scale * pop))
        col = ALERT if red else WHITE
        d.text((cx, self._s(y + self.bot_h * scale - 30 * scale)), kg, font=f_num, fill=col[:3] + (a,),
               anchor="ms", features=["tnum"])

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
        out = []
        for w in self.cfg["title"].upper().split():
            out.append((w, ACCENT if w.strip("?!.,") in hl else WHITE))
        return out

    def _title(self, img, t):
        """The hook: on screen from the very first frame, then flies up and out."""
        words = self._title_words()
        size = 96
        while True:
            f = _font(FONT_BLACK, self._s(size))
            lines = self._wrap(words, f, self._s(SAFE_X1 - SAFE_X0 - 20))
            if len(lines) <= 4 or size <= 56:
                break
            size -= 4
        appear = 0.9 + 0.1 * _ease_out_back(t / 7.0)
        leave = _ease_in_out((t - (self.intro_end - 4)) / 12.0) if t >= self.intro_end - 4 else 0.0
        if leave >= 1.0:
            return
        s = appear * (1.0 - 0.15 * leave)
        alpha = int(255 * (1.0 - leave))
        f = _font(FONT_BLACK, self._s(size * s))
        lh = size * s * 1.08
        y = SAFE_Y0 + 30 - 140 * leave
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for line in lines:
            text = " ".join(w for w, _ in line)
            x = self._s(CENTER_X) - f.getlength(text) / 2
            yy = self._s(y + lh * 0.82)
            for w, col in line:
                # Hard drop shadow, then the outlined word.
                d.text((x + self._s(6), yy + self._s(8)), w, font=f, fill=INK[:3] + (int(alpha * 0.8),),
                       anchor="ls", stroke_width=int(self._s(10)), stroke_fill=INK[:3] + (int(alpha * 0.8),))
                d.text((x, yy), w, font=f, fill=col[:3] + (alpha,), anchor="ls",
                       stroke_width=int(self._s(10)), stroke_fill=INK[:3] + (alpha,))
                x += f.getlength(w + " ")
            y += lh
        img.alpha_composite(layer)
        # "Guess in the comments" pill near the bottom, pointing down at the comments.
        if t >= 5:
            pt = _ease_out_back((t - 5) / 8.0)
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
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
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
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=self._s(14), fill=fill[:3] + (int(255 * alpha),))
        d.text((w / 2, h / 2), text, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
        tag = tag.rotate(-7, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(tag, (int(self._s(cx) - tag.width / 2), int(self._s(y))))

    # ------------------------------------------------------------------ frame
    def render(self, f):
        n, tick, stage, crack, intro, counters_in, brk, rep, outro = self._state(f)
        img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

        if intro is not None:
            self._title(img, intro)

        # Outro: dim the scene and move the counters to the middle, larger.
        o = 0.0
        if outro is not None:
            o = _ease_in_out(outro / 14.0)
            dim = Image.new("RGBA", img.size, INK[:3] + (int(120 * o),))
            img.alpha_composite(dim)

        if counters_in > 0:
            slide = (1.0 - _ease_out_back(counters_in)) * -60
            pop = _pop(tick) if tick is not None else 1.0
            border = None
            red = False
            dx = 0.0
            if tick is not None and tick < 5:
                border = ALERT if stage else ACCENT
            if crack is not None and crack < 12:
                dx = math.sin(crack * 2.1) * 10 * math.exp(-crack / 5.0)
                red = crack < 8
            if brk is not None:
                border = ALERT if brk < 12 else None
                red = brk < 12
            top_y = self.top_y + slide
            bot_y = self.bot_y - slide
            scale_t, scale_b = 1.0, 1.0
            if outro is not None:
                top_y = top_y + (OUTRO_TOP_Y - top_y) * o
                bot_y = bot_y + (OUTRO_BOT_Y - bot_y) * o
                scale_t = 1.0 + 0.30 * o
                scale_b = 1.0 + 0.15 * o
            self._top_counter(img, n, top_y, scale_t, pop, border, counters_in, dx, red)
            self._bottom_counter(img, n, bot_y, scale_b, pop if tick is not None else 1.0,
                                 border, counters_in, dx, red)
            if crack is not None:
                self._tag(img, self.tag_word, CENTER_X + 230, self.top_y + self.top_h - 12, crack)
            if rep is not None:
                self._replay_tag(img, self.top_y + self.top_h + 24, rep)

        if brk is not None and brk < 6:
            flash = Image.new("RGBA", img.size, (255, 255, 255, int(150 * (1 - brk / 6.0))))
            img.alpha_composite(flash)

        if outro is not None:
            t = outro
            a = _ease_in_out((t - 8) / 10.0)
            if a > 0:
                d = ImageDraw.Draw(img)
                self._text(d, (CENTER_X, OUTRO_TOP_Y - 40), "IT BROKE AT", 50, ACCENT[:3] + (int(255 * a),), font=FONT_BOLD,
                           anchor="ms")
            if t >= 12:
                self._end_card(img, t - 12)
        return img

    def _replay_tag(self, img, y, blink):
        d_size = 40
        f = _font(FONT_BLACK, self._s(d_size))
        text = "REPLAY"
        tw = f.getlength(text)
        pad = self._s(22)
        dot = self._s(18)
        w = tw + dot + pad * 3
        h = self._s(d_size * 1.6)
        x0 = self._s(SAFE_X0 + 4)
        y0 = self._s(y)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h / 2, fill=PLATE)
        if blink == 0:
            cy = y0 + h / 2
            d.ellipse([x0 + pad, cy - dot / 2, x0 + pad + dot, cy + dot / 2], fill=ALERT)
        d.text((x0 + pad * 2 + dot, y0 + h / 2), text, font=f, fill=WHITE, anchor="lm")
        img.alpha_composite(layer)

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
            em = self._s(120)
            e = self.emoji.resize((int(em * self.emoji.width / self.emoji.height), int(em)), Image.LANCZOS)
            bob = math.sin(t * 0.32) * self._s(10)
            img.alpha_composite(e, (int(self._s(CENTER_X) - e.width / 2), int(self._s(y - 30) + bob)))

    def frame_bytes(self, f):
        """RGBA bytes for frame f, reusing the previous frame when nothing changed."""
        key = self._state(f)
        if key != self._last_key:
            self._last_bytes = self.render(f).tobytes()
            self._last_key = key
        return self._last_bytes
