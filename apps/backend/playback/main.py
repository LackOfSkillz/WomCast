"""
Playback Service - Manages media playback via Kodi bridge or mpv.
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.health import create_health_router

from .kodi_client import KodiClient, KodiConfig, PlayerState

__version__ = "0.1.0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WomCast Playback Service",
    description="Media playback control via Kodi/mpv",
    version=__version__,
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


@app.get("/v1/ping", response_model=dict[str, bool])
async def ping_kodi():
    """Test connection to Kodi.

    Returns:
        Kodi availability status
    """
    async with KodiClient(kodi_config) as client:
        available = await client.ping()
        return {"available": available}
