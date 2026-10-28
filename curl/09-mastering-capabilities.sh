#!/usr/bin/env bash
# Reads the live contract of the Mastering engine: ranges and steps of the eight settings, loudness
# targets, built-in presets, limits (200 MB, 600 s), and, with a key, renderAllowed and your quota.
# Works without a key (renderAllowed is then false); sending the key adds your own balance.
# Usage: ./09-mastering-capabilities.sh
set -euo pipefail
. "$(dirname "$0")/_mastering.sh"

api "$TMP/body" "$API/mastering/capabilities" ${AUTH[@]+"${AUTH[@]}"}
cat "$TMP/body"
echo
