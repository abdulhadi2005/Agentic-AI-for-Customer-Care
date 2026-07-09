import logging
from pathlib import Path
from faster_whisper import WhisperModel

logger = logging.getLogger("transcriber")

MODEL_SIZE = "base"     
DEVICE = "cpu"          
COMPUTE_TYPE = "int8"   

# ---- Load model once at import time -----------------------------------
logger.info(f"Loading faster-whisper model '{MODEL_SIZE}' on {DEVICE}...")
_model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
logger.info("Model loaded and ready.")

def transcribe(audio_path: str) -> str:
    """
    Transcribe an audio file to plain text.

    Args:
        audio_path: path to an audio file on disk (wav, mp3, webm, m4a, etc.
                    faster-whisper uses ffmpeg under the hood, so most
                    common formats work without pre-conversion).

    Returns:
        The transcribed text as a single string (segments joined together).

    Raises:
        FileNotFoundError: if the given path doesn't exist.
        RuntimeError: if transcription fails for any other reason.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        segments, info = _model.transcribe(str(path), beam_size=5, language="en")
        logger.info(
            f"Detected language '{info.language}' "
            f"(confidence {info.language_probability:.2f})"
        )

        full_text = " ".join(segment.text.strip() for segment in segments)
        return full_text.strip()

    except Exception as e:
        logger.error(f"Transcription failed for {audio_path}: {e}")
        raise RuntimeError(f"Transcription failed: {e}") from e


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <path-to-audio-file>")
        sys.exit(1)

    result = transcribe(sys.argv[1])
    print("\n--- Transcript ---")
    print(result)