#!/usr/bin/env bash
# Full pipeline: build the Blender project -> render -> sound -> composite/encode.
# Requires: python3.13 with bpy==5.2.3 numpy scipy pillow opencv-python-headless,
# plus ffmpeg on PATH.  (Inside Blender 5.2 you can also run:
#   blender -b -P build.py   and   blender -b -P render.py -- --blend out/cat_chef_pizza.blend)
set -euo pipefail
cd "$(dirname "$0")"
OUT=${OUT:-out}
python build.py --out "$OUT"
python render.py --blend "$OUT/cat_chef_pizza.blend" --frames-dir "$OUT/frames"
python audio.py --timeline "$OUT/timeline.json" --out "$OUT/soundtrack.wav"
python post.py --timeline "$OUT/timeline.json" --frames-dir "$OUT/frames" \
               --audio "$OUT/soundtrack.wav" --out "$OUT/cat_chef_pizza_3d.mp4"
echo "done -> $OUT/cat_chef_pizza_3d.mp4"
