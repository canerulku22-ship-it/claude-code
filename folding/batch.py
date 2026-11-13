"""Render several episodes in one go.

    python batch.py episodes/*.json                # full render of each, in turn
    python batch.py episodes/                      # every .json in a folder
    python batch.py my_list.txt                    # a text file, one config per line
    python batch.py episodes/*.json --plan         # check configs, print beats; render nothing
    python batch.py episodes/*.json --preview      # previews instead of full renders
    python batch.py episodes/*.json --parts 4      # use 4 Blender processes per episode

Every config is loaded and checked before anything renders, so a typo in the
last file shows up straight away, not hours later. Landmark beats and pacing
are recalculated for each material automatically.

Any other option is passed to run.py for every episode (for example
--resume, --samples 32, --stills, --dry-run). A failed episode does not stop
the batch unless you add --stop-on-error; a summary is printed at the end.

--parts N runs N Blender processes side by side on this machine, each
rendering every Nth frame, then one more pass that fills any gaps and encodes
the video. On a CPU-only machine 2 is usually best; with a GPU, 1.
"""

import argparse
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from foldlib import DEFAULT_OUTPUT_DIR  # noqa: E402
from foldlib.config import ConfigError, load_config  # noqa: E402
from foldlib.timeline import Timeline  # noqa: E402

RUN = os.path.join(HERE, "run.py")


def parse_args():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="python batch.py CONFIG [CONFIG ...] [--plan] [--parts N] [run.py options]")
    p.add_argument("inputs", nargs="+", help="episode .json files, folders, or .txt lists")
    p.add_argument("--plan", action="store_true", help="check configs and print beats only")
    p.add_argument("--parts", type=int, default=1, help="Blender processes per episode")
    p.add_argument("--stop-on-error", action="store_true", help="stop at the first failure")
    args, extra = p.parse_known_args()
    if args.parts < 1:
        p.error("--parts must be 1 or more")
    return args, extra


def expand(inputs):
    """Turn files, folders, globs and .txt lists into a list of config paths."""
    paths = []
    for item in inputs:
        if os.path.isdir(item):
            paths += sorted(glob.glob(os.path.join(item, "*.json")))
        elif item.lower().endswith(".txt"):
            base = os.path.dirname(os.path.abspath(item))
            with open(item, encoding="utf-8") as fh:
                for line in fh:
                    line = line.split("#", 1)[0].strip()
                    if line:   # relative to the list file, else to the current folder
                        near = os.path.join(base, line)
                        paths.append(near if os.path.exists(near) or not os.path.exists(line) else line)
        elif any(c in item for c in "*?["):    # a glob the shell did not expand (Windows)
            paths += sorted(glob.glob(item))
        else:
            paths.append(item)
    seen, unique = set(), []
    for path in paths:
        key = os.path.abspath(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def check_all(paths):
    """Load and validate every config up front. Returns [(path, cfg, timeline)]."""
    episodes, errors = [], []
    slugs = {}
    for path in paths:
        try:
            cfg = load_config(path)
            tl = Timeline(cfg)
        except FileNotFoundError:
            errors.append(f"{path}: file not found")
            continue
        except (ConfigError, ValueError, KeyError) as e:
            errors.append(f"{path}: {e}")
            continue
        if cfg["slug"] in slugs:
            errors.append(f"{path}: same output name '{cfg['slug']}' as {slugs[cfg['slug']]}; rename one file")
            continue
        slugs[cfg["slug"]] = path
        episodes.append((path, cfg, tl))
    return episodes, errors


def option_value(extra, name, default=None):
    """Value of `--name X` or `--name=X` among the pass-through options."""
    for i, a in enumerate(extra):
        if a == name and i + 1 < len(extra):
            return extra[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def render(path, cfg, extra, parts):
    """Render one episode through run.py. Returns True on success."""
    if parts == 1:
        return subprocess.call([sys.executable, RUN, path, *extra]) == 0

    # Split across processes: each renders every Nth frame, output to a log.
    mode = "preview" if "--preview" in extra else "full"
    out_root = os.path.abspath(option_value(extra, "--out", DEFAULT_OUTPUT_DIR))
    log_dir = os.path.join(out_root, cfg["slug"], mode)
    os.makedirs(log_dir, exist_ok=True)
    procs = []
    for k in range(parts):
        log_path = os.path.join(log_dir, f"part{k}of{parts}.log")
        cmd = [sys.executable, RUN, path, *extra, "--frames-only", "--resume", "--part", f"{k}/{parts}"]
        log = open(log_path, "w", encoding="utf-8")
        procs.append((subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT), log, log_path))
        print(f"  part {k + 1}/{parts} -> {log_path}")
    failed = False
    for proc, log, log_path in procs:
        if proc.wait() != 0:
            failed = True
            print(f"  part failed, see {log_path}")
        log.close()
    if failed:
        return False
    # Final pass: renders any frame a part missed, then audio, overlay, encode.
    extra_final = extra if "--resume" in extra else [*extra, "--resume"]
    return subprocess.call([sys.executable, RUN, path, *extra_final]) == 0


def main():
    args, extra = parse_args()
    paths = expand(args.inputs)
    if not paths:
        print("No episode configs found.")
        return 1

    episodes, errors = check_all(paths)
    for e in errors:
        print("ERROR", e)
    if errors:
        print(f"\n{len(errors)} config(s) have problems; nothing was rendered.")
        return 1

    for path, cfg, tl in episodes:
        print(f"\n{os.path.relpath(path)}")
        print(tl.summary())
    if args.plan:
        print(f"\n{len(episodes)} episode(s) OK.")
        return 0

    results = []
    for i, (path, cfg, tl) in enumerate(episodes, 1):
        print(f"\n=== [{i}/{len(episodes)}] {cfg['title']}  ({os.path.relpath(path)})", flush=True)
        t0 = time.time()
        ok = render(path, cfg, extra, args.parts)
        results.append((path, cfg, ok, time.time() - t0))
        if not ok and args.stop_on_error:
            break

    print("\nBatch summary")
    out_root = os.path.abspath(option_value(extra, "--out", DEFAULT_OUTPUT_DIR))
    suffix = "_preview" if "--preview" in extra else ""
    for path, cfg, ok, secs in results:
        video = os.path.join(out_root, cfg["slug"], f"{cfg['slug']}{suffix}.mp4")
        status = "ok    " if ok else "FAILED"
        where = video if ok and os.path.exists(video) else path
        print(f"  {status} {secs / 60:6.1f} min  {os.path.relpath(where)}")
    skipped = len(episodes) - len(results)
    if skipped:
        print(f"  ({skipped} not started because of --stop-on-error)")
    return 0 if all(r[2] for r in results) and not skipped else 1


if __name__ == "__main__":
    sys.exit(main())
