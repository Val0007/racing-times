#!/bin/sh
# Copy the Racing Times pipeline from the working project into pipeline/.
# Run from this repo's root:  ./sync_pipeline.sh [path-to-project]   (default: ..)
# Publishes only what the project's .gitignore allows, minus raw articles, wire copies, voice previews and build output.
# Never publishes .env, data/, photos, audio or video.
set -e
SRC="${1:-..}"
LIST=$(mktemp)
git -C "$SRC" ls-files -co --exclude-standard \
  | grep -vE '^site/|^episodes/[^/]+/(build[^/]*/|articles\.jsonl|wire\.json)|^show-pixel/voices/previews/|^show-pixel/build/|^\.env' > "$LIST"
rm -rf pipeline && mkdir pipeline
rsync -a --files-from="$LIST" "$SRC"/ pipeline/
rm -f "$LIST"
if [ -f "$SRC/.env" ]; then
  K=$(grep -o 'ELEVENLABS_API_KEY=.*' "$SRC/.env" | cut -d= -f2 | tr -d '"')
  [ -n "$K" ] && grep -rqF "$K" pipeline && { echo "API key found in pipeline/, aborting"; rm -rf pipeline; exit 1; }
fi
echo "pipeline/: $(find pipeline -type f | wc -l | tr -d ' ') files"
