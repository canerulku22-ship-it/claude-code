#!/usr/bin/env bash
# Downloads the official press photos listed in photos.tsv into out/photos/.
# They are Volkswagen AG and AUDI AG press images, provided for editorial use
# only; their terms don't allow passing them on, so they are never committed.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out/photos
grep -v '^#' photos.tsv | while IFS=$'\t' read -r name url credit desc; do
  [ -s "out/photos/$name.jpg" ] || curl -fsSL --retry 3 --max-time 60 -o "out/photos/$name.jpg" "$url"
done
echo "photos: $(ls out/photos | wc -l) in out/photos"
