"""Masters one audio file on the Jam Jam server and saves the result in ./out.

  python mastering.py capabilities                       limits, ranges, built-in presets (no key needed)
  python mastering.py presets                            your presets and the built-in ids
  python mastering.py create-preset "My preset" [settings.json]
  python mastering.py master <audio> [--preset builtin:warm | --settings settings.json] [--format wav-f32]
  python mastering.py delete job|preset <id>

Input: WAV, MP3, FLAC, Ogg, AAC, M4A... 200 MB and 10 minutes at most. Output: a 48 kHz WAV.
`master` without --preset or --settings uses builtin:balanced. Settings default to
../samples/mastering-settings.json for create-preset. Needs JAM_JAM_API_KEY except for capabilities.
Whether your tier may render is shown by `capabilities` (renderAllowed) and the 403 explained below.
"""
import argparse
import json
from pathlib import Path

from jamjam import request
from mastering_lib import (create_preset, describe_report, download_master, load_settings, need_key,
                           run, start_render, wait_for_render)

SAMPLE_SETTINGS = Path(__file__).resolve().parent.parent / "samples" / "mastering-settings.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    sub.add_parser("presets")
    p_create = sub.add_parser("create-preset")
    p_create.add_argument("name")
    p_create.add_argument("settings", nargs="?", default=str(SAMPLE_SETTINGS))
    p_master = sub.add_parser("master")
    p_master.add_argument("audio")
    choice = p_master.add_mutually_exclusive_group()
    choice.add_argument("--preset")
    choice.add_argument("--settings")
    p_master.add_argument("--format", default="wav-pcm16", choices=["wav-pcm16", "wav-pcm24", "wav-f32"])
    p_delete = sub.add_parser("delete")
    p_delete.add_argument("kind", choices=["job", "preset"])
    p_delete.add_argument("id")
    args = parser.parse_args()

    if args.command == "capabilities":
        caps = request("GET", "/mastering/capabilities").json()
        print(f"engine {caps['engineVersion']}, {caps['sampleRate']} Hz, {caps['maxUploadBytes'] // 2**20} MB, "
              f"{caps['maxDurationSeconds']} s, formats {', '.join(caps['formats'])}")
        print("built-in presets:", ", ".join(p["id"] for p in caps["builtinPresets"]))
        print("targets:", ", ".join(f"{t['id']} ({t['lufs']} LUFS)" for t in caps["targets"]))
        for module in caps["modules"]:
            print(f"  {module['id']}: {module['min']}..{module['max']} step {module['step']} ({module['unit']})")
        print("renderAllowed:", caps["renderAllowed"], "| quota:", json.dumps(caps["quota"]))
        return

    need_key()
    if args.command == "presets":
        listing = request("GET", "/mastering/presets").json()
        print("built-in:", ", ".join(listing["builtin"]))
        for preset in listing["presets"]:
            print(f"{preset['id']}  {preset['name']}")
    elif args.command == "create-preset":
        preset = create_preset(args.name, load_settings(args.settings))
        print("preset id:", preset["id"])
    elif args.command == "delete":
        request("DELETE", f"/mastering/{'jobs' if args.kind == 'job' else 'presets'}/{args.id}")
        print("deleted", args.kind, args.id)
    else:
        settings = load_settings(args.settings) if args.settings else None
        preset = args.preset or (None if settings else "builtin:balanced")
        job = start_render(args.audio, preset=preset, settings=settings, audio_format=args.format)
        print("job:", job["id"], "expires", job["expiresAt"])
        job = wait_for_render(job["id"])
        if job["status"] != "done":
            error = job.get("error") or {}
            raise SystemExit(f"not done: {job['status']} {error.get('code', '')} {error.get('detail', '')}".strip())
        print(describe_report(job))
        print("saved:", download_master(job["id"]))


run(main)
