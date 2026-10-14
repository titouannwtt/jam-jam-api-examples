#!/usr/bin/env bash
# Lists the input and output formats this server serves. No API key needed.
# Optional: ./01-list-formats.sh chordpro   (only the outputs possible from that input)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

curl -sS "$API/formats${1:+?input=$1}"
echo
