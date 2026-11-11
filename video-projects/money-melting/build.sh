#!/usr/bin/env bash
# Full pipeline. Requires: node + playwright (Chromium), ffmpeg, and a Python env with
#   kokoro-onnx faster-whisper soundfile scipy   (only needed for the voiceover step)
# Usage: ./build.sh [--skip-voice] [models_dir]
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules ] || npm install
node tools/build_icons.js
if [ "${1:-}" != "--skip-voice" ]; then
  MODELS="${1:-models}"   # must contain kokoro-v1.0.onnx + voices-v1.0.bin (huggingface.co/fastrtc/kokoro-onnx)
  python tools/voiceover.py "$MODELS"
fi
node tools/render.js cues
python tools/mix.py
node tools/render.js all 4
mkdir -p output
for v in full nomusic; do
  ffmpeg -v error -y -framerate 30 -i out/frames/f_%05d.jpg -i audio/mix_$v.wav -map 0:v -map 1:a \
    -c:v libx264 -preset slow -crf 19 -profile:v high -pix_fmt yuv420p -tune animation \
    -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart \
    output/money_melting_$v.mp4
done
echo "done -> output/"
