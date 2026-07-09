# Voice Transcription Wrapper

A browser-based voice input widget connected to a local FastAPI backend that performs
speech-to-text transcription using `faster-whisper`. Supports both live microphone
recording and audio file upload, with the resulting transcript rendered directly in
the UI.

Backend pipeline: **Frontend → FastAPI → faster-whisper → JSON response → rendered
transcript.**

---

## Project Structure

```
project/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── wrapper.js
├── backend/
│   ├── main.py             # FastAPI app, /transcribe and /health endpoints
│   ├── transcriber.py       # transcribe(audio_path) -> str, model abstraction
│   ├── requirements.txt
│   └── uploads/             # temp storage for incoming audio (auto-created, gitignored)
├── report/
│   └── Task2_Report.docx
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

1. Open a terminal and navigate into the `backend/` folder:

   ```bash
   cd backend
   ```

2. (Recommended) Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the server:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   On first run, `faster-whisper` will download the model weights (`base` model by
   default). You should see:

   ```
   INFO:     Loading faster-whisper model 'base' on cpu...
   INFO:     Model loaded and ready.
   INFO:     Application startup complete.
   ```

5. Verify it's running by opening **http://localhost:8000/docs** in your browser
   this is FastAPI's auto-generated interactive API documentation, where you can
   test the `/transcribe` endpoint directly by uploading a sample audio file.

> **Note:** Always run `uvicorn` from *inside* the `backend/` folder, since it
> looks for `main.py` relative to your current directory.

---

## Frontend Setup

No build step required, it's plain HTML/CSS/JS.

1. Open `frontend/index.html` directly in a browser, **or** serve it with a
   simple local server (recommended, avoids some browser `file://` restrictions
   on microphone access):

   ```bash
   cd frontend
   python -m http.server 5500
   ```

   Then visit **http://localhost:5500**.

2. Make sure the backend (step above) is already running on port 8000
   `wrapper.js` is currently hardcoded to POST to `http://localhost:8000/transcribe`.

---

## Using the Widget

**Option 1: Record from microphone**
1. Click **Start Recording** and grant microphone permission when prompted.
2. Speak, the live waveform will animate.
3. Click **Stop Recording**. The clip is automatically sent to the backend.
4. Status changes to "Transcribing…", then the transcript appears in the
   **Transcript** panel once ready.

**Option 2:  Upload an audio file**
1. Click the dropzone (or drag a file onto it) and select an audio file
   (`.mp3`, `.wav`, `.webm`, etc.).
2. The file is automatically sent to the backend.
3. The transcript appears in the same panel once processing completes.

All activity: chunk capture, upload progress, backend responses, and errors
is logged in the console panel at the bottom of the widget for debugging.