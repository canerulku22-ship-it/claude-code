#!/usr/bin/env bash
# Builds golf-r-vs-s3.mp4: fetches the press photos, narrates with Chatterbox,
# renders every frame of film.html (timed to the narration), synthesises the soundtrack, then
# muxes and masters with ffmpeg.
#
# Needs: node + playwright (with Chromium), python3 + numpy + scipy, ffmpeg.
# The first run installs Chatterbox (PyTorch, a few GB) into .venv and
# downloads its model from Hugging Face.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out

./fetch_photos.sh   # official VW / Audi press photos -> out/photos/ (never committed)
[ -d node_modules/three ] || npm ci --no-audit --no-fund

VENV=${VENV:-.venv}
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  # setuptools<81 keeps pkg_resources, which Chatterbox's audio watermarker needs
  "$VENV/bin/pip" install -q chatterbox-tts==0.1.7 "setuptools<81"
fi
# plain HTTPS downloads from Hugging Face rather than its Xet transfer service
HF_HUB_DISABLE_XET=1 "$VENV/bin/python" voiceover.py

node render.mjs video out/video.mp4 "${WORKERS:-4}"
python3 audio.py out/soundtrack.wav

ffmpeg -y -loglevel error -i out/video.mp4 -i out/soundtrack.wav \
  -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 20 -tune animation -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -af "loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89:level=false" \
  -movflags +faststart -shortest golf-r-vs-s3.mp4

echo "done: $(pwd)/golf-r-vs-s3.mp4"
