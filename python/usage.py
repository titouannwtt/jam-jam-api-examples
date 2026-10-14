"""Shows your quota balances and the scopes of your API key. Needs JAM_JAM_API_KEY."""
from jamjam import main, request


def run():
    usage = request("GET", "/me/usage").json()
    print("owner:", usage["ownerKind"], "| scopes:", ", ".join(usage["scopes"]) or "(none)")
    for name in ("conversion", "read", "write", "stems"):
        bucket = usage.get(name)
        if bucket:
            limit = bucket["limit"] if bucket["limit"] is not None else "unlimited"
            print(f"{name}: {bucket['used']} / {limit} ({bucket['window']}, resets {bucket['resetsAt']})")


main(run)
