"""Series persistence: state.json carries ownership, champion and streak between episodes.

Each episode config freezes the state it started from (``start_state``), so an
old episode can always be re-rendered exactly, and the series only advances
when the *next* episode in sequence is fully rendered.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import load_config, new_seed
from .paths import EPISODES, SEASONS, STATE


def fresh_state(start_country: str, season: int = 1) -> dict:
    return {
        "season": season,
        "next_episode": 1,
        "start_country": start_country,
        "champion": start_country,
        "territory": [start_country],
        "streak": 0,
        "color": None,          # empire map colour (None = champion's main flag colour)
        "history": [],
    }


def load_state(cfg: dict, path: Path = STATE) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return fresh_state(cfg["start_country"])


def save_state(state: dict, path: Path = STATE) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
    tmp.replace(path)


def reset_season(cfg: dict, path: Path = STATE) -> dict:
    """Archive the current season's state and start a new season."""
    season = 1
    if path.exists():
        old = load_state(cfg, path)
        season = old.get("season", 1) + 1
        SEASONS.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, SEASONS / f"season_{old.get('season', 1):02d}_final.json")
    state = fresh_state(cfg["start_country"], season)
    save_state(state, path)
    return state


def episode_name(season: int, episode: int) -> str:
    return f"s{season:02d}e{episode:02d}"


def create_episode(base_config: Path | None = None, seed: int | None = None,
                   overrides: dict | None = None) -> Path:
    """Freeze the next episode: base config + seed + current series state."""
    cfg = load_config(base_config)
    if overrides:
        from .config import deep_merge, validate
        cfg = deep_merge(cfg, overrides)
        validate(cfg)
    state = load_state(cfg)
    cfg["seed"] = seed if seed is not None else (cfg.get("seed") or new_seed())
    cfg["season"] = state["season"]
    cfg["episode"] = state["next_episode"]
    cfg["start_state"] = {
        "champion": state["champion"],
        "territory": list(state["territory"]),
        "streak": state["streak"],
        "color": state.get("color"),
    }
    EPISODES.mkdir(parents=True, exist_ok=True)
    path = EPISODES / f"{episode_name(cfg['season'], cfg['episode'])}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    return path


def advance_state(cfg: dict, plan_dict: dict, episode_file: Path) -> bool:
    """After a full render, move the series on. Returns False (and changes
    nothing) if this episode is not the next one in sequence, e.g. when an old
    episode is re-rendered."""
    state = load_state(cfg)
    if (state["season"], state["next_episode"]) != (cfg["season"], cfg["episode"]):
        return False
    if state["champion"] != cfg["start_state"]["champion"] or \
            sorted(state["territory"]) != sorted(cfg["start_state"]["territory"]):
        return False
    end = plan_dict["end"]
    state.update(champion=end["champion"], territory=end["territory"], streak=end["streak"],
                 color=end["color"], next_episode=cfg["episode"] + 1)
    state["history"].append({
        "episode": cfg["episode"],
        "config": str(episode_file.name),
        "seed": cfg["seed"],
        "rounds": [{"opponent": r["opponent"], "winner": r["winner"]} for r in plan_dict["rounds"]],
    })
    save_state(state)
    return True
