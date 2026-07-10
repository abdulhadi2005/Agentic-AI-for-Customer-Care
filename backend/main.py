import logging
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from transcriber import transcribe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="Transcription Pipeline API",
    description="Backend for the Agentic AI Task 2 transcription wrapper.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(tempfile.gettempdir()) / "transcription_wrapper_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = 25
ALLOWED_CONTENT_TYPES = {
    "audio/wav", "audio/x-wav", "audio/webm", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/ogg", "audio/x-m4a",
}

@app.get("/health")
def health_check():
    """Simple readiness check — confirms the server is up and reachable."""
    return {"status": "ok"}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts an audio file upload, runs it through the transcription core,
    and returns the resulting text.

    Frontend sends this as multipart/form-data with the field name "file".

    Response includes a `timing_ms` breakdown (upload_receive, model_inference,
    total) for latency profiling — this has negligible overhead and is safe
    to leave in for production monitoring.

    NOTE: transcribe() is a synchronous, CPU-bound call (faster-whisper on
    CPU). Calling it directly inside this async def would block FastAPI's
    single event loop thread, so any other concurrent request (even a plain
    /health check) would stall behind it until inference finished. We
    offload it to FastAPI's threadpool via run_in_threadpool so the event
    loop stays free to accept and process other requests concurrently.
    """
    request_start = time.perf_counter()

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Rejected upload with content type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {file.content_type}",
        )

    suffix = Path(file.filename).suffix or ".wav"
    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"

    try:
        receive_start = time.perf_counter()
        contents = await file.read()

        size_mb = len(contents) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({size_mb:.1f} MB). Max is {MAX_FILE_SIZE_MB} MB.",
            )

        with open(temp_path, "wb") as f:
            f.write(contents)
        receive_ms = (time.perf_counter() - receive_start) * 1000

        logger.info(f"Saved upload to {temp_path} ({size_mb:.2f} MB)")

        # ---- Run transcription off the event loop thread ----
        inference_start = time.perf_counter()
        text = await run_in_threadpool(transcribe, str(temp_path))
        inference_ms = (time.perf_counter() - inference_start) * 1000

        total_ms = (time.perf_counter() - request_start) * 1000

        logger.info(
            f"Transcription complete: {len(text)} characters returned. "
            f"[receive={receive_ms:.0f}ms, inference={inference_ms:.0f}ms, total={total_ms:.0f}ms]"
        )

        return {
            "text": text,
            "timing_ms": {
                "upload_receive": round(receive_ms, 1),
                "model_inference": round(inference_ms, 1),
                "total": round(total_ms, 1),
            },
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail="Audio file could not be processed.")
    except RuntimeError as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail="Transcription engine failed.")
    except Exception as e:
        logger.exception("Unexpected error during transcription request.")
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")
    finally:
        if temp_path.exists():
            temp_path.unlink()
            logger.info(f"Cleaned up temp file: {temp_path}")
