"""The game simulation. Every outcome in the video comes from here.

Given an episode config (seed + start state) this decides, round by round,
which opponent the spinner lands on, how the battle plays out blow by blow,
and who ends up owning what. Nothing is scripted: the renderer only animates
the results. All randomness comes from ``random.Random`` seeded with the
config's seed, so the same config always produces the same episode.

Battle rules (identical for both sides; game-like, no real-world meaning):
* Both start at 100 HP ("equal"), or the champion gets a small capped bonus
  for each extra country it owns ("territory_bonus").
* Each exchange one side attacks: MISS, HIT (14-26) or CRIT (32-42).
* A side at <=30% HP "rallies": its crit chance rises, which makes comebacks
  possible. A side at <=25% HP dodges a little more often, which produces
  near misses. After 16 exchanges damage doubles so battles always end.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from .render.flags import distinct_color
from .world import World

ALTERNATE_P = 0.72      # chance the other side attacks next
MISS_P, CRIT_P = 0.16, 0.12
LOW_HP_DODGE = 0.10     # extra miss chance against a side at <=25% HP
RALLY_CRIT = 0.14       # extra crit chance for a side at <=30% HP
HIT_DMG, CRIT_DMG = (14, 26), (32, 42)
OVERTIME_AFTER = 16


@dataclass
class Exchange:
    attacker: str           # "A" (champion) or "B" (opponent)
    kind: str               # "hit" | "crit" | "miss"
    damage: int
    hp_a: int               # HP after this exchange
    hp_b: int
    tags: list[str] = field(default_factory=list)   # near_miss, rally, overtime, ko


@dataclass
class Battle:
    a: str
    b: str
    max_a: int
    max_b: int
    exchanges: list[Exchange]
    winner: str             # "A" or "B"
    comeback: bool          # winner was at <=25% HP while the loser still had >=50%
    close: bool             # winner finished with <=10% HP


@dataclass
class Round:
    number: int
    champion: str
    territory: list[str]
    streak: int
    candidates: list[str]
    opponent: str
    nearest_fallback: bool  # no eligible neighbour: picked among the nearest countries
    battle: Battle
    winner: str             # country code
    new_champion: bool
    champion_after: str
    territory_after: list[str]
    streak_after: int
    champion_color: tuple   # the empire's map colour going into the round
    opponent_color: tuple   # opponent's flag colour that contrasts with it
    color_after: tuple      # empire colour after the round (opponent's if it won)


@dataclass
class EpisodePlan:
    season: int
    episode: int
    seed: int
    start: dict
    rounds: list[Round]
    end: dict

    def to_dict(self) -> dict:
        return asdict(self)


def excluded_pairs(cfg: dict) -> set[frozenset]:
    return {frozenset(p) for p in cfg.get("exclude_pairs", [])}


def eligible_opponents(world: World, cfg: dict, champion: str, territory: list[str]) -> tuple[list[str], bool]:
    """Countries the spinner may land on. Returns (sorted codes, used_fallback)."""
    playable = world.playable(cfg)
    owned = set(territory)
    banned = excluded_pairs(cfg)
    # With exclude_pairs_cover_territory, an excluded pair also blocks a country
    # from facing anyone who *holds* the other half of the pair.
    guards = owned | {champion} if cfg.get("exclude_pairs_cover_territory", True) else {champion}

    def allowed(code: str) -> bool:
        return code in playable and code not in owned and not any(
            frozenset((code, g)) in banned for g in guards)

    if cfg.get("neighbours_only", True):
        pool = set()
        for code in owned:
            pool |= world[code].neighbours
        pool = {c for c in pool if allowed(c)}
        if pool:
            return sorted(pool), False
        # Island empires etc.: fall back to the 3 nearest eligible countries.
        rest = [c for c in playable if allowed(c)]
        rest.sort(key=lambda c: (min(world.distance_km(c, o) for o in owned), c))
        return sorted(rest[:3]), True
    return sorted(c for c in playable if allowed(c)), False


def max_hp(cfg: dict, territory_size: int) -> int:
    if cfg.get("strength_mode") == "territory_bonus":
        tb = cfg.get("territory_bonus", {})
        bonus = min(tb.get("max_bonus", 18), tb.get("hp_per_extra_country", 3) * (territory_size - 1))
        return 100 + max(0, bonus)
    return 100


def simulate_battle(rng: random.Random, a: str, b: str, max_a: int, max_b: int) -> Battle:
    hp = {"A": max_a, "B": max_b}
    top = {"A": max_a, "B": max_b}
    behind = {"A": False, "B": False}   # was this side ever <=25% while the other had >=50%?
    other = {"A": "B", "B": "A"}
    attacker = rng.choice("AB")
    exchanges: list[Exchange] = []
    n = 0
    while hp["A"] > 0 and hp["B"] > 0:
        n += 1
        if n > 1 and rng.random() < ALTERNATE_P:
            attacker = other[attacker]
        target = other[attacker]
        rallying = hp[attacker] <= 0.30 * top[attacker]
        cornered = hp[target] <= 0.25 * top[target]
        miss_p = MISS_P + (LOW_HP_DODGE if cornered else 0.0)
        crit_p = CRIT_P + (RALLY_CRIT if rallying else 0.0)
        roll = rng.random()
        tags = []
        if roll < miss_p:
            kind, dmg = "miss", 0
            if cornered:
                tags.append("near_miss")
        elif roll < miss_p + crit_p:
            kind, dmg = "crit", rng.randint(*CRIT_DMG)
        else:
            kind, dmg = "hit", rng.randint(*HIT_DMG)
        if n > OVERTIME_AFTER and dmg:
            dmg *= 2
            tags.append("overtime")
        if rallying and dmg:
            tags.append("rally")
        hp[target] = max(0, hp[target] - dmg)
        if hp[target] > 0 and hp[target] <= 0.25 * top[target] and hp[attacker] >= 0.5 * top[attacker]:
            behind[target] = True
        if hp[target] == 0:
            tags.append("ko")
        exchanges.append(Exchange(attacker, kind, dmg, hp["A"], hp["B"], tags))
    winner = "A" if hp["A"] > 0 else "B"
    return Battle(a, b, max_a, max_b, exchanges, winner,
                  comeback=behind[winner],
                  close=hp[winner] / top[winner] <= 0.10)


def palette(world: World, cfg: dict, code: str) -> list[tuple]:
    """Team colour candidates; a "colors" override in the config comes first."""
    pal = [tuple(c) for c in world[code].palette]
    override = cfg.get("colors", {}).get(code)
    if override:
        h = override.lstrip("#")
        pal.insert(0, tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)))
    return pal


def simulate_episode(world: World, cfg: dict) -> EpisodePlan:
    """Play every round of the episode described by ``cfg``."""
    if cfg.get("seed") is None:
        raise ValueError("episode config has no seed; create episodes with 'conquest.py new'")
    start = cfg["start_state"]
    rng = random.Random(f"{cfg['seed']}:sim")
    champion = start["champion"]
    territory = list(start["territory"])
    streak = int(start.get("streak", 0))
    color = tuple(start.get("color") or palette(world, cfg, champion)[0])
    rounds = []
    for number in range(1, cfg["rounds"] + 1):
        candidates, fallback = eligible_opponents(world, cfg, champion, territory)
        if not candidates:
            print(f"  round {number}: no eligible opponents left; episode ends early")
            break
        opponent = rng.choice(candidates)
        battle = simulate_battle(rng, champion, opponent,
                                 max_hp(cfg, len(territory)), max_hp(cfg, 1))
        opp_color = distinct_color(palette(world, cfg, opponent), color)
        if battle.winner == "A":
            winner, new_champ = champion, False
            territory_after = territory + [opponent]
            streak_after = streak + 1
        else:  # the opponent takes the whole empire and becomes champion
            winner, new_champ = opponent, True
            territory_after = [opponent] + territory
            streak_after = 1
        color_after = opp_color if new_champ else color
        rounds.append(Round(number, champion, list(territory), streak, candidates, opponent,
                            fallback, battle, winner, new_champ, winner, territory_after,
                            streak_after, color, opp_color, color_after))
        champion, territory, streak, color = winner, territory_after, streak_after, color_after
    end = {"champion": champion, "territory": territory, "streak": streak, "color": list(color)}
    return EpisodePlan(cfg["season"], cfg["episode"], cfg["seed"], start, rounds, end)
