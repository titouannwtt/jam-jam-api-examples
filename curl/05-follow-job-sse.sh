#!/usr/bin/env bash
# Follows a job with Server-Sent Events instead of polling.
# Events: state, done, error, ping. The stream closes after done or error.
# Usage: ./05-follow-job-sse.sh <job_id>
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ID="${1:?usage: $0 <job_id>}"
curl -sS -N "$API/jobs/$ID/events" ${AUTH[@]+"${AUTH[@]}"} -H "Accept: text/event-stream"
