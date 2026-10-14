"""Follows a job with Server-Sent Events instead of polling.

Events: state (job snapshot), done (final job), error (problem), ping (keep-alive).
Usage: python follow_events.py <job_id>
"""
import json
import sys

from jamjam import main, request


def run():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python follow_events.py <job_id>")
    response = request("GET", f"/jobs/{sys.argv[1]}/events", headers={"Accept": "text/event-stream"}, stream=True)

    event, data = "message", []
    for raw in response.iter_lines(decode_unicode=True):
        if raw.startswith("event:"):
            event = raw[6:].strip()
        elif raw.startswith("data:"):
            data.append(raw[5:].lstrip())
        elif raw == "":
            payload = json.loads("\n".join(data)) if data else None
            if event == "state":
                print(f"{payload['phase']} {payload['percent']}%")
            elif event == "done":
                print("done:", payload["id"], ", ".join(a["filename"] for a in payload["artifacts"]))
                return
            elif event == "error":
                raise SystemExit(f"error: {payload['code']} {payload.get('detail') or payload.get('title', '')}")
            event, data = "message", []


main(run)
