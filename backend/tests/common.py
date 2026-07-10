"""
Shared helpers for the Task 3 test scripts (test_ecp.py, test_bva.py).

Both scripts POST audio files to the running FastAPI backend's /transcribe
endpoint and record structured pass/fail results, so the output can be
dropped straight into the Task 3 report.

Requires the backend to already be running:
    cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

Requires the `requests` package (test-only dependency, not part of the
backend's own runtime requirements.txt):
    pip install requests
"""

import json
import mimetypes
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
TRANSCRIBE_URL = f"{BASE_URL}/transcribe"
HEALTH_URL = f"{BASE_URL}/health"

SAMPLES_DIR = Path(__file__).parent / "audio_samples"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def check_backend_is_up():
    """Fail fast with a clear message if the backend isn't reachable."""
    try:
        r = requests.get(HEALTH_URL, timeout=5)
        if r.status_code == 200:
            return True
    except requests.exceptions.ConnectionError:
        pass
    print(
        "\n[!] Backend not reachable at " + BASE_URL + "\n"
        "    Start it first: cd backend && uvicorn main:app --reload --port 8000\n"
    )
    return False


def call_transcribe(file_path, content_type=None, timeout=60):
    """
    POST a file to /transcribe and return a structured result dict.

    Never raises on HTTP error responses (400/500) — those are valid,
    expected outcomes for several ECP/BVA cases, not test-harness failures.
    Only raises if the request itself couldn't be made at all (e.g. backend
    down, which check_backend_is_up() should have already caught).
    """
    file_path = Path(file_path)
    guessed_type = content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    result = {
        "file": file_path.name,
        "sent_content_type": guessed_type,
        "status_code": None,
        "response_body": None,
        "elapsed_ms": None,
        "error": None,
    }

    if not file_path.exists():
        result["error"] = "MISSING_SAMPLE_FILE"
        return result

    start = time.perf_counter()
    try:
        with open(file_path, "rb") as f:
            resp = requests.post(
                TRANSCRIBE_URL,
                files={"file": (file_path.name, f, guessed_type)},
                timeout=timeout,
            )
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 1)
        result["status_code"] = resp.status_code
        try:
            result["response_body"] = resp.json()
        except ValueError:
            result["response_body"] = resp.text
    except requests.exceptions.RequestException as e:
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 1)
        result["error"] = str(e)

    return result


def write_markdown_table(rows, headers, out_path):
    """Write a simple markdown table for direct inclusion in the report."""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {out_path}")


def write_json(data, out_path):
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
