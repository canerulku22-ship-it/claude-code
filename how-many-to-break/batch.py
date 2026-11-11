"""Render a list of episodes one after another.

    python batch.py episodes/*.json
    python batch.py episodes/watermelons_trampoline.json episodes/iphones_egg.json --preview
    python batch.py --list my_batch.txt          # one config path per line, # for comments

Each episode is rendered with make_episode.py's pipeline. A failed episode is reported
and the batch moves on. Re-running a batch resumes partly rendered episodes.
"""

import argparse
import glob
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from hmtb import tools  # noqa: E402
from make_episode import make_episode  # noqa: E402


def read_list(path):
    out = []
    base = os.path.dirname(os.path.abspath(path))
    with open(path) as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                out.append(line if os.path.isabs(line) else os.path.join(base, line))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("configs", nargs="*", help="episode JSON files (globs allowed)")
    p.add_argument("--list", help="text file with one config path per line")
    p.add_argument("--preview", action="store_true", help="render previews instead of full episodes")
    p.add_argument("--blender", help="path to blender (or a python with bpy)")
    p.add_argument("--samples", type=int)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--fresh", action="store_true")
    args = p.parse_args()

    configs = []
    for c in args.configs:
        configs += sorted(glob.glob(c)) or [c]
    if args.list:
        configs += read_list(args.list)
    if not configs:
        p.error("no configs given")
    if not tools.check(args.blender, verbose=False):
        tools.check(args.blender)
        raise SystemExit(1)

    results = []
    t_all = time.time()
    for i, cfg in enumerate(configs, 1):
        print("\n" + "=" * 70 + "\n[%d/%d] %s\n" % (i, len(configs), cfg) + "=" * 70, flush=True)
        t0 = time.time()
        try:
            mp4 = make_episode(cfg, preview=args.preview, blender=args.blender, samples=args.samples,
                               scale=args.scale, fresh=args.fresh)
            results.append((cfg, "OK", time.time() - t0, mp4))
        except (Exception, SystemExit) as exc:   # keep going with the rest of the batch
            traceback.print_exc()
            results.append((cfg, "FAILED: %s" % exc, time.time() - t0, ""))

    print("\n" + "=" * 70 + "\nBatch finished in %.1f min" % ((time.time() - t_all) / 60))
    for cfg, status, secs, mp4 in results:
        print("  %-45s %-8s %6.1f min  %s" % (os.path.basename(cfg), status[:40], secs / 60, mp4))
    sys.exit(0 if all(r[1] == "OK" for r in results) else 1)


if __name__ == "__main__":
    main()
