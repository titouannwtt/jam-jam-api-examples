#!/usr/bin/env bash
# Downloads the mastered WAV of a finished job into ./out/ (<name>-master.wav). Needs mastering:read.
# Downloading again is free; the file is kept 24 hours (then 410 expired), 409 not-ready before the end.
# Usage: ./13-mastering-download.sh <job_id>
set -euo pipefail
. "$(dirname "$0")/_mastering.sh"
need_key

ID="${1:?usage: $0 <job_id>}"
api "$TMP/audio" "$API/mastering/jobs/$ID/result" "${AUTH[@]}"
NAME="$(sed -n 's/.*filename="\{0,1\}\([^";]*\)"\{0,1\}.*/\1/p' "$HEADERS_FILE" | tr -d '\r' | head -n 1)"
NAME="$(basename "${NAME:-$ID-master.wav}")"
mkdir -p "$ROOT/out"
mv "$TMP/audio" "$ROOT/out/$NAME"
ls -l "$ROOT/out/$NAME"
