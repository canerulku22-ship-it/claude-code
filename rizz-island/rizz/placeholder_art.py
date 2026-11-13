"""Procedural placeholder characters.

Until real AI art exists in characters/<id>/, this module draws a stand-in for
every cast member so the whole pipeline runs end to end. The look imitates the
target style: chunky shapes, soft gradients, rim shading, a specular "gloss"
highlight and dark outlines.

How it is organised
-------------------
* `Painter` is a tiny supersampled canvas with shape helpers. Everything is
  specified in *design units* on the 1200x1600 sprite canvas and drawn at
  `SS`x resolution, then downsampled for anti-aliasing.
* Each character has a builder (`build_<id>`) that paints the parts that never
  change (body, legs, hair, props behind the body) and returns a `Rig`: where
  the face and shoulders are, arm colours, and callbacks for parts that sit in
  front of the face (mustache, glasses...).
* `render_expression` copies the cached body, adds arms in the expression's
  pose, then the face (eyes, brows, mouth) and little extras (sweat drop,
  anger mark, steam).

Unknown characters (e.g. a bombshell you add mid-season) get a generic
jelly-bean body in their signature colour, so nothing ever breaks.
"""
from __future__ import annotations

import math
import os
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import config
from .cast import Cast, Character, hex_to_rgb

SS = 2                                   # supersampling factor
DW, DH = config.SPRITE_W, config.SPRITE_H  # design canvas (same as sprite canvas)

# Bump this when the drawing code changes so cached placeholders regenerate.
PLACEHOLDER_VERSION = "2"

INK = (34, 22, 30)            # outline / pupil colour
MOUTH_DARK = (92, 18, 38)
TONGUE = (240, 110, 130)
TEETH = (252, 250, 245)
EYE_WHITE = (255, 255, 255)
BLUSH = (255, 105, 140)
HEART = (240, 40, 80)

Point = tuple[float, float]


# ==========================================================================
# Colour helpers
# ==========================================================================
def shade(rgb: tuple[int, int, int], f: float) -> tuple[int, int, int]:
    """Multiply a colour by f (f < 1 darkens, f > 1 lightens towards white)."""
    if f <= 1:
        return tuple(int(c * f) for c in rgb)  # type: ignore[return-value]
    return tuple(int(c + (255 - c) * (f - 1)) for c in rgb)  # type: ignore[return-value]


def rgb(h: str) -> tuple[int, int, int]:
    return hex_to_rgb(h)


# ==========================================================================
# Painter: supersampled canvas + shape helpers
# ==========================================================================
class Painter:
    def __init__(self, img: Image.Image | None = None):
        self.W, self.H = DW * SS, DH * SS
        self.img = img if img is not None else Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def copy(self) -> "Painter":
        return Painter(self.img.copy())

    # -- coordinate helpers -------------------------------------------------
    @staticmethod
    def s(v: float) -> float:
        return v * SS

    @staticmethod
    def pts(points: list[Point]) -> list[Point]:
        return [(x * SS, y * SS) for x, y in points]

    @staticmethod
    def box(x0: float, y0: float, x1: float, y1: float) -> list[float]:
        return [x0 * SS, y0 * SS, x1 * SS, y1 * SS]

    # -- masks ---------------------------------------------------------------
    def mask(self) -> Image.Image:
        return Image.new("L", (self.W, self.H), 0)

    def ellipse_mask(self, x0, y0, x1, y1, m: Image.Image | None = None) -> Image.Image:
        m = m or self.mask()
        ImageDraw.Draw(m).ellipse(self.box(x0, y0, x1, y1), fill=255)
        return m

    def circle_mask(self, cx, cy, r, m: Image.Image | None = None) -> Image.Image:
        return self.ellipse_mask(cx - r, cy - r, cx + r, cy + r, m)

    def rrect_mask(self, x0, y0, x1, y1, radius, m: Image.Image | None = None) -> Image.Image:
        m = m or self.mask()
        ImageDraw.Draw(m).rounded_rectangle(self.box(x0, y0, x1, y1), radius=radius * SS, fill=255)
        return m

    def poly_mask(self, points: list[Point], m: Image.Image | None = None, smooth: float = 0) -> Image.Image:
        m = m or self.mask()
        ImageDraw.Draw(m).polygon(self.pts(points), fill=255)
        return self.smooth(m, smooth) if smooth else m

    def line_mask(self, points: list[Point], width: float, m: Image.Image | None = None) -> Image.Image:
        """A thick polyline with rounded ends and joints (used for arms, legs, stalks)."""
        m = m or self.mask()
        d = ImageDraw.Draw(m)
        p = self.pts(points)
        d.line(p, fill=255, width=int(width * SS), joint="curve")
        r = width * SS / 2
        for x, y in (p[0], p[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return m

    def rotated_ellipse_mask(self, cx, cy, rx, ry, angle_deg, m: Image.Image | None = None) -> Image.Image:
        """Ellipse rotated about its centre (positive angle = counter-clockwise)."""
        m = m or self.mask()
        w, h = int(rx * 2 * SS) + 4, int(ry * 2 * SS) + 4
        small = Image.new("L", (w, h), 0)
        ImageDraw.Draw(small).ellipse([2, 2, w - 2, h - 2], fill=255)
        small = small.rotate(angle_deg, resample=Image.BICUBIC, expand=True)
        tmp = self.mask()
        tmp.paste(small, (int(cx * SS - small.width / 2), int(cy * SS - small.height / 2)))
        return ImageChops.lighter(m, tmp)

    @staticmethod
    def smooth(m: Image.Image, radius: float) -> Image.Image:
        """Round off sharp corners: blur, then re-threshold."""
        return m.filter(ImageFilter.GaussianBlur(radius * SS)).point(lambda v: 255 if v > 127 else 0)

    @staticmethod
    def union(*ms: Image.Image) -> Image.Image:
        out = ms[0]
        for m in ms[1:]:
            out = ImageChops.lighter(out, m)
        return out

    @staticmethod
    def intersect(a: Image.Image, b: Image.Image) -> Image.Image:
        return ImageChops.multiply(a, b)

    @staticmethod
    def subtract(a: Image.Image, b: Image.Image) -> Image.Image:
        return ImageChops.subtract(a, b)

    def albedo(self, color: tuple[int, int, int]) -> Image.Image:
        """A full-canvas RGB 'paint' layer that patterns can be drawn onto."""
        return Image.new("RGB", (self.W, self.H), color)

    # -- the glossy 3D-cartoon look ------------------------------------------
    def glossy(self, mask: Image.Image, paint, *, rim: float = 0.5, gloss: float = 0.5,
               spec: float = 0.7, light: Point = (0.33, 0.2), grad: float = 0.26,
               outline: float = 5, outline_rgb: tuple[int, int, int] | None = None,
               bounce: float = 0.10) -> None:
        """Fill `mask` with `paint` (a colour or an RGB albedo image) and shade it.

        Shading = top-to-bottom gradient + darkened rim (from a blurred mask,
        which approximates a rounded surface) + broad soft highlight + a tight
        specular blob + a little bounce light on the lower rim, then an
        outline ring. Work happens only inside the mask's bounding box.
        """
        bbox = mask.getbbox()
        if bbox is None:
            return
        o = outline * SS
        pad = int(o * 3 + 6)
        x0, y0 = max(0, bbox[0] - pad), max(0, bbox[1] - pad)
        x1, y1 = min(self.W, bbox[2] + pad), min(self.H, bbox[3] + pad)
        crop = (x0, y0, x1, y1)
        m = mask.crop(crop)
        M = np.asarray(m, np.float32) / 255.0
        h, w = M.shape
        bw, bh = max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])
        ys = ((np.arange(h) + y0 - bbox[1]) / bh)[:, None]
        xs = ((np.arange(w) + x0 - bbox[0]) / bw)[None, :]

        if isinstance(paint, Image.Image):
            A = np.asarray(paint.crop(crop).convert("RGB"), np.float32)
            mean = tuple(int(v) for v in A[M > 0.5].mean(axis=0)) if (M > 0.5).any() else (128, 128, 128)
        else:
            A = np.empty((h, w, 3), np.float32)
            A[:] = paint
            mean = paint

        size = min(bw, bh)
        B = np.asarray(m.filter(ImageFilter.GaussianBlur(max(2.0, size * 0.09))), np.float32) / 255.0
        edge = np.clip((1.0 - B) * 2.0, 0, 1)                      # 1 at the silhouette, 0 deep inside
        k = (1.10 - grad * ys) * (1 - rim * edge ** 1.5)
        k = k + bounce * edge * np.clip(ys - 0.55, 0, 1) * 2.0      # reflected light from the ground
        C = A * k[..., None]
        d2 = ((xs - light[0]) / 0.42) ** 2 + ((ys - light[1]) / 0.38) ** 2
        C = C + (255 - C) * (np.exp(-d2 * 2.0) * gloss * 0.5)[..., None]
        d2s = ((xs - light[0]) / 0.11) ** 2 + ((ys - light[1] + 0.02) / 0.065) ** 2
        C = C + (255 - C) * (np.exp(-d2s * 3.0) * spec * (1 - edge))[..., None]
        C = np.clip(C, 0, 255)

        alpha = M
        if o > 0:
            D = np.asarray(m.filter(ImageFilter.GaussianBlur(o * 0.5)), np.float32) / 255.0
            dil = np.maximum(np.clip((D - 0.02) / 0.10, 0, 1), M)
            ring = dil - M
            ocol = np.array(outline_rgb or shade(mean, 0.42), np.float32)
            C = (C * M[..., None] + ocol * ring[..., None]) / np.maximum(dil, 1e-6)[..., None]
            alpha = dil
        layer = Image.fromarray(np.dstack([C, alpha * 255]).astype(np.uint8), "RGBA")
        self.img.alpha_composite(layer, dest=(x0, y0))

    def flat(self, mask: Image.Image, color, outline: float = 0, outline_rgb=INK, opacity: float = 1.0) -> None:
        """Flat fill (no shading), optional outline. Used for small face parts."""
        bbox = mask.getbbox()
        if bbox is None:
            return
        layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        if outline:
            dil = mask.filter(ImageFilter.GaussianBlur(outline * SS * 0.5)).point(lambda v: 255 if v > 10 else 0)
            layer.paste(outline_rgb + (255,), (0, 0), dil)
        layer.paste(tuple(color) + (255,), (0, 0), mask)
        if opacity < 1:
            a = layer.getchannel("A").point(lambda v: int(v * opacity))
            layer.putalpha(a)
        self.img.alpha_composite(layer)

    def draw(self) -> ImageDraw.ImageDraw:
        return ImageDraw.Draw(self.img)

    def stroke(self, points: list[Point], color, width: float, closed: bool = False) -> None:
        """Opaque thick polyline with round caps drawn straight onto the image."""
        m = self.line_mask(points + ([points[0]] if closed else []), width)
        self.flat(m, color)

    def arc_points(self, cx, cy, rx, ry, a0, a1, n: int = 24) -> list[Point]:
        """Points along an elliptical arc; angles in degrees, 0 = +x, 90 = down."""
        return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
                 cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]

    def to_sprite(self) -> Image.Image:
        return self.img.resize((DW, DH), Image.LANCZOS)


def heart_points(cx: float, cy: float, size: float, n: int = 60) -> list[Point]:
    """Classic parametric heart, `size` ~ its width."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 34, cy + y * size / 34))
    return pts


def bezier(p0: Point, p1: Point, p2: Point, n: int = 20) -> list[Point]:
    """Quadratic Bézier curve as a list of points."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


# ==========================================================================
# Rig: what an expression needs to know about a character
# ==========================================================================
@dataclass
class Rig:
    eyes: list[Point]                       # eye centres
    eye_r: tuple[float, float]              # (rx, ry)
    mouth: Point
    mouth_w: float
    skin: tuple[int, int, int]              # colour for eyelids
    shoulders: list[Point] | None = None    # [screen-left, screen-right]; None = no arms
    arm_rgb: tuple[int, int, int] = (200, 200, 200)
    hand_rgb: tuple[int, int, int] | None = None
    arm_w: float = 34
    arm_len: float = 1.0
    lashes: bool = False
    cheeks: bool = False
    lip_rgb: tuple[int, int, int] | None = None
    brow_rgb: tuple[int, int, int] = INK
    head_top: Point = (600, 300)            # where anger marks / steam go
    prop: Callable[[Painter, Point, str], None] | None = None   # drawn at the screen-right hand
    front: Callable[[Painter, str], None] | None = None          # drawn after the face
    extras: Callable[[Painter, str], None] | None = None         # expression-specific extras


# ==========================================================================
# Face
# ==========================================================================
def draw_eye(p: Painter, rig: Rig, cx: float, cy: float, side: int, style: str) -> None:
    """side = -1 for the screen-left eye, +1 for the right one."""
    rx, ry = rig.eye_r
    lw = max(4.0, rx * 0.11)
    if style == "heart":
        pts = heart_points(cx, cy + ry * 0.05, rx * 2.3)
        p.flat(p.poly_mask(pts), HEART, outline=lw * 0.8, outline_rgb=shade(HEART, 0.45))
        p.flat(p.ellipse_mask(cx - rx * 0.55, cy - ry * 0.55, cx - rx * 0.15, cy - ry * 0.2), (255, 220, 230))
        return
    if style == "closed":
        p.stroke(p.arc_points(cx, cy - ry * 0.15, rx * 0.9, ry * 0.45, 15, 165), INK, lw * 1.3)
        if rig.lashes:
            for a in (25, 0):
                ang = math.radians(a)
                x0 = cx + side * rx * 0.85 * math.cos(ang)
                y0 = cy - ry * 0.05
                p.stroke([(x0, y0), (x0 + side * rx * 0.35, y0 + ry * 0.12)], INK, lw)
        return

    srx, sry, pr = rx, ry, rx * 0.5
    if style == "wide":
        srx, sry, pr = rx * 1.15, ry * 1.22, rx * 0.28
    p.flat(p.ellipse_mask(cx - srx, cy - sry, cx + srx, cy + sry), EYE_WHITE, outline=lw, outline_rgb=INK)

    # Pupil: looks slightly towards the centre; smug looks sideways.
    px = cx - side * rx * 0.12
    py = cy + ry * 0.08
    if style == "smug":
        px, py = cx + rx * 0.32, cy + ry * 0.22
    if style == "wide":
        px, py = cx, cy
    p.flat(p.circle_mask(px, py, pr), INK)
    p.flat(p.circle_mask(px - pr * 0.35, py - pr * 0.4, pr * 0.3), (255, 255, 255))

    if rig.lashes and style != "wide":
        for a in (-60, -35, -10):
            ang = math.radians(a)
            x0 = cx + side * srx * 0.95 * math.cos(ang)
            y0 = cy + sry * 0.95 * math.sin(ang)
            p.stroke([(x0, y0), (x0 + side * rx * 0.38 * math.cos(ang), y0 + rx * 0.38 * math.sin(ang) - 6)], INK, lw)
    elif rig.lashes and style == "wide":
        for a in (-70, -45, -20):
            ang = math.radians(a)
            x0 = cx + side * srx * 0.97 * math.cos(ang)
            y0 = cy + sry * 0.97 * math.sin(ang)
            p.stroke([(x0, y0), (x0 + side * rx * 0.42 * math.cos(ang), y0 + rx * 0.42 * math.sin(ang))], INK, lw)

    # Eyelids for angry (slanted towards the nose) and smug (half closed).
    if style in ("angry", "smug"):
        if style == "angry":
            inner_y, outer_y = cy - sry * 0.05, cy - sry * 0.75
        else:
            inner_y = outer_y = cy - sry * 0.05
        inner_x, outer_x = cx - side * srx * 1.3, cx + side * srx * 1.3
        lid = [(inner_x, inner_y), (outer_x, outer_y), (outer_x, cy - sry * 1.6), (inner_x, cy - sry * 1.6)]
        eye_m = p.ellipse_mask(cx - srx - lw, cy - sry - lw, cx + srx + lw, cy + sry + lw)
        lid_m = p.intersect(p.poly_mask(lid), eye_m)
        p.flat(lid_m, rig.skin)
        p.stroke([(inner_x + side * srx * 0.35, inner_y + (outer_y - inner_y) * 0.13),
                  (outer_x - side * srx * 0.35, outer_y - (outer_y - inner_y) * 0.13)], INK, lw * 1.2)


def draw_brows(p: Painter, rig: Rig, style: str) -> None:
    rx, ry = rig.eye_r
    w = max(8.0, rx * 0.24)
    for i, (cx, cy) in enumerate(rig.eyes):
        side = -1 if i == 0 else 1
        top = cy - ry
        if style == "shocked":
            pts = p.arc_points(cx, top - ry * 0.55, rx * 0.85, ry * 0.35, 200, 340)
        elif style == "angry":
            pts = [(cx - side * rx * 0.9, top - ry * 0.05), (cx + side * rx * 0.9, top - ry * 0.65)]
        elif style == "smug":
            if side == -1:
                pts = p.arc_points(cx, top - ry * 0.45, rx * 0.85, ry * 0.3, 200, 340)
            else:
                pts = [(cx - rx * 0.85, top - ry * 0.05), (cx + rx * 0.85, top - ry * 0.2)]
        elif style == "in_love":
            pts = p.arc_points(cx, top - ry * 0.45, rx * 0.8, ry * 0.25, 205, 335)
        else:  # neutral / talking / blink
            pts = p.arc_points(cx, top - ry * 0.18, rx * 0.85, ry * 0.25, 205, 335)
        p.stroke(pts, rig.brow_rgb, w)


def open_mouth(p: Painter, cx: float, top: float, w: float, h: float, *, teeth_top=True,
               teeth_bottom=False, tongue=True, frown=False, skew: float = 0.0) -> None:
    """Dark mouth cavity shaped like a 'D' (flat top, round bottom) with teeth and tongue."""
    lw = max(4.0, w * 0.05)
    if frown:   # flat bottom, round top (shouting)
        cav = p.intersect(p.ellipse_mask(cx - w / 2, top, cx + w / 2, top + h * 2),
                          p.rrect_mask(cx - w, top, cx + w, top + h, 1))
    else:
        cav = p.intersect(p.ellipse_mask(cx - w / 2, top - h, cx + w / 2, top + h),
                          p.rrect_mask(cx - w, top, cx + w, top + h + 4, 1))
    if skew:
        bbox = cav.getbbox()
        if bbox:
            # shear horizontally so one corner rises (smirk)
            cav = cav.transform(cav.size, Image.AFFINE, (1, skew, -skew * (top * SS), 0, 1, 0), Image.BICUBIC)
    p.flat(cav, MOUTH_DARK, outline=lw, outline_rgb=INK)
    if tongue:
        tm = p.intersect(p.ellipse_mask(cx - w * 0.3, top + h * 0.55, cx + w * 0.3, top + h * 1.25), cav)
        p.flat(tm, TONGUE)
    if teeth_top:
        p.flat(p.intersect(p.rrect_mask(cx - w, top, cx + w, top + h * 0.22, 1), cav), TEETH)
    if teeth_bottom:
        p.flat(p.intersect(p.rrect_mask(cx - w, top + h * 0.8, cx + w, top + h + 10, 1), cav), TEETH)


def draw_mouth(p: Painter, rig: Rig, expr: str, talking: bool) -> None:
    mx, my = rig.mouth
    w = rig.mouth_w
    lw = max(7.0, w * 0.08)
    line_rgb = rig.lip_rgb or INK
    if expr in ("neutral", "blink"):
        if talking:
            open_mouth(p, mx, my - w * 0.08, w * 0.8, w * 0.42)
        else:
            p.stroke(p.arc_points(mx, my - w * 0.25, w * 0.42, w * 0.25, 25, 155), line_rgb, lw)
    elif expr == "shocked":
        sw, sh = (w * 0.42, w * 0.55) if not talking else (w * 0.55, w * 0.72)
        m = p.ellipse_mask(mx - sw / 2, my - sh * 0.35, mx + sw / 2, my + sh * 0.65)
        p.flat(m, MOUTH_DARK, outline=lw * 0.7, outline_rgb=INK)
        p.flat(p.intersect(p.ellipse_mask(mx - sw * 0.32, my + sh * 0.25, mx + sw * 0.32, my + sh * 0.75), m), TONGUE)
    elif expr == "angry":
        if talking:
            open_mouth(p, mx, my - w * 0.1, w * 0.85, w * 0.5, teeth_bottom=True, frown=True, tongue=False)
        else:
            # gritted teeth in a slight frown
            g = p.rrect_mask(mx - w * 0.42, my - w * 0.12, mx + w * 0.42, my + w * 0.14, w * 0.1)
            p.flat(g, TEETH, outline=lw * 0.7, outline_rgb=INK)
            p.stroke([(mx - w * 0.42, my + 0.01 * w), (mx + w * 0.42, my + 0.01 * w)], INK, lw * 0.4)
            for k in (-0.2, 0, 0.2):
                p.stroke([(mx + k * w, my - w * 0.1), (mx + k * w, my + w * 0.12)], INK, lw * 0.4)
    elif expr == "smug":
        if talking:
            open_mouth(p, mx + w * 0.08, my - w * 0.05, w * 0.55, w * 0.28, skew=0.18)
        else:
            p.stroke(bezier((mx - w * 0.38, my + w * 0.02), (mx + w * 0.05, my + w * 0.14), (mx + w * 0.42, my - w * 0.16)),
                     line_rgb, lw)
    elif expr == "in_love":
        if talking:
            open_mouth(p, mx, my - w * 0.1, w * 0.85, w * 0.5)
        else:
            p.stroke(p.arc_points(mx, my - w * 0.3, w * 0.5, w * 0.34, 15, 165), line_rgb, lw)


def draw_face(p: Painter, rig: Rig, expr: str) -> None:
    talking = expr == "talking" or expr.endswith("_talking")
    base = "neutral" if expr == "talking" else expr.replace("_talking", "")
    eye_style = {"neutral": "normal", "blink": "closed", "shocked": "wide", "angry": "angry",
                 "smug": "smug", "in_love": "heart"}[base]

    if rig.cheeks or base == "in_love":
        rx, ry = rig.eye_r
        blush = Image.new("L", (p.W, p.H), 0)
        for i, (cx, cy) in enumerate(rig.eyes):
            side = -1 if i == 0 else 1
            bx = cx + side * rx * 0.55
            p.ellipse_mask(bx - rx * 0.7, cy + ry * 0.75, bx + rx * 0.7, cy + ry * 1.2, blush)
        p.flat(blush.filter(ImageFilter.GaussianBlur(6 * SS)), BLUSH, opacity=0.55 if base == "in_love" else 0.35)

    for i, (cx, cy) in enumerate(rig.eyes):
        draw_eye(p, rig, cx, cy, -1 if i == 0 else 1, eye_style)
    draw_brows(p, rig, base)
    draw_mouth(p, rig, base, talking)


# ==========================================================================
# Arms
# ==========================================================================
# Offsets from the shoulder for the screen-RIGHT arm (x positive = outward).
# The screen-left arm mirrors x. "talking" variants reuse their base pose so
# swapping mouth-open/closed never makes the arms flicker.
ARM_POSES: dict[str, tuple[Point, Point]] = {
    "neutral": ((60, 150), (85, 290)),
    "shocked": ((150, -30), (120, -200)),
    "angry":   ((160, 110), (25, 200)),     # fists on hips
    "smug":    ((70, 170), (-150, 135)),    # arms crossed
    "in_love": ((120, 70), (-5, -95)),      # hands up by the cheeks
}


def draw_arms(p: Painter, rig: Rig, expr: str) -> None:
    if not rig.shoulders:
        return
    base = "neutral" if expr in ("talking", "blink") else expr.replace("_talking", "")
    elbow, hand = ARM_POSES.get(base, ARM_POSES["neutral"])
    L = rig.arm_len
    arm_m = p.mask()
    hand_m = p.mask()
    hands = []
    for i, (sx, sy) in enumerate(rig.shoulders):
        side = -1 if i == 0 else 1
        e = (sx + side * elbow[0] * L, sy + elbow[1] * L)
        h = (sx + side * hand[0] * L, sy + hand[1] * L)
        aw = rig.arm_w * 1.2
        p.line_mask([(sx, sy)] + bezier((sx, sy), e, h, 12)[1:], aw, arm_m)
        r = aw * (1.25 if base == "angry" else 1.1)
        p.circle_mask(h[0], h[1], r, hand_m)
        hands.append(h)
    p.glossy(arm_m, rig.arm_rgb, outline=4, rim=0.45, spec=0.3)
    p.glossy(hand_m, rig.hand_rgb or rig.arm_rgb, outline=4, rim=0.4, spec=0.3)
    if rig.prop and base not in ("in_love", "smug"):
        rig.prop(p, hands[1], base)


# ==========================================================================
# Expression extras shared by everyone
# ==========================================================================
def sweat_drop(p: Painter, x: float, y: float, s: float = 1.0) -> None:
    pts = [(x, y - 45 * s)] + p.arc_points(x, y, 26 * s, 28 * s, -30, 210, 20)
    p.glossy(p.poly_mask(pts), (120, 200, 255), outline=3, rim=0.3, spec=0.9, gloss=0.6)


def anger_mark(p: Painter, x: float, y: float, s: float = 1.0) -> None:
    """The anime 'popping vein' symbol: four curved ticks around a centre."""
    col = (235, 30, 50)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        cx, cy = x + math.cos(a) * 30 * s, y + math.sin(a) * 30 * s
        pts = p.arc_points(cx, cy, 26 * s, 26 * s, math.degrees(a) + 120, math.degrees(a) + 240, 10)
        p.stroke(pts, col, 11 * s)


def steam_puff(p: Painter, x: float, y: float, s: float = 1.0) -> None:
    m = p.mask()
    for dx, dy, r in ((0, 0, 40), (35, -30, 32), (-30, -35, 28), (5, -65, 26)):
        p.circle_mask(x + dx * s, y + dy * s, r * s, m)
    p.glossy(m, (250, 250, 255), outline=3, outline_rgb=(170, 170, 190), rim=0.3, spec=0.2)


def common_extras(p: Painter, rig: Rig, expr: str) -> None:
    base = expr.replace("_talking", "")
    hx, hy = rig.head_top
    rx, ry = rig.eye_r
    if base == "shocked":
        ex, ey = rig.eyes[1]
        sweat_drop(p, ex + rx * 2.1, ey - ry * 0.6)
    elif base == "angry":
        anger_mark(p, hx + 170, hy + 50, 1.7)


# ==========================================================================
# Character builders. Each paints the static body onto `p` and returns a Rig.
# Coordinates are design units on the 1200x1600 canvas, feet near y=1560.
# ==========================================================================
def build_baguettini(p: Painter, c: Character) -> Rig:
    crust = rgb("#E2A043")
    dark = rgb("#B97526")
    # legs + loafers
    legs = p.union(p.line_mask([(540, 1380), (535, 1490)], 58), p.line_mask([(660, 1380), (665, 1490)], 58))
    p.glossy(legs, dark, outline=4)
    shoes = p.union(p.ellipse_mask(470, 1480, 590, 1560), p.ellipse_mask(610, 1480, 730, 1560))
    p.glossy(shoes, rgb("#5B3417"), spec=0.9, outline=4)
    # body with score marks painted into the albedo
    body = p.rrect_mask(425, 250, 775, 1430, 175)
    paint = p.albedo(crust)
    scores = p.mask()
    for cy in (360, 960, 1110, 1260):
        scores = p.rotated_ellipse_mask(600, cy, 120, 26, 28, scores)
    paint.paste(rgb("#F8D99A"), (0, 0), scores.filter(ImageFilter.GaussianBlur(3 * SS)))
    # flour speckles
    d = ImageDraw.Draw(paint)
    rnd = random.Random(7)
    for _ in range(140):
        x, y = rnd.uniform(440, 760), rnd.uniform(270, 1410)
        r = rnd.uniform(2, 5)
        d.ellipse(p.box(x - r, y - r, x + r, y + r), fill=rgb("#F3D7A6"))
    p.glossy(body, paint, rim=0.55, gloss=0.55, spec=0.75)
    # beret (tilted) + stalk
    beret = p.rotated_ellipse_mask(615, 255, 165, 62, 10)
    p.glossy(beret, rgb("#D7263D"), spec=0.6)
    p.glossy(p.circle_mask(640, 192, 20), rgb("#B01D31"), outline=3)

    def mustache(pp: Painter, expr: str) -> None:
        for side in (-1, 1):
            pts = bezier((600, 715), (600 + side * 70, 760), (600 + side * 118, 708), 16)
            pts += bezier((600 + side * 118, 708), (600 + side * 128, 675), (600 + side * 100, 680), 8)[1:]
            pp.stroke(pts, rgb("#2B1A12"), 20)

    return Rig(eyes=[(538, 590), (662, 590)], eye_r=(52, 62), mouth=(600, 800), mouth_w=136,
               skin=crust, shoulders=[(450, 900), (750, 900)], arm_rgb=rgb("#D08E33"), arm_w=36,
               head_top=(600, 330), front=mustache)


def build_conetta(p: Painter, c: Character) -> Rig:
    orange = rgb("#FF6A13")
    feet = p.union(p.ellipse_mask(420, 1480, 540, 1560), p.ellipse_mask(660, 1480, 780, 1560))
    p.glossy(feet, (245, 245, 250), outline=4, spec=0.5)
    base = p.rrect_mask(240, 1395, 960, 1495, 30)
    p.glossy(base, rgb("#D9500B"), rim=0.4)
    cone = p.union(p.poly_mask([(548, 240), (652, 240), (925, 1425), (275, 1425)]), p.circle_mask(600, 262, 58))
    cone = p.smooth(cone, 8)
    paint = p.albedo(orange)
    stripes = p.union(p.rrect_mask(0, 470, DW, 560, 1), p.rrect_mask(0, 1060, DW, 1170, 1))
    paint.paste((248, 248, 248), (0, 0), stripes)
    p.glossy(cone, paint, rim=0.5, gloss=0.6, spec=0.85)

    def phone(pp: Painter, hand: Point, expr: str) -> None:
        hx, hy = hand
        pp.stroke([(hx, hy), (hx + 40, hy - 230)], (60, 60, 70), 12)       # selfie stick
        ph = pp.rrect_mask(hx + 5, hy - 360, hx + 85, hy - 220, 14)
        pp.glossy(ph, (35, 35, 45), outline=3, spec=0.9)
        pp.flat(pp.rrect_mask(hx + 14, hy - 350, hx + 76, hy - 232, 8), (120, 210, 255))
        pp.flat(pp.circle_mask(hx + 45, hy - 291, 12), (255, 80, 120))     # REC dot

    return Rig(eyes=[(535, 765), (665, 765)], eye_r=(54, 64), mouth=(600, 925), mouth_w=124,
               skin=orange, shoulders=[(390, 990), (810, 990)], arm_rgb=rgb("#B8460C"),
               hand_rgb=(250, 250, 252), arm_w=32,
               lashes=True, lip_rgb=rgb("#E83E8C"), head_top=(600, 330), prop=phone)


def build_ranocchio(p: Painter, c: Character) -> Rig:
    green = rgb("#4FC232")
    belly = rgb("#B9F07C")
    feet = p.union(p.ellipse_mask(320, 1490, 560, 1565), p.ellipse_mask(640, 1490, 880, 1565))
    p.glossy(feet, rgb("#7BE04F"), outline=4)
    thighs = p.union(p.rotated_ellipse_mask(460, 1390, 95, 120, 25), p.rotated_ellipse_mask(740, 1390, 95, 120, -25))
    p.glossy(thighs, green)
    body = p.union(p.ellipse_mask(320, 600, 880, 1330), p.ellipse_mask(290, 320, 910, 780),
                   p.circle_mask(430, 310, 105), p.circle_mask(770, 310, 105))
    paint = p.albedo(green)
    paint.paste(belly, (0, 0), p.ellipse_mask(410, 700, 790, 1260).filter(ImageFilter.GaussianBlur(4 * SS)))
    p.glossy(body, paint, rim=0.5, gloss=0.55, spec=0.7)
    # gym shorts
    shorts = p.intersect(p.rrect_mask(330, 1170, 870, 1360, 60), p.ellipse_mask(300, 560, 900, 1370))
    sp = p.albedo(rgb("#243B8F"))
    sp.paste((250, 250, 250), (0, 0), p.union(p.rrect_mask(352, 1180, 372, 1360, 1), p.rrect_mask(828, 1180, 848, 1360, 1)))
    p.glossy(shorts, sp, rim=0.45)
    # pecs + six-pack, each pad shaded on its own for a chiselled look
    for box in ((440, 690, 592, 800), (608, 690, 760, 800)):
        p.glossy(p.rrect_mask(*box, 45), belly, rim=0.6, outline=3, outline_rgb=rgb("#5E9E33"), spec=0.5)
    for row in range(3):
        for col in range(2):
            x0 = 482 + col * 124
            y0 = 825 + row * 112
            p.glossy(p.rrect_mask(x0, y0, x0 + 112, y0 + 100, 34), belly, rim=0.65, outline=3,
                     outline_rgb=rgb("#5E9E33"), spec=0.55)
    # sweatband across the forehead
    band = p.intersect(p.rotated_ellipse_mask(600, 455, 330, 30, -3), p.ellipse_mask(290, 320, 910, 780))
    p.glossy(band, rgb("#E5243B"), rim=0.35, outline=3)
    # nostrils
    for x in (575, 625):
        p.flat(p.ellipse_mask(x - 9, 525, x + 9, 540), shade(green, 0.45))

    def shaker(pp: Painter, hand: Point, expr: str) -> None:
        hx, hy = hand
        body_m = pp.rrect_mask(hx - 38, hy - 150, hx + 38, hy + 20, 18)
        pp.glossy(body_m, (250, 250, 255), outline=3, spec=0.8)
        pp.flat(pp.rrect_mask(hx - 38, hy - 95, hx + 38, hy - 40, 1), (255, 120, 170))
        pp.glossy(pp.rrect_mask(hx - 42, hy - 185, hx + 42, hy - 140, 12), (60, 60, 70), outline=3)

    return Rig(eyes=[(430, 300), (770, 300)], eye_r=(64, 66), mouth=(600, 615), mouth_w=300,
               skin=green, shoulders=[(360, 820), (840, 820)], arm_rgb=green, arm_w=50, arm_len=1.05,
               head_top=(600, 200), prop=shaker)


def build_lumachina(p: Painter, c: Character) -> Rig:
    pink = rgb("#FFB0D5")
    foot = p.union(p.rrect_mask(160, 1340, 1040, 1560, 110), p.rrect_mask(600, 940, 850, 1460, 120),
                   p.circle_mask(725, 850, 205))
    paint = p.albedo(pink)
    paint.paste(rgb("#FFD3E8"), (0, 0), p.ellipse_mask(640, 880, 820, 1380).filter(ImageFilter.GaussianBlur(10 * SS)))
    # antennae (behind the head)
    for (x0, y0, x1, y1) in ((680, 690, 630, 560), (775, 690, 830, 565)):
        p.glossy(p.line_mask([(x0, y0), (x1, y1)], 18), pink, outline=3)
        p.glossy(p.circle_mask(x1, y1, 26), rgb("#FF7FB0"), outline=3)
    p.glossy(foot, paint, rim=0.5, gloss=0.6, spec=0.75)
    # waffle cone shell with a cross-hatch pattern
    cone = p.smooth(p.poly_mask([(150, 830), (600, 830), (380, 1390)]), 6)
    wp = p.albedo(rgb("#E0A458"))
    d = ImageDraw.Draw(wp)
    for k in range(-20, 30):
        x = k * 55
        d.line(p.pts([(x, 800), (x + 700, 1500)]), fill=rgb("#B9783A"), width=7 * SS)
        d.line(p.pts([(x + 700, 800), (x, 1500)]), fill=rgb("#B9783A"), width=7 * SS)
    p.glossy(cone, wp, rim=0.45, spec=0.4)
    # drippy gelato scoops + sprinkles + a cherry
    for (cy, r, col) in ((680, 215, "#A8D88A"), (465, 178, "#FF7FA8")):
        scoop = p.circle_mask(375, cy, r)
        for k in range(7):
            x = 375 - r + 20 + k * (2 * r - 40) / 6
            p.circle_mask(x, cy + r * 0.72 + (k % 2) * 22, 42, scoop)
        p.glossy(scoop, rgb(col), rim=0.45, gloss=0.6, spec=0.8)
    rnd = random.Random(3)
    for _ in range(26):
        x, y = rnd.uniform(240, 510), rnd.uniform(330, 760)
        col = rnd.choice([(255, 255, 255), (255, 214, 60), (90, 190, 255), (180, 110, 255), (255, 90, 90)])
        p.flat(p.rotated_ellipse_mask(x, y, 16, 5, rnd.uniform(0, 180)), col)
    p.glossy(p.circle_mask(375, 270, 46), rgb("#E0102F"), spec=1.0)
    p.stroke(bezier((375, 228), (390, 180), (430, 160)), rgb("#3C7A2A"), 8)

    return Rig(eyes=[(660, 840), (790, 840)], eye_r=(50, 60), mouth=(725, 965), mouth_w=100,
               skin=pink, shoulders=None, lashes=True, cheeks=True, head_top=(725, 650))


def build_gnometta(p: Painter, c: Character) -> Rig:
    peach = rgb("#F5C6A5")
    boots = p.union(p.ellipse_mask(440, 1475, 590, 1562), p.ellipse_mask(610, 1475, 760, 1562))
    p.glossy(boots, rgb("#6B3E1E"), outline=4, spec=0.7)
    dress = p.smooth(p.poly_mask([(450, 970), (750, 970), (850, 1500), (350, 1500)]), 14)
    dp = p.albedo(rgb("#2D6CDF"))
    dd = ImageDraw.Draw(dp)
    for yy in range(1010, 1500, 90):
        for xx in range(380, 840, 90):
            off = 45 if (yy // 90) % 2 else 0
            dd.ellipse(p.box(xx + off - 12, yy - 12, xx + off + 12, yy + 12), fill=(235, 240, 255))
    p.glossy(dress, dp, rim=0.5)
    belt = p.intersect(p.rrect_mask(300, 1075, 900, 1125, 1), dress)
    p.glossy(belt, rgb("#6B3E1E"), rim=0.3, outline=3)
    p.glossy(p.rrect_mask(570, 1068, 630, 1132, 8), rgb("#E8C547"), outline=3, spec=1.0)
    # hair buns (behind the face)
    hair = p.union(p.circle_mask(420, 860, 80), p.circle_mask(780, 860, 80))
    p.glossy(hair, (246, 246, 250), rim=0.35, outline=4, outline_rgb=(170, 170, 185))
    p.glossy(p.circle_mask(600, 830, 178), peach, rim=0.45, spec=0.5)
    curls = p.mask()
    for x in range(445, 780, 48):
        p.circle_mask(x, 690, 42, curls)
    p.glossy(curls, (246, 246, 250), rim=0.35, outline=4, outline_rgb=(170, 170, 185))
    # droopy pointy hat
    hat = p.smooth(p.poly_mask([(395, 705), (470, 470), (520, 300), (455, 150), (575, 245),
                                (660, 410), (765, 590), (805, 705)]), 10)
    p.glossy(hat, rgb("#D62839"), rim=0.5, spec=0.6)

    def specs_and_nose(pp: Painter, expr: str) -> None:
        pp.glossy(pp.circle_mask(600, 895, 44), rgb("#F2A488"), rim=0.4, spec=0.8, outline=3)
        for x in (535, 665):
            ring = pp.subtract(pp.circle_mask(x, 822, 70), pp.circle_mask(x, 822, 60))
            pp.flat(ring, rgb("#C9A227"))
        pp.stroke([(588, 812), (612, 812)], rgb("#C9A227"), 10)

    def notebook(pp: Painter, hand: Point, expr: str) -> None:
        hx, hy = hand
        pp.glossy(pp.rrect_mask(hx - 10, hy - 140, hx + 100, hy + 10, 8), rgb("#8B4A2B"), outline=3)
        pp.flat(pp.rrect_mask(hx + 2, hy - 128, hx + 88, hy - 4, 4), (255, 250, 235))
        for k in range(4):
            pp.stroke([(hx + 14, hy - 105 + k * 26), (hx + 76, hy - 105 + k * 26)], (150, 150, 170), 4)

    return Rig(eyes=[(535, 822), (665, 822)], eye_r=(40, 47), mouth=(600, 978), mouth_w=100,
               skin=peach, shoulders=[(460, 1010), (740, 1010)], arm_rgb=rgb("#2D6CDF"), hand_rgb=peach,
               arm_w=32, arm_len=0.95, lashes=True, cheeks=True, head_top=(600, 180),
               front=specs_and_nose, prop=notebook)


def disco_albedo(p: Painter, cx: float, cy: float, r: float) -> Image.Image:
    """Mirror tiles mapped onto a sphere (latitude/longitude grid, random tile tints)."""
    W, H = p.W, p.H
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx / SS - cx) / r
    ny = (yy / SS - cy) / r
    inside = nx * nx + ny * ny < 1
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lat = np.arcsin(np.clip(ny, -1, 1))
    lon = np.arctan2(nx, nz)
    rows, cols = 16, 26
    fr = (lat / np.pi + 0.5) * rows
    fc = (lon / np.pi + 0.5) * cols
    ri, ci = np.floor(fr).astype(int), np.floor(fc).astype(int)
    rnd = np.random.default_rng(11)
    tints = rnd.uniform(0.62, 1.0, size=(rows + 2, cols + 2))
    hue = rnd.choice(4, size=(rows + 2, cols + 2), p=[0.7, 0.12, 0.1, 0.08])
    palette = np.array([(215, 218, 230), (205, 160, 255), (150, 220, 255), (255, 170, 220)], np.float32)
    col = palette[hue[ri.clip(0, rows + 1), ci.clip(0, cols + 1)]] * tints[ri.clip(0, rows + 1), ci.clip(0, cols + 1)][..., None]
    grout = ((fr % 1) < 0.09) | ((fc % 1) < 0.07)
    col[grout] = (70, 70, 90)
    out = np.full((H, W, 3), 200, np.float32)
    out[inside] = col[inside]
    return Image.fromarray(out.astype(np.uint8), "RGB")


def sparkle(p: Painter, x: float, y: float, s: float) -> None:
    pts = []
    for k in range(8):
        a = math.radians(k * 45 - 90)
        rr = s if k % 2 == 0 else s * 0.28
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    p.flat(p.poly_mask(pts), (255, 255, 255))


def build_discotto(p: Painter, c: Character) -> Rig:
    purple = rgb("#9B5CFF")
    shoes = p.union(p.rrect_mask(420, 1465, 575, 1562, 26), p.rrect_mask(625, 1465, 780, 1562, 26))
    p.glossy(shoes, rgb("#7B2FF7"), outline=4, spec=0.9)
    p.flat(p.union(p.rrect_mask(420, 1535, 575, 1550, 1), p.rrect_mask(625, 1535, 780, 1550, 1)), (255, 255, 255))
    legs = p.union(p.poly_mask([(510, 1000), (570, 1000), (585, 1475), (415, 1475)]),
                   p.poly_mask([(630, 1000), (690, 1000), (785, 1475), (615, 1475)]))
    p.glossy(legs, purple, rim=0.45)
    ball = p.circle_mask(600, 640, 385)
    p.glossy(ball, disco_albedo(p, 600, 640, 385), rim=0.55, gloss=0.5, spec=1.0)
    for (x, y, s) in ((380, 400, 46), (820, 520, 34), (470, 930, 28), (870, 860, 40), (300, 700, 24)):
        sparkle(p, x, y, s)
    return Rig(eyes=[(515, 590), (685, 590)], eye_r=(60, 70), mouth=(600, 790), mouth_w=160,
               skin=(200, 204, 220), shoulders=[(250, 770), (950, 770)], arm_rgb=purple,
               hand_rgb=(250, 250, 255), arm_w=30, arm_len=1.05, head_top=(600, 260))


def build_polpetta(p: Painter, c: Character) -> Rig:
    brown = rgb("#8B4A2B")
    shoes = p.union(p.ellipse_mask(430, 1480, 580, 1562), p.ellipse_mask(620, 1480, 770, 1562))
    p.glossy(shoes, (250, 250, 250), outline=4)
    p.flat(p.union(p.rrect_mask(450, 1525, 560, 1538, 1), p.rrect_mask(640, 1525, 750, 1538, 1)), rgb("#E5243B"))
    legs = p.union(p.line_mask([(515, 1350), (510, 1495)], 52), p.line_mask([(685, 1350), (690, 1495)], 52))
    p.glossy(legs, shade(brown, 0.85), outline=4)
    # bumpy meatball outline + speckled texture
    pts = []
    for k in range(180):
        t = 2 * math.pi * k / 180
        rr = 385 * (1 + 0.022 * math.sin(9 * t) + 0.014 * math.sin(17 * t + 1.0) + 0.01 * math.sin(29 * t))
        pts.append((600 + rr * math.cos(t), 990 + rr * math.sin(t)))
    ball = p.poly_mask(pts)
    paint = p.albedo(brown)
    d = ImageDraw.Draw(paint)
    rnd = random.Random(5)
    for _ in range(420):
        x, y = rnd.uniform(220, 980), rnd.uniform(610, 1370)
        r = rnd.uniform(4, 14)
        d.ellipse(p.box(x - r, y - r, x + r, y + r), fill=shade(brown, rnd.choice([0.7, 0.8, 1.25, 1.35])))
    paint = paint.filter(ImageFilter.GaussianBlur(1.5 * SS))
    p.glossy(ball, paint, rim=0.55, gloss=0.5, spec=0.6)
    # glossy tomato sauce with drips
    sauce = p.intersect(p.ellipse_mask(300, 560, 900, 860), ball)
    for (x, l) in ((380, 900), (470, 930), (720, 915), (820, 880)):
        p.line_mask([(x, 800), (x, l)], 46, sauce)
    p.glossy(p.intersect(sauce, ball), rgb("#C8261B"), rim=0.35, gloss=0.6, spec=1.0, outline=3)
    # basil leaves as a bow
    p.glossy(p.rotated_ellipse_mask(650, 600, 85, 38, 25), rgb("#3FA34D"), outline=4, spec=0.6)
    p.glossy(p.rotated_ellipse_mask(745, 590, 85, 38, -20), rgb("#3FA34D"), outline=4, spec=0.6)

    def accessories(pp: Painter, expr: str) -> None:
        # heart sunglasses pushed up on her head
        for x in (520, 680):
            m = pp.poly_mask(heart_points(x, 735, 130))
            pp.glossy(m, rgb("#E0218A"), outline=4, rim=0.3, spec=0.8)
            pp.glossy(pp.poly_mask(heart_points(x, 738, 98)), (40, 20, 50), outline=0, spec=1.0, rim=0.2)
        pp.stroke([(575, 735), (625, 735)], rgb("#E0218A"), 12)
        for x in (232, 968):   # gold hoops
            ring = pp.subtract(pp.circle_mask(x, 1085, 48), pp.circle_mask(x, 1085, 36))
            pp.glossy(ring, rgb("#E8C547"), outline=2, spec=1.0, rim=0.2)

    def steam(pp: Painter, expr: str) -> None:
        if expr.startswith("angry"):
            steam_puff(pp, 300, 640)
            steam_puff(pp, 900, 640)

    return Rig(eyes=[(520, 960), (680, 960)], eye_r=(54, 64), mouth=(600, 1135), mouth_w=145,
               skin=brown, shoulders=[(250, 1090), (950, 1090)], arm_rgb=shade(brown, 0.9), arm_w=40,
               lashes=True, cheeks=True, brow_rgb=(40, 20, 15), head_top=(600, 620),
               front=accessories, extras=steam)


def build_broccolo(p: Painter, c: Character) -> Rig:
    stalk = rgb("#9CCC65")
    floret = rgb("#2E7D32")
    # surfboard standing behind him
    board = p.rotated_ellipse_mask(935, 1030, 95, 470, -6)
    bp = p.albedo((250, 250, 245))
    bp.paste(rgb("#17B6A7"), (0, 0), p.rotated_ellipse_mask(935, 1030, 22, 470, -6))
    p.glossy(board, bp, rim=0.4, spec=0.9)
    # mullet ("party in the back") behind the stalk
    for (x, y, r) in ((360, 800, 95), (840, 800, 95), (345, 940, 80), (855, 940, 80), (370, 1050, 62), (830, 1050, 62)):
        p.glossy(p.circle_mask(x, y, r), shade(floret, 0.9), rim=0.55, outline=4, spec=0.3)
    legs = p.union(p.line_mask([(520, 1400), (515, 1530)], 46), p.line_mask([(680, 1400), (685, 1530)], 46))
    p.glossy(legs, stalk, outline=4)
    flops = p.union(p.ellipse_mask(440, 1525, 585, 1562), p.ellipse_mask(615, 1525, 760, 1562))
    p.glossy(flops, rgb("#17B6A7"), outline=4)
    body = p.smooth(p.poly_mask([(375, 640), (825, 640), (790, 1290), (410, 1290)]), 16)
    paint = p.albedo(stalk)
    paint.paste(rgb("#C5E1A5"), (0, 0), p.ellipse_mask(470, 700, 730, 1250).filter(ImageFilter.GaussianBlur(12 * SS)))
    p.glossy(body, paint, rim=0.5, gloss=0.55)
    shorts = p.intersect(p.rrect_mask(380, 1230, 820, 1420, 50), p.rrect_mask(395, 1220, 805, 1430, 60))
    sp = p.albedo(rgb("#17B6A7"))
    sd = ImageDraw.Draw(sp)
    for (x, y) in ((450, 1300), (560, 1370), (700, 1290), (770, 1380)):
        for k in range(5):
            a = math.radians(k * 72)
            sd.ellipse(p.box(x + 18 * math.cos(a) - 14, y + 18 * math.sin(a) - 14,
                             x + 18 * math.cos(a) + 14, y + 18 * math.sin(a) + 14), fill=(255, 240, 245))
        sd.ellipse(p.box(x - 9, y - 9, x + 9, y + 9), fill=(255, 200, 60))
    p.glossy(shorts, sp, rim=0.45)
    # floret crown: many little domes, back to front, each shaded
    for (x, y, r) in ((600, 330, 200), (420, 410, 165), (780, 410, 165), (320, 560, 130), (880, 560, 130),
                      (470, 560, 150), (730, 560, 150), (600, 500, 170), (600, 640, 120), (400, 660, 105),
                      (800, 660, 105)):
        p.glossy(p.circle_mask(x, y, r), floret, rim=0.55, gloss=0.45, spec=0.35, outline=4)
        rnd = random.Random(int(x * 7 + y))
        for _ in range(int(r / 12)):
            a, d = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, r * 0.8)
            bx, by = x + math.cos(a) * d, y + math.sin(a) * d
            p.flat(p.circle_mask(bx, by, rnd.uniform(8, 16)), shade(floret, 1.18), opacity=0.7)

    def shades_necklace(pp: Painter, expr: str) -> None:
        for x in (530, 670):
            pp.glossy(pp.rrect_mask(x - 62, 425, x + 62, 490, 22), (25, 40, 45), outline=4, spec=1.0, rim=0.2)
        pp.stroke([(592, 450), (608, 450)], (25, 40, 45), 12)
        for k in range(9):
            x, y = 600 + 175 * math.cos(math.radians(160 - k * 17.5)), 1065 + 70 * math.sin(math.radians(160 - k * 17.5))
            pp.glossy(pp.ellipse_mask(x - 14, y - 10, x + 14, y + 12), (255, 245, 225), outline=2, spec=0.6)

    return Rig(eyes=[(540, 850), (660, 850)], eye_r=(44, 54), mouth=(600, 990), mouth_w=112,
               skin=stalk, shoulders=[(415, 1000), (785, 1000)], arm_rgb=stalk, arm_w=34,
               head_top=(600, 150), front=shades_necklace)


def build_generic(p: Painter, c: Character) -> Rig:
    """Fallback for characters without a custom design (e.g. new bombshells)."""
    col = c.rgb
    feet = p.union(p.ellipse_mask(440, 1480, 580, 1562), p.ellipse_mask(620, 1480, 760, 1562))
    p.glossy(feet, shade(col, 0.6), outline=4)
    body = p.union(p.ellipse_mask(330, 300, 870, 900), p.ellipse_mask(360, 700, 840, 1500))
    p.glossy(body, col, rim=0.5, gloss=0.6, spec=0.8)
    # emoji badge on the belly
    emoji_font = config.find_font(config.FONT_CANDIDATES_EMOJI)
    if emoji_font:
        try:
            f = ImageFont.truetype(emoji_font, 109)
            em = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(em).text((80, 80), c.emoji, font=f, embedded_color=True, anchor="mm")
            em = em.resize((int(220 * SS), int(220 * SS)), Image.LANCZOS)
            p.img.alpha_composite(em, dest=(int(490 * SS), int(1000 * SS)))
        except OSError:
            pass
    return Rig(eyes=[(530, 560), (670, 560)], eye_r=(55, 65), mouth=(600, 740), mouth_w=140,
               skin=col, shoulders=[(380, 900), (820, 900)], arm_rgb=shade(col, 0.9), arm_w=36,
               head_top=(600, 300))


BUILDERS: dict[str, Callable[[Painter, Character], Rig]] = {
    "baguettini": build_baguettini, "conetta": build_conetta, "ranocchio": build_ranocchio,
    "lumachina": build_lumachina, "gnometta": build_gnometta, "discotto": build_discotto,
    "polpetta": build_polpetta, "broccolo": build_broccolo,
}


# ==========================================================================
# Public API
# ==========================================================================
def render_character(c: Character, expressions: list[str] | None = None) -> dict[str, Image.Image]:
    """Draw every expression for one character; returns {expression: RGBA image}."""
    expressions = expressions or config.ALL_EXPRESSIONS
    base = Painter()
    rig = BUILDERS.get(c.id, build_generic)(base, c)
    out: dict[str, Image.Image] = {}
    for expr in expressions:
        p = base.copy()
        draw_face(p, rig, expr)
        if rig.front:
            rig.front(p, expr)
        draw_arms(p, rig, expr)
        common_extras(p, rig, expr)
        if rig.extras:
            rig.extras(p, expr)
        out[expr] = p.to_sprite()
    return out


def placeholder_path(cid: str, expr: str) -> Path:
    return config.PLACEHOLDER_DIR / cid / f"{expr}.png"


def ensure_placeholders(cast: Cast, force: bool = False, only: list[str] | None = None,
                        log: Callable[[str], None] = print) -> None:
    """Generate placeholder art for every character that is missing it (or all, with force)."""
    todo: list[Character] = []
    for c in cast.characters.values():
        if only and c.id not in only:
            continue
        stamp = config.PLACEHOLDER_DIR / c.id / ".version"
        if not force and stamp.exists() and stamp.read_text() == PLACEHOLDER_VERSION and \
                all(placeholder_path(c.id, e).exists() for e in config.ALL_EXPRESSIONS):
            continue
        todo.append(c)
    if not todo:
        return
    log(f"  drawing placeholder art for: {', '.join(c.short_name for c in todo)}")
    # One process per character: drawing is CPU-bound numpy/Pillow work.
    with ProcessPoolExecutor(max_workers=min(len(todo), os.cpu_count() or 1)) as pool:
        for cid in pool.map(_draw_and_save, todo):
            log(f"    done: {cid}")


def _draw_and_save(c: Character) -> str:
    imgs = render_character(c)
    (config.PLACEHOLDER_DIR / c.id).mkdir(parents=True, exist_ok=True)
    for expr, im in imgs.items():
        im.save(placeholder_path(c.id, expr))
    (config.PLACEHOLDER_DIR / c.id / ".version").write_text(PLACEHOLDER_VERSION)
    return c.id
