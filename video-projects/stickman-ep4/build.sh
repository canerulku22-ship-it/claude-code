#!/usr/bin/env bash
# Full pipeline for episode 4 (glow + solid A/B). Needs node + playwright (Chromium), ffmpeg, and a Python env with
#   kokoro-onnx faster-whisper soundfile scipy   (kokoro only for the voice step)
# Usage: ./build.sh [--skip-voice] [models_dir]   models_dir holds kokoro-v1.0.onnx + voices-v1.0.bin
# Narration is a stock American-English Kokoro voice (am_michael) at a slower, horror pace.
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules ] || npm install
if [ "${1:-}" != "--skip-voice" ]; then
  python tools/voiceover.py --engine kokoro --voice am_michael --speed 0.9 --takes 4 --models "${1:-models}"
  python tools/regap.py
fi
node tools/render.js cues
python tools/mix.py
mkdir -p output
for style in glow solid; do
  STYLE=$style node tools/render.js all 4
  for v in full nomusic; do
    ffmpeg -v error -y -framerate 30 -i out/frames_$style/f_%05d.jpg -i audio/mix_$v.wav -map 0:v -map 1:a \
      -c:v libx264 -preset slow -crf 22 -maxrate 6M -bufsize 12M -profile:v high -pix_fmt yuv420p \
      -af "loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,alimiter=limit=0.6:attack=1:release=60:level=false" \
      -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart \
      output/last_bus_${style}_$v.mp4
  done
done
echo "done -> output/"
