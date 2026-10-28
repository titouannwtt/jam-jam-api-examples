#!/usr/bin/env bash
# Polls a mastering job until it is finished (done, failed, cancelled or expired), honouring Retry-After.
# When done, prints the loudness measured before and after (report). Needs mastering:read.
# Usage: ./12-mastering-poll.sh <job_id>
set -euo pipefail
. "$(dirname "$0")/_mastering.sh"
need_key

ID="${1:?usage: $0 <job_id>}"
while true; do
  api "$TMP/body" "$API/mastering/jobs/$ID" "${AUTH[@]}"
  STATUS="$(json_field status "$TMP/body")"
  echo "status: $STATUS"
  case "$STATUS" in
    done) cat "$TMP/body"; echo; break ;;
    failed|cancelled|expired) cat "$TMP/body" >&2; echo >&2; exit 1 ;;
  esac
  WAIT="$(sed -n 's/^[Rr]etry-[Aa]fter: *\([0-9]*\).*/\1/p' "$HEADERS_FILE" | head -n 1)"
  sleep "${WAIT:-2}"
done
