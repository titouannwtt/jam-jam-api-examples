#!/usr/bin/env bash
# Saves a named preset on your account (mastering:write). Open to any account; 50 presets at most.
# The eight modules are required and every value must sit on its step: read the ranges on
# 09-mastering-capabilities.sh. A bad value answers 422 invalid-settings with one entry per problem.
# Usage: ./10-mastering-create-preset.sh ["name"] [settings.json]
#        default settings: samples/mastering-settings.json
set -euo pipefail
. "$(dirname "$0")/_mastering.sh"
need_key

NAME="${1:-My warm preset}"
SETTINGS="${2:-$ROOT/samples/mastering-settings.json}"
NAME="${NAME//\"/}"   # the name goes in a JSON string: drop quotes and backslashes
NAME="${NAME//\\/}"

# Idempotency-Key is required: 16 to 80 characters among A-Za-z0-9_-.
api "$TMP/body" -X POST "$API/mastering/presets" \
  "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(idempotency_key)" \
  -d '{"name":"'"$NAME"'","settings":'"$(cat "$SETTINGS")"'}'
cat "$TMP/body"
echo
echo "preset id (use it as the preset of a render): $(json_field id "$TMP/body")" >&2
