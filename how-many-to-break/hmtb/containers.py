"""Containers for 'fill' episodes: how volume is distributed with height, and units.

Each container gives:
    table        [(level, fraction of the volume below level)], monotonic
    bottom, top  fill range in scene units
    ruler_z      scene heights for the overlay's ruler: base, top, tip
    to_metres    scene units -> real metres (for the height marker)
    floor_m      metres per floor for "FLOOR 87" (None = no floors)
    scene        scene3d module that builds it
"""

from . import skyline

EARTH_R = 1000.0                 # scene units
EARTH_R_M = 6371000.0            # mean radius (m)


def earth_table(samples=800):
    R = EARTH_R
    out = []
    for i in range(samples + 1):
        z = -R + 2 * R * i / samples
        h = z + R
        out.append((z, h * h * (3 * R - h) / (4 * R ** 3)))   # spherical cap volume fraction
    return out


def get(name):
    if name == "burj_khalifa":
        return {"table": skyline.fill_fraction_table(), "bottom": 0.0, "top": skyline.H_OCC,
                "ruler_z": (0.0, skyline.H_OCC, skyline.H_TIP), "to_metres": 1.0, "floor_m": 3.59,
                "scene": "skyscraper"}
    if name == "earth":
        return {"table": earth_table(), "bottom": -EARTH_R, "top": EARTH_R,
                "ruler_z": (-EARTH_R, EARTH_R, EARTH_R), "to_metres": EARTH_R_M / EARTH_R, "floor_m": None,
                "scene": "globe"}
    raise KeyError("Unknown container %r (known: burj_khalifa, earth)" % name)
