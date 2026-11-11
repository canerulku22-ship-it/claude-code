"""Episode config loading: defaults, validation and derived values.

An episode is one JSON file. Only a handful of keys are required; everything else
has a default here so configs stay short. ``load_config`` returns a plain dict with
every key filled in, which is what the render, overlay and audio stages all read.
"""

import json
import os
import re

from . import catalog

REQUIRED = ("title", "drop_object", "target", "break_at")

DEFAULTS = {
    "drop_mass_kg": None,            # None = use the catalogue mass for the drop object
    "drop_interval_start_s": 1.5,    # gap between the first impacts
    "drop_interval_end_s": 0.6,      # gap between the last impacts
    "crack_stages": None,            # None = picked automatically from break_at
    "duration_s": 70,
    "counter_label": None,           # None = catalogue label, e.g. "BALLS"
    "counter_label_singular": None,  # None = catalogue label, e.g. "BALL"
    "seed": 1,                       # changes pile layout, colours, crack shapes
    "intro_s": 2.0,                  # title + empty target before the first drop
    "outro_s": 5.0,                  # freeze-frame with the final counters
    "crack_beat_s": 1.0,             # extra pause after each crack stage
    "suspense_s": 1.2,               # extra pause before the final drop
    "shatter_s": 3.5,                # slow-motion shatter, main camera
    "replay": True,                  # low-angle slow-motion replay of the break
    "slowmo_factor": 0.22,           # physics speed during the shatter (1 = real time)
    "samples": 16,                   # Eevee samples for the final render
    "preview_samples": 6,            # Eevee samples for --preview
    "motion_blur": False,
    "slug": None,                    # None = config file name without extension
}


def _slugify(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def auto_crack_stages(break_at):
    """Four crack stages spread over the second half of the build, densest near the end."""
    fractions = (0.55, 0.76, 0.89, 0.97)
    stages = []
    for f in fractions:
        n = max(1, min(break_at - 1, int(round(break_at * f))))
        if not stages or n > stages[-1]:
            stages.append(n)
    return stages


def validate(cfg):
    """Raise ValueError with a readable message if the config can't make a valid episode."""
    for key in REQUIRED:
        if key not in cfg:
            raise ValueError("Config is missing required key %r" % key)
    catalog.drop_object(cfg["drop_object"])
    catalog.target(cfg["target"])

    n = cfg["break_at"]
    if not isinstance(n, int) or n < 2:
        raise ValueError("break_at must be a whole number of at least 2 (got %r)" % (n,))
    stages = cfg["crack_stages"]
    if any((not isinstance(s, int)) or s < 1 or s >= n for s in stages):
        raise ValueError("crack_stages must be whole numbers between 1 and break_at-1 (got %r)" % (stages,))
    if list(stages) != sorted(set(stages)):
        raise ValueError("crack_stages must be strictly increasing (got %r)" % (stages,))
    if cfg["duration_s"] <= 60:
        raise ValueError("duration_s must be over 60 seconds (got %r)" % cfg["duration_s"])
    if cfg["drop_interval_start_s"] <= 0 or cfg["drop_interval_end_s"] <= 0:
        raise ValueError("drop intervals must be positive")
    if cfg["drop_mass_kg"] <= 0:
        raise ValueError("drop_mass_kg must be positive")


def resolve(raw, source_path=None):
    """Merge defaults and catalogue values into a raw config dict and validate it."""
    cfg = dict(DEFAULTS)
    cfg.update(raw)
    obj = catalog.drop_object(cfg.get("drop_object", ""))

    if cfg["drop_mass_kg"] is None:
        cfg["drop_mass_kg"] = obj["mass_kg"]
    if cfg["counter_label"] is None:
        cfg["counter_label"] = obj["label"]
    if cfg["counter_label_singular"] is None:
        cfg["counter_label_singular"] = obj["label_singular"]
    if cfg["crack_stages"] is None and "break_at" in cfg:
        cfg["crack_stages"] = auto_crack_stages(cfg["break_at"])
    if cfg["slug"] is None:
        if source_path:
            cfg["slug"] = os.path.splitext(os.path.basename(source_path))[0]
        else:
            cfg["slug"] = _slugify("%s_%s" % (cfg["drop_object"], cfg["target"]))

    validate(cfg)
    warnings = []
    if not 65 <= cfg["duration_s"] <= 75:
        warnings.append("duration_s=%s is outside the recommended 65-75 s" % cfg["duration_s"])
    cfg["_warnings"] = warnings
    return cfg


def load_config(path):
    """Load, fill in and validate an episode JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return resolve(raw, source_path=path)


def format_weight(kg):
    """Format a weight for the counter: '259 KG', '2.4 KG', '0.2 KG'."""
    if kg >= 100 or abs(kg - round(kg)) < 1e-6:
        return "%d KG" % int(round(kg))
    return ("%.1f" % kg) + " KG"


def counter_text(cfg, n):
    """Top counter text, e.g. '37 BALLS' (singular for 1)."""
    label = cfg["counter_label_singular"] if n == 1 else cfg["counter_label"]
    return "%d %s" % (n, label)
