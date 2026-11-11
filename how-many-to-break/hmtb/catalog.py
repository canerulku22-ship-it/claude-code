"""Catalogue of drop objects and targets: the plain data every stage shares.

Geometry is built in ``scene3d/drop_objects.py`` and ``scene3d/targets.py``. This file
holds what the timeline, stacking, overlay and audio need to know without Blender.

Adding a drop object or target: add an entry here, then a builder function with the
same key in the matching scene3d module. See the README for a walk-through.
"""

# ---------------------------------------------------------------------------
# Drop objects
# ---------------------------------------------------------------------------
# shape:      "ellipsoid" (stacked as a pyramid) or "box" (stacked in brick-bond layers)
# size_m:     full size (x, y, z) in metres, x being the longest horizontal side
# gap_m:      spacing added between neighbours in the pile
# bounce:     how high it bounces on landing, as a fraction of the drop height
# squash:     squash on impact (0 = rigid, 0.15 = soft)
# rock_deg:   how much it wobbles while settling
# sound:      impact sound profile (see hmtb/audio.py)
# collision:  Blender rigid-body collision shape used after the break

DROP_OBJECTS = {
    "bowling_ball": {
        "singular": "bowling ball",
        "plural": "bowling balls",
        "label": "BALLS",
        "label_singular": "BALL",
        "mass_kg": 7.0,
        "shape": "ellipsoid",
        "size_m": (0.218, 0.218, 0.218),
        "gap_m": 0.004,
        "bounce": 0.035,
        "squash": 0.0,
        "rock_deg": 0.0,
        "sound": "heavy_ball",
        "collision": "SPHERE",
    },
    "watermelon": {
        "singular": "watermelon",
        "plural": "watermelons",
        "label": "MELONS",
        "label_singular": "MELON",
        "mass_kg": 6.0,
        "shape": "ellipsoid",
        "size_m": (0.30, 0.23, 0.23),
        "gap_m": 0.006,
        "bounce": 0.02,
        "squash": 0.12,
        "rock_deg": 7.0,
        "sound": "melon",
        "collision": "CONVEX_HULL",
    },
    "brick": {
        "singular": "brick",
        "plural": "bricks",
        "label": "BRICKS",
        "label_singular": "BRICK",
        "mass_kg": 2.5,
        "shape": "box",
        "size_m": (0.215, 0.1025, 0.065),
        "gap_m": 0.004,
        "bounce": 0.02,
        "squash": 0.0,
        "rock_deg": 6.0,
        "sound": "brick",
        "collision": "BOX",
    },
    "iphone": {
        "singular": "iPhone",
        "plural": "iPhones",
        "label": "IPHONES",
        "label_singular": "IPHONE",
        "mass_kg": 0.2,
        "shape": "box",
        "size_m": (0.1476, 0.0716, 0.011),     # includes the camera bump
        "gap_m": 0.003,
        "bounce": 0.03,
        "squash": 0.0,
        "rock_deg": 9.0,
        "sound": "phone",
        "collision": "BOX",
    },
    "anvil": {
        "singular": "anvil",
        "plural": "anvils",
        "label": "ANVILS",
        "label_singular": "ANVIL",
        "mass_kg": 50.0,
        "shape": "box",
        "size_m": (0.46, 0.135, 0.194),
        "gap_m": 0.01,
        "bounce": 0.01,
        "squash": 0.0,
        "rock_deg": 3.0,
        "sound": "anvil",
        "collision": "CONVEX_HULL",
    },
}

# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------
# material:   drives crack drawing and the creak / crack / shatter sounds
# max_sag_m:  how far the support surface sinks under the full load at break time
# bounciness: multiplies the drop objects' bounce (a trampoline is springy)

TARGETS = {
    "glass_table": {
        "name": "glass table",
        "material": "glass",
        "max_sag_m": 0.004,
        "bounciness": 1.0,
    },
    "trampoline": {
        "name": "trampoline",
        "material": "fabric",
        "max_sag_m": 0.15,
        "bounciness": 3.0,
    },
    "egg": {
        "name": "egg",
        "material": "shell",
        "max_sag_m": 0.0,
        "bounciness": 0.8,
    },
    "wooden_chair": {
        "name": "wooden chair",
        "material": "wood",
        "max_sag_m": 0.018,
        "bounciness": 0.8,
    },
}


def drop_object(key):
    """Return the catalogue entry for a drop object, with a helpful error."""
    if key not in DROP_OBJECTS:
        raise KeyError("Unknown drop_object %r. Known: %s" % (key, ", ".join(sorted(DROP_OBJECTS))))
    return DROP_OBJECTS[key]


def target(key):
    """Return the catalogue entry for a target, with a helpful error."""
    if key not in TARGETS:
        raise KeyError("Unknown target %r. Known: %s" % (key, ", ".join(sorted(TARGETS))))
    return TARGETS[key]
