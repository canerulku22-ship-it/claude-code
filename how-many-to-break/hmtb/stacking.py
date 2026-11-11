"""Where each dropped object comes to rest in the pile.

Instead of a fully simulated pile (round objects roll off tables, and big stacks can
become unstable), the pile is laid out procedurally so every episode is stable and
repeatable. Real rigid-body physics takes over at the break.

Three packing modes, picked from the catalogue entry:

* ``ellipsoid``: square-pyramid packing (each upper object sits in the pocket of four
  below it). It also works for stretched shapes like watermelons because an affine
  stretch keeps "touching" ellipsoids touching.
* ``box``: neat layers, with alternate layers turned 90 degrees or offset by half a block
  like brickwork.
* ``tower``: thin slabs (phones) are stacked into a messy single tower.

A support surface is a dict:
``{"shape": "rect", "cx", "cy", "z", "sx", "sy"}`` or
``{"shape": "circle", "cx", "cy", "z", "r"}``.
"""

import math
import random


def _inside(support, x, y, margin):
    if support["shape"] == "circle":
        return math.hypot(x - support["cx"], y - support["cy"]) <= support["r"] - margin
    return (abs(x - support["cx"]) <= support["sx"] / 2 - margin
            and abs(y - support["cy"]) <= support["sy"] / 2 - margin)


def _extent(support):
    if support["shape"] == "circle":
        return support["r"] * 2, support["r"] * 2
    return support["sx"], support["sy"]


def _ellipsoid_positions(obj, support, count, rng):
    rx, ry, rz = (s / 2.0 for s in obj["size_m"])
    gap = obj["gap_m"]
    ax, ay = 2 * rx + gap, 2 * ry + gap
    # Pocket height in "unit sphere" space, scaled back by rz (see module docstring).
    a, b = ax / rx, ay / ry
    h = math.sqrt(max(0.5, 4.0 - (a / 2) ** 2 - (b / 2) ** 2)) * rz
    margin = min(rx, ry) * 0.2    # centres stay just inside the edge
    ex, ey = _extent(support)
    ni, nj = int(ex / ax) + 2, int(ey / ay) + 2
    cx, cy, z0 = support["cx"], support["cy"], support["z"]

    # Layer 0: a grid centred on the support. Try a centred and a half-offset grid on
    # each axis and keep whichever fits the most objects.
    best = None
    for off_i in (0.0, 0.5):
        for off_j in (0.0, 0.5):
            cells = set()
            for i in range(-ni, ni + 1):
                for j in range(-nj, nj + 1):
                    if _inside(support, cx + (i + off_i) * ax, cy + (j + off_j) * ay, margin):
                        cells.add((i, j))
            if best is None or len(cells) > len(best[2]):
                best = (off_i, off_j, cells)
    off_i, off_j, layer0 = best
    if not layer0:
        layer0 = {(0, 0)}
    filled = {}

    def pos(layer, i, j):
        x = cx + (i + off_i + layer * 0.5) * ax
        y = cy + (j + off_j + layer * 0.5) * ay
        return x, y, z0 + rz + layer * h

    def yaw():
        # Round objects can face any way; stretched ones (melons) must stay axis-aligned
        # or they would overlap their neighbours.
        if abs(rx - ry) < 1e-6:
            return rng.uniform(-math.pi, math.pi)
        return rng.choice((0.0, math.pi)) + rng.uniform(-0.05, 0.05)

    out = []
    jitter = {}
    while len(out) < count:
        candidates = []
        for (i, j) in layer0:
            if (0, i, j) not in filled:
                candidates.append((0, i, j))
        layers = {k[0] for k in filled}
        for layer in range(1, (max(layers) if layers else 0) + 2):
            for (l, i, j) in list(filled):
                if l != layer - 1:
                    continue
                key = (layer, i, j)
                if key in filled:
                    continue
                below = [(layer - 1, i, j), (layer - 1, i + 1, j), (layer - 1, i, j + 1), (layer - 1, i + 1, j + 1)]
                if all(bk in filled for bk in below):
                    candidates.append(key)
        if not candidates:
            # Pyramid is complete: start a column on top of a random top-layer object.
            top = max(k[0] for k in filled)
            l, i, j = rng.choice([k for k in filled if k[0] == top])
            x, y, z = pos(l, i, j)
            k_extra = sum(1 for o in out if abs(o["x"] - x) < 1e-6 and abs(o["y"] - y) < 1e-6)
            out.append({"x": x, "y": y, "z": z + 2 * rz * k_extra, "yaw": yaw(),
                        "layer": l + k_extra})
            continue

        def score(key):
            layer, i, j = key
            x, y, _ = pos(layer, i, j)
            d = math.hypot((x - cx) / ax, (y - cy) / ay)
            if key not in jitter:
                jitter[key] = rng.uniform(0, 0.9)
            return d + 1.3 * layer + jitter[key]

        key = min(candidates, key=score)
        filled[key] = True
        x, y, z = pos(*key)
        out.append({"x": x, "y": y, "z": z, "yaw": yaw(), "layer": key[0]})
    return out


def _box_layer(obj, support, rotated, offset, layer_z, rng):
    lx, ly, lz = obj["size_m"]
    gap = obj["gap_m"]
    if rotated:
        lx, ly = ly, lx
    sx, sy = lx + gap, ly + gap
    ex, ey = _extent(support)
    # Allow a little overhang at the edges, like a real stack.
    over = 0.12
    nx = max(1, int((ex + over * lx) / sx))
    ny = max(1, int((ey + over * ly) / sy))
    spots = []
    for i in range(nx):
        for j in range(ny):
            x = support["cx"] + (i - (nx - 1) / 2.0 + (0.5 if offset else 0.0)) * sx
            y = support["cy"] + (j - (ny - 1) / 2.0) * sy
            if offset and i == nx - 1:
                continue
            if support["shape"] == "circle":
                corner = math.hypot(abs(x - support["cx"]) + lx / 2, abs(y - support["cy"]) + ly / 2)
                if corner > support["r"] * 1.04:
                    continue
            spots.append((x, y))
    if not spots:
        spots = [(support["cx"], support["cy"])]
    cx, cy = support["cx"], support["cy"]
    keyed = [(math.hypot(x - cx, y - cy) + rng.uniform(0, 0.05), x, y) for x, y in spots]
    keyed.sort()
    yaw0 = math.pi / 2 if rotated else 0.0
    return [{"x": x, "y": y, "z": layer_z + lz / 2, "yaw": yaw0 + rng.uniform(-0.03, 0.03)}
            for _, x, y in keyed]


def _box_positions(obj, support, count, rng):
    lx, ly, lz = obj["size_m"]
    plain = _box_layer(obj, support, False, False, 0.0, rng)
    turned = _box_layer(obj, support, True, False, 0.0, rng)
    use_turn = len(turned) >= 0.7 * len(plain)
    out = []
    layer = 0
    z = support["z"]
    while len(out) < count:
        if layer % 2 == 0:
            spots = _box_layer(obj, support, False, False, z, rng)
        elif use_turn:
            spots = _box_layer(obj, support, True, False, z, rng)
        else:
            spots = _box_layer(obj, support, False, True, z, rng)
        for s in spots:
            if len(out) >= count:
                break
            s["layer"] = layer
            out.append(s)
        z += lz + 0.0008
        layer += 1
    return out


def _tower_positions(obj, support, count, rng):
    lx, ly, lz = obj["size_m"]
    out = []
    z = support["z"]
    for k in range(count):
        out.append({
            "x": support["cx"] + rng.uniform(-0.18, 0.18) * ly,
            "y": support["cy"] + rng.uniform(-0.18, 0.18) * ly,
            "z": z + lz / 2,
            "yaw": rng.uniform(-0.45, 0.45),
            "layer": k,
        })
        z += lz + 0.0006
    return out


def pile_positions(obj, support, count, seed=1):
    """Rest positions for ``count`` objects, in the order they land.

    Returns dicts with x, y, z (object centre, metres), yaw (radians) and layer.
    """
    rng = random.Random(seed * 7919 + count)
    if obj["shape"] == "ellipsoid":
        return _ellipsoid_positions(obj, support, count, rng)
    lx, ly, lz = obj["size_m"]
    if lz < 0.25 * ly:
        return _tower_positions(obj, support, count, rng)
    return _box_positions(obj, support, count, rng)


def pile_bounds(obj, positions):
    """Axis-aligned bounds (min xyz, max xyz) of a pile, using each object's bounding radius."""
    lx, ly, lz = obj["size_m"]
    rxy = math.hypot(lx, ly) / 2 if obj["shape"] == "box" else max(lx, ly) / 2
    lo = [min(p["x"] for p in positions) - rxy, min(p["y"] for p in positions) - rxy,
          min(p["z"] for p in positions) - lz / 2]
    hi = [max(p["x"] for p in positions) + rxy, max(p["y"] for p in positions) + rxy,
          max(p["z"] for p in positions) + lz / 2]
    return lo, hi
