"""Animated salary-breakdown video for TikTok/Reels/Shorts (1080x1920, 30 fps): a spinning globe
that lands on the country, the payslip, cost of living, what's left, a student-loan comparison and
a closing question, with voiceover and sound effects.

Usage:  python3 make_video.py config.json out.mp4
        python3 make_video.py config.json --stills   (key frames as PNG, no video)
Needs: Python 3 with Pillow and numpy, ffmpeg. Fonts: Inter if installed, else DejaVu.
Voice: see audio.py ("flite" works out of the box; "kokoro" sounds natural but needs kokoro-onnx).
"""
import json, math, multiprocessing, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import audio, globe

W, H, FPS = 1080, 1920, 30
BG_TOP, BG_BOT = (12, 16, 28), (22, 28, 48)
CARD, INK, MUTED = (255, 253, 247), (20, 22, 28), (120, 124, 135)
RED, GREEN, YELLOW, WHITE = (220, 60, 66), (30, 160, 95), (255, 199, 44), (255, 255, 255)

FONT_CANDIDATES = {
    "Black": ["/usr/share/fonts/opentype/inter/InterDisplay-Black.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "ExtraBold": ["/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "Bold": ["/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "SemiBold": ["/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "Medium": ["/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
_fonts = {}
def font(weight, size):
    key = (weight, max(8, int(size)))
    if key not in _fonts:
        path = next(p for p in FONT_CANDIDATES[weight] if os.path.exists(p))
        _fonts[key] = ImageFont.truetype(path, key[1])
    return _fonts[key]

def fit(d, s, weight, size, max_w):
    """Largest font size <= size at which s fits in max_w pixels."""
    while size > 12 and d.textlength(s, font=font(weight, size)) > max_w:
        size -= 2
    return font(weight, size)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, start, dur): return clamp((t - start) / dur)
def ease_out(x): return 1 - (1 - x) ** 3
def ease_in_out(x): return 3 * x * x - 2 * x * x * x
def ease_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def ease_bounce(x):
    if x < 1 / 2.75: return 7.5625 * x * x
    if x < 2 / 2.75: x -= 1.5 / 2.75; return 7.5625 * x * x + 0.75
    if x < 2.5 / 2.75: x -= 2.25 / 2.75; return 7.5625 * x * x + 0.9375
    x -= 2.625 / 2.75; return 7.5625 * x * x + 0.984375
def mix(c1, c2, a): return tuple(int(c1[i] * (1 - a) + c2[i] * a) for i in range(3))
def rgba(c, a): return (c[0], c[1], c[2], int(255 * clamp(a)))
def canvas(im):
    d = ImageDraw.Draw(im, "RGBA")
    d.target = im  # text() and flag() paste straight into the image
    return d

def text(d, xy, s, f, fill, anchor="la"):
    a = fill[3] if len(fill) == 4 else 255
    if a <= 0: return
    if a >= 255:
        d.text(xy, s, font=f, fill=fill[:3], anchor=anchor)
        return
    # Pillow ignores a text fill's alpha on RGB images, so fade the glyph mask instead
    x0, y0, x1, y1 = (int(v) for v in d.textbbox(xy, s, font=f, anchor=anchor))
    x0, y0, x1, y1 = x0 - 2, y0 - 2, x1 + 2, y1 + 2
    m = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(m).text((xy[0] - x0, xy[1] - y0), s, font=f, fill=a, anchor=anchor)
    d.target.paste(fill[:3], (x0, y0, x1, y1), m)

def lines(d, cx, cy, s, weight, size, max_w, fill):
    """Centre a block of newline-separated lines on (cx, cy); returns the line count."""
    rows = s.split("\n")
    f = min((fit(d, r, weight, size, max_w) for r in rows), key=lambda f: f.size)
    for i, r in enumerate(rows):
        text(d, (cx, cy + (i - (len(rows) - 1) / 2) * f.size * 1.12), r, f, fill, "mm")
    return len(rows)


# Simplified national flags: ("nordic", field, cross[, inner cross]), ("h3"/"v3", stripes...), ("h2", top, bottom), ("uk",)
FLAGS = {
    "DK": ("nordic", (200, 16, 46), (255, 255, 255)),
    "SE": ("nordic", (0, 106, 167), (254, 204, 0)),
    "NO": ("nordic", (186, 12, 47), (255, 255, 255), (0, 32, 91)),
    "FI": ("nordic", (255, 255, 255), (0, 47, 108)),
    "IS": ("nordic", (2, 82, 156), (255, 255, 255), (220, 30, 53)),
    "DE": ("h3", (0, 0, 0), (221, 0, 0), (255, 206, 0)),
    "NL": ("h3", (174, 28, 40), (255, 255, 255), (33, 70, 139)),
    "AT": ("h3", (200, 16, 46), (255, 255, 255), (200, 16, 46)),
    "FR": ("v3", (0, 38, 84), (255, 255, 255), (206, 17, 38)),
    "IT": ("v3", (0, 146, 70), (255, 255, 255), (206, 43, 55)),
    "IE": ("v3", (22, 155, 98), (255, 255, 255), (255, 136, 62)),
    "BE": ("v3", (0, 0, 0), (253, 218, 36), (239, 51, 64)),
    "PL": ("h2", (255, 255, 255), (220, 20, 60)),
    "GB": ("uk",),
}
_flags = {}
def flag_image(code, w, h):
    if (code, w, h) in _flags:
        return _flags[(code, w, h)]
    S = 4
    fw, fh = w * S, h * S
    im = Image.new("RGB", (fw, fh))
    g = ImageDraw.Draw(im)
    kind, *cols = FLAGS[code]
    if kind == "nordic":
        g.rectangle([0, 0, fw, fh], fill=cols[0])
        vx, hy = fw * 14 / 37, fh / 2
        for col, half in ((cols[1], fh * (0.125 if len(cols) > 2 else 0.07)), *(((cols[2], fh * 0.0625),) if len(cols) > 2 else ())):
            g.rectangle([vx - half, 0, vx + half, fh], fill=col)
            g.rectangle([0, hy - half, fw, hy + half], fill=col)
    elif kind in ("h3", "h2"):
        for i, col in enumerate(cols):
            g.rectangle([0, fh * i / len(cols), fw, fh * (i + 1) / len(cols)], fill=col)
    elif kind == "v3":
        for i, col in enumerate(cols):
            g.rectangle([fw * i / 3, 0, fw * (i + 1) / 3, fh], fill=col)
    elif kind == "uk":
        blue, red, white = (1, 33, 105), (200, 16, 46), (255, 255, 255)
        g.rectangle([0, 0, fw, fh], fill=blue)
        for col, wd in ((white, 0.2), (red, 0.067)):
            g.line([(0, 0), (fw, fh)], fill=col, width=int(fh * wd))
            g.line([(0, fh), (fw, 0)], fill=col, width=int(fh * wd))
        for col, half in ((white, fh / 6), (red, fh / 10)):
            g.rectangle([fw / 2 - half, 0, fw / 2 + half, fh], fill=col)
            g.rectangle([0, fh / 2 - half, fw, fh / 2 + half], fill=col)
    _flags[(code, w, h)] = im = im.resize((w, h), Image.LANCZOS)
    return im

def flag(d, x, y, w, h, code, a=1.0):
    if code not in FLAGS or a <= 0: return
    im = flag_image(code, int(w), int(h))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], max(2, int(h * 0.12)), fill=int(255 * clamp(a)))
    d.target.paste(im, (int(x), int(y)), m)


def voice_lines(c):
    """(key, text) for every voiceover line in the config."""
    vo = c.get("vo", {})
    for key in ("globe", "globe_country", "hook", "pay", "take_home", "left", "question"):
        if vo.get(key): yield key, vo[key]
    for prefix, rows in (("ded", c["deductions"][:5]), ("bill", c["bills"][:6])):
        for i, r in enumerate(rows):
            if len(r) > 2 and r[2]: yield f"{prefix}{i}", r[2]
    loans = c.get("loans") or {}
    if loans.get("say"): yield "loans_intro", loans["say"]
    for i, r in enumerate(loans.get("rows", [])[:4]):
        if r.get("say"): yield f"loan{i}", r["say"]


class Video:
    def __init__(self, c, vo_dur=None):
        self.c = c
        dur = vo_dur or {}
        D = lambda k: dur.get(k, 0.0)
        self.sym, self.after = c["symbol"], c.get("symbol_after", False)
        self.hsym = c.get("home_symbol", "£")
        self.rate = c["rate_to_home"]
        self.bg = Image.new("RGB", (W, H))
        g = ImageDraw.Draw(self.bg)
        for y in range(H):
            g.line([(0, y), (W, y)], fill=mix(BG_TOP, BG_BOT, y / H))
        self.ded = [(r[0], r[1]) for r in c["deductions"][:5]]
        self.bills = [(r[0], r[1]) for r in c["bills"][:6]]
        self.take_home = c["gross"] - sum(v for _, v in self.ded)
        self.left = self.take_home - sum(v for _, v in self.bills)
        self.cmp = c.get("compare")
        if self.cmp is None and c.get("compare_value") is not None:
            self.cmp = {"title": c.get("compare_title", "Take-home pay"), "take_home": c["compare_value"]}
        self.loans = c.get("loans")

        # ---- timeline (seconds); with a voiceover each beat lasts as long as its line
        self.vo_at = {}
        def say(key, t):
            if key in dur: self.vo_at[key] = t
        self.has_globe = c.get("globe", True)
        if self.has_globe:
            country = c.get("map_country", c["country"])
            self.tex = globe.build_texture(country)
            self.map_point = c.get("map_point") or globe.country_point(country)
            say("globe", 0.35)
            self.g_pin = max(2.7, 0.35 + D("globe") + 0.2)
            say("globe_country", self.g_pin + 0.05)
            self.g_spin = self.g_pin - 0.2
            self.g_zoom = self.g_pin + max(1.3, D("globe_country") + 0.6)
            self.g_end = self.g_zoom + 1.0
            self.t_hook = self.g_end - 0.3
            self.stars_bg = self.bg.copy()
            sd = ImageDraw.Draw(self.stars_bg, "RGBA")
            rnd = __import__("random").Random(3)
            for _ in range(260):
                x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.choice((1, 1, 1.5, 2))
                sd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rnd.randint(40, 170)))
        else:
            self.t_hook = 0.0
        h = self.t_hook
        say("hook", h + 0.3)
        self.t_card = h + max(4.0, 0.3 + D("hook") + 0.5)
        c0 = self.t_card
        say("pay", c0 + 1.0)
        self.t_tax = max(c0 + 7.0, c0 + 1.0 + D("pay") + 0.4)
        s = self.t_tax + 0.3
        self.ded_times = []
        for i in range(len(self.ded)):
            self.ded_times.append(s)
            say(f"ded{i}", s + 0.1)
            s += max(1.4, D(f"ded{i}") + 0.45) if f"ded{i}" in dur else 2.2
        self.t_take = s + (0.5 if dur else 0.8)
        say("take_home", self.t_take + 0.3)
        self.t_bills = self.t_take + max(4.0, 0.3 + D("take_home") + 0.5)
        s = self.t_bills + 0.3
        self.bill_times = []
        for i in range(len(self.bills)):
            self.bill_times.append(s)
            say(f"bill{i}", s + 0.1)
            s += max(1.4, D(f"bill{i}") + 0.45) if f"bill{i}" in dur else 2.5
        self.t_left = tl = s + (0.7 if dur else 1.2)
        say("left", tl + 0.5)
        self.t_left_end = max(tl + 6.0, tl + 0.5 + D("left") + 0.7)
        if self.cmp and not self.loans:
            n_cmp = sum(k in self.cmp for k in ("gross", "take_home", "left"))
            self.t_left_end = max(self.t_left_end, tl + 9.0 + max(0, n_cmp - 1))
        if self.loans:
            L = self.t_loans = self.t_left_end
            say("loans_intro", L + 0.2)
            s = L + max(1.2, 0.2 + D("loans_intro") + 0.25)
            self.loan_times = []
            for i in range(len(self.loans["rows"][:4])):
                self.loan_times.append(s)
                say(f"loan{i}", s + 0.15)
                s += max(2.4, 0.15 + D(f"loan{i}") + 0.4)
            self.t_q = s + 1.2
        else:
            self.t_q = self.t_left_end
        say("question", self.t_q + 0.3)
        self.t_end = self.t_q + max(5.0, 0.3 + D("question") + 1.3)

        # Card geometry: rows shrink a little when there are many lines
        n = len(self.ded) + len(self.bills)
        self.row_h = 66 if n <= 8 else max(52, int(66 * 8 / n))
        self.cx, self.cy, self.cw = 80, 250, 860
        self.y_ded = 340
        self.y_take = self.y_ded + len(self.ded) * self.row_h + 30
        self.y_bills = self.y_take + 150
        self.ch = self.y_bills + len(self.bills) * self.row_h + 40
        sh = Image.new("RGBA", (self.cw + 80, self.ch + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([40, 50, self.cw + 40, self.ch + 40], 36, fill=(0, 0, 0, 150))
        self.shadow = sh.filter(ImageFilter.GaussianBlur(22)).getchannel("A")

    def money(self, v, sym=None, after=None):
        sym = self.sym if sym is None else sym
        after = self.after if after is None else after
        s = f"{abs(round(v)):,}"
        s = f"{s} {sym}" if after else f"{sym}{s}"
        return ("-" if v < 0 else "") + s

    def home(self, v):
        return self.money(v * self.rate, self.hsym, self.c.get("home_symbol_after", False))

    def running_left(self, t):
        g = self.c["gross"] * ease_out(prog(t, self.t_card + 1.6, 1.4))
        for (_, v), st in zip(self.ded, self.ded_times):
            g -= v * ease_out(prog(t, st + 0.3, 0.7))
        for (_, v), st in zip(self.bills, self.bill_times):
            g -= v * ease_out(prog(t, st + 0.3, 0.7))
        return g

    def color_for(self, frac):
        return GREEN if frac > 0.5 else (YELLOW if frac > 0.2 else RED)

    # ------------------------------------------------------------ globe intro
    def globe_layer(self, t):
        c = self.c
        im = self.stars_bg.copy() if t >= 0.6 else Image.blend(self.bg, self.stars_bg, ease_out(prog(t, 0, 0.6)))
        d = canvas(im)
        lon_t, lat_t = self.map_point
        ps = prog(t, 0, self.g_spin)
        lon0 = lon_t - 420 * (1 - ps) ** 4
        lat0 = 15 + (lat_t - 15) * ease_in_out(ps)
        z = prog(t, self.g_zoom, self.g_end - self.g_zoom)
        R = 470 * (0.8 + 0.2 * ease_out(prog(t, 0, 0.8))) * (1 + 2.0 * z ** 2.2)
        cx, cy = 540, 1010
        globe.draw(im, self.tex, cx, cy, R, lon0, lat0, alpha=ease_out(prog(t, 0, 0.6)))
        out = 1 - prog(t, self.g_zoom, 0.3)
        for i, line in enumerate(c.get("globe_lines", [])[:2]):
            p = ease_out(prog(t, 0.25 + i * 0.35, 0.4)) * out
            text(d, (W / 2, 250 + i * 86 + (1 - p) * 30), line, fit(d, line, "ExtraBold", 66, 940), rgba(WHITE, p), "mm")
        if t >= self.g_pin:
            px, py, _ = globe.project(lon_t, lat_t, lon0, lat0, cx, cy, R)
            sc = 1 + 0.5 * z
            for k in range(3):  # pulsing rings
                ph = ((t - self.g_pin - 0.3) * 0.8 + k / 3) % 1 if t > self.g_pin + 0.3 else 1
                r = (14 + 120 * ph) * sc
                d.ellipse([px - r, py - r * 0.75, px + r, py + r * 0.75], outline=rgba(YELLOW, (1 - ph) * 0.9), width=5)
            d.ellipse([px - 10 * sc, py - 10 * sc, px + 10 * sc, py + 10 * sc], fill=rgba(YELLOW, 1), outline=rgba(WHITE, 1), width=3)
            p = prog(t, self.g_pin, 0.55)
            self.pin(d, px, py - (1 - ease_bounce(p)) * 320, sc, min(1, p * 5))
            pl = prog(t, self.g_pin + 0.4, 0.45)
            if pl > 0:
                self.map_label(d, px, py - 165 * sc, ease_back(pl) * sc)
        return im

    def pin(self, d, x, y, s, a):
        r, cyc = 30 * s, y - 70 * s
        d.polygon([(x - r * 0.86, cyc + r * 0.5), (x + r * 0.86, cyc + r * 0.5), (x, y)], fill=rgba(YELLOW, a))
        d.ellipse([x - r, cyc - r, x + r, cyc + r], fill=rgba(YELLOW, a), outline=rgba(INK, a * 0.35), width=2)
        d.ellipse([x - r * 0.42, cyc - r * 0.42, x + r * 0.42, cyc + r * 0.42], fill=rgba(INK, a))

    def map_label(self, d, x, y, s):
        name = self.c["country"].upper()
        f = font("Black", 58 * s)
        code = self.c.get("flag")
        fw, fh = (62 * s, 42 * s) if code in FLAGS else (0, 0)
        gap = 16 * s if fw else 0
        tw = d.textlength(name, font=f)
        w, hh = fw + gap + tw + 56 * s, 46 * s
        d.rounded_rectangle([x - w / 2, y - hh, x + w / 2, y + hh], hh, fill=rgba(CARD, 1))
        d.polygon([(x - 16 * s, y + hh - 2), (x + 16 * s, y + hh - 2), (x, y + hh + 18 * s)], fill=rgba(CARD, 1))
        x0 = x - w / 2 + 28 * s
        if fw:
            flag(d, x0, y - fh / 2, fw, fh, code)
        text(d, (x0 + fw + gap, y + 2 * s), name, f, rgba(INK, 1), "lm")

    # ------------------------------------------------------------ payslip card
    def pill(self, d, a):
        if a <= 0: return
        label = f'{self.c["episode"]}  |  {self.c["country"]}' + (f' ({self.c["region"]})' if self.c.get("region") else "")
        f = fit(d, label, "Bold", 34, 800)
        w = d.textlength(label, font=f)
        x0 = (W - w) / 2 - 30
        d.rounded_rectangle([x0, 140, x0 + w + 60, 204], 32, fill=rgba(YELLOW, a))
        text(d, (W / 2, 172), label, f, rgba(INK, a), "mm")

    def row(self, d, y, name, v, t, st):
        p = prog(t, st, 0.45)
        if p <= 0: return
        e = ease_out(p)
        size = 34 if self.row_h >= 60 else 30
        val = self.money(v * ease_out(prog(t, st + 0.3, 0.7)))
        vf = font("Bold", size + 6)
        name_w = self.cw - 96 - d.textlength(self.money(v), font=vf) - 30
        text(d, (48 + (1 - e) * 30, y + 44), name, fit(d, name, "Medium", size, name_w), rgba(INK, e), "ls")
        text(d, (self.cw - 48, y + 46), val, vf, rgba(RED, e), "rs")

    def dashed(self, d, y, p, label=None):
        if p <= 0: return
        x = 48
        if label:
            f = font("Bold", 24)
            text(d, (x, y), label, f, rgba(MUTED, p), "lm")
            x += d.textlength(label, font=f) + 20
        x1 = x + (self.cw - 48 - x) * ease_out(p)
        while x < x1:
            d.line([(x, y), (min(x + 14, x1), y)], fill=(190, 190, 195), width=3)
            x += 24

    def card(self, t):
        c, c0 = self.c, self.t_card
        im = Image.new("RGB", (self.cw, self.ch), CARD)
        d = canvas(im)
        R = self.cw - 48
        text(d, (48, 46), "MONTHLY BREAKDOWN", font("Bold", 26), rgba(MUTED, 1))
        text(d, (48, 92), c["wage_line"], fit(d, c["wage_line"], "SemiBold", 34, self.cw - 96), rgba(INK, prog(t, c0 + 1.0, 0.4)))
        a = prog(t, c0 + 1.5, 0.3)
        text(d, (48, 190), "Gross pay", font("SemiBold", 40), rgba(INK, a), "ls")
        gs = self.money(c["gross"] * ease_out(prog(t, c0 + 1.6, 1.4)))
        text(d, (R, 196), gs, fit(d, self.money(c["gross"]), "Black", 72, 480), rgba(GREEN, a), "rs")
        text(d, (R, 250), f'about {self.home(c["gross"])} a month', font("Medium", 30), rgba(MUTED, prog(t, c0 + 3.1, 0.5)), "rs")
        self.dashed(d, 290, prog(t, c0 + 3.5, 0.6), c.get("ded_label", "TAX & DEDUCTIONS"))
        for i, ((n, v), st) in enumerate(zip(self.ded, self.ded_times)):
            self.row(d, self.y_ded + i * self.row_h, n, -v, t, st)
        yt, a = self.y_take, prog(t, self.t_take + 0.2, 0.4)
        if a > 0:
            pulse = 0.5 + 0.5 * math.sin((t - self.t_take) * 6) if t < self.t_take + 3 else 0
            d.rounded_rectangle([28, yt - 12, R + 20, yt + 112], 20, fill=rgba(GREEN, (0.10 + 0.10 * pulse) * a))
            text(d, (48, yt + 62), "Take-home", font("ExtraBold", 46), rgba(INK, a), "ls")
            text(d, (R, yt + 60), self.money(self.take_home), fit(d, self.money(self.take_home), "Black", 64, 440), rgba(INK, a), "rs")
            text(d, (R, yt + 99), f"about {self.home(self.take_home)}", font("Medium", 28), rgba(MUTED, a), "rs")
        self.dashed(d, yt + 132, prog(t, self.t_bills, 0.5), c.get("bills_label", "COST OF LIVING"))
        for i, ((n, v), st) in enumerate(zip(self.bills, self.bill_times)):
            self.row(d, self.y_bills + i * self.row_h, n, -v, t, st)
        return im

    def bar(self, d, t, a):
        if a <= 0: return
        lv = self.running_left(t)
        y0 = self.cy + self.ch + 40
        frac = clamp(lv / self.c["gross"])
        col = self.color_for(frac)
        text(d, (self.cx, y0 + 34), self.c.get("bar_label", "LEFT FROM MY PAY"), font("Bold", 30), rgba(WHITE, a * 0.75), "ls")
        text(d, (self.cx + self.cw, y0 + 40), self.money(lv), font("Black", 52), rgba(col, a), "rs")
        d.rounded_rectangle([self.cx, y0 + 64, self.cx + self.cw, y0 + 94], 15, fill=rgba(WHITE, a * 0.15))
        if frac > 0.01:
            d.rounded_rectangle([self.cx, y0 + 64, self.cx + self.cw * frac, y0 + 94], 15, fill=rgba(col, a))

    def footnote(self, d, a, fn=None):
        lines(d, W / 2, 1600, fn or self.c["footnote"], "Medium", 26, 900, rgba(WHITE, a * 0.6))

    def compare_box(self, d, a):
        """Table of monthly figures, here vs home; the better value in each row is green."""
        c, cmp = self.c, self.cmp
        names = {"gross": "Gross pay", "take_home": "Take-home", "left": "Left after bills"}
        mine = {"gross": c["gross"], "take_home": self.take_home, "left": self.left}
        rows = [(names[k], mine[k] * self.rate, cmp[k]) for k in names if k in cmp]
        y0, X1, X2 = 1120, 730, 930  # right edges of the two money columns
        d.rounded_rectangle([110, y0, 970, y0 + 180 + len(rows) * 74], 32, fill=rgba(WHITE, 0.08 * a))
        text(d, (W / 2, y0 + 52), cmp.get("title", "Per month"), font("Bold", 34), rgba(WHITE, a * 0.7), "mm")
        for x, name, col in ((X1, c["country"], YELLOW), (X2, c["home_country"], WHITE)):
            text(d, (x, y0 + 120), name.upper(), fit(d, name.upper(), "Bold", 28, 190), rgba(col, a), "rm")
        for i, (name, here, home) in enumerate(rows):
            y = y0 + 196 + i * 74
            text(d, (150, y), name, fit(d, name, "SemiBold", 38, 320), rgba(WHITE, a * 0.85), "lm")
            for x, v, other in ((X1, here, home), (X2, home, here)):
                s = self.money(v, self.hsym, c.get("home_symbol_after", False))
                text(d, (x, y), s, fit(d, s, "ExtraBold", 50, 186), rgba(GREEN if v > other else WHITE, a), "rm")

    # ------------------------------------------------------------ student loans
    def loans_scene(self, d, t, out):
        L, c, t0 = self.loans, self.c, self.t_loans
        p = ease_out(prog(t, t0 + 0.1, 0.45))
        title = L.get("title", "STUDENT LOANS")
        f = fit(d, title, "Black", 62, 820)
        w, y = d.textlength(title, font=f), 250 + (1 - p) * 30
        d.rounded_rectangle([W / 2 - w / 2 - 40, y - 50, W / 2 + w / 2 + 40, y + 50], 50, fill=rgba(YELLOW, p * out))
        text(d, (W / 2, y + 2), title, f, rgba(INK, p * out), "mm")
        sub = L.get("subtitle", f'{c["country"]} vs the {c["home_country"]}')
        text(d, (W / 2, 368), sub, fit(d, sub, "Bold", 48, 940), rgba(WHITE, ease_out(prog(t, t0 + 0.3, 0.4)) * out * 0.9), "mm")
        ah = ease_out(prog(t, t0 + 0.5, 0.4)) * out
        X = (305, 775)
        for x, name, code, col in ((X[0], c["country"], c.get("flag"), YELLOW), (X[1], c["home_country"], c.get("home_flag"), WHITE)):
            name = name.upper()
            f = fit(d, name, "ExtraBold", 40, 300)
            tw = d.textlength(name, font=f)
            fw = 57 if code in FLAGS else 0
            gap = 16 if fw else 0
            x0 = x - (fw + gap + tw) / 2
            if fw:
                flag(d, x0, 474 - 19, fw, 38, code, ah)
            text(d, (x0 + fw + gap, 476), name, f, rgba(col, ah), "lm")
        for i, (row, st) in enumerate(zip(L["rows"][:4], self.loan_times)):
            e = ease_out(prog(t, st, 0.45))
            if e <= 0: continue
            a = e * out
            y = 540 + i * 212 + (1 - e) * 40
            d.rounded_rectangle([70, y, 1010, y + 190], 28, fill=rgba(WHITE, 0.08 * a))
            text(d, (W / 2, y + 44), row["label"], fit(d, row["label"], "SemiBold", 34, 860), rgba(WHITE, 0.75 * a), "mm")
            d.line([(W / 2, y + 86), (W / 2, y + 166)], fill=rgba(WHITE, 0.15 * a), width=2)
            pv = ease_back(prog(t, st + 0.15, 0.4))
            for x, key in zip(X, ("here", "home")):
                s = row[key]
                fv = fit(d, s, "ExtraBold", 64, 400)
                text(d, (x, y + 126), s, font("ExtraBold", fv.size * (0.7 + 0.3 * pv)), rgba(GREEN if row.get("better") == key else WHITE, a), "mm")
        self.footnote(d, ease_out(prog(t, t0 + 0.5, 0.5)) * out, L.get("footnote"))

    # ------------------------------------------------------------ frame
    def frame(self, t):
        im = self.bg.copy()
        if self.has_globe and t < self.g_end:
            layer = self.globe_layer(t)
            a = 1 - prog(t, self.g_end - 0.35, 0.35)
            im = layer if a >= 1 else Image.blend(im, layer, a)
        d = canvas(im)
        c, h = self.c, self.t_hook
        if h <= t < self.t_card + 0.4:
            out = 1 - prog(t, self.t_card - 0.3, 0.5)
            for i, line in enumerate(c["hook_lines"][:3]):
                p = ease_out(prog(t, h + 0.15 + i * 0.45, 0.4))
                text(d, (W / 2, 560 + i * 110 + (1 - p) * 40), line, fit(d, line, "ExtraBold", 74, 920), rgba(WHITE, p * out), "mm")
            p = prog(t, h + 1.6, 0.5)
            s = 0.4 + 0.6 * ease_back(p) if p > 0 else 0
            if s > 0:
                f = fit(d, c["hook_country"], "Black", 210, 900)
                text(d, (W / 2, 1000), c["hook_country"], font("Black", f.size * s), rgba(YELLOW, out), "mm")
            hq = c.get("hook_question", "What would I keep?")
            text(d, (W / 2, 1230), hq, fit(d, hq, "Bold", 64, 940), rgba(WHITE, ease_out(prog(t, h + 2.4, 0.4)) * out), "mm")

        c0 = self.t_card
        if c0 <= t < self.t_left + 0.45:
            p = ease_out(prog(t, c0, 0.8))
            fade = 1 - prog(t, self.t_left, 0.45)
            y = int(self.cy + (1 - p) * 500)
            sa = self.shadow if (p >= 1 and fade >= 1) else self.shadow.point(lambda v: int(v * p * fade))
            im.paste((0, 0, 0), (self.cx - 40, y - 40, self.cx - 40 + sa.width, y - 40 + sa.height), sa)
            mask = Image.new("L", (self.cw, self.ch), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, self.cw, self.ch], 36, fill=int(255 * min(p * 1.6, 1) * fade))
            im.paste(self.card(t), (self.cx, y), mask)
            self.pill(d, min(p, fade))
            self.bar(d, t, prog(t, c0 + 1.4, 0.5) * fade)
            self.footnote(d, prog(t, c0 + 1.0, 0.5) * fade)

        tl = self.t_left
        if tl + 0.45 <= t < self.t_left_end:  # each scene is gone before the next one's text arrives
            out = 1 - prog(t, self.t_left_end - 0.4, 0.4)
            a = prog(t, tl + 0.45, 0.5) * out
            text(d, (W / 2, 420), "What's left every month", font("Bold", 58), rgba(WHITE, a), "mm")
            cnt = self.take_home + (self.left - self.take_home) * ease_in_out(prog(t, tl + 0.9, 2.2))
            p = prog(t, tl + 3.1, 0.4)
            s = 1 + 0.12 * math.sin(math.pi * p) if p > 0 else 1
            f = fit(d, self.money(self.take_home), "Black", 250, 940)
            text(d, (W / 2, 720), self.money(cnt), font("Black", f.size * s), rgba(self.color_for(self.left / c["gross"]), a), "mm")
            text(d, (W / 2, 900), f"about {self.home(self.left)} a month", font("ExtraBold", 66), rgba(WHITE, prog(t, tl + 3.4, 0.5) * out), "mm")
            pct = round(self.left / c["gross"] * 100)
            text(d, (W / 2, 1010), c.get("pct_line", "That's {pct}% of my pay").format(pct=pct), font("SemiBold", 52), rgba(WHITE, prog(t, tl + 4.4, 0.5) * out * 0.85), "mm")
            a4 = prog(t, tl + 5.6, 0.5) * out
            if a4 > 0 and self.cmp and not self.loans:
                self.compare_box(d, a4)
            self.footnote(d, a)

        if self.loans and self.t_loans <= t < self.t_q:
            self.loans_scene(d, t, 1 - prog(t, self.t_q - 0.4, 0.4))

        if t >= self.t_q:
            tq = self.t_q
            p = ease_out(prog(t, tq + 0.1, 0.5))
            n = lines(d, W / 2, 760 + (1 - p) * 40, c.get("question", "Would you move?"), "Black", 100, 940, rgba(WHITE, p))
            dy = (n - 1) * 56
            cta = c.get("cta", "Comment the next country")
            text(d, (W / 2, 920 + dy), cta, fit(d, cta, "Bold", 58, 940), rgba(YELLOW, ease_out(prog(t, tq + 0.9, 0.5))), "mm")
            p3 = prog(t, tq + 1.7, 0.5)
            s = 0.6 + 0.4 * ease_back(p3) if p3 > 0 else 0
            if s > 0:
                label = c.get("next_label", "NEXT EPISODE = YOU DECIDE")
                f = fit(d, label, "Black", 54, 820)
                f = font("Black", f.size * s)
                w = d.textlength(label, font=f)
                hh = f.size * 0.85
                d.rounded_rectangle([W / 2 - w / 2 - 34, 1060 + dy - hh, W / 2 + w / 2 + 34, 1060 + dy + hh], hh, fill=rgba(YELLOW, 1))
                text(d, (W / 2, 1060 + dy), label, f, rgba(INK, 1), "mm")
        return im

    # ------------------------------------------------------------ sound effects
    def effects(self):
        """[(start, name, kwargs, gain)] for audio.mix()."""
        ev = []
        E = lambda t, name, gain, **kw: ev.append((t, name, kw, gain))
        if self.has_globe:
            E(0.0, "spin", 0.5, dur=round(self.g_spin + 0.4, 2))
            for i in range(len(self.c.get("globe_lines", [])[:2])):
                E(0.25 + i * 0.35, "pop", 0.15, f=520)
            E(self.g_pin + 0.05, "ping", 0.45)
            E(self.g_pin + 0.4, "pop", 0.35, f=760)
            E(self.g_zoom - 0.1, "whoosh", 0.55, dur=round(self.g_end - self.g_zoom + 0.4, 2), rise=True)
        h = self.t_hook
        for i in range(len(self.c["hook_lines"][:3])):
            E(h + 0.15 + i * 0.45, "pop", 0.15, f=480 + 60 * i)
        E(h + 1.6, "impact", 0.55)
        E(h + 2.4, "pop", 0.2, f=700)
        c0 = self.t_card
        E(c0 - 0.05, "whoosh", 0.35, dur=0.7, rise=False)
        E(c0 + 1.6, "ticks", 0.2, dur=1.4)
        E(c0 + 3.0, "ding", 0.3)
        for st in self.ded_times:
            E(st + 0.3, "boop", 0.35)
        E(self.t_take + 0.2, "cash", 0.4)
        E(self.t_bills, "whoosh", 0.22, dur=0.5, rise=False)
        for st in self.bill_times:
            E(st + 0.3, "boop", 0.35)
        tl = self.t_left
        E(tl + 0.2, "whoosh", 0.3, dur=0.6, rise=True)
        E(tl + 0.9, "ticks", 0.2, dur=2.2)
        E(tl + 3.1, "impact", 0.55)
        if self.loans:
            E(self.t_loans, "whoosh", 0.3, dur=0.6, rise=False)
            E(self.t_loans + 0.1, "pop", 0.35, f=620)
            for st in self.loan_times:
                E(st, "pop", 0.3, f=560)
        q = self.t_q
        E(q, "whoosh", 0.28, dur=0.5, rise=True)
        E(q + 0.15, "impact", 0.4)
        E(q + 0.9, "pop", 0.25, f=650)
        E(q + 1.7, "ding", 0.3)
        return ev


# ---------------------------------------------------------------- rendering

def prepare(cfg_path):
    """Config, voiceover clips {key: samples} and their lengths in seconds."""
    c = json.load(open(cfg_path, encoding="utf-8"))
    clips = {}
    if c.get("voice"):
        for key, line in voice_lines(c):
            clips[key] = audio.tts(line, c["voice"])
    return c, clips, {k: len(x) / audio.SR for k, x in clips.items()}


_video = None
def _init_worker(c, durs):
    global _video
    _video = Video(c, durs)

def _render_chunk(job):
    path, n0, n1 = job
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                          "-preset", "veryfast", "-pix_fmt", "yuv420p", path + ".part.mp4"], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        p.stdin.write(_video.frame(n / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on {path}")
    os.replace(path + ".part.mp4", path)
    return path


def render(cfg_path, out_path):
    c, clips, durs = prepare(cfg_path)
    v = Video(c, durs)  # also builds the globe texture cache before the workers start
    work = os.path.join(os.path.dirname(os.path.abspath(out_path)), "build")
    os.makedirs(work, exist_ok=True)
    total = round(v.t_end * FPS)
    jobs = [(os.path.join(work, f"part{i:03d}.mp4"), n0, min(n0 + 90, total)) for i, n0 in enumerate(range(0, total, 90))]
    with multiprocessing.get_context("fork").Pool(os.cpu_count(), _init_worker, (c, durs)) as pool:
        for i, _ in enumerate(pool.imap_unordered(_render_chunk, jobs), 1):
            print(f"\rframes: {i}/{len(jobs)} chunks", end="", flush=True)
    print()
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{j[0]}'\n" for j in jobs)
    silent = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    wav = os.path.join(work, "audio.wav")
    audio.mix(v.t_end, [(v.vo_at[k], x) for k, x in clips.items() if k in v.vo_at], v.effects(), wav)
    tmp = os.path.splitext(out_path)[0] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out_path)
    print(f"wrote {out_path} ({v.t_end:.1f}s)")


def stills(cfg_path):
    c, _, durs = prepare(cfg_path)
    v = Video(c, durs)
    ts = [v.t_hook + 2.8, v.ded_times[-1] + 1.0, v.t_left - 0.3, v.t_left_end - 1.0, v.t_end - 1.0]
    if v.has_globe:
        ts = [v.g_spin * 0.5, v.g_pin + 0.9] + ts
    if v.loans:
        ts.insert(-1, v.t_q - 0.5)
    for t in ts:
        v.frame(t).save(f"still_{t:05.1f}.png")
    print("stills written; video length", round(v.t_end, 1), "s")


if __name__ == "__main__":
    stills(sys.argv[1]) if "--stills" in sys.argv else render(sys.argv[1], sys.argv[2])
