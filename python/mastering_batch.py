"""Masters every audio file of a folder with one preset, one after the other.

  python mastering_batch.py <input_dir> [--out out] [--preset builtin:balanced | --settings settings.json]
                            [--format wav-pcm16|wav-pcm24|wav-f32]

Files are sent one at a time (the API keeps one active job and three waiting per account). A file whose
<name>-master.wav is already in the output folder is skipped, so the script can be run again after an
interruption. On a 429 it waits the Retry-After the server gives, then retries the same file once with
the same Idempotency-Key (only if the wait is 5 minutes or less; a spent quota ends the file with its message). On a 403 (tier or scope) or a long 429 it stops: the next files would fail the same way.
Needs JAM_JAM_API_KEY with mastering:read and mastering:write.
"""
import argparse
import sys
import time
from pathlib import Path

from jamjam import ApiError, idempotency_key
from mastering_lib import (describe_report, download_master, explain, load_settings, need_key, run,
                           start_render, wait_for_render)

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".oga", ".opus", ".aac", ".m4a"}
MAX_BYTES = 200 * 1024 * 1024
MAX_WAIT = 300  # seconds: a longer Retry-After means a spent quota (a day, a week), not a busy moment


def master_one(path: Path, out: Path, preset, settings, audio_format: str) -> str:
    key = idempotency_key()
    for attempt in (1, 2):
        try:
            job = start_render(path, preset=preset, settings=settings, audio_format=audio_format, key=key)
            break
        except ApiError as err:
            if err.status == 429 and attempt == 1 and err.retry_after and err.retry_after <= MAX_WAIT:
                print(f"  429, waiting {err.retry_after} s", file=sys.stderr)
                time.sleep(err.retry_after)
                continue
            raise
    job = wait_for_render(job["id"])
    if job["status"] != "done":
        error = job.get("error") or {}
        return f"failed ({job['status']} {error.get('code', '')})"
    saved = download_master(job["id"], out)
    return f"{saved.name} ({describe_report(job)})"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_dir")
    parser.add_argument("--out", default="out")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--preset")
    choice.add_argument("--settings")
    parser.add_argument("--format", default="wav-pcm16", choices=["wav-pcm16", "wav-pcm24", "wav-f32"])
    args = parser.parse_args()

    need_key()
    settings = load_settings(args.settings) if args.settings else None
    preset = args.preset or (None if settings else "builtin:balanced")
    out = Path(args.out)
    files = sorted(p for p in Path(args.input_dir).iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)
    if not files:
        raise SystemExit(f"no audio file in {args.input_dir}")

    done = skipped = failed = 0
    for path in files:
        if (out / f"{path.stem}-master.wav").exists():
            print(f"skip {path.name} (already mastered)")
            skipped += 1
        elif path.stat().st_size > MAX_BYTES:
            print(f"skip {path.name} (over 200 MB)")
            failed += 1
        else:
            print(f"master {path.name}")
            try:
                result = master_one(path, out, preset, settings, args.format)
            except ApiError as err:
                print(explain(err), file=sys.stderr)
                if err.status in (401, 403) or (err.status == 429 and (err.retry_after or 0) > MAX_WAIT):
                    raise SystemExit("stopping: the next files would be refused the same way (rerun later, finished files are skipped).")
                failed += 1
                continue
            print("  ", result)
            if result.startswith("failed"):
                failed += 1
            else:
                done += 1
    print(f"done {done}, skipped {skipped}, failed {failed}")
    if failed:
        sys.exit(1)


run(main)
