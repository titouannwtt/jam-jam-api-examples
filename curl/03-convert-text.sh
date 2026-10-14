#!/usr/bin/env bash
# Starts a conversion from raw ChordPro text (application/json, no upload).
# Usage: ./03-convert-text.sh [output]     default output: txt
set -euo pipefail
. "$(dirname "$0")/_common.sh"

OUTPUT="${1:-txt}"

curl -sS -D /dev/stderr -X POST "$API/jobs" \
  ${AUTH[@]+"${AUTH[@]}"} \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(idempotency_key)" \
  -d '{
    "text": "{title: Amazing Grace}\n{key: G}\n[G]Amazing grace! how [G7]sweet the [C]sound,\nThat [G]saved a [Em]wretch like [D]me!",
    "inputFormat": "chordpro",
    "output": "'"${OUTPUT}"'"
  }'
echo
