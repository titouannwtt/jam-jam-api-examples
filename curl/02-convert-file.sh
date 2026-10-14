#!/usr/bin/env bash
# Uploads a file (multipart/form-data) and starts a conversion job.
# Usage: ./02-convert-file.sh [output] [file] [inputFormat]
#   defaults: pdf-chords, samples/amazing-grace.cho, chordpro
# Prints the job as JSON; keep its "id" for the next scripts.
set -euo pipefail
. "$(dirname "$0")/_common.sh"

OUTPUT="${1:-pdf-chords}"
FILE="${2:-$ROOT/samples/amazing-grace.cho}"
INPUT="${3:-chordpro}"

curl -sS -D /dev/stderr -X POST "$API/jobs" \
  ${AUTH[@]+"${AUTH[@]}"} \
  -H "Idempotency-Key: $(idempotency_key)" \
  -F "file=@${FILE}" \
  -F "inputFormat=${INPUT}" \
  -F "output=${OUTPUT}"
echo
