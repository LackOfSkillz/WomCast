"""
Voice Service - Handles speech recognition and voice commands via Whisper.
"""

import base64
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from common.health import create_health_router
from voice.server_audio import ServerAudioCapture, get_server_audio
from voice.stt import ModelSize, WhisperSTT

__version__ = "0.2.0"

logger = logging.getLogger(__name__)

# Global STT engine and server audio
stt_engine: WhisperSTT | None = None
server_audio: ServerAudioCapture | None = None


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
    global stt_engine, server_audio

    logger.info("Initializing Voice service...")

    # Initialize STT engine (lazy load model)
    stt_engine = WhisperSTT(model_size=ModelSize.SMALL, device="cpu", compute_type="int8")

    # Initialize server audio capture
    server_audio = get_server_audio()

    logger.info("Voice service initialized")

    yield

    # Cleanup
    if server_audio:
        server_audio.cleanup()
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



# Server-side audio capture endpoints


class ServerAudioDeviceInfo(BaseModel):
    ""Server audio device information.""

    index: int
    name: str
    channels: int
    sample_rate: int


class ServerAudioAvailableResponse(BaseModel):
    ""Server audio availability response.""

    available: bool
    devices: list[ServerAudioDeviceInfo]
    default_device: int | None = None


class StartRecordingRequest(BaseModel):
    ""Request to start server-side recording.""

    device_index: int | None = None


class StartRecordingResponse(BaseModel):
    ""Response after starting recording.""

    recording: bool
    message: str


class StopRecordingResponse(BaseModel):
    ""Response after stopping recording with transcription.""

    text: str
    duration: float
    language: str | None = None
    language_probability: float | None = None
    audio_duration_seconds: float


@app.get(""/v1/voice/server-audio/available"", response_model=ServerAudioAvailableResponse)
async def get_server_audio_availability():
    ""
    Check if server-side audio capture is available.

    Returns:
        Availability status and list of input devices

    Raises:
        HTTPException: 500 if server audio not initialized
    ""
    if server_audio is None:
        raise HTTPException(status_code=500, detail=""Server audio not initialized"")

    try:
        available = server_audio.is_available()
        devices_raw = server_audio.get_devices() if available else []

        devices = [
            ServerAudioDeviceInfo(
                index=d[""index""],
                name=d[""name""],
                channels=d[""channels""],
                sample_rate=d[""sample_rate""],
            )
            for d in devices_raw
        ]

        # Try to find default device
        default_device = None
        if available and devices:
            default_device = devices[0].index

        return ServerAudioAvailableResponse(
            available=available, devices=devices, default_device=default_device
        )

    except Exception as e:
        logger.error(f""Failed to check server audio availability: {e}"")
        raise HTTPException(
            status_code=500, detail=f""Server audio check failed: {e}""
        ) from e


@app.post(""/v1/voice/server-audio/start"", response_model=StartRecordingResponse)
async def start_server_recording(request: StartRecordingRequest):
    ""
    Start recording from server microphone.

    Args:
        request: Device index (optional, None for default)

    Returns:
        Recording status

    Raises:
        HTTPException: 400 if already recording, 500 if start fails
    ""
    if server_audio is None:
        raise HTTPException(status_code=500, detail=""Server audio not initialized"")

    if stt_engine is None:
        raise HTTPException(status_code=500, detail=""STT engine not initialized"")

    try:
        # Update device index if provided
        if request.device_index is not None:
            server_audio.device_index = request.device_index

        await server_audio.start_recording()

        return StartRecordingResponse(
            recording=True,
            message=f""Recording started from device {server_audio.device_index or 'default'}"",
        )

    except RuntimeError as e:
        logger.warning(f""Cannot start recording: {e}"")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f""Failed to start recording: {e}"")
        raise HTTPException(
            status_code=500, detail=f""Recording start failed: {e}""
        ) from e


@app.post(""/v1/voice/server-audio/stop"", response_model=StopRecordingResponse)
async def stop_server_recording():
    ""
    Stop recording and transcribe captured audio.

    Returns:
        Transcription of recorded audio

    Raises:
        HTTPException: 400 if not recording, 500 if transcription fails
    ""
    if server_audio is None:
        raise HTTPException(status_code=500, detail=""Server audio not initialized"")

    if stt_engine is None:
        raise HTTPException(status_code=500, detail=""STT engine not initialized"")

    try:
        # Stop recording and get audio
        audio_data = await server_audio.stop_recording()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail=""No audio captured"")

        # Convert to WAV format
        wav_bytes = server_audio.to_wav_bytes(audio_data)

        # Calculate audio duration
        audio_duration = len(audio_data) / (
            server_audio.sample_rate * server_audio.channels * 2
        )

        # Transcribe
        result = await stt_engine.transcribe_bytes(wav_bytes)

        return StopRecordingResponse(
            text=result[""text""],
            duration=result[""duration""],
            language=result.get(""language""),
            language_probability=result.get(""language_probability""),
            audio_duration_seconds=audio_duration,
        )

    except RuntimeError as e:
        logger.warning(f""Cannot stop recording: {e}"")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f""Failed to stop recording or transcribe: {e}"")
        raise HTTPException(
            status_code=500, detail=f""Recording stop failed: {e}""
        ) from e
