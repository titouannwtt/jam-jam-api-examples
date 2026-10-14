"""Shared helpers for the examples. Python 3.10+, requests."""
from __future__ import annotations

import os
import re
import sys
import time
import uuid
from pathlib import Path

import requests

API = "https://jam-jam.org/api/v1"

# Anonymous mode: the Authorization header is only sent when JAM_JAM_API_KEY is set.
_KEY = os.environ.get("JAM_JAM_API_KEY")
HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}

FINAL_PHASES = ("done", "failed", "cancelled")


class ApiError(Exception):
    """Every API error is application/problem+json (RFC 9457): `code` is the stable value to test."""

    def __init__(self, response: requests.Response):
        problem = None
        if "json" in response.headers.get("Content-Type", ""):
            try:
                problem = response.json()
            except ValueError:
                pass
        self.status = response.status_code
        self.problem = problem
        retry_after = response.headers.get("Retry-After")
        self.retry_after = int(retry_after) if retry_after and retry_after.isdigit() else None
        code = f" {problem['code']}" if problem and problem.get("code") else ""
        detail = (
            (problem or {}).get("detail")
            or (problem or {}).get("title")
            or "not a Jam Jam error response (the anti-bot protection may block calls without an API key)"
        )
        super().__init__(f"HTTP {self.status}{code}: {detail}")


def request(method: str, path: str, **kwargs) -> requests.Response:
    headers = {**HEADERS, **kwargs.pop("headers", {})}
    response = requests.request(method, f"{API}{path}", headers=headers, timeout=60, **kwargs)
    if not response.ok:
        raise ApiError(response)
    return response


def idempotency_key() -> str:
    """A fresh key per write: replaying the same key returns the same result, no duplicate."""
    return str(uuid.uuid4())


def create_job(**kwargs) -> dict:
    """POST /jobs with json=... (text or url) or data=... and files=... (upload)."""
    response = request("POST", "/jobs", headers={"Idempotency-Key": idempotency_key()}, **kwargs)
    print(
        f"quota remaining: {response.headers.get('X-Quota-Remaining', 'n/a')} "
        f"(window {response.headers.get('X-Quota-Window', 'n/a')})"
    )
    return response.json()


def wait_for_job(job_id: str) -> dict:
    """Polls GET /jobs/{id}, waiting as long as the server asks (Retry-After, in seconds)."""
    while True:
        response = request("GET", f"/jobs/{job_id}")
        job = response.json()
        print(f"{job['phase']} {job['percent']}%")
        if job["phase"] in FINAL_PHASES:
            return job
        time.sleep(int(response.headers.get("Retry-After") or 2))


def download_result(job_id: str, directory: str = "out") -> Path:
    """Saves the main result file in ./out. Results are kept 24 h after the job was created (then 410)."""
    response = request("GET", f"/jobs/{job_id}/result")
    disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?", disposition, re.IGNORECASE)
    raw = (match.group(1) or match.group(2)) if match else f"{job_id}.bin"
    name = Path(requests.utils.unquote(raw)).name
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    path.write_bytes(response.content)
    return path


def main(function) -> None:
    """Runs a script's main function and prints API errors readably."""
    try:
        function()
    except (ApiError, ValueError, OSError, requests.RequestException) as err:
        print(err, file=sys.stderr)
        if getattr(err, "retry_after", None):
            print(f"Retry after {err.retry_after} s.", file=sys.stderr)
        sys.exit(1)
