#!/usr/bin/env python3
"""Country Conquest - command line.

  python conquest.py fetch-assets                 download map data, flags and font
  python conquest.py episode [--preview] [--seed N] [--reset]
                                                  create the next episode config and render it
  python conquest.py new [--seed N] [--reset]     only create the next episode config
  python conquest.py render episodes/s01e01.json [--preview]
                                                  (re-)render an existing episode config exactly
  python conquest.py batch 3 [--reset]            render several episodes in a row
  python conquest.py reset                        start a new season
  python conquest.py status                       show the series state
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from conquest import assets
from conquest.config import ConfigError, load_config
from conquest.paths import DEFAULT_CONFIG
from conquest.state import create_episode, load_state, reset_season


def _base(args) -> Path:
    return Path(args.base) if args.base else DEFAULT_CONFIG


def cmd_fetch(args) -> None:
    assets.fetch_assets(force=args.force)


def cmd_reset(args) -> None:
    state = reset_season(load_config(_base(args)))
    print(f"New season {state['season']} starts with {state['champion']}.")


def cmd_status(args) -> None:
    state = load_state(load_config(_base(args)))
    print(f"Season {state['season']}, next episode {state['next_episode']}")
    print(f"Champion {state['champion']} owns {len(state['territory'])} countries "
          f"(streak {state['streak']}): {', '.join(state['territory'])}")


def _new(args) -> Path:
    if getattr(args, "reset", False):
        cmd_reset(args)
    overrides = {}
    if getattr(args, "spinner", None):
        overrides["spinner_style"] = args.spinner
    path = create_episode(_base(args), seed=args.seed, overrides=overrides or None)
    print(f"Episode config: {path}")
    return path


def cmd_new(args) -> None:
    _new(args)


def cmd_render(args) -> None:
    from conquest.pipeline import render_episode
    stills = [float(x) for x in args.stills.split(",")] if args.stills else None
    render_episode(Path(args.episode), preview=args.preview, workers=args.workers,
                   out=Path(args.out) if args.out else None, stills=stills,
                   advance=not args.no_advance, guides=args.guides)


def cmd_episode(args) -> None:
    from conquest.pipeline import render_episode
    path = _new(args)
    render_episode(path, preview=args.preview, workers=args.workers)


def cmd_batch(args) -> None:
    from conquest.pipeline import render_episode
    if args.reset:
        cmd_reset(args)
    for i in range(args.count):
        print(f"\n=== batch {i + 1}/{args.count} ===")
        path = create_episode(_base(args))
        render_episode(path, workers=args.workers)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="Country Conquest animation pipeline")
    p.add_argument("--base", help="base config (default: configs/default.json)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("fetch-assets", help="download Natural Earth, flag-icons and the font")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("reset", help="start a new season")
    s.set_defaults(func=cmd_reset)

    s = sub.add_parser("status", help="show the series state")
    s.set_defaults(func=cmd_status)

    def episode_opts(s):
        s.add_argument("--seed", type=int, help="fix the random seed (default: a new random seed)")
        s.add_argument("--reset", action="store_true", help="start a new season first")
        s.add_argument("--spinner", choices=["map_roulette", "wheel"], help="override spinner_style")

    s = sub.add_parser("new", help="create the next episode config")
    episode_opts(s)
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("episode", help="create and render the next episode")
    episode_opts(s)
    s.add_argument("--preview", action="store_true", help="540x960, first round only, fast")
    s.add_argument("--workers", type=int)
    s.set_defaults(func=cmd_episode)

    s = sub.add_parser("render", help="render an episode config")
    s.add_argument("episode")
    s.add_argument("--preview", action="store_true", help="540x960, first round only, fast")
    s.add_argument("--workers", type=int)
    s.add_argument("--out", help="output .mp4 path")
    s.add_argument("--stills", help="comma-separated times: save PNG frames instead of a video")
    s.add_argument("--no-advance", action="store_true", help="never update state.json")
    s.add_argument("--guides", action="store_true", help="shade TikTok's UI zones (layout check)")
    s.set_defaults(func=cmd_render)

    s = sub.add_parser("batch", help="render several episodes in a row")
    s.add_argument("count", type=int)
    s.add_argument("--reset", action="store_true", help="start a new season first")
    s.add_argument("--workers", type=int)
    s.set_defaults(func=cmd_batch)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except ConfigError as e:
        sys.exit(f"config error: {e}")


if __name__ == "__main__":
    main()
