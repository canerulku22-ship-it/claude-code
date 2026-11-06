#!/bin/bash
# resumable render: 12 chunks of 300 frames, 4 workers; finished chunks are skipped
cd "$(dirname "$0")"
work() { for c in $(seq $1 4 11); do
  if grep -q CHUNKDONE out2/log$c.txt 2>/dev/null; then continue; fi
  node render.js chunk $((c*300)) $(((c+1)*300)) out2/c$c.mp4 > out2/log$c.txt 2>&1
done; }
for w in 0 1 2 3; do work $w & done; wait
echo ALLDONE
