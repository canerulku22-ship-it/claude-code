"""Episode config loading, defaults and validation.

An episode is one JSON file. Only the first block below is required; the
rest have sensible defaults (some come from the material preset).

    {
      "title": "What if you fold paper 42 times?",
      "material": "paper",
      "thickness_mm": 0.1,
      "colour": "#f5f2ea",
      "folds": 42,
      "duration_s": 70
    }
"""

import json
import os
import re

from .mathutil import hex_to_srgb

# Per-material defaults. Anything here can be overridden in the episode JSON.
MATERIAL_PRESETS = {
    "paper":       dict(sheet_size_mm=[210, 297], sound="paper", roughness=0.62, sheen=0.25),
    "banknote":    dict(sheet_size_mm=[156, 66], sound="paper", roughness=0.55, sheen=0.2),
    "pizza dough": dict(sheet_size_mm=[300, 300], sound="dough", roughness=0.85, sheen=0.0),
    "bedsheet":    dict(sheet_size_mm=[2000, 2400], sound="cloth", roughness=0.9, sheen=0.6),
}
GENERIC_PRESET = dict(sheet_size_mm=[210, 297], sound="paper", roughness=0.6, sheen=0.1)

DEFAULTS = dict(
    duration_s=70.0,
    fps=30,
    physical_folds=10,          # folds shown as a real fold animation
    cta="What should we fold next?",
    seed=7,
    landmarks="auto",           # "auto", or a list of landmark ids to allow
    sfx_dir=None,               # folder with optional royalty-free SFX overrides
    music=None,                 # optional background music file
)

REQUIRED = ("title", "material", "thickness_mm", "colour", "folds")


class ConfigError(ValueError):
    pass


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"{path}: invalid JSON ({e})") from e
    cfg = normalise(raw)
    cfg["config_path"] = os.path.abspath(path)
    cfg.setdefault("slug", slugify(os.path.splitext(os.path.basename(path))[0]))
    return cfg


def normalise(raw):
    """Fill defaults and check every value; returns a new dict."""
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise ConfigError(f"missing required field(s): {', '.join(missing)}")

    cfg = dict(DEFAULTS)
    preset = MATERIAL_PRESETS.get(str(raw["material"]).strip().lower(), GENERIC_PRESET)
    cfg.update(preset)
    cfg.update(raw)

    cfg["title"] = str(cfg["title"]).strip()
    cfg["material"] = str(cfg["material"]).strip()
    cfg["thickness_mm"] = _positive_float(cfg, "thickness_mm")
    cfg["duration_s"] = _positive_float(cfg, "duration_s")
    cfg["folds"] = _int_in_range(cfg, "folds", 1, 60)
    cfg["fps"] = _int_in_range(cfg, "fps", 12, 60)
    cfg["physical_folds"] = _int_in_range(cfg, "physical_folds", 0, 20)
    cfg["roughness"] = min(max(float(cfg["roughness"]), 0.0), 1.0)
    cfg["sheen"] = min(max(float(cfg.get("sheen", 0.0)), 0.0), 1.0)

    try:
        hex_to_srgb(cfg["colour"])
    except ValueError as e:
        raise ConfigError(str(e)) from e

    size = cfg["sheet_size_mm"]
    if not (isinstance(size, (list, tuple)) and len(size) == 2 and all(float(v) > 0 for v in size)):
        raise ConfigError("sheet_size_mm must be [width, height] in millimetres")
    cfg["sheet_size_mm"] = [float(size[0]), float(size[1])]

    if cfg["sound"] not in ("paper", "cloth", "dough"):
        raise ConfigError("sound must be one of: paper, cloth, dough")

    # TikTok rewards > 60 s; the series targets 65-75 s.
    if cfg["duration_s"] <= 60:
        raise ConfigError("duration_s must be over 60 seconds")
    if not 65 <= cfg["duration_s"] <= 75:
        print(f"[config] note: duration_s={cfg['duration_s']} is outside the 65-75 s target")
    return cfg


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "episode"


def _positive_float(cfg, key):
    try:
        value = float(cfg[key])
    except (TypeError, ValueError):
        raise ConfigError(f"{key} must be a number") from None
    if value <= 0:
        raise ConfigError(f"{key} must be greater than 0")
    return value


def _int_in_range(cfg, key, lo, hi):
    try:
        value = int(cfg[key])
    except (TypeError, ValueError):
        raise ConfigError(f"{key} must be a whole number") from None
    if not lo <= value <= hi:
        raise ConfigError(f"{key} must be between {lo} and {hi}")
    return value
