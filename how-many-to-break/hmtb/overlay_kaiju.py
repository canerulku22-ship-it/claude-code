"""Motion graphics for 'kaiju' episodes: a breaking-news look over the 3D action.

Same fonts, colours and safe zones as the other episode types (hmtb/overlay.py):

* LIVE bug + BREAKING NEWS plate and a clock across the top
* a location chip that slides in for each place ("WESTMINSTER BRIDGE")
* the hook title, word by word, in the first second
* a name card with the monster's stats when it's introduced
* word-by-word captions of the voiceover, the spoken word lit in the accent colour
* comic words on the big hits (ROAR!, CHOMP!) and white flashes
* an end card with the question for the comments
"""

import math

from PIL import Image, ImageDraw

from .kaiju import caption_words
from .overlay import (ACCENT, ALERT, CENTER_X, FONT_BLACK, FONT_BOLD, INK, PLATE, SAFE_X0, SAFE_X1, SAFE_Y0,
                      WHITE, Overlay, _ease_in_out, _ease_out, _ease_out_back, _font)

LIVE_Y = SAFE_Y0 + 14          # top row: LIVE bug, BREAKING NEWS, clock
CHIP_Y = LIVE_Y + 82           # location chip under it
TITLE_Y = CHIP_Y + 92          # hook title under the chip
NAME_Y = CHIP_Y + 96           # name card
CAPTION_Y = 1290               # baseline of the first caption line
CAPTION_SIZE = 76
COMIC_LIFE = 28
FLASH_LIFE = 6
HL = {"PIZZA", "MONSTER", "LONDON", "PEPPERONI", "REX"}


class KaijuOverlay(Overlay):
    def __init__(self, events, width, height):
        import os
        from .overlay import EMOJI_POINT_DOWN
        self.ev = events
        self.cfg = events["config"]
        self.W, self.H = width, height
        self.k = width / 1080.0
        self.fps = fps = events["fps"]
        self.total = events["total_frames"]
        self.seg = events["segments"]
        self.m = events["moments"]
        self.intro_end = self.seg["erupt"][0]
        self.end_f = self.seg["end"][0]
        self.name_f = self.m.get("name_card", self.seg["rise"][0] + 60)
        self.name_end = self.seg["bridge"][0] - 4
        durs = events.get("vo_durations") or [0.075 * len(v["text"]) + 0.4 for v in self.cfg["voiceover"]]
        self.chunks = self._caption_chunks(caption_words(self.cfg, durs))
        self.labels = [(int(round(lb["at_s"] * fps)), int(round(lb["until_s"] * fps)), lb["text"])
                       for lb in self.cfg.get("labels", [])]
        self.comics = [(int(round(c["at_s"] * fps)), c["text"]) for c in self.cfg.get("comic_words", [])]
        self.flashes = [self.m[k] for k in ("geyser", "bite", "stomp", "splash") if k in self.m]
        self.end_question = self.cfg.get("end_question", "WHERE SHOULD IT GO NEXT?")
        self.outro_card_y = 930
        self.clock = self.cfg.get("clock", "20:14")
        self.emoji = Image.open(EMOJI_POINT_DOWN).convert("RGBA") if os.path.exists(EMOJI_POINT_DOWN) else None
        self._vignette = None
        self._last_key = None
        self._last_bytes = None

    # ------------------------------------------------------------------ captions
    def _caption_chunks(self, words):
        """Group the timed words into short chunks (2-4 words, split at punctuation)."""
        fps = self.fps
        font = _font(FONT_BLACK, CAPTION_SIZE)
        max_w = (SAFE_X1 - SAFE_X0 - 40) * 1.75           # about two lines
        chunks, cur = [], []

        def close():
            if cur:
                chunks.append(list(cur))
                cur.clear()

        for i, (s, e, w, line) in enumerate(words):
            if cur and (cur[-1][3] != line or len(cur) >= 4 or
                        font.getlength(" ".join(x[2] for x in cur + [(s, e, w, line)]).upper()) > max_w):
                close()
            cur.append((s, e, w, line))
            nxt = words[i + 1] if i + 1 < len(words) else None
            if w[-1] in ".?!," and len(cur) >= 2 and (nxt is None or nxt[3] == line):
                close()
        close()
        out = []
        for i, ch in enumerate(chunks):
            start = int(round(ch[0][0] * fps))
            end = int(round((ch[-1][1] + 0.45) * fps))
            if i + 1 < len(chunks):
                end = min(end, int(round(chunks[i + 1][0][0] * fps)))
            out.append({"start": start, "end": end,
                        "words": [(w.upper(), int(round(s * fps)), int(round(e * fps))) for s, e, w, _l in ch]})
        return out

    def _caption_state(self, f):
        for i, ch in enumerate(self.chunks):
            if ch["start"] <= f < ch["end"]:
                cur = max([j for j, (_w, s, _e) in enumerate(ch["words"]) if s <= f] or [0])
                return i, cur, min(f - ch["start"], 6), min(f - ch["words"][cur][1], 6)
        return None

    def _captions(self, img, state):
        i, cur, t_chunk, t_word = state
        ch = self.chunks[i]
        pop = 0.82 + 0.18 * _ease_out_back(t_chunk / 5.0)
        size = CAPTION_SIZE * pop
        f = _font(FONT_BLACK, self._s(size))
        lines = self._wrap([(w, j) for j, (w, _s, _e) in enumerate(ch["words"])], f,
                            self._s(SAFE_X1 - SAFE_X0 - 40))
        d = ImageDraw.Draw(img)
        y = CAPTION_Y - (len(lines) - 1) * size * 0.55
        sw = int(self._s(11))
        for line in lines:
            text = " ".join(w for w, _ in line)
            x = self._s(CENTER_X) - f.getlength(text) / 2
            for w, j in line:
                ww = f.getlength(w)
                cx = x + ww / 2
                if j == cur:
                    s = 1.0 + 0.16 * (1.0 - _ease_out(t_word / 6.0))
                    fw = _font(FONT_BLACK, self._s(size * s))
                    col = ACCENT
                else:
                    fw, col = f, WHITE
                d.text((cx + self._s(5), self._s(y + 7)), w, font=fw, anchor="ms", fill=INK[:3] + (200,),
                       stroke_width=sw, stroke_fill=INK[:3] + (200,))
                d.text((cx, self._s(y)), w, font=fw, anchor="ms", fill=col, stroke_width=sw, stroke_fill=INK)
                x += f.getlength(w + " ")
            y += size * 1.1

    # ------------------------------------------------------------------ top row
    def _live_row(self, img, t, blink, alpha):
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        h = 62
        slide = (1.0 - _ease_out(min(1.0, t / 9.0))) * -300
        x = SAFE_X0 + slide
        a = int(255 * alpha)
        # LIVE pill
        f = _font(FONT_BLACK, self._s(36))
        lw = f.getlength("LIVE") / self.k + 66
        d.rounded_rectangle([self._s(x), self._s(LIVE_Y), self._s(x + lw), self._s(LIVE_Y + h)],
                            radius=self._s(12), fill=ALERT[:3] + (a,))
        if blink:
            d.ellipse([self._s(x + 16), self._s(LIVE_Y + h / 2 - 9), self._s(x + 34), self._s(LIVE_Y + h / 2 + 9)],
                      fill=WHITE[:3] + (a,))
        d.text((self._s(x + 44), self._s(LIVE_Y + h / 2)), "LIVE", font=f, fill=WHITE[:3] + (a,), anchor="lm")
        x += lw + 10
        # BREAKING NEWS plate
        text = self.cfg.get("banner", "BREAKING NEWS")
        bw = f.getlength(text) / self.k + 44
        d.rounded_rectangle([self._s(x), self._s(LIVE_Y), self._s(x + bw), self._s(LIVE_Y + h)],
                            radius=self._s(12), fill=PLATE[:3] + (int(PLATE[3] * alpha),))
        d.text((self._s(x + 22), self._s(LIVE_Y + h / 2)), text, font=f, fill=ACCENT[:3] + (a,), anchor="lm")
        x += bw + 16
        fc = _font(FONT_BOLD, self._s(34))
        d.text((self._s(x), self._s(LIVE_Y + h / 2)), self.clock, font=fc, fill=WHITE[:3] + (a,), anchor="lm",
               stroke_width=int(self._s(6)), stroke_fill=INK[:3] + (a,))
        img.alpha_composite(layer)

    def _chip(self, img, text, t_in, t_out):
        """Yellow location chip with a map pin; slides in from the left, wipes out."""
        u = _ease_out_back(min(1.0, t_in / 10.0), s=1.2)
        v = _ease_in_out(min(1.0, t_out / 8.0)) if t_out is not None else 0.0
        f = _font(FONT_BLACK, self._s(40))
        w = f.getlength(text) / self.k + 96
        h = 66
        x = SAFE_X0 - (1.0 - u) * (w + 80) - v * (w + 80)
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([self._s(x + 5), self._s(CHIP_Y + 7), self._s(x + w + 5), self._s(CHIP_Y + h + 7)],
                            radius=self._s(14), fill=INK[:3] + (170,))
        d.rounded_rectangle([self._s(x), self._s(CHIP_Y), self._s(x + w), self._s(CHIP_Y + h)],
                            radius=self._s(14), fill=ACCENT, outline=INK, width=int(self._s(5)))
        # Map pin: a circle with a point under it.
        px, py, r = x + 38, CHIP_Y + 28, 13
        d.polygon([(self._s(px - r * 0.8), self._s(py + 6)), (self._s(px + r * 0.8), self._s(py + 6)),
                   (self._s(px), self._s(py + r + 15))], fill=ALERT)
        d.ellipse([self._s(px - r), self._s(py - r), self._s(px + r), self._s(py + r)], fill=ALERT)
        d.ellipse([self._s(px - 5), self._s(py - 5), self._s(px + 5), self._s(py + 5)], fill=WHITE)
        d.text((self._s(x + 66), self._s(CHIP_Y + h / 2 + 1)), text, font=f, fill=INK, anchor="lm")
        img.alpha_composite(layer)

    # ------------------------------------------------------------------ title and name card
    def _hook_title(self, img, t):
        words = [(w, ACCENT if w.strip("?!.,") in HL else WHITE) for w in self.cfg["title"].upper().split()]
        size = 100
        while True:
            f = _font(FONT_BLACK, self._s(size))
            lines = self._wrap(words, f, self._s(SAFE_X1 - SAFE_X0 - 20))
            if len(lines) <= 4 or size <= 56:
                break
            size -= 4
        leave = _ease_in_out((t - (self.intro_end - 12)) / 10.0) if t >= self.intro_end - 12 else 0.0
        if leave >= 1.0:
            return
        alpha = int(255 * (1.0 - leave))
        f_full = _font(FONT_BLACK, self._s(size))
        lh = size * 1.08
        y = TITLE_Y - 160 * leave
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        k = 0
        sw = int(self._s(11))
        for line in lines:
            text = " ".join(w for w, _ in line)
            x = self._s(CENTER_X) - f_full.getlength(text) / 2
            yy = self._s(y + lh * 0.82)
            for w, col in line:
                ww = f_full.getlength(w)
                appear = t - k * 1.3
                s = 0.45 + 0.55 * _ease_out_back(appear / 6.0, s=1.4) if appear >= 0 else 0.0
                if s > 0:
                    fw = _font(FONT_BLACK, self._s(size * s))
                    cx = x + ww / 2
                    d.text((cx + self._s(6), yy + self._s(8)), w, font=fw, anchor="ms",
                           fill=INK[:3] + (int(alpha * 0.8),), stroke_width=sw,
                           stroke_fill=INK[:3] + (int(alpha * 0.8),))
                    d.text((cx, yy), w, font=fw, fill=col[:3] + (alpha,), anchor="ms", stroke_width=sw,
                           stroke_fill=INK[:3] + (alpha,))
                x += f_full.getlength(w + " ")
                k += 1
            y += lh
        img.alpha_composite(layer)

    def _name_card(self, img, t, t_out):
        v = _ease_in_out(min(1.0, t_out / 8.0)) if t_out is not None else 0.0
        a = 1.0 - v
        layer = self._layer()
        d = ImageDraw.Draw(layer)
        # Little red stamp above the name.
        st = _ease_out_back(min(1.0, t / 6.0), s=2.0)
        if st > 0:
            fs = _font(FONT_BLACK, self._s(34 * st))
            text = self.cfg.get("name_tag", "KAIJU ALERT")
            tw = fs.getlength(text)
            x0, y0 = self._s(SAFE_X0 + 8), self._s(NAME_Y)
            d.rounded_rectangle([x0, y0, x0 + tw + self._s(36), y0 + self._s(54 * st)], radius=self._s(10),
                                fill=ALERT[:3] + (int(255 * a),))
            d.text((x0 + self._s(18), y0 + self._s(27 * st)), text, font=fs, fill=WHITE[:3] + (int(255 * a),),
                   anchor="lm")
        # The name, one word per line, slamming in.
        words = self.cfg["monster_name"].upper().split()
        y = NAME_Y + 70
        size = 132
        f = _font(FONT_BLACK, self._s(size))
        while size > 70 and max(f.getlength(w) for w in words) > self._s(SAFE_X1 - SAFE_X0 - 30):
            size -= 6
            f = _font(FONT_BLACK, self._s(size))
        for i, w in enumerate(words):
            u = t - 3 - i * 4
            if u < 0:
                continue
            s = 1.6 - 0.6 * _ease_out(min(1.0, u / 5.0))
            al = min(1.0, u / 3.0) * a
            fw = _font(FONT_BLACK, self._s(size * s))
            x = self._s(SAFE_X0 + 8) - v * self._s(500)
            yy = self._s(y + size * 0.86)
            d.text((x + self._s(7), yy + self._s(9)), w, font=fw, anchor="ls", fill=INK[:3] + (int(200 * al),),
                   stroke_width=int(self._s(12)), stroke_fill=INK[:3] + (int(200 * al),))
            d.text((x, yy), w, font=fw, anchor="ls", fill=ACCENT[:3] + (int(255 * al),),
                   stroke_width=int(self._s(12)), stroke_fill=INK[:3] + (int(255 * al),))
            y += size * 0.98
        # Stats in small plates, one after the other.
        fs = _font(FONT_BOLD, self._s(36))
        y += 18
        for i, stat in enumerate(self.cfg.get("monster_stats", [])):
            u = t - 14 - i * 6
            if u < 0:
                continue
            e = _ease_out_back(min(1.0, u / 7.0), s=1.3)
            w = fs.getlength(stat) / self.k + 40
            x = SAFE_X0 + 8 - (1.0 - e) * 420 - v * 600
            d.rounded_rectangle([self._s(x), self._s(y), self._s(x + w), self._s(y + 58)], radius=self._s(12),
                                fill=PLATE[:3] + (int(PLATE[3] * a),))
            d.text((self._s(x + 20), self._s(y + 29)), stat, font=fs, fill=WHITE[:3] + (int(255 * a),),
                   anchor="lm")
            y += 68
        img.alpha_composite(layer)

    # ------------------------------------------------------------------ state + frame
    def _state(self, f):
        intro = f if f < self.intro_end else None
        on_air = f < self.end_f + 6
        live = (min(f, 10), (f // 15) % 2 == 0, round(1.0 - max(0.0, (f - self.end_f) / 6.0), 2)) if on_air else None
        chip = None
        for i, (a, b, _t) in enumerate(self.labels):
            if a <= f < b + 9:
                chip = (i, min(f - a, 12), (f - b) if f >= b else None)
        name = None
        if self.name_f <= f < self.name_end + 9:
            name = (min(f - self.name_f, 40), (f - self.name_end) if f >= self.name_end else None)
        comic = next(((i, f - a) for i, (a, _t) in enumerate(self.comics) if 0 <= f - a < COMIC_LIFE), None)
        cap = self._caption_state(f) if f < self.end_f + 8 else None
        flash = next((f - a for a in self.flashes if 0 <= f - a < FLASH_LIFE), None)
        outro = f - self.end_f if f >= self.end_f else None
        if outro is not None and outro > 40:
            outro = 40 + (outro // 2) % 20      # only the emoji keeps bobbing
        return intro, live, chip, name, comic, cap, flash, outro

    def render(self, f):
        intro, live, chip, name, comic, cap, flash, outro = self._state(f)
        img = self._layer()
        if flash is not None:
            img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, int(140 * (1 - flash / FLASH_LIFE)))))
        if outro is not None:
            o = _ease_in_out(outro / 14.0)
            img.alpha_composite(Image.new("RGBA", img.size, INK[:3] + (int(130 * o),)))
        if live is not None:
            self._live_row(img, live[0], live[1], live[2])
        if chip is not None:
            i, t_in, t_out = chip
            self._chip(img, self.labels[i][2], t_in, t_out)
        if intro is not None:
            self._hook_title(img, intro)
        if name is not None:
            self._name_card(img, name[0], name[1])
        if comic is not None:
            i, t = comic
            self.break_word = self.comics[i][1]
            self._break_word(img, t)
        if cap is not None:
            self._captions(img, cap)
        if outro is not None and outro >= 10:
            self._end_card(img, outro - 10)
            t = outro - 10
            if t >= 10:
                self._pill(img, CENTER_X, 1330, "TELL US IN THE COMMENTS", 50 * (0.8 + 0.2 * _ease_out_back(
                    min(1.0, (t - 10) / 8.0))), t, emoji=False)
        return img
