"""
Voice Service - Handles speech recognition and voice commands via Whisper.
"""

import base64
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from common.health import create_health_router
from voice.stt import ModelSize, WhisperSTT

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

# Global STT engine
stt_engine: WhisperSTT | None = None


class TranscribeRequest(BaseModel):
    """Request to transcribe audio data."""

    audio_data: str  # Base64-encoded WAV audio


class TranscribeResponse(BaseModel):
    """Response with transcription."""

    text: str
    duration: float
    language: str | None = None
    language_probability: float | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global stt_engine

    logger.info("Initializing Voice service...")

    # Initialize STT engine (lazy load model)
    stt_engine = WhisperSTT(model_size=ModelSize.SMALL, device="cpu", compute_type="int8")

    logger.info("Voice service initialized")

    yield

    # Cleanup
    logger.info("Voice service shutdown")


app = FastAPI(
    title="WomCast Voice Service",
    description="Speech recognition and voice command processing",
    version=__version__,
    lifespan=lifespan,
)

create_health_router(app, "voice-service", __version__)


@app.post("/v1/voice/stt", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio to text using Whisper STT.

    Args:
        request: Audio data (base64-encoded WAV)

    Returns:
        Transcription with text and metadata

    Raises:
        HTTPException: 400 if audio invalid, 500 if STT fails
    """
    if stt_engine is None:
        raise HTTPException(status_code=500, detail="STT engine not initialized")

    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio_data)
    except Exception as e:
        logger.error(f"Failed to decode audio data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {e}") from e

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio data")

    try:
        # Transcribe audio
        result = await stt_engine.transcribe_bytes(audio_bytes)

        return TranscribeResponse(
            text=result["text"],
            duration=result["duration"],
            language=result.get("language"),
            language_probability=result.get("language_probability"),
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}") from e


@app.post("/v1/voice/stt/file", response_model=TranscribeResponse)
async def transcribe_file(file: UploadFile):
    """
    Transcribe uploaded audio file to text.

    Args:
        file: Audio file (WAV, MP3, etc.)

    Returns:
        Transcription with text and metadata

    Raises:
        HTTPException: 400 if file invalid, 500 if STT fails
    """
    if stt_engine is None:
        raise HTTPException(status_code=500, detail="STT engine not initialized")

    try:
        # Read file content
        audio_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}") from e

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        # Transcribe audio
        result = await stt_engine.transcribe_bytes(audio_bytes)

        return TranscribeResponse(
            text=result["text"],
            duration=result["duration"],
            language=result.get("language"),
            language_probability=result.get("language_probability"),
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}") from e

