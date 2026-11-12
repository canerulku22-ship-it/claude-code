"""A procedural supertall in the style of the Burj Khalifa (no Blender needed).

The plan is a "Y": three rounded wings around a core. Going up, the wings step back one
at a time in a spiral (27 tiers up to the top occupied floor), then a few mechanical
tiers and a tapering spire reach 828 m. Real proportions are approximate; the shape
just has to read as *that* tower.

The fill animation and the counter both use ``fill_fraction(level)``: the share of the
occupied volume below a height. So the counter climbs fast through the wide lower tiers
and slows near the slender top, like the real building would.
"""

import math

H_OCC = 585.0        # top of the occupied floors (m); the fill stops here
H_MECH = 640.0       # top of the mechanical tiers
H_TIP = 828.0        # tip of the spire
N_TIERS = 27         # setbacks up to H_OCC
ARM_ANGLES = (270.0, 30.0, 150.0)   # one wing points at the camera (-Y)

WING_L0, WING_L_TOP = 53.0, 13.0    # centre-to-tip wing length, bottom and top
WING_W0, WING_W_TOP = 30.0, 12.0    # wing width, bottom and top (volume matches the real ~1.1M m³)


def _dir(deg):
    a = math.radians(deg)
    return math.cos(a), math.sin(a)


def y_plan(lengths, width, tip_segments=8):
    """Outline (counter-clockwise) of a three-wing plan with rounded wing tips."""
    r = width / 2.0
    dirs = [_dir(a) for a in ARM_ANGLES]
    pts = []
    for i in range(3):
        dx, dy = dirs[i]
        nx, ny = -dy, dx
        L = max(lengths[i], r + 1.0)
        cx, cy = dx * (L - r), dy * (L - r)
        for s in range(tip_segments + 1):
            a = -math.pi / 2 + math.pi * s / tip_segments
            vx = math.cos(a) * dx + math.sin(a) * nx
            vy = math.cos(a) * dy + math.sin(a) * ny
            pts.append((cx + r * vx, cy + r * vy))
        # Inner corner: arm i's +n edge meets arm i+1's -n edge.
        ex, ey = dirs[(i + 1) % 3]
        mx, my = -ey, ex
        # t*d + r*n = s*e - r*m  ->  t*d - s*e = -r*(n + m)
        bx, by = -r * (nx + mx), -r * (ny + my)
        det = dx * (-ey) - (-ex) * dy
        t = (bx * (-ey) - (-ex) * by) / det
        pts.append((t * dx + r * nx, t * dy + r * ny))
    return pts


def polygon_area(pts):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def occupied_tiers():
    """[(z0, z1, outline)] for the 27 occupied tiers, wings stepping back in a spiral."""
    tiers = []
    th = H_OCC / N_TIERS
    steps_per_wing = N_TIERS // 3
    dl = (WING_L0 - WING_L_TOP) / steps_per_wing
    for k in range(N_TIERS):
        steps = [sum(1 for j in range(1, k + 1) if j % 3 == i) for i in range(3)]
        lengths = [WING_L0 - dl * steps[i] for i in range(3)]
        w = WING_W0 - (WING_W0 - WING_W_TOP) * k / (N_TIERS - 1)
        tiers.append((k * th, (k + 1) * th, y_plan(lengths, w)))
    return tiers


def mechanical_tiers():
    """Three slimmer tiers between the occupied floors and the spire."""
    tiers = []
    n = 3
    th = (H_MECH - H_OCC) / n
    for k in range(n):
        L = WING_L_TOP - 2.0 * (k + 1)
        w = WING_W_TOP - 1.5 * (k + 1)
        tiers.append((H_OCC + k * th, H_OCC + (k + 1) * th, y_plan([L, L, L], w)))
    return tiers


def fill_fraction_table(samples=600):
    """[(level, fraction of occupied volume below level)] for interpolation."""
    tiers = occupied_tiers()
    areas = [(z0, z1, polygon_area(p)) for z0, z1, p in tiers]
    total = sum((z1 - z0) * a for z0, z1, a in areas)
    out = []
    for i in range(samples + 1):
        lvl = H_OCC * i / samples
        v = sum(max(0.0, min(lvl, z1) - z0) * a for z0, z1, a in areas)
        out.append((lvl, v / total))
    return out


def model_volume():
    return sum((z1 - z0) * polygon_area(p) for z0, z1, p in occupied_tiers())
