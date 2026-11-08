#!/usr/bin/env bash
# Builds bmw-m5.mp4: renders every frame of film.html, synthesises the
# soundtrack, then muxes and masters both with ffmpeg.
# Needs: node + playwright (with Chromium), python3 + numpy + scipy, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out

node render.mjs video out/video.mp4 "${WORKERS:-4}"
python3 audio.py out/soundtrack.wav

ffmpeg -y -loglevel error -i out/video.mp4 -i out/soundtrack.wav \
  -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 20 -tune animation -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -movflags +faststart -shortest bmw-m5.mp4

echo "done: $(pwd)/bmw-m5.mp4"
