#!/usr/bin/env bash
# Shows the quota balances and the scopes of your API key. Needs a key.
set -euo pipefail
. "$(dirname "$0")/_common.sh"

curl -sS "$API/me/usage" ${AUTH[@]+"${AUTH[@]}"}
echo
