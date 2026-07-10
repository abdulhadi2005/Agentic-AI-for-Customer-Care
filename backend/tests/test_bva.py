"""
Task 3 — Boundary Value Analysis (BVA) test script.

Tests the extreme edges of the system's constraints:
    - Max file size boundary (just under / at / just over the 25MB limit)
    - Shortest possible voice clip
    - Concurrent/rapid-fire requests hitting the backend at once

NOTE — rapid Start/Stop button clicking is a frontend-only concern (it
exercises wrapper.js's MediaRecorder state machine, not the backend) and
can't be exercised from a Python script. That case is tested manually in
the browser; see the Task 3 report for those results and the isTransitioning
guard added to wrapper.js to fix it.

Expected sample files (place in tests/audio_samples/ — see step 4):
    under_limit.wav     just under MAX_FILE_SIZE_MB (currently 25MB)
    at_limit.wav        at/just under the exact boundary
    over_limit.wav      just over MAX_FILE_SIZE_MB
    shortest_clip.wav    ~0.3-0.5 second clip

Run with the backend already running:
    python test_bva.py
"""

import concurrent.futures

from common import (
    SAMPLES_DIR,
    RESULTS_DIR,
    call_transcribe,
    check_backend_is_up,
    write_markdown_table,
    write_json,
)

MAX_FILE_SIZE_MB = 25  # keep in sync with backend/main.py


def evaluate_size_case(expected_status, result):
    if result["error"] == "MISSING_SAMPLE_FILE":
        return False, "Sample file not found — see step 4 (generate audio samples)."
    if result["error"]:
        return False, f"Request failed: {result['error']}"
    if result["status_code"] == expected_status:
        return True, f"Got expected status {expected_status}."
    return False, f"Expected status {expected_status}, got {result['status_code']}."


def run_size_boundary_tests():
    cases = [
        {
            "label": f"Just under {MAX_FILE_SIZE_MB}MB limit",
            "file": SAMPLES_DIR / "under_limit.wav",
            "expected_status": 200,
        },
        {
            "label": f"At/near {MAX_FILE_SIZE_MB}MB limit",
            "file": SAMPLES_DIR / "at_limit.wav",
            "expected_status": 200,
        },
        {
            "label": f"Just over {MAX_FILE_SIZE_MB}MB limit",
            "file": SAMPLES_DIR / "over_limit.wav",
            "expected_status": 400,
        },
        {
            "label": "Shortest possible clip (~0.3-0.5s)",
            "file": SAMPLES_DIR / "shortest_clip.wav",
            "expected_status": 200,
        },
    ]

    rows = []
    raw = []
    for case in cases:
        result = call_transcribe(case["file"], content_type="audio/wav", timeout=120)
        passed, note = evaluate_size_case(case["expected_status"], result)
        label = "PASS" if passed else "FAIL"
        print(f"[{label}] {case['label']} — {note} (elapsed: {result['elapsed_ms']}ms)")
        rows.append([
            case["label"],
            case["file"].name,
            case["expected_status"],
            result["status_code"],
            result["elapsed_ms"],
            label,
            note,
        ])
        raw.append({"case": case["label"], "result": result, "passed": passed, "note": note})

    return rows, raw


def run_concurrent_request_test(n=5):
    """
    Fires N /transcribe requests at once using the same short sample, to
    check the backend doesn't corrupt state or crash under simultaneous
    load — the closest backend-side equivalent to a user rapid-clicking
    record (which on the frontend is guarded separately in wrapper.js).
    """
    sample = SAMPLES_DIR / "clear_speech.wav"
    print(f"\nFiring {n} concurrent requests using {sample.name}...")

    if not sample.exists():
        print("[FAIL] Sample file not found — see step 4.")
        return [["Concurrent requests", "N/A", "N/A", "N/A", "N/A", "FAIL", "Missing sample file"]], []

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = [executor.submit(call_transcribe, sample, "audio/wav", 60) for _ in range(n)]
        results = [f.result() for f in futures]

    success_count = sum(1 for r in results if r["status_code"] == 200)
    passed = success_count == n
    label = "PASS" if passed else "FAIL"
    note = f"{success_count}/{n} concurrent requests succeeded."
    print(f"[{label}] Concurrent request handling — {note}")

    avg_latency = round(sum(r["elapsed_ms"] or 0 for r in results) / len(results), 1)
    rows = [["Concurrent requests (n=" + str(n) + ")", sample.name, f"{n}/{n} succeed", f"{success_count}/{n}", avg_latency, label, note]]
    raw = [{"case": "concurrent_requests", "results": results, "passed": passed, "note": note}]
    return rows, raw


def main():
    if not check_backend_is_up():
        return

    print("Running BVA size/duration boundary cases...\n")
    size_rows, size_raw = run_size_boundary_tests()

    concurrent_rows, concurrent_raw = run_concurrent_request_test(n=5)

    all_rows = size_rows + concurrent_rows
    write_markdown_table(
        all_rows,
        headers=["Boundary Case", "Sample File", "Expected", "Actual", "Elapsed (ms)", "Result", "Notes"],
        out_path=RESULTS_DIR / "bva_results.md",
    )
    write_json(size_raw + concurrent_raw, RESULTS_DIR / "bva_results.json")

    passed_count = sum(1 for r in size_raw if r["passed"]) + sum(1 for r in concurrent_raw if r["passed"])
    total_count = len(size_raw) + len(concurrent_raw)
    print(f"\n{passed_count}/{total_count} BVA cases passed.")
    print(
        "\nReminder: rapid Start/Stop button clicking must still be tested manually "
        "in the browser — see Task 3 report for that result."
    )


if __name__ == "__main__":
    main()
