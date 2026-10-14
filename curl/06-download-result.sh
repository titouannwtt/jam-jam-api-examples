#!/usr/bin/env bash
# Downloads the main result file of a finished job into ./out/ (name from Content-Disposition).
# Results are available for 24 hours after the job was created (then 410).
# Usage: ./06-download-result.sh <job_id> [artifact_id]
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ID="${1:?usage: $0 <job_id> [artifact_id]}"
mkdir -p "$ROOT/out"
cd "$ROOT/out"
curl -sS --fail -L -OJ ${AUTH[@]+"${AUTH[@]}"} "$API/jobs/$ID/result${2:+?artifact=$2}"
ls -l "$ROOT/out"
