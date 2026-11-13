"""Season persistence: season_state.json.

Holds everything the script writer needs for continuity: who is still in the
villa, couples, eliminations, storylines, rivalries, running jokes, a log of
past episodes, and the vote that the last episode asked viewers for.

The state only advances when an episode is *finished* (full render), so you
can regenerate or hand-edit a script as often as you like first.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from typing import Any

from . import config
from .cast import Cast


def initial_state(cast: Cast, season: int = 1) -> dict[str, Any]:
    """A fresh season built from the story bible."""
    villa = [c.id for c in cast.characters.values() if not c.raw.get("bombshell")]
    couples, seen = [], set()
    for cid in villa:
        p = cast.characters[cid].raw["relationship"].get("partner")
        if p and p in villa and cid not in seen and p not in seen:
            couples.append([cid, p])
            seen |= {cid, p}
    return {
        "season": season,
        "episode": 0,                       # last finished episode
        "in_villa": villa,
        "bombshells_waiting": [c.id for c in cast.characters.values() if c.raw.get("bombshell")],
        "couples": couples,
        "eliminated": [],                   # [{"id", "episode", "how", "votes"}]
        "storylines": list(cast.raw.get("starting_storylines", [])),
        "rivalries": [],
        "running_jokes": list(cast.raw.get("running_jokes", [])),
        "episode_log": [],                  # [{"episode", "title", "summary", "biggest_moment", "vote_options"}]
        "pending_vote": None,               # {"episode", "options"} from the last cliffhanger
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def load_state(cast: Cast) -> dict[str, Any]:
    if config.STATE_FILE.exists():
        return json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
    state = initial_state(cast)
    save_state(state)
    return state


def save_state(state: dict[str, Any]) -> None:
    config.STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def new_season(cast: Cast) -> dict[str, Any]:
    """Archive the current season (state + episodes folder) and start over."""
    old_season = 0
    if config.STATE_FILE.exists():
        old = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
        old_season = int(old.get("season", 1))
        archive = config.ROOT / "seasons" / f"season{old_season:02d}"
        archive.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config.STATE_FILE, archive / "season_state.json")
        if config.EPISODES_DIR.exists():
            shutil.move(str(config.EPISODES_DIR), str(archive / "episodes"))
    state = initial_state(cast, season=old_season + 1)
    save_state(state)
    return state


def singles(state: dict[str, Any]) -> list[str]:
    coupled = {cid for pair in state["couples"] for cid in pair}
    return [cid for cid in state["in_villa"] if cid not in coupled]


def episode_dir(n: int):
    return config.EPISODES_DIR / f"ep{n:02d}"


def apply_episode(state: dict[str, Any], script: dict[str, Any]) -> dict[str, Any]:
    """Advance the season with a finished episode's script. Returns the new state."""
    s = json.loads(json.dumps(state))   # deep copy
    n = int(script["episode"])
    vr = script.get("vote_result", {})
    dumped = vr.get("dumped", "none")
    if vr.get("kind") in ("viewer_vote", "producer_decision") and dumped in s["in_villa"]:
        s["in_villa"].remove(dumped)
        s["eliminated"].append({"id": dumped, "episode": n,
                                "how": "dumped by the viewers" if vr["kind"] == "viewer_vote" else "dumped by the producers",
                                "votes": vr.get("tally")})
    tw = script.get("twist", {})
    if tw.get("kind") == "new_arrival":
        for cid in tw.get("characters", []):
            if cid in s.get("bombshells_waiting", []):
                s["bombshells_waiting"].remove(cid)
                s["in_villa"].append(cid)

    cont = script.get("continuity", {})
    villa = set(s["in_villa"])
    pairs, used = [], set()
    for p in cont.get("couples", []):
        a, b = p["a"], p["b"]
        if a in villa and b in villa and a != b and not ({a, b} & used):
            pairs.append([a, b])
            used |= {a, b}
    s["couples"] = pairs
    for key in ("storylines", "running_jokes", "rivalries"):
        if cont.get(key):
            s[key] = cont[key]
    s["episode_log"].append({
        "episode": n, "title": script.get("title", ""), "summary": cont.get("summary", ""),
        "biggest_moment": cont.get("biggest_moment", ""), "dumped": dumped if dumped != "none" else None,
        "vote_options": script.get("cliffhanger", {}).get("vote_options", []),
    })
    s["pending_vote"] = {"episode": n, "options": script.get("cliffhanger", {}).get("vote_options", [])}
    s["episode"] = n
    return s
