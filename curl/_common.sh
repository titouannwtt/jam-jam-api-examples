# Sourced by the other scripts, not run directly.
# Anonymous mode: the Authorization header is only sent when JAM_JAM_API_KEY is set.
API="https://jam-jam.org/api/v1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTH=()
if [ -n "${JAM_JAM_API_KEY:-}" ]; then
  AUTH=(-H "Authorization: Bearer ${JAM_JAM_API_KEY}")
fi
# A fresh key per request: replaying the same key returns the same job instead of a duplicate.
idempotency_key() { echo "example-$(date +%s)-$RANDOM$RANDOM"; }
