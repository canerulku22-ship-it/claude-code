"""Compositing + motion graphics + encode.

Reads the Cycles frames, upscales them to 1080x1920, adds heat-haze, bloom,
grade, vignette, grain, whip/zoom transitions and draws all 2D motion
graphics (headers, tracked labels, callouts, kinetic type) at native
resolution, then pipes the result into ffmpeg.

    python post.py --timeline out/timeline.json --frames-dir out/frames \
                   --audio out/soundtrack.wav --out out/spaghetti_bolognese_3d.mp4
"""
import argparse
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import config as C  # noqa: E402

W, H = C.RES_X, C.RES_Y
CREAM, RED, GOLD, INK = C.BRAND["cream"], C.BRAND["red"], C.BRAND["gold"], C.BRAND["ink"]
UI = getattr(C, "UI_SCALE", 1.0)   # size of all 2D motion graphics


# ----------------------------------------------------------------- easing --
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(f, a, b):
    return clamp((f - a) / float(b - a)) if b != a else float(f >= a)


def eout(t, p=3):
    t = clamp(t)
    return 1 - (1 - t) ** p


def ein(t, p=3):
    return clamp(t) ** p


def eback(t, s=1.7):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


_fonts = {}


def font(path, size):
    k = (path, int(size))
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, int(size))
    return _fonts[k]


# ------------------------------------------------------------ text tools ---
_tl_cache = {}


def text_layer(txt, fnt, fill, spacing=0, shadow=True):
    k = (txt, id(fnt), tuple(fill), spacing, shadow)
    if k not in _tl_cache:
        _tl_cache[k] = _text_layer(txt, fnt, fill, spacing, shadow)
    return _tl_cache[k]


def _text_layer(txt, fnt, fill, spacing=0, shadow=True):
    """Render text (with tracking) into a tight RGBA image (+ soft shadow)."""
    widths = [fnt.getlength(ch) for ch in txt]
    tw = int(sum(widths) + spacing * max(len(txt) - 1, 0)) + 4
    asc, desc = fnt.getmetrics()
    th = asc + desc + 4
    pad = 30 if shadow else 4
    im = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for ch, w in zip(txt, widths):
        d.text((x, pad), ch, font=fnt, fill=fill)
        x += w + spacing
    if shadow:
        a = im.split()[3]
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.55)))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 6))
        out.alpha_composite(im)
        im = out
    return im, pad


def paste(canvas, im, x, y, alpha=1.0, scale=1.0, clip_w=None, anchor="lt"):
    if alpha <= 0.003 or scale <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if clip_w is not None:
        cw = max(0, min(im.width, int(clip_w)))
        if cw == 0:
            return
        im = im.crop((0, 0, cw, im.height))
    if alpha < 1.0:
        a = im.split()[3].point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    if anchor == "c":
        x, y = x - im.width / 2, y - im.height / 2
    elif anchor == "ct":
        x = x - im.width / 2
    canvas.alpha_composite(im, (int(round(x)), int(round(y))))


def rrect(d, box, r, fill):
    d.rounded_rectangle(box, radius=r, fill=fill)


SAFE = 28          # px: no label or callout is drawn closer than this to the frame edge


def label_layout(x, y, sgn, pw, ph, L=120, k=1.0):
    """Place a side label's pill for an anchor at (x, y).

    Preferred: pill beside the anchor (left or right), at the end of a leader
    line with an elbow. If that would leave the frame, the pill slides inward
    by the overflow and rises above the anchor so it never covers the dot.
    Both offsets grow continuously with the overflow, so a label tracking an
    orbiting object never jumps. Returns the pill's top-left, the leader's
    elbow and the leader's end point on the pill's edge.
    """
    px0 = x + sgn * L if sgn > 0 else x + sgn * L - pw
    shift = 0.0
    if px0 < SAFE:
        shift = SAFE - px0
    elif px0 + pw > W - SAFE:
        shift = (W - SAFE) - (px0 + pw)
    px0 += shift
    lift = min(1.0, abs(shift) / (90.0 * k)) * (ph / 2 + 30 * k)
    cy = y - 40 * k - lift
    py0 = min(max(cy - ph / 2, SAFE), H - SAFE - ph)
    w_ = 1 - min(1.0, abs(shift) / (90.0 * k))
    elx, ely = x + sgn * 60 * k * w_, y - 40 * k * w_
    # leader ends at the point of the pill's box nearest to the elbow
    tx = min(max(elx, px0 + ph / 2), px0 + pw - ph / 2)
    ty = min(max(ely, py0), py0 + ph)
    return (px0, py0), (elx, ely), (tx, ty)


# --------------------------------------------------------------- overlays ---
class Overlays:
    def __init__(self, shot):
        self.shot = shot
        self.tracks = shot["tracks"]
        self.items = shot["overlays"]
        self.rng = np.random.default_rng(len(shot["name"]))
        self.sparks = self.rng.uniform(0, 1, (14, 4))

    def anchor(self, name, f):
        tr = self.tracks.get(name)
        if not tr:
            return None
        p = tr[max(0, min(len(tr) - 1, f - 1))]
        return None if p is None else (p[0], p[1])

    def draw(self, canvas, f):
        d = ImageDraw.Draw(canvas)
        for it in self.items:
            t0, t1 = it.get("t0", 1), it.get("t1", 10 ** 6)
            if not (t0 <= f <= t1 + 8):
                continue
            fn = getattr(self, "o_" + it["type"], None)
            if fn:
                fn(canvas, d, it, f, t0, t1)

    # -- "THE INGREDIENTS" / "01 SEASON" headers -----------------------------
    def o_header(self, cv, d, it, f, t0, t1):
        tin = eout(seg(f, t0, t0 + 9), 4)
        tout = ein(seg(f, t1 - 5, t1 + 1), 2)
        a = tin * (1 - tout)
        if a <= 0:
            return
        y = 118 - 30 * tout
        if it.get("num"):
            num, _ = text_layer(it["num"], font(C.FONT_BLACK, 120 * UI), RED + (255,), spacing=-2)
            txt, pad = text_layer(it["text"], font(C.FONT_BLACK, 120 * UI), CREAM + (255,), spacing=4)
            x0 = 56
            paste(cv, num, x0 - pad - 60 * UI * (1 - tin), y - pad, a)
            nx = x0 + num.width - 2 * pad + 26 * UI
            paste(cv, txt, nx - pad, y - pad, a, clip_w=pad + (txt.width - pad) * tin)
            bw = (num.width - 2 * pad + 26 * UI + txt.width - 2 * pad) * eout(seg(f, t0 + 4, t0 + 14))
            d.rectangle((x0, y + 150 * UI, x0 + bw * (1 - tout), y + 150 * UI + 6), fill=GOLD + (int(255 * a),))
        else:
            txt, pad = text_layer(it["text"], font(C.FONT_BLACK, 86 * UI), CREAM + (255,), spacing=6)
            paste(cv, txt, W / 2, y - pad + 30 * (1 - tin), a, anchor="ct")
            bw = 160 * UI * eout(seg(f, t0 + 3, t0 + 13))
            d.rectangle((W / 2 - bw / 2, y - 20, W / 2 + bw / 2, y - 14), fill=RED + (int(255 * a),))

    # -- tracked ingredient / layer labels ------------------------------------
    def o_label(self, cv, d, it, f, t0, t1):
        p = self.anchor(it["track"], f)
        if p is None:
            return
        x, y = p
        tout = ein(seg(f, t1 - 4, t1 + 2), 2)
        a_dot = eback(seg(f, t0, t0 + 5)) * (1 - tout)
        a_line = eout(seg(f, t0 + 2, t0 + 8)) * (1 - tout)
        a_pill = eout(seg(f, t0 + 5, t0 + 12)) * (1 - tout)
        if a_dot <= 0:
            return
        side = it.get("side", "below")
        fnt = font(C.FONT_BOLD, 38 * UI)
        txt, pad = text_layer(it["text"], fnt, INK + (255,), spacing=2, shadow=False)
        tw, th = txt.width - 2 * pad, fnt.getmetrics()[0] + 4
        pw, ph = tw + 78 * UI, th + 26 * UI
        if side == "below":
            ex, ey = x, y + 10 * UI
            px0, py0 = clamp(x - pw / 2, SAFE, W - SAFE - pw), ey + 18 * UI
            rd = 9 * UI * a_dot
            d.ellipse((x - rd, y - rd, x + rd, y + rd), fill=RED + (int(255 * min(1, a_dot)),))
        else:
            sgn = 1 if side == "right" else -1
            (px0, py0), (elx, ely), (tx_, ty_) = label_layout(x, y, sgn, pw, ph, L=120 * UI, k=UI)
            # the pill slides out with its leader line
            slide = sgn * 120 * UI * (a_line - 1)
            px0 += slide
            ring = (9 + 10 * seg(f, t0, t0 + 12)) * UI
            d.ellipse((x - ring, y - ring, x + ring, y + ring), outline=CREAM + (int(160 * (1 - seg(f, t0, t0 + 12)) * (1 - tout)),), width=max(2, round(3 * UI)))
            rd = 8 * UI * a_dot
            d.ellipse((x - rd, y - rd, x + rd, y + rd), fill=RED + (int(255 * min(1, a_dot)),))
            if a_line > 0:
                pts = [(x, y), (x + (elx - x) * a_line, y + (ely - y) * a_line),
                       (x + (tx_ + slide - x) * a_line, y + (ty_ - y) * a_line)]
                d.line(pts, fill=CREAM + (int(230 * a_line),), width=max(2, round(4 * UI)), joint="curve")
        if a_pill > 0:
            s = 0.75 + 0.25 * a_pill
            cx, cy = px0 + pw / 2, py0 + ph / 2
            box = (cx - pw * s / 2, cy - ph * s / 2, cx + pw * s / 2, cy + ph * s / 2)
            sh = Image.new("RGBA", (int(pw + 60), int(ph + 60)), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((30, 36, 30 + pw * s, 36 + ph * s), radius=ph / 2,
                                                 fill=(0, 0, 0, int(110 * a_pill)))
            cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9 * UI)), (int(box[0] - 30), int(box[1] - 30)))
            rrect(d, box, ph * s / 2, CREAM + (int(245 * a_pill),))
            d.ellipse((box[0] + 18 * UI * s, cy - 6 * UI * s, box[0] + 30 * UI * s, cy + 6 * UI * s), fill=RED + (int(255 * a_pill),))
            tr = eout(seg(f, t0 + 7, t0 + 14))
            paste(cv, txt, box[0] + 44 * UI * s - pad, cy - th / 2 - pad + 2, a_pill, scale=1.0,
                  clip_w=pad + (txt.width - pad) * tr)

    # -- arrow callouts --------------------------------------------------------
    def o_callout(self, cv, d, it, f, t0, t1):
        p = self.anchor(it["track"], f)
        if p is None:
            return
        x, y = p
        fnt = font(C.FONT_BLACK, 50 * UI)
        txt, pad = text_layer(it["text"], fnt, CREAM + (255,), spacing=3, shadow=False)
        tw, th = txt.width - 2 * pad, fnt.getmetrics()[0]
        half = (tw + 50 * UI) / 2 + SAFE          # full-size half-width of the red box, plus margin
        tx, ty = x + it.get("dx", -200), y + it.get("dy", -300)
        tx = clamp(tx, half, W - half)
        ty = clamp(ty, 300, H - 260)
        tin = eout(seg(f, t0, t0 + 10))
        tout = ein(seg(f, t1 - 3, t1 + 3))
        a = tin * (1 - tout)
        if a <= 0:
            return
        # bezier arrow from text box towards the anchor
        cxp, cyp = (tx + x) / 2 + (y - ty) * 0.25, (ty + y) / 2 - (x - tx) * 0.25
        n = 28
        k = eout(seg(f, t0 + 3, t0 + 13))
        pts = []
        for i in range(n + 1):
            u = i / n * k
            bx = (1 - u) ** 2 * tx + 2 * (1 - u) * u * cxp + u * u * x
            by = (1 - u) ** 2 * (ty + (40 * UI if y > ty else -40 * UI)) + 2 * (1 - u) * u * cyp + u * u * y
            pts.append((bx, by))
        if len(pts) > 1:
            d.line(pts, fill=CREAM + (int(240 * a),), width=max(3, round(6 * UI)), joint="curve")
            if k > 0.95:
                (x1, y1), (x2, y2) = pts[-3], pts[-1]
                ang = math.atan2(y2 - y1, x2 - x1)
                hl = 26 * UI
                d.polygon([(x2, y2), (x2 - hl * math.cos(ang - 0.45), y2 - hl * math.sin(ang - 0.45)),
                           (x2 - hl * math.cos(ang + 0.45), y2 - hl * math.sin(ang + 0.45))],
                          fill=CREAM + (int(240 * a),))
        s = 0.7 + 0.3 * eback(seg(f, t0, t0 + 9))
        pw, ph = (tw + 50 * UI) * s, (th + 34 * UI) * s
        box = (tx - pw / 2, ty - ph / 2, tx + pw / 2, ty + ph / 2)
        rrect(d, box, 14 * UI * s, RED + (int(240 * a),))
        paste(cv, txt, tx, ty - 4, a, scale=s, anchor="c")

    # -- intro kinetic words ----------------------------------------------------
    def o_kinetic(self, cv, d, it, f, t0, t1):
        y0 = 230
        for i, (w, tw) in enumerate(zip(it["words"], it["times"])):
            if f < tw:
                continue
            tin = seg(f, tw, tw + 6)
            tout = ein(seg(f, t1 - 6 + i, t1 + i), 2)
            a = eout(tin) * (1 - tout)
            s = 1.0 + 0.6 * (1 - eback(tin, 2.4))
            body, dot = w.rstrip("."), "." if w.endswith(".") else ""
            fnt = font(C.FONT_BLACK, 120 * UI)
            im_b, pad = text_layer(body, fnt, CREAM + (255,), spacing=2)
            im_d, _ = text_layer(dot, fnt, RED + (255,), spacing=0) if dot else (None, 0)
            tot = Image.new("RGBA", (im_b.width + (im_d.width - 2 * pad if im_d else 0), im_b.height), (0, 0, 0, 0))
            tot.alpha_composite(im_b, (0, 0))
            if im_d:
                tot.alpha_composite(im_d, (im_b.width - 2 * pad, 0))
            paste(cv, tot, W / 2 - 220 * UI * tout * (1 if i % 2 else -1), y0 + i * 135 * UI, a, scale=s, anchor="c")

    def o_subtitle(self, cv, d, it, f, t0, t1):
        tin = eout(seg(f, t0, t0 + 8))
        tout = ein(seg(f, t1 - 4, t1))
        a = tin * (1 - tout)
        if a <= 0:
            return
        txt, pad = text_layer(it["text"], font(C.FONT_BOLD, 58 * UI), CREAM + (255,), spacing=int(10 * UI))
        y = 1660 + 20 * (1 - tin)
        paste(cv, txt, W / 2, y, a, anchor="c")
        bw = 300 * UI * eout(seg(f, t0 + 4, t0 + 14))
        d.rectangle((W / 2 - bw / 2, y + 52 * UI, W / 2 + bw / 2, y + 52 * UI + 5), fill=RED + (int(255 * a),))

    def o_temp(self, cv, d, it, f, t0, t1):
        tin = eout(seg(f, t0, t0 + 10))
        tout = ein(seg(f, t1 - 4, t1))
        a = tin * (1 - tout)
        if a <= 0:
            return
        x, y = W - 250, 360
        rrect(d, (x, y, x + 170, y + 92), 46, (20, 18, 16, int(200 * a)))
        d.ellipse((x + 18, y + 22, x + 66, y + 70), fill=RED + (int(255 * a),))
        txt, pad = text_layer(it["text"], font(C.FONT_BLACK, 44), CREAM + (255,), shadow=False)
        paste(cv, txt, x + 78 - pad, y + 46 - txt.height / 2, a)

    def o_sparkle(self, cv, d, it, f, t0, t1):
        for i, (u, v, ph, sz) in enumerate(self.sparks):
            k = math.sin(math.pi * ((f - t0) / 22.0 + ph * 3) % math.pi)
            if f < t0 or k <= 0:
                continue
            x, y = 140 + u * (W - 280), 200 + v * 900
            r = (10 + 22 * sz) * k * UI
            al = int(220 * k)
            d.polygon([(x, y - r), (x + r * 0.18, y - r * 0.18), (x + r, y), (x + r * 0.18, y + r * 0.18),
                       (x, y + r), (x - r * 0.18, y + r * 0.18), (x - r, y), (x - r * 0.18, y - r * 0.18)],
                      fill=(255, 236, 200, al))


# --------------------------------------------------------- image effects ---
def load_frame(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(path)
    im = im[:, :, :3][:, :, ::-1].astype(np.float32)
    im /= 65535.0 if im.max() > 255.5 else 255.0
    if im.shape[1] != W or im.shape[0] != H:
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_LANCZOS4)
    return np.clip(im, 0, 1)


_grid = None


def haze(im, f, y0, y1, amp):
    global _grid
    if _grid is None:
        _grid = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    xx, yy = _grid
    m = np.clip((yy / H - y0) / max(y1 - y0, 1e-3), 0, 1)
    # clip: float32 sin(pi) is slightly negative, and a negative ** 0.8 is NaN
    m = np.clip(np.sin(np.pi * m), 0.0, 1.0) ** 0.8
    dx = amp * m * np.sin(yy * 0.045 - f * 0.55 + 1.7 * np.sin(xx * 0.012 + f * 0.21))
    dy = 0.5 * amp * m * np.sin(xx * 0.03 + f * 0.4)
    return cv2.remap(im, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def bloom(im, strength=0.22):
    lum = im.max(axis=2, keepdims=True)
    hi = im * np.clip((lum - 0.62) / 0.38, 0, 1)
    sm = cv2.resize(hi, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(sm, (0, 0), 6) * 0.6 + cv2.GaussianBlur(sm, (0, 0), 18) * 0.4
    return im + strength * cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)


_vig = None


def grade(im):
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.62)) ** 2)
        _vig = (1 - 0.30 * np.clip(r, 0, 1.4) ** 2.2)[..., None]
    lum = (im * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    im = lum + (im - lum) * 1.08                  # +8% saturation
    im = im * _vig
    im = np.clip(im, 0, 1)
    im = im + 0.06 * (im - im * im) * (2 * im - 1) * -1  # gentle S-curve
    return im


def motion_blur(im, amount, axis):
    k = int(abs(amount))
    if k < 2:
        return im
    if axis == "x":
        return cv2.blur(im, (k, 1))
    if axis == "y":
        return cv2.blur(im, (1, k))
    acc = np.zeros_like(im)
    n = 6
    for i in range(n):
        s = 1 + amount / 900.0 * i / (n - 1)
        M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, s)
        acc += cv2.warpAffine(im, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / n


# ---------------------------------------------------------------- main -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", default=os.path.join(ROOT, "out", "timeline.json"))
    ap.add_argument("--frames-dir", default=os.path.join(ROOT, "out", "frames"))
    ap.add_argument("--audio", default=os.path.join(ROOT, "out", "soundtrack.wav"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "spaghetti_bolognese_3d.mp4"))
    ap.add_argument("--stills", default="", help="comma list of global frames to save as PNG instead")
    ap.add_argument("--stills-dir", default=os.path.join(ROOT, "out", "stills"))
    ap.add_argument("--crf", type=int, default=16)
    a = ap.parse_args()
    tl = json.load(open(a.timeline))
    shots = tl["shots"]
    seq = []
    for si, s in enumerate(shots):
        for f in range(1, s["n"] + 1):
            seq.append((si, f))
    ovs = [Overlays(s) for s in shots]
    cuts = [sum(s["n"] for s in shots[:i + 1]) for i in range(len(shots) - 1)]  # last global idx of shot
    axes = ["z", "x", "y", "x", "z", "y"]
    stills = set(int(x) for x in a.stills.split(",") if x)
    proc = None
    if not stills:
        tmp = a.out + ".video.mp4"
        proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                 "-s", f"{W}x{H}", "-r", str(tl["fps"]), "-i", "-", "-c:v", "libx264",
                                 "-preset", "slow", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
                                 "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
    else:
        os.makedirs(a.stills_dir, exist_ok=True)
    rng = np.random.default_rng(1)
    for g, (si, f) in enumerate(seq, start=1):
        if stills and g not in stills:
            continue
        s = shots[si]
        im = load_frame(os.path.join(a.frames_dir, s["name"], f"{f:04d}.png"))
        for it in s["overlays"]:
            if it["type"] == "haze" and it["t0"] <= f <= it["t1"]:
                k = min(seg(f, it["t0"], it["t0"] + 8), 1 - seg(f, it["t1"] - 4, it["t1"]))
                im = haze(im, f, it["y0"], it["y1"], it["amp"] * max(k, 0.0))
        im = bloom(im)
        im = grade(im)
        for it in s["overlays"]:
            if it["type"] == "fade_in" and f <= it["t1"]:
                im = im * eout(seg(f, it["t0"], it["t1"]), 2)
        # transitions around cuts
        for ci, c in enumerate(cuts):
            dist = g - c - 0.5          # <0 : before the cut, >0 : after
            if abs(dist) < 4:
                w = 1 - abs(dist) / 4.0
                im = motion_blur(im, 140 * w ** 1.6, axes[ci % len(axes)])
                im = im + 0.22 * max(0.0, 1 - abs(dist) / 1.5)
        im = np.clip(im + rng.normal(0, 0.006, im.shape).astype(np.float32), 0, 1)
        frame = Image.fromarray((im * 255 + 0.5).astype(np.uint8), "RGB").convert("RGBA")
        ovs[si].draw(frame, f)
        out = np.asarray(frame.convert("RGB"))
        if stills:
            Image.fromarray(out).save(os.path.join(a.stills_dir, f"g{g:04d}_{s['name']}_{f:04d}.png"))
        else:
            proc.stdin.write(out.tobytes())
        if g % 30 == 0:
            print(f"[post] {g}/{len(seq)}", flush=True)
    if proc:
        proc.stdin.close()
        proc.wait()
        if os.path.exists(a.audio):
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-i", a.audio, "-c:v", "copy",
                                   "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", a.out])
            os.remove(tmp)
        else:
            os.replace(tmp, a.out)
        print(f"[post] wrote {a.out}")


if __name__ == "__main__":
    main()
