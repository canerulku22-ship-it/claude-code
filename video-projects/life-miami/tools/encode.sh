#!/bin/bash
# Encode the rendered frames with each audio mix: bleeped (main, monetisable), uncut, and no music.
cd "$(dirname "$0")/.."
mkdir -p output out
# refuse to encode a partial render: every frame must exist and be a complete JPEG
python3 - <<'PY' || exit 1
import json, math, os, sys
n = math.ceil(json.load(open('audio/timing.json'))['duration'] * 30)
bad = [i for i in range(n) if not os.path.exists(f'out/frames/f_{i:05d}.jpg') or open(f'out/frames/f_{i:05d}.jpg', 'rb').read()[-2:] != b'\xff\xd9']
print(f'{n} frames expected, {len(bad)} missing/truncated', bad[:10]); sys.exit(1 if bad else 0)
PY
for v in bleep full nomusic; do
  nice -n 5 ffmpeg -v error -y -framerate 30 -i out/frames/f_%05d.jpg -i audio/mix_$v.wav -map 0:v -map 1:a \
    -c:v libx264 -preset slow -crf 20 -maxrate 6M -bufsize 12M -profile:v high -pix_fmt yuv420p \
    -af "loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,alimiter=limit=0.6:attack=1:release=60:level=false" \
    -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart out/tmp_born_miami_$v.mp4 \
    && mv out/tmp_born_miami_$v.mp4 output/born_miami_$v.mp4 && echo "ENCODED $v"
done
