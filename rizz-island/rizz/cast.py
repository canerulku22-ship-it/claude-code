"""Load and validate the story bible (cast.json).

cast.json is hand-edited, so this module is forgiving about extras but strict
about the fields the pipeline depends on, and reports every problem at once.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

REQUIRED_FIELDS = ["id", "name", "emoji", "nicknames", "species", "look", "personality",
                   "catchphrase", "color", "relationship", "voice"]
REQUIRED_VOICE = ["engine", "voice_id", "pitch", "speed"]


@dataclass
class Character:
    """One cast member. `raw` keeps the full JSON entry for the script writer."""
    id: str
    name: str
    short_name: str
    emoji: str
    color: str
    voice: dict[str, Any]
    nicknames: list[str]
    scale: float = 1.0
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def rgb(self) -> tuple[int, int, int]:
        return hex_to_rgb(self.color)


@dataclass
class Cast:
    show: dict[str, Any]
    locations: dict[str, str]
    characters: dict[str, Character]          # id -> Character, in cast.json order
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def get(self, cid: str) -> Character:
        if cid not in self.characters:
            raise KeyError(f"Unknown character id '{cid}'. Known: {', '.join(self.characters)}")
        return self.characters[cid]

    @property
    def narrator_voice(self) -> dict[str, Any]:
        return self.show.get("narrator", {}).get("voice", {})

    def ids(self) -> list[str]:
        return list(self.characters)


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def load_cast(path: Path = config.CAST_FILE) -> Cast:
    """Parse cast.json and raise a single ValueError listing every problem found."""
    data = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    chars: dict[str, Character] = {}

    for i, c in enumerate(data.get("characters", [])):
        label = c.get("id", f"#{i}")
        for f in REQUIRED_FIELDS:
            if f not in c:
                problems.append(f"{label}: missing '{f}'")
        if "id" in c and not re.fullmatch(r"[a-z0-9_]+", c["id"]):
            problems.append(f"{label}: id must be lowercase letters/digits/underscores (used as a folder name)")
        if c.get("id") in chars:
            problems.append(f"{label}: duplicate id")
        if "color" in c and not re.fullmatch(r"#[0-9A-Fa-f]{6}", c["color"]):
            problems.append(f"{label}: color must look like #RRGGBB")
        for f in REQUIRED_VOICE:
            if f not in c.get("voice", {}):
                problems.append(f"{label}: voice missing '{f}'")
        if problems:
            continue
        chars[c["id"]] = Character(
            id=c["id"], name=c["name"], short_name=c.get("short_name") or c["name"].split()[0],
            emoji=c["emoji"], color=c["color"], voice=c["voice"], nicknames=c["nicknames"],
            scale=float(c.get("scale", 1.0)), raw=c,
        )

    # Partners must point at real characters.
    for c in chars.values():
        p = c.raw["relationship"].get("partner")
        if p and p not in chars:
            problems.append(f"{c.id}: partner '{p}' is not a character id")

    if len(chars) < 2 and not problems:
        problems.append("need at least two characters")
    if problems:
        raise ValueError("cast.json problems:\n  - " + "\n  - ".join(problems))

    return Cast(show=data.get("show", {}), locations=data.get("locations", {}),
                characters=chars, raw=data)
