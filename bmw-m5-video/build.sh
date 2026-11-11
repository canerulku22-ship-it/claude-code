#!/usr/bin/env bash
# Builds bmw-m5.mp4: synthesises the narration, renders every frame of
# film.html, synthesises the soundtrack, then muxes and masters with ffmpeg.
#
# Needs: node + playwright (with Chromium), python3 + numpy + scipy, ffmpeg.
# The narration downloads Kokoro-82M and Chatterbox from Hugging Face on the
# first run and installs Chatterbox (PyTorch, a few GB) into .venv.
# VOICE=kokoro skips Chatterbox and uses the lighter Kokoro narration.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out

[ -d node_modules/kokoro-js ] || npm install --no-audit --no-fund
# NODE_USE_ENV_PROXY lets Node's fetch use HTTPS_PROXY where one is set
NODE_USE_ENV_PROXY=1 node voiceover.mjs                 # Kokoro lines -> out/vo_ref/

if [ "${VOICE:-chatterbox}" = kokoro ]; then
  rm -rf out/vo && cp -r out/vo_ref out/vo
else
  VENV=${VENV:-.venv}
  if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
    # setuptools<81 keeps pkg_resources, which Chatterbox's audio watermarker needs
    "$VENV/bin/pip" install -q chatterbox-tts==0.1.7 "setuptools<81"
  fi
  # plain HTTPS downloads from Hugging Face rather than its Xet transfer service
  HF_HUB_DISABLE_XET=1 "$VENV/bin/python" voiceover.py  # Chatterbox lines -> out/vo/
fi

node render.mjs video out/video.mp4 "${WORKERS:-4}"
python3 audio.py out/soundtrack.wav

ffmpeg -y -loglevel error -i out/video.mp4 -i out/soundtrack.wav \
  -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 20 -tune animation -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
  -movflags +faststart -shortest bmw-m5.mp4

echo "done: $(pwd)/bmw-m5.mp4"
