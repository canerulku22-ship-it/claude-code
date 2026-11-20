#!/bin/bash
# Encode the rendered frames with each audio mix: uncut (swearing), bleeped, and no music.
cd "$(dirname "$0")/.."
mkdir -p output out
for v in full bleep nomusic; do
  nice -n 5 ffmpeg -v error -y -framerate 30 -i out/frames/f_%05d.jpg -i audio/mix_$v.wav -map 0:v -map 1:a \
    -c:v libx264 -preset slow -crf 22 -maxrate 6M -bufsize 12M -profile:v high -pix_fmt yuv420p \
    -af "loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,alimiter=limit=0.6:attack=1:release=60:level=false" \
    -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart out/tmp_uk_born_scunthorpe_$v.mp4 \
    && mv out/tmp_uk_born_scunthorpe_$v.mp4 output/uk_born_scunthorpe_$v.mp4 && echo "ENCODED $v"
done
