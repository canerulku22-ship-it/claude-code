#!/usr/bin/env python3
"""Rizz Island — command-line entry point.

Built so far (step 1):
  python rizz_island.py --check [--install]   check / install dependencies
  python rizz_island.py --art [--force]       process character art (or draw placeholders)
                                              and write review/cast_sheet.jpg + review/lineup.jpg
  python rizz_island.py --auditions           review/auditions.mp3: every voice saying its catchphrase

Planned (later steps):
  python rizz_island.py                       votes.txt -> finished next episode, in one go
  python rizz_island.py --script-only         write the next script and stop for editing
  python rizz_island.py --preview             540x960 render of the first ~15 seconds
  python rizz_island.py --count-votes         tally votes.txt only
  python rizz_island.py --new-season          reset season_state.json
"""
from __future__ import annotations

import argparse
import sys
import time

from rizz import config


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="rizz_island.py", description="Make episodes of Rizz Island.")
    ap.add_argument("--check", action="store_true", help="check dependencies")
    ap.add_argument("--install", action="store_true", help="with --check: pip install anything missing")
    ap.add_argument("--art", action="store_true", help="process character art and write review sheets")
    ap.add_argument("--force", action="store_true", help="with --art: rebuild every sprite from scratch")
    ap.add_argument("--only", default="", help="comma-separated character ids to limit --art/--auditions to")
    ap.add_argument("--auditions", action="store_true", help="render a voice audition MP3")
    # Planned flags, accepted now so the interface is stable.
    ap.add_argument("--script-only", action="store_true", help="write the next episode script and stop")
    ap.add_argument("--preview", action="store_true", help="540x960, first ~15 s")
    ap.add_argument("--render", metavar="SCRIPT", help="render an existing script.json")
    ap.add_argument("--count-votes", action="store_true", help="tally votes.txt and print the result")
    ap.add_argument("--new-season", action="store_true", help="reset the season state")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    only = [s.strip() for s in args.only.split(",") if s.strip()] or None
    t0 = time.time()

    if args.check:
        from rizz.deps import check

        return 0 if check(install=args.install) else 1

    from rizz.cast import load_cast

    cast = load_cast()

    if args.art:
        from rizz.sheets import contact_sheet, lineup
        from rizz.sprites import build_sprites

        print("Processing character art...")
        build_sprites(cast, force=args.force, only=only)
        review = config.ROOT / "review"
        print(f"  wrote {contact_sheet(cast, review / 'cast_sheet.jpg').relative_to(config.ROOT)}")
        print(f"  wrote {lineup(cast, review / 'lineup.jpg').relative_to(config.ROOT)}")
        print(f"Done in {time.time() - t0:.0f}s")
        return 0

    if args.auditions:
        from rizz.auditions import make_auditions

        print("Recording voice auditions...")
        out = make_auditions(cast, config.ROOT / "review" / "auditions.mp3", only=only)
        print(f"  wrote {out.relative_to(config.ROOT)} in {time.time() - t0:.0f}s")
        return 0

    print("That part of the pipeline isn't built yet: the cast is waiting for approval (step 1).\n"
          "Available now: --check, --art, --auditions", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
