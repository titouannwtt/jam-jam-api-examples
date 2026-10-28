"""Helpers for the Mastering examples. Builds on jamjam.py (same key, same error type)."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

from jamjam import ApiError, idempotency_key, request

FINAL_STATUSES = ("done", "failed", "cancelled", "expired")
DEVELOPERS = "https://jam-jam.org/app/developers"


def explain(err: ApiError) -> str:
    """A readable message for the errors a Mastering call can answer. `code` is the stable value to test."""
    problem = err.problem or {}
    code = problem.get("code", "")
    if err.status == 401:
        hint = "The key is missing or invalid. Check JAM_JAM_API_KEY."
    elif err.status == 403 and code == "insufficient-scope":
        hint = "This key lacks a scope: mastering:read to follow and download, mastering:write to create, render and delete."
    elif err.status == 403:
        hint = f"Not allowed for your key or tier. Depending on your tier, see {DEVELOPERS}"
    elif err.status == 409 and code == "not-ready":
        hint = "The render is not finished yet."
    elif err.status == 410:
        hint = "The result expired: files are kept 24 hours."
    elif err.status == 413:
        hint = "File too large: 200 MB at most."
    elif err.status == 429:
        hint = f"Too many requests or quota spent. Wait {err.retry_after or 'a little'} s before trying again."
    else:
        hint = ""
    lines = [str(err)]
    if hint:
        lines.append(hint)
    for issue in problem.get("errors", []):  # 422 invalid-settings: one entry per refused value
        lines.append(f"  {issue.get('pointer')}: {issue.get('code')} {issue.get('message', '')}".rstrip())
    return "\n".join(lines)


def need_key() -> None:
    if not os.environ.get("JAM_JAM_API_KEY"):
        raise SystemExit("JAM_JAM_API_KEY is not set (see .env.example).")


def load_settings(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_preset(name: str, settings: dict) -> dict:
    """POST /mastering/presets (mastering:write). Idempotency-Key is required."""
    return request(
        "POST", "/mastering/presets", json={"name": name, "settings": settings},
        headers={"Idempotency-Key": idempotency_key()},
    ).json()


def start_render(path: str | Path, preset: str | None = None, settings: dict | None = None,
                 audio_format: str = "wav-pcm16", key: str | None = None) -> dict:
    """POST /mastering/jobs (mastering:write). Exactly one of `preset` and `settings`.

    `preset` is "builtin:<id>" or the uuid of one of your presets. `key` lets a caller replay the
    same Idempotency-Key after a network error: the same upload then returns the same job.
    """
    if (preset is None) == (settings is None):
        raise ValueError("give exactly one of preset and settings")
    fields = {"format": audio_format}
    if preset is not None:
        fields["preset"] = preset
    else:
        fields["settings"] = json.dumps(settings)
    with open(path, "rb") as handle:
        response = request(
            "POST", "/mastering/jobs", data=fields, files={"file": (Path(path).name, handle)},
            headers={"Idempotency-Key": key or idempotency_key()},
        )
    remaining = response.headers.get("X-Mastering-Quota-Remaining")
    if remaining is not None:
        print(f"mastering quota remaining: {remaining}", file=sys.stderr)
    return response.json()


def wait_for_render(job_id: str) -> dict:
    """Polls GET /mastering/jobs/{id} (mastering:read), waiting as long as the server asks (Retry-After)."""
    while True:
        response = request("GET", f"/mastering/jobs/{job_id}")
        job = response.json()
        print(f"{job['status']} {round((job.get('progress') or 0) * 100)}%", file=sys.stderr)
        if job["status"] in FINAL_STATUSES:
            return job
        time.sleep(int(response.headers.get("Retry-After") or 2))


def download_master(job_id: str, directory: str | Path = "out") -> Path:
    """Saves the mastered WAV as <name>-master.wav. Kept 24 h (then 410); downloading again is free."""
    with request("GET", f"/mastering/jobs/{job_id}/result", stream=True) as response:
        disposition = response.headers.get("Content-Disposition", "")
        match = re.search(r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?", disposition, re.IGNORECASE)
        raw = (match.group(1) or match.group(2)) if match else f"{job_id}-master.wav"
        name = Path(unquote(raw)).name
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        path = out / name
        with open(path, "wb") as handle:
            for chunk in response.iter_content(1 << 20):
                handle.write(chunk)
    return path


def describe_report(job: dict) -> str:
    """One line with the integrated loudness and true peak before and after (null = silence)."""
    report = job.get("report")
    if not report:
        return "no report"
    b, a = report["before"], report["after"]
    return (f"integrated LUFS {b['integratedLufs']} -> {a['integratedLufs']}, "
            f"true peak dBTP {b['truePeakDbtp']} -> {a['truePeakDbtp']}")


def run(function) -> None:
    """Runs a script's main function and prints Mastering errors readably."""
    try:
        function()
    except ApiError as err:
        print(explain(err), file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)
