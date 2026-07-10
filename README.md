# Voice Transcription Wrapper

A browser-based voice input widget connected to a local FastAPI backend that performs
speech-to-text transcription using [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper).
Supports live microphone recording and audio file upload, with the transcript rendered
directly in the UI.

Built as part of the AIRC/AIST Agentic AI internship — Week 1 deliverable
(Task 1: frontend widget, Task 2: transcription backend, Task 3: testing & validation).

**Pipeline:** `Browser (mic / file) → wrapper.js → FastAPI → faster-whisper → JSON → transcript rendered`

---

## Project Structure

```
project/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── wrapper.js           # Self-contained recording/upload widget
├── backend/
│   ├── main.py               # FastAPI app — /health and /transcribe endpoints
│   ├── transcriber.py        # transcribe(audio_path) -> str, model wrapper
│   ├── requirements.txt      # Version-locked (pip freeze)
│   └── tests/
│       ├── common.py         # Shared test helper (POST + result logging)
│       ├── test_ecp.py       # Equivalence Class Partitioning tests
│       ├── test_bva.py       # Boundary Value Analysis tests
│       ├── audio_samples/    # Test audio fixtures (speech, silence, noise, etc.)
│       └── results/          # Generated .md / .json test reports
├── report.docx                # Task write-up (gitignored — not pushed to GitHub)
└── README.md
```

---

## Prerequisites

- Python 3.9+
- A working microphone and a modern browser (Chrome/Edge/Firefox — all support
  `getUserMedia` and `MediaRecorder`)
- ~1–2 GB free disk space for the Whisper model weights (downloaded automatically
  on first run)

---

## Backend Setup

1. Navigate into the `backend/` folder:

   ```bash
   cd backend
   ```

2. (Recommended) Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

3. Install dependencies (pinned exact versions, tested on Python 3.10):

   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   On first run, `faster-whisper` downloads the model weights (`base` model,
   `int8` compute, CPU). You should see:

   ```
   INFO:     Loading faster-whisper model 'base' on cpu...
   INFO:     Model loaded and ready.
   INFO:     Application startup complete.
   ```

5. Verify it's running by opening **http://localhost:8000/docs** — FastAPI's
   interactive API docs, where you can test `/transcribe` directly by uploading
   a sample audio file.

> **Note:** Always run `uvicorn` from *inside* the `backend/` folder — it looks
> for `main.py` relative to your current directory.

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Simple readiness check |
| `/transcribe` | POST | Accepts `multipart/form-data` with field `file`; returns `{ text, timing_ms }` |

`timing_ms` breaks down `upload_receive`, `model_inference`, and `total` latency
for each request — useful for performance monitoring.

**Limits & validation:** max file size 25 MB; only audio content types are accepted
(`audio/wav`, `audio/mpeg`, `audio/webm`, `audio/mp4`, `audio/ogg`, etc.) — anything
else returns `400`.

---

## Frontend Setup

No build step required — plain HTML/CSS/JS.

1. Serve it with a simple local server (recommended over opening the file
   directly, to avoid `file://` restrictions on mic access):

   ```bash
   cd frontend
   python -m http.server 5500
   ```

   Then visit **http://localhost:5500**.

2. Make sure the backend is already running on port 8000 — `wrapper.js` is
   hardcoded to POST to `http://localhost:8000/transcribe`.

### Using the Widget

**Option 1 — Record from microphone**
1. Click **Start Recording** and grant microphone permission.
2. Speak — the live waveform animates.
3. Click **Stop Recording**. The clip is sent to the backend automatically.
4. Status shows "Transcribing…", then the transcript appears in the panel.

**Option 2 — Upload an audio file**
1. Click the dropzone (or drag a file onto it) and select an audio file.
2. It's sent to the backend automatically; the transcript appears once ready.

All activity (chunk capture, upload progress, backend responses, errors) is
logged in the console panel at the bottom of the widget for debugging.

---

## Running the Tests (Task 3)

With the backend running (`uvicorn main:app --reload` in `backend/`), open a
second terminal in `backend/`:

```bash
cd backend
python tests/test_ecp.py     # Equivalence Class Partitioning
python tests/test_bva.py     # Boundary Value Analysis
```

Each script checks `/health` first, then POSTs each sample file in
`tests/audio_samples/` to `/transcribe` and writes results to
`tests/results/` as both Markdown (report-ready table) and JSON (raw data).

**Current results: 11/11 tests passing** (6/6 ECP, 5/5 BVA).

| Suite | Cases covered |
|---|---|
| ECP | Clear speech, noisy speech, silence, non-speech/music, corrupted file, wrong file type |
| BVA | Just under / at / over the 25MB limit, shortest possible clip, 5 concurrent requests |

---

## Design Notes

- **`int8` compute type / `base` model** — chosen for CPU-only inference with a
  good speed/accuracy tradeoff, no GPU required.
- **Silence/non-speech filtering** — Whisper can hallucinate text on silence or
  music. Segments with `no_speech_prob ≥ 0.6` are dropped so these inputs
  correctly return an empty transcript instead of fabricated text.
- **Threadpool offloading** — transcription is CPU-bound and synchronous;
  running it inline would block FastAPI's event loop and stall other requests
  (even `/health`). It's offloaded via `run_in_threadpool` so the server stays
  responsive under concurrent load.
- **Temp file cleanup** — every upload is deleted in a `finally` block, even on
  failure, so no audio ever accumulates on disk.
- **Frontend click-lock** — an `isTransitioning` guard prevents rapid
  Start/Stop clicks from spawning overlapping recording streams (a race
  condition where `isRecording` wasn't set until after the async mic
  permission prompt resolved).

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError` on startup | Make sure your virtual environment is activated and `pip install -r requirements.txt` completed without errors |
| Mic permission blocked | Serve the frontend over `http://localhost` (not `file://`) |
| `500 Transcription engine failed` | Check the audio file isn't corrupted/empty; see backend console logs |
| Frontend can't reach backend | Confirm backend is running on port 8000 and check for CORS errors in the browser console |
