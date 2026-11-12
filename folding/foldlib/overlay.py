"""Builds the on-screen text layer as an ASS subtitle file for ffmpeg/libass.

Everything is laid out on a 1080x1920 canvas (libass scales it for the
preview). Elements, all in the series' signature style (style.py):

  - hook title in the first seconds
  - FOLDS counter (top) and LAYERS / THICKNESS counters (bottom), each on a
    rounded dark panel. Digits sit in fixed-width cells so values never
    jitter, and pop when they change.
  - landmark callouts that follow the landmark on screen (positions come
    from the per-frame anchors the renderer projected from 3D)
  - finale headline, call to action, and a small "enlarged" note

Nothing is placed in the top 10%, bottom 20% or the right-hand button rail.
"""

import re

from . import style
from .mathutil import clamp, hex_to_srgb
from .numbers import format_int, format_length, split_value_unit

KAPPA = 0.5523  # bezier circle constant


# --- ASS primitives -------------------------------------------------------------

def ass_colour(hex_colour):
    r, g, b = (round(c * 255) for c in hex_to_srgb(hex_colour))
    return f"&H{b:02X}{g:02X}{r:02X}&"


def ass_alpha(opacity):
    """Opacity 0..1 -> ASS alpha (00 opaque, FF transparent)."""
    return f"&H{round((1 - clamp(opacity)) * 255):02X}&"


def ass_time(t):
    # Floor (not round) so an event for frame f never starts after f/fps.
    t = max(0.0, t)
    cs = int(t * 100 + 1e-6)
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def rounded_rect(w, h, r):
    """ASS drawing commands for a w x h rectangle with radius-r corners."""
    r = min(r, w / 2, h / 2)
    k = r * (1 - KAPPA)

    def f(v):
        return f"{v:.1f}".rstrip("0").rstrip(".")
    p = [
        f"m {f(r)} 0", f"l {f(w - r)} 0", f"b {f(w - k)} 0 {f(w)} {f(k)} {f(w)} {f(r)}",
        f"l {f(w)} {f(h - r)}", f"b {f(w)} {f(h - k)} {f(w - k)} {f(h)} {f(w - r)} {f(h)}",
        f"l {f(r)} {f(h)}", f"b {f(k)} {f(h)} 0 {f(h - k)} 0 {f(h - r)}",
        f"l 0 {f(r)}", f"b 0 {f(k)} {f(k)} 0 {f(r)} 0",
    ]
    return " ".join(p)


def circle(r):
    return rounded_rect(2 * r, 2 * r, r)


def escape(text):
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


class Ass:
    def __init__(self):
        self.events = []

    def add(self, start, end, text, layer=1, style_name="Base"):
        if end - start < 0.005:
            return
        self.events.append((layer, start, end, style_name, text))

    def render(self):
        head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {style.WIDTH}
PlayResY: {style.HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{style.FONT_HEAVY},80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        lines = [f"Dialogue: {layer},{ass_time(s)},{ass_time(e)},{st},,0,0,0,,{txt}"
                 for layer, s, e, st, txt in sorted(self.events, key=lambda ev: (ev[1], ev[0]))]
        return head + "\n".join(lines) + "\n"


# --- Building blocks ------------------------------------------------------------

INK = ass_colour(style.INK)
WHITE = ass_colour(style.WHITE)
ACCENT = ass_colour(style.ACCENT)
HEAVY = style.FONT_HEAVY
LABEL = style.FONT_LABEL + " Bold"


def panel(ass, start, end, x, y, w, h, radius=26, opacity=style.PANEL_ALPHA, extra=""):
    ass.add(start, end,
            f"{{\\an7\\pos({x:.1f},{y:.1f})\\p1\\bord0\\shad0\\1c{INK}\\1a{ass_alpha(opacity)}{extra}}}"
            f"{rounded_rect(w, h, radius)}{{\\p0}}", layer=0)


def cell_width(ch, size):
    if ch.isdigit():
        return style.DIGIT_EM * size
    if ch in ",.":
        return style.COMMA_EM * size
    if ch == " ":
        return style.SPACE_EM * size
    return style.LETTER_EM * size


def text_width(text, size):
    return sum(cell_width(c, size) for c in text)


def cells(ass, start, end, text, x, y_mid, size, colour=WHITE, font=HEAVY, pop=False, extra=""):
    """Draw text one character per fixed-width cell, starting at x."""
    anim = ""
    if pop:
        anim = (f"\\fscx122\\fscy122\\1c{ACCENT}"
                f"\\t(0,90,\\fscx100\\fscy100)\\t(60,320,\\1c{colour})")
    cx = x
    for ch in text:
        w = cell_width(ch, size)
        if ch != " ":
            ass.add(start, end,
                    f"{{\\an5\\pos({cx + w / 2:.1f},{y_mid:.1f})\\fn{font}\\fs{size}\\bord0\\shad0"
                    f"\\1c{colour}{anim}{extra}}}{escape(ch)}", layer=2)
        cx += w
    return cx


def label_text(ass, start, end, text, x, y_mid, size, colour=ACCENT, extra=""):
    ass.add(start, end,
            f"{{\\an4\\pos({x:.1f},{y_mid:.1f})\\fn{LABEL}\\fs{size}\\fsp{size * 0.12:.1f}"
            f"\\bord0\\shad0\\1c{colour}{extra}}}{escape(text)}", layer=2)


# --- The overlay ----------------------------------------------------------------

class OverlayBuilder:
    def __init__(self, log):
        self.log = log
        self.fps = log["fps"]
        self.end = log["render_end"]
        self.events = log["events"]
        self.frames = {fr["frame"]: fr for fr in log["frames"]}
        self.ass = Ass()

    def build(self):
        self.title()
        self.counters()
        self.callouts()
        self.finale()
        self.enlarged_note()
        return self.ass.render()

    def first(self, kind):
        return next((e for e in self.events if e["type"] == kind), None)

    # Title ----------------------------------------------------------------------

    def title(self):
        ev_in, ev_out = self.first("title_in"), self.first("title_out")
        if not ev_in:
            return
        start, end = 0.0, min(ev_out["t"], self.end)
        lines = best_wrap(ev_in["text"])
        safe_w = style.SAFE_RIGHT - style.MARGIN_LEFT - 40
        size = int(min(112, safe_w / (0.56 * max(len(l) for l in lines))))
        line_h = size * 1.1
        cx = (style.MARGIN_LEFT + style.SAFE_RIGHT) / 2
        top = style.TITLE_Y - line_h * len(lines) / 2
        out_ms = int((end - start) * 1000)
        for i, line in enumerate(lines):
            y = top + line_h * (i + 0.5)
            text = highlight_numbers(escape(line))
            fx = (f"\\fscx92\\fscy92\\t(0,200,\\fscx100\\fscy100)"
                  f"\\t({out_ms - 260},{out_ms},\\alpha&HFF&\\fscx106\\fscy106)")
            self.ass.add(start, end,
                         f"{{\\an5\\pos({cx:.1f},{y:.1f})\\fn{HEAVY}\\fs{size}\\1c{WHITE}\\3c{INK}"
                         f"\\4c{INK}\\4a&H80&\\bord9\\shad5{fx}}}{text}", layer=3)

    # Counters -------------------------------------------------------------------

    def counters(self):
        changes = [(0.0, 0, False)]
        for e in self.events:
            if e["type"] == "counter":
                changes.append((e["t"], e["n"], True))
        thickness_mm = self.log["config"]["thickness_mm"]
        for i, (t, n, pop) in enumerate(changes):
            if t >= self.end:
                break
            t_end = changes[i + 1][0] if i + 1 < len(changes) else self.log["duration"]
            t_end = min(t_end, self.end)
            self.folds_block(t, t_end, str(n), pop)
            self.value_block(style.LAYERS_BOX, "LAYERS", t, t_end, format_int(2 ** n), "", pop)
            value, unit = split_value_unit(format_length(thickness_mm / 1000.0 * 2 ** n))
            self.value_block(style.THICK_BOX, "THICKNESS", t, t_end, value, unit, pop)

    def folds_block(self, start, end, value, pop):
        b = style.FOLDS_BOX
        pad = 30
        vw = text_width(value, b["value_size"])
        w = max(vw, 200) + pad * 2
        h = 236
        panel(self.ass, start, end, b["x"], b["y"], w, h, radius=34)
        label_text(self.ass, start, end, "FOLDS", b["x"] + pad + 2, b["y"] + 44, b["label_size"])
        cells(self.ass, start, end, value, b["x"] + pad, b["y"] + 150, b["value_size"], pop=pop)

    def value_block(self, box, label, start, end, value, unit, pop):
        pad = 26
        size = box["value_size"]
        unit_size = int(size * 0.68)
        vw = text_width(value, size) + (text_width(" " + unit, unit_size) + 8 if unit else 0)
        w = max(vw, 260) + pad * 2
        h = 140
        panel(self.ass, start, end, box["x"], box["y"], w, h, radius=26)
        label_text(self.ass, start, end, label, box["x"] + pad + 2, box["y"] + 34, box["label_size"])
        x_end = cells(self.ass, start, end, value, box["x"] + pad, box["y"] + 94, size, pop=pop)
        if unit:
            self.ass.add(start, end,
                         f"{{\\an1\\pos({x_end + 12:.1f},{box['y'] + 94 + size * 0.36:.1f})"
                         f"\\fn{HEAVY}\\fs{unit_size}\\bord0\\shad0\\1c{ACCENT}}}{unit}", layer=2)

    # Landmark callouts ----------------------------------------------------------

    def callouts(self):
        label_events = [e for e in self.events if e["type"] == "label_in"]
        outs = {e["id"]: e["t"] for e in self.events if e["type"] == "label_out"}
        for ev in label_events:
            t_in, t_out = ev["t"], min(outs.get(ev["id"], self.log["duration"]), self.end)
            if t_in >= self.end:
                continue
            for part, name, value in ev["labels"]:
                self.callout_track(ev["id"], part, name, value, t_in, t_out)

    def callout_track(self, lm_id, part, name, value, t_in, t_out):
        f0 = int(round(t_in * self.fps))
        f1 = int(round(t_out * self.fps))
        name_size, value_size = 46, 40
        w = max(text_width_prop(name, name_size), text_width_prop(value, value_size)) + 76
        h = 118
        for f in range(f0, f1):
            fr = self.frames.get(f)
            if fr is None:
                continue
            a = fr["anchors"].get(lm_id, {}).get(part)
            if not a or not a[3]:
                continue
            ax, ay, presence = a[0], a[1], a[2]
            fade = min(1.0, (f - f0 + 1) / 6.0, (f1 - f) / 6.0) * clamp(presence)
            if fade <= 0.01:
                continue
            start, end = f / self.fps, (f + 1) / self.fps
            # Box sits above the anchor, kept inside the safe area.
            bx = clamp(ax - w / 2, style.MARGIN_LEFT, style.SAFE_RIGHT - w)
            by = ay - 70 - h
            min_y = style.FOLDS_BOX["y"] + 236 + 24
            by = clamp(by, min_y, style.SAFE_BOTTOM - 420)
            leader_top = by + h
            alpha = ass_alpha(fade)
            panel(self.ass, start, end, bx, by, w, h, radius=22, opacity=style.PANEL_ALPHA * fade)
            self.ass.add(start, end,
                         f"{{\\an8\\pos({bx + w / 2:.1f},{by + 12:.1f})\\fn{HEAVY}\\fs{name_size}"
                         f"\\bord0\\shad0\\1c{WHITE}\\alpha{alpha}}}{escape(name)}", layer=2)
            self.ass.add(start, end,
                         f"{{\\an8\\pos({bx + w / 2:.1f},{by + 64:.1f})\\fn{LABEL}\\fs{value_size}"
                         f"\\bord0\\shad0\\1c{ACCENT}\\alpha{alpha}}}{escape(value)}", layer=2)
            if ay - leader_top > 8:
                lx = clamp(ax, bx + 20, bx + w - 20)
                self.ass.add(start, end,
                             f"{{\\an7\\pos({lx - 2:.1f},{leader_top:.1f})\\p1\\bord0\\shad0\\1c{ACCENT}"
                             f"\\1a{alpha}}}m 0 0 l 4 0 l 4 {ay - leader_top - 10:.1f} l 0 {ay - leader_top - 10:.1f}{{\\p0}}",
                             layer=1)
                self.ass.add(start, end,
                             f"{{\\an7\\pos({ax - 9:.1f},{ay - 9:.1f})\\p1\\bord3\\3c{INK}\\shad0\\1c{ACCENT}"
                             f"\\1a{alpha}\\3a{alpha}}}{circle(9)}{{\\p0}}", layer=1)

    # Finale -------------------------------------------------------------------------

    def finale(self):
        cx = (style.MARGIN_LEFT + style.SAFE_RIGHT) / 2
        head = self.first("headline")
        cta = self.first("cta_in")
        if head and head["t"] < self.end:
            end = min(cta["t"] if cta else self.end, self.end)
            dur = int((end - head["t"]) * 1000)
            self.ass.add(head["t"], end,
                         f"{{\\an5\\pos({cx:.1f},540)\\fn{HEAVY}\\fs96\\1c{ACCENT}\\3c{INK}\\bord8"
                         f"\\4c{INK}\\4a&H80&\\shad5\\fscx70\\fscy70\\t(0,180,\\fscx106\\fscy106)"
                         f"\\t(180,300,\\fscx100\\fscy100)\\t({dur - 250},{dur},\\alpha&HFF&)}}"
                         f"{escape(head['text'])}", layer=3)
        if cta and cta["t"] < self.end:
            lines = wrap(cta["text"], 14)
            size, line_h = 104, 114
            top = 540 - line_h * (len(lines) - 1) / 2
            for i, line in enumerate(lines):
                delay = 120 * i
                text = escape(line)
                if i == len(lines) - 1:
                    text = re.sub(r"(\S+)$", lambda m: f"{{\\1c{ACCENT}}}{m.group(1)}", text)
                self.ass.add(cta["t"], self.end,
                             f"{{\\an5\\pos({cx:.1f},{top + i * line_h:.1f})\\fn{HEAVY}\\fs{size}"
                             f"\\1c{WHITE}\\3c{INK}\\bord9\\4c{INK}\\4a&H80&\\shad5\\alpha&HFF&"
                             f"\\t({delay},{delay + 1},\\alpha&H00&\\fscx80\\fscy80)"
                             f"\\t({delay},{delay + 200},\\fscx100\\fscy100)}}{text}", layer=3)

    def enlarged_note(self):
        """Small honesty note while some objects are drawn bigger than true scale."""
        on, start = False, 0.0
        for _, fr in sorted(self.frames.items()):
            t = fr["t"]
            if fr.get("boosted") and not on:
                on, start = True, t
            elif not fr.get("boosted") and on:
                on = False
                self._note(start, t)
        if on:
            self._note(start, self.end)

    def _note(self, start, end):
        if end - start < 0.5:
            return
        self.ass.add(start, min(end, self.end),
                     f"{{\\an1\\pos({style.MARGIN_LEFT + 4},{style.LAYERS_BOX['y'] - 14})\\fn{LABEL}\\fs26"
                     f"\\1c{WHITE}\\1a&H60&\\bord0\\shad0\\fad(250,250)}}objects enlarged to be visible",
                     layer=2)


def text_width_prop(text, size):
    """Rough width of proportional text (for sizing callout boxes)."""
    return sum((0.36 if c in " ,.~'" else 0.70 if c.isupper() else 0.60) * size for c in text)


def wrap(text, max_chars):
    """Greedy word wrap into balanced lines."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    # Avoid a lonely last word when two lines could be balanced.
    if len(lines) == 2 and len(lines[1].split()) == 1 and len(lines[0].split()) > 2:
        first = lines[0].split()
        lines = [" ".join(first[:-1]), first[-1] + " " + lines[1]]
    return lines


def best_wrap(text):
    """Fewest lines, then the most even line lengths."""
    options = []
    for width in range(12, 21):
        lines = wrap(text, width)
        spread = max(len(l) for l in lines) - min(len(l) for l in lines)
        options.append((len(lines), spread, max(len(l) for l in lines), lines))
    return min(options)[3]


def highlight_numbers(text):
    return re.sub(r"(\d[\d,.]*)", lambda m: f"{{\\1c{ACCENT}}}{m.group(1)}{{\\1c{WHITE}}}", text)


def write_overlay(log, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(OverlayBuilder(log).build())
    return path
