#!/usr/bin/env bash
# Downloads the official press photos listed in photos.tsv into out/photos/.
# They are AUDI AG and BMW AG press images, provided for editorial use only;
# their terms don't allow passing them on, so they are never committed.
# BMW's originals are about 8000 px wide, so they're scaled down to 2400 px.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out/photos
grep -v '^#' photos.tsv | while IFS=$'\t' read -r name url credit desc; do
  dst="out/photos/$name.jpg"
  [ -s "$dst" ] && continue
  curl -fsSL --retry 3 --max-time 120 -o "$dst.part" "$url"
  w=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$dst.part")
  if [ "$w" -gt 2400 ]; then
    ffmpeg -nostdin -v error -y -i "$dst.part" -vf "scale=2400:-2:flags=lanczos" -q:v 2 "$dst" && rm "$dst.part"
  else
    mv "$dst.part" "$dst"
  fi
done
echo "photos: $(ls out/photos | wc -l) in out/photos"
