"""Reads and writes your private notebook (the carnet).

  python notebook.py list     needs scope carnet:read  (draws on the read quota)
  python notebook.py add      needs scope carnet:write (draws on the write quota)
"""
import sys

from jamjam import idempotency_key, main, request


def run():
    action = sys.argv[1] if len(sys.argv) > 1 else None

    if action == "list":
        # Cursor pagination: replay nextCursor until it is null.
        page = request("GET", "/me/songs", params={"limit": 10}).json()
        for s in page["items"]:
            artist = f" - {s['artist']}" if s["artist"] else ""
            print(f"{s['id']}  {s['title']}{artist}  (key {s['key'] or '?'})")
        print(f"more: cursor={page['nextCursor']}" if page["nextCursor"] else "end of list")
    elif action == "add":
        # A public domain song. The id is derived (artist-title slug): posting it twice replaces it.
        song = {
            "title": "Amazing Grace",
            "artist": "John Newton (1779), traditional melody",
            "sections": [
                {
                    "label": "Verse 1",
                    "lines": [{"lyrics": "Amazing grace! how sweet the sound", "chords": [{"offset": 0, "chord": "G"}]}],
                }
            ],
        }
        ack = request("POST", "/me/songs", json={"song": song}, headers={"Idempotency-Key": idempotency_key()}).json()
        print("saved:", ack["id"], ack["updatedAt"])
    else:
        raise SystemExit("usage: python notebook.py list|add")


main(run)
