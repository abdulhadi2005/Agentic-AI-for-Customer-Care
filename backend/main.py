import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
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
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Rejected upload with content type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {file.content_type}",
        )

    suffix = Path(file.filename).suffix or ".wav"
    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"

    try:
        contents = await file.read()

        size_mb = len(contents) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({size_mb:.1f} MB). Max is {MAX_FILE_SIZE_MB} MB.",
            )

        with open(temp_path, "wb") as f:
            f.write(contents)

        logger.info(f"Saved upload to {temp_path} ({size_mb:.2f} MB)")

        # ---- Run transcription ----
        text = transcribe(str(temp_path))
        logger.info(f"Transcription complete: {len(text)} characters returned.")

        return {"text": text}

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