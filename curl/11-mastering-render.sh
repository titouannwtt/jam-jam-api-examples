#!/usr/bin/env bash
# Uploads an audio file and starts its mastering on the server (mastering:write).
# Input: WAV, MP3, FLAC, Ogg, AAC, M4A... up to 200 MB and 10 minutes. Output: a 48 kHz WAV.
# Exactly one of: a preset (built-in "builtin:<id>" or the uuid of one of yours) or custom settings.
#
# Usage: ./11-mastering-render.sh <audio> [builtin:balanced | <preset-uuid> | settings.json] [wav-pcm16|wav-f32]
#   ./11-mastering-render.sh song.wav                          built-in preset builtin:balanced
#   ./11-mastering-render.sh song.mp3 builtin:warm             another built-in preset
#   ./11-mastering-render.sh song.wav samples/mastering-settings.json   custom settings, sent inline
#   ./11-mastering-render.sh song.wav 0b3c...-uuid wav-f32     one of your saved presets, 32-bit float
# Prints the job; note its "id" for 12-mastering-poll.sh.
set -euo pipefail
. "$(dirname "$0")/_mastering.sh"
need_key

FILE="${1:?usage: $0 <audio> [builtin:<id> | <preset-uuid> | settings.json] [wav-pcm16|wav-f32]}"
CHOICE="${2:-builtin:balanced}"
FORMAT="${3:-wav-pcm16}"

if [ -f "$CHOICE" ]; then
  CHOICE_FIELD=(-F "settings=<$CHOICE")   # "<file" sends the content of the file as the field value
else
  CHOICE_FIELD=(-F "preset=$CHOICE")
fi

# Idempotency-Key is required. Replaying it with the same body returns the same job, no second charge.
api "$TMP/body" -X POST "$API/mastering/jobs" \
  "${AUTH[@]}" \
  -H "Idempotency-Key: $(idempotency_key)" \
  -F "file=@$FILE" \
  "${CHOICE_FIELD[@]}" \
  -F "format=$FORMAT"
grep -i '^x-mastering-quota' "$HEADERS_FILE" >&2 || true
cat "$TMP/body"
echo
