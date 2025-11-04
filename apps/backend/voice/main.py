"""
Voice Service - Handles speech recognition and voice commands via Whisper.
"""

import asyncio
import base64
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from common.health import create_health_router
from common.settings import SettingsManager, get_settings_manager
from ai.chroma import ChromaManager
from ai.intent.engine import IntentEngine, IntentPrediction
from voice.server_audio import ServerAudioCapture, get_server_audio
from voice.stt import ModelSize, WhisperSTT

__version__ = "0.2.0"

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_DIR = Path(__file__).parent.parent / "voice_history"
VOICE_HISTORY_DIR = Path(os.getenv("VOICE_HISTORY_DIR", str(DEFAULT_HISTORY_DIR)))
VOICE_HISTORY_FILE = VOICE_HISTORY_DIR / "history.jsonl"
SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"

settings_manager: SettingsManager | None = None
history_lock: asyncio.Lock | None = None
current_voice_model: ModelSize | None = None

# Global STT engine and server audio
stt_engine: WhisperSTT | None = None
server_audio: ServerAudioCapture | None = None
intent_engine: IntentEngine | None = None
semantic_store: ChromaManager | None = None


class TranscribeRequest(BaseModel):
    """Request to transcribe audio data."""

    audio_data: str  # Base64-encoded WAV audio


class TranscribeResponse(BaseModel):
    """Response with transcription."""

    text: str
    duration: float
    language: str | None = None
    language_probability: float | None = None
    model: str | None = None


def _get_settings_manager() -> SettingsManager:
    if settings_manager is None:
        raise RuntimeError("Settings manager not initialized")
    return settings_manager


def _resolve_voice_model(model_name: Any) -> ModelSize:
    if isinstance(model_name, str):
        try:
            return ModelSize(model_name)
        except ValueError:
            logger.warning("Unknown voice model '%s', falling back to 'small'", model_name)
    return ModelSize.SMALL


async def get_stt_engine() -> WhisperSTT:
    global stt_engine, current_voice_model

    manager = _get_settings_manager()
    await manager.refresh()
    model_name = manager.get("voice_model", ModelSize.SMALL.value)
    target_model = _resolve_voice_model(model_name)

    if stt_engine is None or current_voice_model != target_model:
        logger.info("Initializing Whisper STT with model '%s'", target_model.value)
        stt_engine = WhisperSTT(model_size=target_model, device="cpu", compute_type="int8")
        current_voice_model = target_model

    return stt_engine


async def get_intent_engine() -> IntentEngine:
    global intent_engine

    if intent_engine is None:
        raise HTTPException(status_code=503, detail="Intent engine unavailable")

    return intent_engine


def _append_history_line(line: str) -> None:
    with VOICE_HISTORY_FILE.open("a", encoding="utf-8") as file:
        file.write(f"{line}\n")


def _count_history_entries() -> int:
    if not VOICE_HISTORY_FILE.exists():
        return 0
    with VOICE_HISTORY_FILE.open("r", encoding="utf-8") as file:
        return sum(1 for _ in file)


def _cleanup_history_dir() -> None:
    if VOICE_HISTORY_DIR.exists():
        try:
            next(VOICE_HISTORY_DIR.iterdir())
        except StopIteration:
            VOICE_HISTORY_DIR.rmdir()


def _read_history_entries() -> list[dict[str, Any]]:
    if not VOICE_HISTORY_FILE.exists():
        return []

    entries: list[dict[str, Any]] = []
    with VOICE_HISTORY_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:  # pragma: no cover - legacy records
                logger.warning("Skipping malformed voice history entry")
    return entries


async def record_voice_history(entry: dict[str, Any]) -> None:
    if history_lock is None:
        return

    async with history_lock:
        try:
            VOICE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            line = json.dumps(entry, ensure_ascii=True)
            await asyncio.to_thread(_append_history_line, line)
        except Exception as exc:  # pragma: no cover - logging fallback
            logger.error("Failed to record voice history: %s", exc)


async def _record_semantic_voice(text: str, metadata: dict[str, Any]) -> None:
    if semantic_store is None:
        return

    try:
        await semantic_store.store_voice_query(text, metadata=metadata)
    except Exception as exc:  # pragma: no cover - semantic storage best-effort
        logger.debug("Skipping semantic voice storage: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global stt_engine, server_audio, settings_manager, history_lock, current_voice_model, intent_engine, semantic_store

    logger.info("Initializing Voice service...")

    # Load shared settings
    settings_manager = get_settings_manager(SETTINGS_PATH)
    await settings_manager.load()

    # Reset STT engine so model selection happens on first request
    stt_engine = None
    current_voice_model = None

    # Initialize history lock for file writes
    history_lock = asyncio.Lock()
    # Initialize server audio capture
    server_audio = get_server_audio()

    # Initialize intent engine lazily; client created on first use
    intent_engine = IntentEngine(settings_manager=_get_settings_manager())

    try:
        semantic_store = ChromaManager()
    except Exception as exc:  # pragma: no cover - Chroma optional
        semantic_store = None
        logger.debug("Semantic voice history unavailable: %s", exc)

    logger.info("Voice service initialized")

    yield

    # Cleanup
    if server_audio:
        server_audio.cleanup()
    if intent_engine:
        await intent_engine.aclose()
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
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio_data)
    except Exception as e:
        logger.error(f"Failed to decode audio data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {e}") from e

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio data")

    try:
        engine = await get_stt_engine()
        # Transcribe audio
        result = await engine.transcribe_bytes(audio_bytes)

        await record_voice_history(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "upload",
                "duration": result["duration"],
                "language": result.get("language"),
                "text": result["text"],
                "model": current_voice_model.value if current_voice_model else None,
            }
        )

        return TranscribeResponse(
            text=result["text"],
            duration=result["duration"],
            language=result.get("language"),
            language_probability=result.get("language_probability"),
            model=current_voice_model.value if current_voice_model else None,
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
        engine = await get_stt_engine()
        result = await engine.transcribe_bytes(audio_bytes)

        await record_voice_history(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "file-upload",
                "duration": result["duration"],
                "language": result.get("language"),
                "text": result["text"],
                "model": current_voice_model.value if current_voice_model else None,
            }
        )

        return TranscribeResponse(
            text=result["text"],
            duration=result["duration"],
            language=result.get("language"),
            language_probability=result.get("language_probability"),
            model=current_voice_model.value if current_voice_model else None,
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}") from e



# Server-side audio capture endpoints


class ServerAudioDeviceInfo(BaseModel):
    """Server audio device information."""

    index: int
    name: str
    channels: int
    sample_rate: int


class ServerAudioAvailableResponse(BaseModel):
    """Server audio availability response."""

    available: bool
    devices: list[ServerAudioDeviceInfo]
    default_device: int | None = None


class StartRecordingRequest(BaseModel):
    """Request to start server-side recording."""

    device_index: int | None = None


class StartRecordingResponse(BaseModel):
    """Response after starting recording."""

    recording: bool
    message: str


class StopRecordingResponse(BaseModel):
    """Response after stopping recording with transcription."""

    text: str
    duration: float
    language: str | None = None
    language_probability: float | None = None
    audio_duration_seconds: float
    model: str | None = None


class DeleteHistoryResponse(BaseModel):
    """Response after deleting voice history."""

    deleted_entries: int
    message: str


class VoiceHistoryResponse(BaseModel):
    """Voice history export payload."""

    entries: list[dict[str, Any]]
    total_entries: int


class IntentRequest(BaseModel):
    """Request payload for intent classification."""

    text: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class IntentResponse(BaseModel):
    """Response payload returning structured user intent."""

    action: str
    args: dict[str, Any]
    confidence: float
    model: str
    latency_ms: float
    raw_response: str | None = None


class IntentModelsResponse(BaseModel):
    """Available intent models and the currently selected one."""

    active_model: str
    models: list[dict[str, Any]]


class UpdateIntentModelRequest(BaseModel):
    """Request payload for selecting an Ollama intent model."""

    model: str


@app.get("/v1/voice/server-audio/available", response_model=ServerAudioAvailableResponse)
async def get_server_audio_availability():
    """
    Check if server-side audio capture is available.

    Returns:
        Availability status and list of input devices

    Raises:
        HTTPException: 500 if server audio not initialized
    """
    if server_audio is None:
        raise HTTPException(status_code=500, detail="Server audio not initialized")

    try:
        available = server_audio.is_available()
        devices_raw = server_audio.get_devices() if available else []

        devices = [
            ServerAudioDeviceInfo(
                index=d["index"],
                name=d["name"],
                channels=d["channels"],
                sample_rate=d["sample_rate"],
            )
            for d in devices_raw
        ]

        default_device = devices[0].index if available and devices else None

        return ServerAudioAvailableResponse(
            available=available,
            devices=devices,
            default_device=default_device,
        )

    except Exception as e:
        logger.error(f"Failed to check server audio availability: {e}")
        raise HTTPException(
            status_code=500, detail=f"Server audio check failed: {e}"
        ) from e


@app.post("/v1/voice/server-audio/start", response_model=StartRecordingResponse)
async def start_server_recording(request: StartRecordingRequest):
    """
    Start recording from the server microphone.

    Args:
        request: Device index (optional, None for default)

    Returns:
        Recording status

    Raises:
        HTTPException: 400 if already recording, 500 if start fails
    """
    if server_audio is None:
        raise HTTPException(status_code=500, detail="Server audio not initialized")

    try:
        await get_stt_engine()
        if request.device_index is not None:
            server_audio.device_index = request.device_index

        await server_audio.start_recording()

        return StartRecordingResponse(
            recording=True,
            message=f"Recording started from device {server_audio.device_index or 'default'}",
        )

    except RuntimeError as e:
        logger.warning(f"Cannot start recording: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        raise HTTPException(
            status_code=500, detail=f"Recording start failed: {e}"
        ) from e


@app.post("/v1/voice/server-audio/stop", response_model=StopRecordingResponse)
async def stop_server_recording():
    """
    Stop server-side recording and transcribe captured audio.

    Returns:
        Transcription of recorded audio

    Raises:
        HTTPException: 400 if not recording, 500 if transcription fails
    """
    if server_audio is None:
        raise HTTPException(status_code=500, detail="Server audio not initialized")

    try:
        audio_data = await server_audio.stop_recording()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="No audio captured")

        wav_bytes = server_audio.to_wav_bytes(audio_data)

        audio_duration = len(audio_data) / (
            server_audio.sample_rate * server_audio.channels * 2
        )

        engine = await get_stt_engine()
        result = await engine.transcribe_bytes(wav_bytes)

        await record_voice_history(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "server-audio",
                "duration": result["duration"],
                "language": result.get("language"),
                "text": result["text"],
                "model": current_voice_model.value if current_voice_model else None,
                "audio_duration_seconds": audio_duration,
            }
        )

        return StopRecordingResponse(
            text=result["text"],
            duration=result["duration"],
            language=result.get("language"),
            language_probability=result.get("language_probability"),
            audio_duration_seconds=audio_duration,
            model=current_voice_model.value if current_voice_model else None,
        )

    except RuntimeError as e:
        logger.warning(f"Cannot stop recording: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop recording or transcribe: {e}")
        raise HTTPException(
            status_code=500, detail=f"Recording stop failed: {e}"
        ) from e


@app.get("/v1/voice/history", response_model=VoiceHistoryResponse)
async def list_voice_history() -> VoiceHistoryResponse:
    """Return recorded voice history entries."""

    if history_lock is None:
        raise HTTPException(status_code=500, detail="Voice service not initialized")

    async with history_lock:
        try:
            entries = await asyncio.to_thread(_read_history_entries)
        except Exception as exc:  # pragma: no cover - unexpected filesystem errors
            logger.error("Failed to read voice history: %s", exc)
            raise HTTPException(
                status_code=500, detail=f"Failed to read voice history: {exc}"
            ) from exc

    return VoiceHistoryResponse(entries=entries, total_entries=len(entries))


@app.delete("/v1/voice/history", response_model=DeleteHistoryResponse)
async def delete_voice_history() -> DeleteHistoryResponse:
    """Delete persisted voice transcription history."""

    if history_lock is None:
        raise HTTPException(status_code=500, detail="Voice service not initialized")

    async with history_lock:
        try:
            deleted_entries = await asyncio.to_thread(_count_history_entries)

            if VOICE_HISTORY_FILE.exists():
                await asyncio.to_thread(VOICE_HISTORY_FILE.unlink)

            await asyncio.to_thread(_cleanup_history_dir)

            message = (
                "Voice history cleared"
                if deleted_entries
                else "No voice history to delete"
            )

            return DeleteHistoryResponse(
                deleted_entries=deleted_entries,
                message=message,
            )
        except Exception as exc:  # pragma: no cover - unexpected filesystem errors
            logger.error("Failed to delete voice history: %s", exc)
            raise HTTPException(
                status_code=500, detail=f"Failed to delete voice history: {exc}"
            ) from exc


@app.post("/v1/voice/intent", response_model=IntentResponse)
async def classify_intent(request: IntentRequest) -> IntentResponse:
    """Classify a transcript into an actionable intent."""

    engine = await get_intent_engine()

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    prediction: IntentPrediction
    try:
        prediction = await engine.predict_intent(
            text,
            context=request.context or {},
        )
    except Exception as exc:  # pragma: no cover - network issues
        logger.error("Intent classification failed: %s", exc)
        raise HTTPException(status_code=502, detail="Intent service unavailable") from exc

    asyncio.create_task(
        _record_semantic_voice(
            text,
            {
                "action": prediction.action,
                "confidence": prediction.confidence,
                "model": prediction.model,
                "session_id": request.session_id,
                "source": "voice-intent",
            },
        )
    )

    return IntentResponse(
        action=prediction.action,
        args=prediction.args,
        confidence=prediction.confidence,
        model=prediction.model,
        latency_ms=prediction.latency_ms,
        raw_response=prediction.raw_response,
    )


@app.get("/v1/voice/intent/models", response_model=IntentModelsResponse)
async def list_intent_models() -> IntentModelsResponse:
    """List available Ollama models for intent processing."""

    engine = await get_intent_engine()
    model_infos = await engine.list_models()

    manager = _get_settings_manager()
    await manager.refresh()
    active_model = str(manager.get("llm_model", ""))

    model_dicts: list[dict[str, Any]] = [
        {
            "name": info.name,
            "size": info.size,
            "digest": info.digest,
            "modified_at": info.modified_at,
        }
        for info in model_infos
    ]

    return IntentModelsResponse(active_model=active_model, models=model_dicts)


@app.post("/v1/voice/intent/models/select", response_model=IntentModelsResponse)
async def select_intent_model(payload: UpdateIntentModelRequest) -> IntentModelsResponse:
    """Persist the active Ollama model for intent parsing."""

    engine = await get_intent_engine()
    model_infos = await engine.list_models()
    available_names = {info.name for info in model_infos}

    target_model = payload.model.strip()
    if not target_model:
        raise HTTPException(status_code=400, detail="Model name required")

    if available_names and target_model not in available_names:
        raise HTTPException(status_code=404, detail=f"Model '{target_model}' not found")

    manager = _get_settings_manager()
    await manager.set("llm_model", target_model)

    model_dicts: list[dict[str, Any]] = [
        {
            "name": info.name,
            "size": info.size,
            "digest": info.digest,
            "modified_at": info.modified_at,
        }
        for info in model_infos
    ]

    return IntentModelsResponse(active_model=target_model, models=model_dicts)
