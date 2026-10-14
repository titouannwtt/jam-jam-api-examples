#!/usr/bin/env bash
# Polls a job until it is finished (done, failed or cancelled).
# Usage: ./04-poll-job.sh <job_id>
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ID="${1:?usage: $0 <job_id>}"
while true; do
  BODY="$(curl -sS "$API/jobs/$ID" ${AUTH[@]+"${AUTH[@]}"})"
  echo "$BODY"
  PHASE="$(echo "$BODY" | sed -n 's/.*"phase" *: *"\([a-z]*\)".*/\1/p')"
  case "$PHASE" in
    done|failed|cancelled|"") break ;;
  esac
  sleep 2
done
