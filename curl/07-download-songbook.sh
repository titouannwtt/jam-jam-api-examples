#!/usr/bin/env bash
# Prints the songbook JSON (chords, lyrics, structure) of a finished job.
# Usage: ./07-download-songbook.sh <job_id>
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ID="${1:?usage: $0 <job_id>}"
curl -sS "$API/jobs/$ID/result/songbook" ${AUTH[@]+"${AUTH[@]}"}
echo
