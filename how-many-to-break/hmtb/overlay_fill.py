"""Motion graphics for 'fill' episodes ("How many ___ to fill ___?").

Same signature style as the break episodes (hmtb/overlay.py), different layout:

* both counters live in one plate at the top: a big number ("13.46") with its scale
  and label ("BILLION PHONES") and the weight under it, so the tall container gets the
  rest of the frame
* a height marker rides the fill level on the left ("312 M - FLOOR 87")
* fact callouts pop in at milestones
* FULL! explodes when it's full
* the answer card shows the count, weight, a comparison, the question and the maths
"""

import math

from PIL import Image, ImageDraw

from .fill import big_mass, big_number
from .overlay import (ACCENT, ALERT, CENTER_X, FONT_BLACK, FONT_BOLD, INK, POPUP_LIFE, SAFE_X0, SAFE_X1,
                      SAFE_Y0, SAFE_Y1, WHITE, Overlay, _ease_in_out, _ease_out, _ease_out_back, _font, _pop)

CALLOUT_LIFE = 66        # frames a milestone callout stays up


class FillOverlay(Overlay):
    def __init__(self, events, width, height):
        self.ev = events
        self.cfg = events["config"]
        self.W, self.H = width, height
        self.k = width / 1080.0
        self.fps = events["fps"]
        self.total = events["total_frames"]
        seg = events["segments"]
        self.intro_end = seg["hook"][1]
        self.zoom_end = seg["zoom"][1]
        self.full_f = seg["full"][0]
        self.outro_f = seg["outro"][0]
        self.count = events["count"]
        self.level = events["level_m"]
        self.ruler = {int(k): v for k, v in events["ruler"].items()}
        self.floor_h = events.get("floor_height_m", 3.59)
        self.h_occ = events.get("h_occ", 585.0)
        self.drop = next(e for e in events["events"] if e["type"] == "drop")
        self.milestones = [e for e in events["events"] if e["type"] == "milestone"]
        self.break_word = "FULL!"
        self.end_question = self.cfg.get("end_question", "WHAT SHOULD WE FILL NEXT?")
        self.outro_card_y = 1020
        from .overlay import EMOJI_POINT_DOWN
        import os
        self.emoji = Image.open(EMOJI_POINT_DOWN).convert("RGBA") if os.path.exists(EMOJI_POINT_DOWN) else None
        self._vignette = None
        self.plate_w = SAFE_X1 - SAFE_X0 - 40
        self.plate_h = 250
        self.top_y = SAFE_Y0 + 8
        self._last_key = None
        self._last_bytes = None

    def _title_words(self):
        hl = {w.upper() for w in self.cfg.get("highlight", [])} or {"PHONES"}
        return [(w, ACCENT if w.strip("?!.,") in hl else WHITE) for w in self.cfg["title"].upper().split()]

    # ------------------------------------------------------------------ state
    def _state(self, f):
        intro = f if f < self.intro_end + 12 else None
        counters_in = min(1.0, max(0.0, (f - (self.intro_end - 2)) / 9.0))
        count = self.count[min(f, len(self.count) - 1)]
        callout = tuple((i, f - m["frame"]) for i, m in enumerate(self.milestones) if 0 <= f - m["frame"] < CALLOUT_LIFE)
        drop_t = f - self.drop["frame"] if 0 <= f - self.drop["frame"] < POPUP_LIFE else None
        full = f - self.full_f if 0 <= f - self.full_f < 30 else None
        outro = f - self.outro_f if f >= self.outro_f else None
        if outro is not None and outro > 50:
            outro = 50 + (outro // 2) % 20
        ruler = tuple(self.ruler.get(f, ())) if self.zoom_end <= f < self.outro_f else None
        return (round(count, 0), intro, round(counters_in, 3), callout, drop_t, full, outro, ruler,
                round(self.level[min(f, len(self.level) - 1)], 1))

    # ------------------------------------------------------------------ pieces
    def _counter(self, img, count, top_y, scale, alpha, pop=1.0, final=False):
        """One plate: big number, its scale + label, and the weight under it."""
        w, h = self.plate_w * scale, self.plate_h * scale
        self._plate(img, CENTER_X, top_y, self.plate_w, self.plate_h, scale, None, alpha)
        d = ImageDraw.Draw(img)
        a = int(255 * alpha)
        num, unit = big_number(count)
        label = self.cfg.get("counter_label", "PHONES")
        if count < 1.5 and not unit:
            label = label[:-1] if label.endswith("S") else label
        line2 = (unit + " " + label).strip()
        if final:
            num = "≈ " + num
        f_num = _font(FONT_BLACK, self._s(130 * scale * pop))
        f_l2 = _font(FONT_BLACK, self._s(54 * scale))
        f_w = _font(FONT_BOLD, self._s(38 * scale))
        cx = self._s(CENTER_X)
        y = self._s(top_y)
        d.text((cx, y + self._s(122 * scale)), num, font=f_num, fill=WHITE[:3] + (a,), anchor="ms",
               features=["tnum"])
        d.text((cx, y + self._s(182 * scale)), line2, font=f_l2, fill=ACCENT[:3] + (a,), anchor="ms")
        weight = big_mass(count * self.cfg["item_mass_kg"])
        d.text((cx, y + self._s(228 * scale)), "WEIGHT  " + weight, font=f_w, fill=(255, 255, 255, int(a * 0.8)),
               anchor="ms")

    def _ruler(self, img, ruler, level):
        """Height marker riding the fill level, on the left of the tower."""
        if not ruler:
            return
        base_y, lvl_y, occ_y, _tip_y = [v * 1920 for v in ruler]
        lo = self.top_y + self.plate_h + 30
        hi = SAFE_Y1 - 10
        x = SAFE_X0 + 26
        d = ImageDraw.Draw(img)
        y0, y1 = max(lo, min(hi, occ_y)), max(lo, min(hi, base_y))
        if y1 - y0 > 20:
            d.line([(self._s(x), self._s(y0)), (self._s(x), self._s(y1))], fill=(255, 255, 255, 90),
                   width=int(self._s(8)))
            yl = max(lo, min(hi, lvl_y))
            d.line([(self._s(x), self._s(yl)), (self._s(x), self._s(y1))], fill=ACCENT, width=int(self._s(8)))
        if level <= 0.5 or not (lo - 40 <= lvl_y <= hi + 40):
            return
        yl = max(lo, min(hi, lvl_y))
        floor = max(1, int(level / self.floor_h))
        text = "%d M" % round(level)
        sub = "FLOOR %d" % floor
        f1, f2 = _font(FONT_BLACK, self._s(40)), _font(FONT_BOLD, self._s(26))
        w = max(f1.getlength(text), f2.getlength(sub)) + self._s(30)
        h = self._s(78)
        x0 = self._s(x + 16)
        layer = self._layer()
        dl = ImageDraw.Draw(layer)
        dl.polygon([(self._s(x + 4), self._s(yl)), (x0 + self._s(2), self._s(yl) - self._s(12)),
                    (x0 + self._s(2), self._s(yl) + self._s(12))], fill=ACCENT)
        dl.rounded_rectangle([x0, self._s(yl) - h / 2, x0 + w, self._s(yl) + h / 2], radius=self._s(14),
                             fill=INK[:3] + (220,), outline=ACCENT, width=int(self._s(3)))
        dl.text((x0 + self._s(15), self._s(yl) - self._s(4)), text, font=f1, fill=WHITE, anchor="ls")
        dl.text((x0 + self._s(15), self._s(yl) + self._s(28)), sub, font=f2, fill=ACCENT, anchor="ls")
        img.alpha_composite(layer)

    def _callout(self, img, idx, t):
        """A fact that pops in on the right side, tilted, then flies off."""
        m = self.milestones[idx]
        s = 0.5 + 0.5 * _ease_out_back(t / 8.0, s=2.0)
        leave = _ease_in_out((t - (CALLOUT_LIFE - 10)) / 10.0) if t > CALLOUT_LIFE - 10 else 0.0
        words = [(w, INK) for w in m["text"].split()]
        size = 50
        f = _font(FONT_BLACK, self._s(size))
        lines = self._wrap(words, f, self._s(400))
        lh = self._s(size * 1.12)
        w = max(f.getlength(" ".join(x for x, _ in ln)) for ln in lines) + self._s(56)
        h = lh * len(lines) + self._s(44)
        card = Image.new("RGBA", (int(w + self._s(20)), int(h + self._s(20))), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle([self._s(8), self._s(10), w + self._s(8), h + self._s(10)], radius=self._s(20),
                            fill=INK[:3] + (200,))
        d.rounded_rectangle([0, 0, w, h], radius=self._s(20), fill=ACCENT, outline=INK, width=int(self._s(5)))
        y = self._s(22)
        for ln in lines:
            d.text((w / 2, y + lh * 0.8), " ".join(x for x, _ in ln), font=f, fill=INK, anchor="ms")
            y += lh
        card = card.rotate(4, resample=Image.BICUBIC, expand=True)
        cw, ch = max(1, int(card.width * s)), max(1, int(card.height * s))
        card = card.resize((cw, ch), Image.BICUBIC)
        cx = self._s(SAFE_X1 - 20) - cw / 2 + self._s(500) * leave
        cy = self._s(860 - 60 * idx)
        img.alpha_composite(card, (int(cx), int(cy - ch / 2)))

    def _plus_one(self, img, t):
        sx, sy = self.drop.get("screen", [0.4, 0.7])
        x, y = sx * 1080, sy * 1920
        s = 0.5 + 0.5 * _ease_out_back(t / 5.0)
        rise = 120 * _ease_out(t / float(POPUP_LIFE))
        fade = 1.0 if t < POPUP_LIFE - 6 else (POPUP_LIFE - t) / 6.0
        d = ImageDraw.Draw(img)
        a = int(255 * fade)
        d.text((self._s(x), self._s(y - 60 - rise)), "+1", font=_font(FONT_BLACK, self._s(96 * s)),
               fill=ACCENT[:3] + (a,), anchor="ms", stroke_width=int(self._s(9)), stroke_fill=INK[:3] + (a,))

    def _answer_card(self, img, t):
        """End card: the answer, a comparison, the question and the maths."""
        a = min(1.0, t / 6.0)
        d = ImageDraw.Draw(img)
        fact = self.cfg.get("fact")
        y = 830
        if fact:
            self._pill(img, CENTER_X, y, fact, 40 * (0.8 + 0.2 * _ease_out_back(t / 8.0)), t, alpha=a,
                       fill=WHITE, color=INK, emoji=False)
        if t >= 10:
            self._end_card(img, t - 10)
        note = self.cfg.get("footnote")
        if note and t >= 4:
            f = _font(FONT_BOLD, self._s(25))
            lines = self._wrap([(w, WHITE) for w in note.split()], f, self._s(SAFE_X1 - SAFE_X0 - 30))
            yy = SAFE_Y1 - 12 - 32 * (len(lines) - 1)
            for ln in lines:
                d.text((self._s(CENTER_X), self._s(yy)), " ".join(x for x, _ in ln), font=f,
                       fill=(255, 255, 255, int(190 * min(1.0, (t - 4) / 6.0))), anchor="ms")
                yy += 32

    # ------------------------------------------------------------------ frame
    def render(self, f):
        count, intro, counters_in, callout, drop_t, full, outro, ruler, level = self._state(f)
        img = self._layer()
        if intro is not None:
            self._title(img, intro)
        if ruler is not None and outro is None:
            self._ruler(img, ruler, level)
        for idx, t in callout:
            self._callout(img, idx, t)
        if drop_t is not None:
            self._plus_one(img, drop_t)
        o = 0.0
        if outro is not None:
            o = _ease_in_out(outro / 14.0)
            img.alpha_composite(Image.new("RGBA", img.size, INK[:3] + (int(140 * o),)))
        if counters_in > 0:
            pop = 1.0
            for _i, t in callout:
                pop = max(pop, _pop(t, amount=0.18))
            if full is not None:
                pop = max(pop, _pop(full, amount=0.22))
            top_y = self.top_y - (1.0 - _ease_out_back(counters_in)) * 60
            scale = 1.0
            if outro is not None:
                top_y += (430 - top_y) * o
                scale = 1.0 + 0.12 * o
                pop = _pop(outro - 14, amount=0.2) if outro >= 14 else 1.0
            self._counter(img, count, top_y, scale, counters_in, pop, final=outro is not None)
        if full is not None:
            if full < 6:
                img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, int(130 * (1 - full / 6.0)))))
            self._break_word(img, full)
        if outro is not None:
            ta = _ease_in_out((outro - 6) / 10.0)
            if ta > 0:
                d = ImageDraw.Draw(img)
                d.text((self._s(CENTER_X), self._s(395)), "IT WOULD TAKE", font=_font(FONT_BOLD, self._s(50)),
                       fill=ACCENT[:3] + (int(255 * ta),), anchor="ms")
            if outro >= 12:
                self._answer_card(img, outro - 12)
        return img
