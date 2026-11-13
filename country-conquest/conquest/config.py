"""Config loading.

An episode config is the base config (configs/default.json) deep-merged with
any overrides, plus the fields that freeze an episode so it re-renders exactly:
``seed``, ``season``, ``episode`` and ``start_state``.
"""
from __future__ import annotations

import copy
import json
import random
from pathlib import Path

from .paths import DEFAULT_CONFIG

SPINNER_STYLES = ("map_roulette", "wheel")
STRENGTH_MODES = ("equal", "territory_bonus")


class ConfigError(ValueError):
    pass


def deep_merge(base: dict, override: dict) -> dict:
    """Return a copy of ``base`` with ``override`` merged in (dicts merge recursively)."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_config(path: Path | None = None) -> dict:
    """Load a config file on top of the defaults. ``path=None`` gives the defaults."""
    cfg = load_json(DEFAULT_CONFIG)
    if path is not None and Path(path).resolve() != DEFAULT_CONFIG.resolve():
        cfg = deep_merge(cfg, load_json(Path(path)))
    validate(cfg)
    return cfg


def new_seed() -> int:
    """A fresh random seed, saved into the episode config so it can be replayed."""
    return random.SystemRandom().randrange(1, 2**31 - 1)


def validate(cfg: dict) -> None:
    """Fail early with a readable message instead of deep inside rendering."""
    def need(cond: bool, msg: str) -> None:
        if not cond:
            raise ConfigError(msg)

    need(isinstance(cfg.get("start_country"), str) and len(cfg["start_country"]) == 3,
         "start_country must be an ISO-3166 alpha-3 code such as \"TUR\"")
    need(isinstance(cfg.get("rounds"), int) and 1 <= cfg["rounds"] <= 12, "rounds must be 1-12")
    need(cfg.get("spinner_style") in SPINNER_STYLES, f"spinner_style must be one of {SPINNER_STYLES}")
    need(cfg.get("strength_mode") in STRENGTH_MODES, f"strength_mode must be one of {STRENGTH_MODES}")
    need(cfg.get("seed") is None or isinstance(cfg["seed"], int), "seed must be an integer or null")
    for pair in cfg.get("exclude_pairs", []):
        need(isinstance(pair, list) and len(pair) == 2, f"exclude_pairs entries must be [A, B]: {pair}")
    v, t = cfg["video"], cfg["timing"]
    fixed = t["intro"] + t["outro"]
    per_round = (v["target_duration"] - fixed) / cfg["rounds"]
    need(v["target_duration"] < 60, "target_duration must stay under 60 seconds")
    need(per_round >= 6.0, f"target_duration leaves only {per_round:.1f}s per round; "
                           "lower 'rounds' or raise target_duration")
    need(v["width"] % 2 == 0 and v["height"] % 2 == 0, "video width/height must be even (H.264)")
