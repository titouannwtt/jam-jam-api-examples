# Sourced by the Mastering scripts, not run directly.
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# A path that sits next to the response body: the header dump of the last call.
HEADERS_FILE="$TMP/headers"

# need_key: the Mastering routes that read or write an account need a key.
need_key() {
  if [ -z "${JAM_JAM_API_KEY:-}" ]; then
    echo "JAM_JAM_API_KEY is not set (see .env.example)." >&2
    exit 1
  fi
}

# api <body-file> <curl args...>: runs curl, keeps the body in <body-file>, the headers in $HEADERS_FILE.
# On HTTP >= 400 it prints a readable explanation and returns 1.
api() {
  local out="$1"
  shift
  local code
  code="$(curl -sS -o "$out" -D "$HEADERS_FILE" -w '%{http_code}' "$@")"
  if [ "$code" -ge 400 ]; then
    explain_error "$code" "$out"
    return 1
  fi
}

# explain_error <status> <body-file>: every error is application/problem+json, `code` is the stable value.
explain_error() {
  local status="$1" body="$2" code retry
  code="$(sed -n 's/.*"code" *: *"\([a-z0-9-]*\)".*/\1/p' "$body" | head -n 1)"
  retry="$(sed -n 's/^[Rr]etry-[Aa]fter: *\([0-9]*\).*/\1/p' "$HEADERS_FILE" | head -n 1)"
  echo "HTTP $status${code:+ $code}" >&2
  case "$status:$code" in
    401:*) echo "The key is missing or invalid. Check JAM_JAM_API_KEY." >&2 ;;
    403:insufficient-scope) echo "This key lacks a scope: mastering:read to follow and download, mastering:write to create, render and delete." >&2 ;;
    403:*premium*) echo "Rendering is not available for your account tier. Depending on your tier, see https://jam-jam.org/app/developers" >&2 ;;
    403:*) echo "Forbidden. Check the scopes of your key and your tier: https://jam-jam.org/app/developers" >&2 ;;
    409:not-ready) echo "The render is not finished yet. Poll it with 12-mastering-poll.sh first." >&2 ;;
    410:*) echo "The result expired: files are kept 24 hours." >&2 ;;
    413:*) echo "File too large: 200 MB at most." >&2 ;;
    422:*) echo "Rejected (invalid settings, idempotency conflict or audio longer than 10 minutes). Details below." >&2 ;;
    429:*) echo "Too many requests or quota spent. Wait ${retry:-a little} s before trying again." >&2 ;;
  esac
  cat "$body" >&2
  echo >&2
}

# json_field <name> <file>: first string value of "name" (the scripts only need top-level fields).
json_field() { sed -n 's/.*"'"$1"'" *: *"\([^"]*\)".*/\1/p' "$2" | head -n 1; }
