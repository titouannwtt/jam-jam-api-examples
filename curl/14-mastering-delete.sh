#!/usr/bin/env bash
# Deletes a mastering job (cancels it if running and erases its files) or a saved preset.
# Both need mastering:write and answer 204 with no body. Presets already used by a job do not
# affect it: the settings are copied when the file is uploaded.
# Usage: ./14-mastering-delete.sh job <job_id>
#        ./14-mastering-delete.sh preset <preset_id>
set -euo pipefail
. "$(dirname "$0")/_mastering.sh"
need_key

KIND="${1:?usage: $0 job|preset <id>}"
ID="${2:?usage: $0 job|preset <id>}"
case "$KIND" in
  job) URL="$API/mastering/jobs/$ID" ;;
  preset) URL="$API/mastering/presets/$ID" ;;
  *) echo "usage: $0 job|preset <id>" >&2; exit 1 ;;
esac
api "$TMP/body" -X DELETE "$URL" "${AUTH[@]}"
echo "deleted $KIND $ID"
