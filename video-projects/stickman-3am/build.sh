#!/usr/bin/env bash
# Full pipeline for the 3AM stickman video. Needs node + playwright (Chromium), ffmpeg, and a Python env with
#   chatterbox-tts faster-whisper soundfile scipy   (chatterbox only for the voice step)
# Usage: ./build.sh [--skip-voice]
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules ] || npm install
node tools/build_icons.js
[ "${1:-}" = "--skip-voice" ] || python tools/voiceover.py --takes 2 --exaggeration 0.42 --cfg 0.5
node tools/render.js cues
python tools/mix.py
node tools/render.js all 4
mkdir -p output
for v in full nomusic; do
  ffmpeg -v error -y -framerate 30 -i out/frames/f_%05d.jpg -i audio/mix_$v.wav -map 0:v -map 1:a \
    -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p \
    -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart \
    output/3am_rules_$v.mp4
done
echo "done -> output/"
