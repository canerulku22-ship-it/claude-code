"""High-level steps: simulate an episode config, write its events log, render it."""
from __future__ import annotations

import json
from pathlib import Path

from . import assets
from .config import load_json, validate
from .encode import encode, render_still
from .paths import OUT
from .sim import simulate_episode
from .state import advance_state, episode_name
from .timeline import build_timeline
from .world import load_world


def ensure_assets() -> None:
    if not assets.assets_present():
        print("Fetching assets (one-off)...")
        assets.fetch_assets()


def plan_episode(episode_file: Path):
    """Load a frozen episode config and run the simulation + choreography."""
    ensure_assets()
    cfg = load_json(episode_file)
    validate(cfg)
    if "start_state" not in cfg:
        raise ValueError(f"{episode_file} is not an episode config (no start_state); "
                         "create one with: python conquest.py new")
    world = load_world(cfg["sea_neighbour_km"])
    for code in cfg["start_state"]["territory"]:
        if code not in world:
            raise ValueError(f"unknown country code {code!r} in start_state")
    plan = simulate_episode(world, cfg)
    timeline = build_timeline(world, cfg, plan)
    return cfg, world, plan, timeline


def describe(world, plan) -> str:
    lines = []
    for r in plan.rounds:
        b = r.battle
        res = f"{world[r.winner].name} wins"
        if r.new_champion:
            res += " - NEW CHAMPION"
        lines.append(f"  round {r.number}: {world[r.champion].name} vs {world[r.opponent].name} "
                     f"({len(r.candidates)} candidates, {len(b.exchanges)} exchanges) -> {res}")
    end = plan.end
    lines.append(f"  end: {world[end['champion']].name} owns {len(end['territory'])} countries, "
                 f"streak {end['streak']}")
    return "\n".join(lines)


def write_events(path: Path, cfg: dict, plan, timeline) -> None:
    """The events log: every timed moment of the video (used to place the audio)."""
    data = {
        "episode": episode_name(cfg["season"], cfg["episode"]),
        "seed": cfg["seed"],
        "fps": timeline.fps,
        "duration": round(timeline.duration, 4),
        "events": [{**e, "t": round(e["t"], 4)} for e in timeline.events],
        "rounds": [{"number": r.number, "champion": r.champion, "opponent": r.opponent,
                    "winner": r.winner, "new_champion": r.new_champion,
                    "exchanges": [vars(x) for x in r.battle.exchanges]} for r in plan.rounds],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)


def render_episode(episode_file: Path, preview: bool = False, workers: int | None = None,
                   out: Path | None = None, advance: bool = True, stills: list[float] | None = None,
                   guides: bool = False) -> Path:
    cfg, world, plan, timeline = plan_episode(episode_file)
    name = episode_name(cfg["season"], cfg["episode"])
    print(f"Episode {name} (seed {cfg['seed']}):")
    print(describe(world, plan))

    if preview:
        pv = cfg["preview"]
        width, height, ss = pv["width"], pv["height"], pv["supersample"]
        duration = min(pv["duration"], timeline.duration)
        out = out or OUT / f"{name}_preview.mp4"
        crf, preset = 20, "veryfast"
    else:
        v = cfg["video"]
        width, height, ss = v["width"], v["height"], v["supersample"]
        duration = timeline.duration
        out = out or OUT / f"{name}.mp4"
        crf, preset = v["crf"], v["x264_preset"]
    OUT.mkdir(parents=True, exist_ok=True)
    events_path = out.with_suffix(".events.json")
    write_events(events_path, cfg, plan, timeline)

    if stills:
        for t in stills:
            p = out.with_name(f"{out.stem}_t{t:05.2f}.png")
            render_still(timeline, t, p, width, height, ss, guides)
            print("  still:", p)
        return out

    print(f"Rendering {width}x{height} @ {timeline.fps}fps, {duration:.1f}s -> {out}")
    encode(timeline, out, width, height, ss, duration, audio=None, crf=crf, preset=preset,
           workers=workers, guides=guides)
    print(f"  events log: {events_path}")
    if not preview and advance and not guides:
        if advance_state(cfg, plan.to_dict(), episode_file):
            print("  state.json updated: the next episode continues from here")
        else:
            print("  state.json unchanged (this is not the next episode in the series)")
    return out
