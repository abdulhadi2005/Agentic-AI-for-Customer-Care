"""
Task 3 — Equivalence Class Partitioning (ECP) test script.

Partitions audio input into representative classes (valid and invalid) and
runs one sample per class through /transcribe, checking the actual result
against the expected behavior for that class.

Expected sample files (place in tests/audio_samples/ — see step 4):
    clear_speech.wav        valid   — clean spoken audio
    noisy_speech.wav        valid   — speech with heavy background noise
    silence.wav             valid*  — pure silence (valid input, expect empty transcript)
    non_speech_music.wav    valid*  — music/tone, no speech (expect empty transcript)
    corrupted.mp3           invalid — malformed/truncated audio bytes
    wrong_type.txt          invalid — non-audio file content

Run with the backend already running:
    python test_ecp.py
"""

from common import (
    SAMPLES_DIR,
    RESULTS_DIR,
    call_transcribe,
    check_backend_is_up,
    write_markdown_table,
    write_json,
)


def evaluate(case_name, expected, result):
    """
    Returns (passed: bool, note: str) for a single test case, given the
    expectation for that equivalence class and the actual result dict.
    """
    if result["error"] == "MISSING_SAMPLE_FILE":
        return False, "Sample file not found — see step 4 (generate audio samples)."
    if result["error"]:
        return False, f"Request failed: {result['error']}"

    status = result["status_code"]
    body = result["response_body"]

    if expected["status"] != status:
        return False, f"Expected status {expected['status']}, got {status}"

    if expected["status"] == 200:
        text = (body or {}).get("text", None)
        if expected["expect_text"] == "non_empty":
            if text:
                return True, f"Got {len(text)} chars of transcript."
            return False, "Expected non-empty transcript, got empty."
        elif expected["expect_text"] == "empty":
            if not text:
                return True, "Correctly returned empty transcript (no hallucinated text)."
            return False, f"Expected empty transcript, but got: {text[:80]!r}"
    else:
        # Non-200 — just confirm the server responded gracefully, not a hang/crash
        return True, f"Server correctly rejected with {status}: {str(body)[:100]}"

    return False, "Unhandled evaluation branch."


TEST_CASES = [
    {
        "class_name": "Clear speech (valid)",
        "file": SAMPLES_DIR / "clear_speech.wav",
        "content_type": "audio/wav",
        "expected": {"status": 200, "expect_text": "non_empty"},
    },
    {
        "class_name": "Speech + heavy background noise (valid)",
        "file": SAMPLES_DIR / "noisy_speech.wav",
        "content_type": "audio/wav",
        "expected": {"status": 200, "expect_text": "non_empty"},
    },
    {
        "class_name": "Silence / muted audio (valid input, no speech)",
        "file": SAMPLES_DIR / "silence.wav",
        "content_type": "audio/wav",
        "expected": {"status": 200, "expect_text": "empty"},
    },
    {
        "class_name": "Non-speech audio — music/tone (valid input, no speech)",
        "file": SAMPLES_DIR / "non_speech_music.wav",
        "content_type": "audio/wav",
        "expected": {"status": 200, "expect_text": "empty"},
    },
    {
        "class_name": "Corrupted/malformed audio file (invalid)",
        "file": SAMPLES_DIR / "corrupted.mp3",
        "content_type": "audio/mpeg",
        "expected": {"status": 500, "expect_text": None},
    },
    {
        "class_name": "Wrong file type — not audio at all (invalid)",
        "file": SAMPLES_DIR / "wrong_type.txt",
        "content_type": "text/plain",
        "expected": {"status": 400, "expect_text": None},
    },
]


def main():
    if not check_backend_is_up():
        return

    rows = []
    raw_results = []

    print(f"Running {len(TEST_CASES)} ECP test cases...\n")

    for case in TEST_CASES:
        result = call_transcribe(case["file"], content_type=case["content_type"])
        passed, note = evaluate(case["class_name"], case["expected"], result)

        status_label = "PASS" if passed else "FAIL"
        print(f"[{status_label}] {case['class_name']} — {note}")

        rows.append([
            case["class_name"],
            case["file"].name,
            f"status={case['expected']['status']}",
            result["status_code"],
            status_label,
            note,
        ])
        raw_results.append({"case": case["class_name"], "result": result, "passed": passed, "note": note})

    write_markdown_table(
        rows,
        headers=["Input Class", "Sample File", "Expected", "Actual Status", "Result", "Notes"],
        out_path=RESULTS_DIR / "ecp_results.md",
    )
    write_json(raw_results, RESULTS_DIR / "ecp_results.json")

    passed_count = sum(1 for r in raw_results if r["passed"])
    print(f"\n{passed_count}/{len(TEST_CASES)} ECP cases passed.")


if __name__ == "__main__":
    main()
