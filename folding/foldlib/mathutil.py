"""Small maths helpers: easing curves, interpolation and colour conversion."""

import math


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, t):
    return a + (b - a) * t


def inv_lerp(a, b, x):
    """Where x sits between a and b, clamped to 0..1."""
    if b == a:
        return 0.0 if x < a else 1.0
    return clamp((x - a) / (b - a))


def smoothstep(a, b, x):
    t = inv_lerp(a, b, x)
    return t * t * (3.0 - 2.0 * t)


# --- Easing curves (input and output in 0..1) --------------------------------

def ease_in_out_cubic(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t)
    return t * t * t


def ease_out_back(t, overshoot=1.70158):
    t = clamp(t)
    c3 = overshoot + 1
    return 1 + c3 * (t - 1) ** 3 + overshoot * (t - 1) ** 2


def ease_in_out_sine(t):
    t = clamp(t)
    return -(math.cos(math.pi * t) - 1) / 2


def damped_bounce(t, cycles=1.5, decay=5.0):
    """0 at t=0, wobbles and settles back to 0 by t=1 (used for squash/settle)."""
    t = clamp(t)
    return math.sin(t * math.pi * 2 * cycles) * math.exp(-decay * t) * (1 - t)


# --- Monotone cubic interpolation (Fritsch-Carlson) --------------------------

class MonotoneCurve:
    """Smooth curve through (x, y) keys that never overshoots between keys.

    Used for the camera: it glides between framing keys without the bouncing
    a normal spline would add.
    """

    def __init__(self, keys):
        keys = sorted(keys)
        # Drop keys that share (almost) the same x - the later one wins.
        cleaned = []
        for x, y in keys:
            if cleaned and abs(x - cleaned[-1][0]) < 1e-6:
                cleaned[-1] = (x, y)
            else:
                cleaned.append((x, y))
        self.xs = [k[0] for k in cleaned]
        self.ys = [k[1] for k in cleaned]
        n = len(self.xs)
        if n == 1:
            self.ms = [0.0]
            return
        d = [(self.ys[i + 1] - self.ys[i]) / (self.xs[i + 1] - self.xs[i]) for i in range(n - 1)]
        m = [0.0] * n
        m[0], m[-1] = d[0], d[-1]
        for i in range(1, n - 1):
            m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
        for i in range(n - 1):
            if d[i] == 0:
                m[i] = m[i + 1] = 0.0
                continue
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                tau = 3 / math.sqrt(s)
                m[i], m[i + 1] = tau * a * d[i], tau * b * d[i]
        self.ms = m

    def __call__(self, x):
        xs, ys, ms = self.xs, self.ys, self.ms
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        h = xs[hi] - xs[lo]
        t = (x - xs[lo]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[lo] + (t3 - 2 * t2 + t) * h * ms[lo]
                + (-2 * t3 + 3 * t2) * ys[hi] + (t3 - t2) * h * ms[hi])


# --- Colours -----------------------------------------------------------------

def hex_to_srgb(hex_colour):
    """'#f5f2ea' -> (0.96, 0.95, 0.92) in 0..1 sRGB."""
    h = hex_colour.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Bad colour {hex_colour!r}, expected #rrggbb")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(hex_colour, alpha=None):
    """Hex colour -> linear RGB(A) tuple, which is what Blender shaders expect."""
    rgb = tuple(srgb_to_linear(c) for c in hex_to_srgb(hex_colour))
    return rgb if alpha is None else rgb + (alpha,)


def mix_colours(a, b, t):
    return tuple(lerp(x, y, t) for x, y in zip(a, b))
