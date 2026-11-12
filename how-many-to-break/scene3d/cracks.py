"""Procedural crack textures that grow stage by stage.

Cracks are drawn with numpy into two float images in the target's "CrackUV" space:

* ``alpha``: anti-aliased crack lines (linear filtering)
* ``stage``: for each crack pixel, ``stage + 0.98 * progress`` where progress runs 0 to 1
  along the crack from where it starts (nearest-pixel filtering)

The shader shows a pixel when ``stage_value < CrackLevel``. Animating that one value from
``k`` to ``k + 1`` just after crack stage ``k`` makes stage ``k``'s cracks grow outward
from their origin. Earlier stages stay visible.

Styles:
    glass   radial cracks plus a spider-web of rings (bright white lines)
    wood    long splits along the grain (X), with a few branches (dark)
    shell   branching cracks running down from the contact point (dark)
    fabric  jagged tears radiating from the centre (light, frayed)
"""

import math
import random

import bpy
import numpy as np

STYLE = {
    #          rays  ring_p jitter width  branch_p  colour              strength  spread
    "glass":  (6,    0.85,  0.10,  6.5,   0.55,     (0.95, 0.98, 1.0),  3.0,      (0.0, 2 * math.pi)),
    "wood":   (2,    0.00,  0.05,  7.0,   0.30,     (0.05, 0.025, 0.01), 0.0,     None),
    "shell":  (4,    0.25,  0.22,  5.0,   0.55,     (0.10, 0.06, 0.03), 0.0,      (math.pi * 1.05, math.pi * 1.95)),
    "fabric": (6,    0.20,  0.30,  6.0,   0.35,     (0.80, 0.80, 0.76), 0.6,      (0.0, 2 * math.pi)),
}


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

class CrackCanvas:
    def __init__(self, res):
        self.res = res
        self.alpha = np.zeros((res, res), dtype=np.float32)
        self.stage = np.full((res, res), np.inf, dtype=np.float32)

    def polyline(self, pts, stage, width_px):
        """Draw a polyline (UV points) belonging to ``stage``; progress runs along it."""
        if len(pts) < 2:
            return
        p = np.asarray(pts, dtype=np.float64) * self.res
        seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
        total = max(seg.sum(), 1e-6)
        acc = np.concatenate([[0.0], np.cumsum(seg)]) / total
        half = width_px / 2.0
        reach = half + 1.5
        for k in range(len(p) - 1):
            a, b = p[k], p[k + 1]
            x0 = int(max(0, math.floor(min(a[0], b[0]) - reach)))
            x1 = int(min(self.res - 1, math.ceil(max(a[0], b[0]) + reach)))
            y0 = int(max(0, math.floor(min(a[1], b[1]) - reach)))
            y1 = int(min(self.res - 1, math.ceil(max(a[1], b[1]) + reach)))
            if x1 < x0 or y1 < y0:
                continue
            ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            px, py = xs + 0.5, ys + 0.5
            ab = b - a
            L2 = max(ab @ ab, 1e-9)
            t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / L2, 0.0, 1.0)
            dx = px - (a[0] + t * ab[0])
            dy = py - (a[1] + t * ab[1])
            d = np.sqrt(dx * dx + dy * dy)
            # Taper the line towards its tip so cracks look sharp.
            prog = acc[k] + t * (acc[k + 1] - acc[k])
            w = half * (1.0 - 0.55 * prog)
            alpha = np.clip(w + 0.5 - d, 0.0, 1.0)
            value = stage + 0.98 * prog
            region_a = self.alpha[y0:y1 + 1, x0:x1 + 1]
            np.maximum(region_a, alpha, out=region_a)
            region_s = self.stage[y0:y1 + 1, x0:x1 + 1]
            mask = d <= reach
            region_s[mask] = np.minimum(region_s[mask], value[mask])

    def finish(self):
        stage = np.where(np.isfinite(self.stage), self.stage, 0.0).astype(np.float32)
        return self.alpha, stage


def _walk(rng, start, angle, length, steps, jitter, grain=None):
    """Random-walk polyline from ``start`` heading ``angle`` for ``length`` (UV units)."""
    pts = [start]
    x, y = start
    step = length / steps
    for _ in range(steps):
        angle += rng.gauss(0.0, jitter)
        if grain is not None:   # pull back towards the grain direction
            angle = angle * 0.7 + grain * 0.3
        x += math.cos(angle) * step
        y += math.sin(angle) * step
        pts.append((x, y))
    return pts


def _split_by_radius(pts, origin, radii):
    """Split a ray polyline into pieces between consecutive radii."""
    pieces = [[] for _ in radii]
    for p in pts:
        r = math.hypot(p[0] - origin[0], p[1] - origin[1])
        k = 0
        while k < len(radii) - 1 and r > radii[k]:
            k += 1
        pieces[k].append(p)
    # Share endpoints so pieces join up.
    for k in range(1, len(pieces)):
        if pieces[k] and pieces[k - 1]:
            pieces[k].insert(0, pieces[k - 1][-1])
    return pieces


def draw_cracks(style, origin, n_stages, seed, res=1024, reach=0.75, width_mult=1.0):
    """Return (alpha, stage) float arrays for ``n_stages`` crack stages."""
    rays, ring_p, jitter, width, branch_p, _c, _s, spread = STYLE[style]
    width *= width_mult
    rng = random.Random(seed)
    cv = CrackCanvas(res)
    K = max(1, n_stages)
    # Even the first stage reaches well out from the load, so cracks show at the
    # visible edges of the surface instead of hiding under the pile.
    radii = [reach * (0.40 + 0.60 * (k + 1) / K) for k in range(K)]

    if style == "wood":
        # Splits along the grain, appearing one or two per stage and lengthening.
        lines = []
        for k in range(K):
            for _ in range(1 if k < K - 1 else 2):
                y = origin[1] + rng.uniform(-0.18, 0.18) * (0.4 + k / K)
                lines.append((k, y))
        for k, y in lines:
            for direction in (0.0, math.pi):
                length = radii[min(K - 1, k + 1)] * rng.uniform(0.8, 1.2)
                pts = _walk(rng, (origin[0] + rng.uniform(-0.03, 0.03), y), direction, length, 40,
                            jitter, grain=direction)
                cv.polyline(pts, k + 1, width * (1.1 - 0.3 * (k / K)))
                if rng.random() < branch_p:
                    j = rng.randrange(10, 35)
                    b = _walk(rng, pts[j], direction + rng.choice((-0.5, 0.5)), 0.08, 10, jitter * 2)
                    cv.polyline(b, min(K, k + 2), width * 0.6)
        return cv.finish()

    lo, hi = spread
    n_rays = rays + 2 * (K - 1)
    angles = sorted(rng.uniform(lo, hi) for _ in range(n_rays))
    if hi - lo >= 2 * math.pi - 1e-3:
        # Spread evenly with jitter so the first cracks don't all bunch together.
        base = rng.uniform(0, 2 * math.pi)
        angles = [base + (i + rng.uniform(-0.3, 0.3)) * 2 * math.pi / n_rays for i in range(n_rays)]
    order = list(range(n_rays))
    rng.shuffle(order)
    start_stage = {}
    for rank, i in enumerate(order):
        start_stage[i] = 1 if rank < rays else min(K, 2 + (rank - rays) // 2)

    ray_pts = {}
    for i, ang in enumerate(angles):
        pts = _walk(rng, origin, ang, reach * rng.uniform(0.85, 1.1), 60, jitter)
        ray_pts[i] = pts
        s0 = start_stage[i]
        pieces = _split_by_radius(pts, origin, radii)
        # Everything inside the starting stage's radius appears at the starting stage.
        first = [p for piece in pieces[:s0] for p in piece]
        if len(first) > 1:
            cv.polyline(first, s0, width)
        for k in range(s0, K):
            if len(pieces[k]) > 1:
                cv.polyline(pieces[k], k + 1, width * (1.0 - 0.35 * k / K))
        # Side branches.
        for k in range(max(2, s0), K + 1):
            if rng.random() < branch_p:
                j = rng.randrange(5, 50)
                b = _walk(rng, pts[j], ang + rng.choice((-1, 1)) * rng.uniform(0.4, 0.9),
                          rng.uniform(0.04, 0.12), 12, jitter * 1.5)
                cv.polyline(b, k, width * 0.55)

    # Concentric rings ("spider web") between neighbouring rays.
    if ring_p > 0:
        for k in range(1, K):
            rho = radii[k - 1] * rng.uniform(0.55, 0.9)
            for i in range(n_rays):
                j = (i + 1) % n_rays
                if j == 0 and hi - lo < 2 * math.pi - 1e-3:
                    continue
                if start_stage[i] > k + 1 or start_stage[j] > k + 1 or rng.random() > ring_p:
                    continue
                a0, a1 = angles[i], angles[j]
                if a1 < a0:
                    a1 += 2 * math.pi
                if a1 - a0 > math.pi * 0.9:
                    continue
                arc = []
                steps = 10
                for s in range(steps + 1):
                    a = a0 + (a1 - a0) * s / steps
                    r = rho * (1.0 + rng.uniform(-0.06, 0.06))
                    arc.append((origin[0] + math.cos(a) * r, origin[1] + math.sin(a) * r))
                cv.polyline(arc, k + 1, width * 0.7)
    return cv.finish()


# ---------------------------------------------------------------------------
# Blender hookup
# ---------------------------------------------------------------------------

def _image(name, data):
    h, w = data.shape
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    rgba[..., 0] = data
    rgba[..., 1] = data
    rgba[..., 2] = data
    rgba[..., 3] = 1.0
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.pack()
    return img


def set_crack_uv(me, uv_func, name="CrackUV"):
    """Write a UV layer from a function of the (local) vertex position."""
    uv = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    co = [me.vertices[l.vertex_index].co for l in me.loops]
    data = []
    for c in co:
        u, v = uv_func(c)
        data += [u, v]
    uv.data.foreach_set("uv", data)


def add_crack_layer(mat, style, origin_uv, n_stages, seed, res=1024, width_mult=1.0):
    """Add growing cracks to ``mat`` (in place). Returns the CrackLevel value node."""
    alpha, stage = draw_cracks(style, origin_uv, n_stages, seed, res=res, width_mult=width_mult)
    a_img = _image(mat.name + "_crack_alpha", alpha)
    s_img = _image(mat.name + "_crack_stage", stage)
    color, strength = STYLE[style][5], STYLE[style][6]

    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    surface_link = out.inputs["Surface"].links[0]
    base_shader = surface_link.from_socket

    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "CrackUV"
    ta = nt.nodes.new("ShaderNodeTexImage")
    ta.image = a_img
    ta.interpolation = "Linear"
    ts = nt.nodes.new("ShaderNodeTexImage")
    ts.image = s_img
    ts.interpolation = "Closest"
    for t in (ta, ts):
        nt.links.new(uvn.outputs[0], t.inputs[0])
    level = nt.nodes.new("ShaderNodeValue")
    level.name = "CrackLevel"
    level.label = "CrackLevel"
    level.outputs[0].default_value = 0.0

    def math_node(op, a, b):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    shown = math_node("LESS_THAN", ts.outputs["Color"], level.outputs[0])
    exists = math_node("GREATER_THAN", ts.outputs["Color"], 0.5)
    mask = math_node("MULTIPLY", math_node("MULTIPLY", shown, exists), ta.outputs["Color"])

    crack = nt.nodes.new("ShaderNodeBsdfPrincipled")
    crack.inputs["Base Color"].default_value = (*color, 1.0)
    crack.inputs["Roughness"].default_value = 0.35
    if strength > 0:
        for name in ("Emission Color", "Emission"):
            if name in crack.inputs:
                crack.inputs[name].default_value = (*color, 1.0)
                break
        crack.inputs["Emission Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mask, mix.inputs[0])
    nt.links.new(base_shader, mix.inputs[1])
    nt.links.new(crack.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return level
