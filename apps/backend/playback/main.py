"""
Playback Service - Manages media playback via Kodi bridge or mpv.
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from common.health import create_health_router

from .kodi_client import KodiClient, KodiConfig, PlayerState
from .cec_routes import router as cec_router

__version__ = "0.1.0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WomCast Playback Service",
    description="Media playback control via Kodi/mpv",
    version=__version__,
)

_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
)
allowed_origins = (
    os.getenv("PLAYBACK_CORS_ORIGINS")
    or os.getenv("WOMCAST_CORS_ORIGINS")
    or _default_origins
)
cors_origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

create_health_router(app, "playback-service", __version__)

# Kodi configuration from environment
kodi_config = KodiConfig(
    host=os.getenv("KODI_HOST", "localhost"),
    port=int(os.getenv("KODI_PORT", "9090")),
    username=os.getenv("KODI_USERNAME"),
    password=os.getenv("KODI_PASSWORD"),
)


class PlayRequest(BaseModel):
    """Request to play a media file."""

    file_path: str = Field(..., description="Path to the media file")


class SeekRequest(BaseModel):
    """Request to seek to a position."""

    position_seconds: float = Field(..., ge=0, description="Position in seconds")


class VolumeRequest(BaseModel):
    """Request to set volume."""

    volume: int = Field(..., ge=0, le=100, description="Volume level (0-100)")


class VolumeAdjustRequest(BaseModel):
    """Request to adjust volume by delta."""

    delta: int = Field(
        ...,
        ge=-100,
        le=100,
        description="Relative volume change (-100 to 100)",
    )


SUPPORTED_INPUT_ACTIONS: set[str] = {
    "up",
    "down",
    "left",
    "right",
    "select",
    "back",
    "context",
    "info",
    "home",
    "menu",
    "play_pause",
}


@app.post("/v1/play", response_model=dict[str, bool])
async def play_media(request: PlayRequest):
    """Start playback of a media file.

    Args:
        request: Play request with file path

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        # Test connection first
        if not await client.ping():
            raise HTTPException(status_code=503, detail="Kodi not available")

        success = await client.play_file(request.file_path)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start playback")

        return {"success": True}


@app.post("/v1/stop", response_model=dict[str, bool])
async def stop_playback():
    """Stop all active players.

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        success = await client.stop()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to stop playback")

        return {"success": True}


@app.post("/v1/pause", response_model=dict[str, bool])
async def pause_playback():
    """Pause/unpause the active player.

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        success = await client.pause()
        if not success:
            raise HTTPException(
                status_code=404, detail="No active player to pause"
            )

        return {"success": True}


@app.post("/v1/seek", response_model=dict[str, bool])
async def seek_playback(request: SeekRequest):
    """Seek to a specific position.

    Args:
        request: Seek request with position

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        success = await client.seek(request.position_seconds)
        if not success:
            raise HTTPException(status_code=404, detail="No active player to seek")

        return {"success": True}


@app.get("/v1/player/state", response_model=PlayerState)
async def get_player_state():
    """Get current player state.

    Returns:
        Current player state with position, duration, etc.
    """
    async with KodiClient(kodi_config) as client:
        return await client.get_player_state()


@app.post("/v1/volume", response_model=dict[str, bool])
async def set_volume(request: VolumeRequest):
    """Set the volume level.

    Args:
        request: Volume request with level

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        success = await client.set_volume(request.volume)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set volume")

        return {"success": True}


@app.get("/v1/volume", response_model=dict[str, int])
async def get_volume():
    """Get current volume level.

    Returns:
        Volume level (0-100)
    """
    async with KodiClient(kodi_config) as client:
        volume = await client.get_volume()
        return {"volume": volume}


@app.post("/v1/volume/adjust", response_model=dict[str, int])
async def adjust_volume(request: VolumeAdjustRequest):
    """Adjust the volume by a relative delta."""
    async with KodiClient(kodi_config) as client:
        current_volume = await client.get_volume()
        target_volume = max(0, min(100, current_volume + request.delta))

        success = await client.set_volume(target_volume)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to adjust volume")

        return {"volume": target_volume}


@app.post("/v1/input/{action}", response_model=dict[str, bool])
async def send_input_action(action: str):
    """Send a remote input action to Kodi."""

    normalized = action.strip().lower()
    if normalized not in SUPPORTED_INPUT_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported input action '{action}'")

    async with KodiClient(kodi_config) as client:
        try:
            delivered = await client.input_action(normalized)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not delivered:
            raise HTTPException(status_code=500, detail="Failed to send input action")

        return {"success": True}


@app.post("/v1/application/quit", response_model=dict[str, bool])
async def quit_application():
    """Close Kodi so the kiosk can return to the web UI."""

    async with KodiClient(kodi_config) as client:
        success = await client.application_quit()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to quit Kodi")

        return {"success": True}


@app.get("/v1/ping", response_model=dict[str, bool])
async def ping_kodi():
    """Test connection to Kodi.

    Returns:
        Kodi availability status
    """
    async with KodiClient(kodi_config) as client:
        available = await client.ping()
        return {"available": available}


@app.get("/v1/subtitles", response_model=list[dict])
async def get_subtitles():
    """Get available subtitle tracks for current media.

    Returns:
        List of subtitle tracks with index, language, and current status
    """
    async with KodiClient(kodi_config) as client:
        return await client.get_subtitles()


class SubtitleRequest(BaseModel):
    """Request model for subtitle selection"""

    subtitle_index: int


@app.post("/v1/subtitles", response_model=dict[str, bool])
async def set_subtitle(request: SubtitleRequest):
    """Set active subtitle track.

    Args:
        request: Subtitle request with track index

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        success = await client.set_subtitle(request.subtitle_index)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set subtitle")

        return {"success": True}


@app.post("/v1/subtitles/toggle", response_model=dict[str, bool])
async def toggle_subtitles():
    """Toggle subtitles on/off.

    Returns:
        Success status
    """
    async with KodiClient(kodi_config) as client:
        success = await client.toggle_subtitles()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to toggle subtitles")

        return {"success": True}


app.include_router(cec_router)

