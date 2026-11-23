"""Animated salary-breakdown video for TikTok/Reels/Shorts (1080x1920, 30 fps).

Usage:  python3 make_video.py config.json out.mp4
        python3 make_video.py config.json --stills   (check frames only)
Needs: Python 3 + Pillow, ffmpeg. Fonts: Inter if installed, else DejaVu.
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
def mix(c1, c2, a): return tuple(int(c1[i] * (1 - a) + c2[i] * a) for i in range(3))
def rgba(c, a): return (c[0], c[1], c[2], int(255 * clamp(a)))
def canvas(im):
    d = ImageDraw.Draw(im, "RGBA")
    d.target = im  # text() pastes faded text straight into the image
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


class Video:
    def __init__(self, c):
        self.c = c
        self.sym, self.after = c["symbol"], c.get("symbol_after", False)
        self.hsym = c.get("home_symbol", "£")
        self.rate = c["rate_to_home"]
        self.bg = Image.new("RGB", (W, H))
        g = ImageDraw.Draw(self.bg)
        for y in range(H):
            g.line([(0, y), (W, y)], fill=mix(BG_TOP, BG_BOT, y / H))
        self.ded, self.bills = c["deductions"][:5], c["bills"][:6]
        self.ded_total = sum(v for _, v in self.ded)
        self.take_home = c["gross"] - self.ded_total
        self.bill_total = sum(v for _, v in self.bills)
        self.left = self.take_home - self.bill_total
        self.cmp = c.get("compare")
        if self.cmp is None and c.get("compare_value") is not None:
            self.cmp = {"title": c.get("compare_title", "Take-home pay"), "take_home": c["compare_value"]}
        # Timeline (seconds), sized to the number of lines
        self.t_tax = 11.0
        self.ded_times = [self.t_tax + 0.3 + i * 2.2 for i in range(len(self.ded))]
        self.t_take = self.t_tax + 0.3 + len(self.ded) * 2.2 + 0.8
        self.t_bills = self.t_take + 4.0
        self.bill_times = [self.t_bills + 0.3 + i * 2.5 for i in range(len(self.bills))]
        self.t_left = self.t_bills + 0.3 + len(self.bills) * 2.5 + 1.2
        n_cmp = sum(k in self.cmp for k in ("gross", "take_home", "left")) if self.cmp else 0
        self.t_q = self.t_left + 9.0 + max(0, n_cmp - 1)  # a second more per extra comparison row
        self.t_end = self.t_q + 5.0
        self.scenes = [("hook", 0.0, 4.0), ("pay", 4.0, self.t_tax), ("tax", self.t_tax, self.t_take),
                       ("takehome", self.t_take, self.t_bills), ("bills", self.t_bills, self.t_left),
                       ("left", self.t_left, self.t_q), ("question", self.t_q, self.t_end)]
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
        g = self.c["gross"] * ease_out(prog(t, 5.6, 1.4))
        for (_, v), st in zip(self.ded, self.ded_times):
            g -= v * ease_out(prog(t, st + 0.3, 0.7))
        for (_, v), st in zip(self.bills, self.bill_times):
            g -= v * ease_out(prog(t, st + 0.3, 0.7))
        return g

    def color_for(self, frac):
        return GREEN if frac > 0.5 else (YELLOW if frac > 0.2 else RED)

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
        c = self.c
        im = Image.new("RGB", (self.cw, self.ch), CARD)
        d = canvas(im)
        R = self.cw - 48
        text(d, (48, 46), "MONTHLY BREAKDOWN", font("Bold", 26), rgba(MUTED, 1))
        text(d, (48, 92), c["wage_line"], fit(d, c["wage_line"], "SemiBold", 34, self.cw - 96), rgba(INK, prog(t, 5.0, 0.4)))
        a = prog(t, 5.5, 0.3)
        text(d, (48, 190), "Gross pay", font("SemiBold", 40), rgba(INK, a), "ls")
        gs = self.money(c["gross"] * ease_out(prog(t, 5.6, 1.4)))
        text(d, (R, 196), gs, fit(d, self.money(c["gross"]), "Black", 72, 480), rgba(GREEN, a), "rs")
        text(d, (R, 250), f'about {self.home(c["gross"])} a month', font("Medium", 30), rgba(MUTED, prog(t, 7.1, 0.5)), "rs")
        self.dashed(d, 290, prog(t, 7.5, 0.6), c.get("ded_label", "TAX & DEDUCTIONS"))
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

    def footnote(self, d, a):
        fn = self.c["footnote"]
        lines(d, W / 2, 1600, fn, "Medium", 26, 900, rgba(WHITE, a * 0.6))

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

    def frame(self, t):
        im = self.bg.copy()
        d = canvas(im)
        c = self.c
        if t < 4.4:
            out = 1 - prog(t, 3.7, 0.5)
            for i, line in enumerate(c["hook_lines"][:3]):
                p = ease_out(prog(t, 0.15 + i * 0.45, 0.4))
                text(d, (W / 2, 560 + i * 110 + (1 - p) * 40), line, fit(d, line, "ExtraBold", 74, 920), rgba(WHITE, p * out), "mm")
            p = prog(t, 1.6, 0.5)
            s = 0.4 + 0.6 * ease_back(p) if p > 0 else 0
            if s > 0:
                f = fit(d, c["hook_country"], "Black", 210, 900)
                text(d, (W / 2, 1000), c["hook_country"], font("Black", f.size * s), rgba(YELLOW, out), "mm")
            hq = c.get("hook_question", "What would I keep?")
            text(d, (W / 2, 1230), hq, fit(d, hq, "Bold", 64, 940), rgba(WHITE, ease_out(prog(t, 2.4, 0.4)) * out), "mm")

        if 4.0 <= t < self.t_left + 0.8:
            p = ease_out(prog(t, 4.0, 0.8))
            fade = 1 - prog(t, self.t_left, 0.8)
            y = int(self.cy + (1 - p) * 500)
            sa = self.shadow if (p >= 1 and fade >= 1) else self.shadow.point(lambda v: int(v * p * fade))
            im.paste((0, 0, 0), (self.cx - 40, y - 40, self.cx - 40 + sa.width, y - 40 + sa.height), sa)
            mask = Image.new("L", (self.cw, self.ch), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, self.cw, self.ch], 36, fill=int(255 * min(p * 1.6, 1) * fade))
            im.paste(self.card(t), (self.cx, y), mask)
            self.pill(d, min(p, fade))
            self.bar(d, t, prog(t, 5.4, 0.5) * fade)
            self.footnote(d, prog(t, 5.0, 0.5) * fade)

        tl = self.t_left
        if tl + 0.4 <= t < self.t_q + 0.5:
            out = 1 - prog(t, self.t_q - 0.2, 0.6)
            a = prog(t, tl + 0.4, 0.5) * out
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
            if a4 > 0 and self.cmp:
                self.compare_box(d, a4)
            self.footnote(d, a)

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


def render(cfg_path, out_path):
    v = Video(json.load(open(cfg_path, encoding="utf-8")))
    work = os.path.join(os.path.dirname(os.path.abspath(out_path)), "scenes")
    os.makedirs(work, exist_ok=True)
    parts = []
    for name, t0, t1 in v.scenes:
        final, tmp = os.path.join(work, f"{name}.mp4"), os.path.join(work, f"{name}.part.mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                              "-preset", "veryfast", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for n in range(round(t0 * FPS), round(t1 * FPS)):
            p.stdin.write(v.frame(n / FPS).tobytes())
        p.stdin.close()
        if p.wait() != 0:
            sys.exit(f"ffmpeg failed on scene {name}")
        os.replace(tmp, final)
        parts.append(final)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{x}'\n" for x in parts)
    tmp = os.path.splitext(out_path)[0] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out_path)
    print(f"wrote {out_path} ({v.t_end:.0f}s)")


def stills(cfg_path):
    v = Video(json.load(open(cfg_path, encoding="utf-8")))
    for t in [2.8, 9.0, v.t_bills - 0.5, v.t_left - 0.3, v.t_q - 2.0, v.t_end - 1.0]:
        v.frame(t).save(f"still_{t:05.1f}.png")
    print("stills written; video length", round(v.t_end), "s")


if __name__ == "__main__":
    stills(sys.argv[1]) if "--stills" in sys.argv else render(sys.argv[1], sys.argv[2])
