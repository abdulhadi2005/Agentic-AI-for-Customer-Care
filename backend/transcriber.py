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
        Returns an empty string if the audio contains no detectable speech
        (silence, pure noise, music, etc.) rather than hallucinated text.

    Raises:
        FileNotFoundError: if the given path doesn't exist.
        RuntimeError: if transcription fails for any other reason.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Segments with a high no_speech_prob are the model's own signal that it
    # doesn't believe there's speech in that segment — filtering on this
    # prevents silence/background-noise/music inputs from returning
    # hallucinated text (a known Whisper failure mode on non-speech audio).
    NO_SPEECH_THRESHOLD = 0.6

    try:
        segments, info = _model.transcribe(str(path), beam_size=5, language="en")
        logger.info(
            f"Detected language '{info.language}' "
            f"(confidence {info.language_probability:.2f})"
        )

        kept_parts = []
        dropped_count = 0
        for segment in segments:
            if segment.no_speech_prob is not None and segment.no_speech_prob >= NO_SPEECH_THRESHOLD:
                dropped_count += 1
                continue
            text = segment.text.strip()
            if text:
                kept_parts.append(text)

        if dropped_count:
            logger.info(f"Dropped {dropped_count} low-confidence/no-speech segment(s).")

        full_text = " ".join(kept_parts).strip()
        if not full_text:
            logger.info("No speech detected in audio — returning empty transcript.")
        return full_text

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