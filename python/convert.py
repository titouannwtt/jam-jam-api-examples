"""Converts text, a file or a web page, waits for the job, saves the result and prints the songbook.

  python convert.py text [file.cho]            ChordPro text (default: the sample song)
  python convert.py file <path> [--input id]   file upload (multipart/form-data)
  python convert.py url <https://...>          a web page you have the right to convert

Options: --output <id> (default pdf-chords), --input <id> (default chordpro for text).
Valid ids come from GET /formats (served: true). Run list_formats.py.
"""
import argparse
from pathlib import Path

from jamjam import create_job, download_result, main, request, wait_for_job

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "amazing-grace.cho"


def run():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["text", "file", "url"])
    parser.add_argument("source", nargs="?")
    parser.add_argument("--output", default="pdf-chords")
    parser.add_argument("--input", dest="input_format")
    args = parser.parse_args()

    if args.mode == "text":
        text = Path(args.source or SAMPLE).read_text(encoding="utf-8")
        job = create_job(json={"text": text, "inputFormat": args.input_format or "chordpro", "output": args.output})
    elif args.source is None:
        parser.error(f"{args.mode} needs a source")
    elif args.mode == "url":
        body = {"url": args.source, "output": args.output}
        if args.input_format:
            body["inputFormat"] = args.input_format
        job = create_job(json=body)
    else:
        fields = {"output": args.output}
        if args.input_format:
            fields["inputFormat"] = args.input_format
        with open(args.source, "rb") as handle:
            job = create_job(data=fields, files={"file": (Path(args.source).name, handle)})

    print("job:", job["id"], f"({job['inputFormat']} -> {job['outputFormat']}), expires {job['expiresAt']}")
    job = wait_for_job(job["id"])

    if job["phase"] != "done":
        problem = job.get("problem") or {}
        raise SystemExit(f"not done: {job['phase']} {problem.get('code', '')} {problem.get('detail') or problem.get('title', '')}")
    print("artifacts:", ", ".join(f"{a['filename']} ({a['mediaType']}, {a['bytes']} bytes)" for a in job["artifacts"]))
    print("saved:", download_result(job["id"]))

    # The canonical songbook JSON is available after any successful job, whatever the output.
    song = request("GET", f"/jobs/{job['id']}/result/songbook").json()["songs"][0]
    print(f"songbook: \"{song['title']}\", {len(song.get('sections', []))} sections")


main(run)
