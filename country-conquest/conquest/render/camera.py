"""2D map camera: maps projected metres to screen pixels, with smooth interpolation."""
from __future__ import annotations

import math
from dataclasses import dataclass


def ease_in_out(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def ease_in_out_cubic(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_cubic(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ease_out_back(t: float, s: float = 1.70158) -> float:
    t = min(max(t, 0.0), 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


@dataclass(frozen=True)
class Camera:
    """World point (cx, cy) appears at screen point (ax, ay); ``scale`` is px per metre.

    Screen values are in reference pixels (a 1080-wide frame); the renderer
    multiplies by its own resolution factor."""
    cx: float
    cy: float
    scale: float
    ax: float
    ay: float

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        return self.ax + (x - self.cx) * self.scale, self.ay - (y - self.cy) * self.scale

    @staticmethod
    def fit(bbox, rect, pad: float = 0.12, min_span_m: float = 900_000.0,
            max_span_m: float = 36_000_000.0) -> "Camera":
        """Frame ``bbox`` (minx, miny, maxx, maxy in metres) inside screen ``rect``
        (x0, y0, x1, y1 in reference px), keeping ``pad`` margin on each side."""
        minx, miny, maxx, maxy = bbox
        bw = max(maxx - minx, 1.0)
        bh = max(maxy - miny, 1.0)
        # Never zoom closer than min_span_m across the smaller rect side.
        rx0, ry0, rx1, ry1 = rect
        rw, rh = (rx1 - rx0) * (1 - 2 * pad), (ry1 - ry0) * (1 - 2 * pad)
        scale = min(rw / bw, rh / bh)
        scale = min(scale, min(rw, rh) / min_span_m)
        scale = max(scale, rw / max_span_m)
        return Camera((minx + maxx) / 2, (miny + maxy) / 2, scale,
                      (rx0 + rx1) / 2, (ry0 + ry1) / 2)

    def zoomed(self, factor: float) -> "Camera":
        return Camera(self.cx, self.cy, self.scale * factor, self.ax, self.ay)


def lerp_camera(a: Camera, b: Camera, t: float) -> Camera:
    """Interpolate position linearly and zoom geometrically (feels uniform)."""
    if t <= 0:
        return a
    if t >= 1:
        return b
    lerp = lambda p, q: p + (q - p) * t
    scale = math.exp(lerp(math.log(a.scale), math.log(b.scale)))
    return Camera(lerp(a.cx, b.cx), lerp(a.cy, b.cy), scale, lerp(a.ax, b.ax), lerp(a.ay, b.ay))
