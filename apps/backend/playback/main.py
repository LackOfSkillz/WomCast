"""
Playback Service - Manages media playback via Kodi bridge or mpv.
"""

import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from common.health import create_health_router

from .cec_helper import CecDevice, get_cec_helper
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


# ============================================================================
# HDMI-CEC Endpoints
# ============================================================================


class CecDeviceResponse(BaseModel):
    """CEC device information response."""

    model_config = ConfigDict(populate_by_name=True)

    address: int = Field(..., description="CEC logical address (0-15)")
    name: str = Field(..., description="Device name")
    vendor: str = Field(..., description="Vendor name")
    device_type: str = Field(..., alias="deviceType", description="Device type")
    active_source: bool = Field(..., alias="activeSource", description="Is active source")
    physical_address: str = Field(..., alias="physicalAddress", description="HDMI physical address")


class CecSwitchRequest(BaseModel):
    """Request to switch CEC input."""

    model_config = ConfigDict(populate_by_name=True)

    address: int | None = Field(None, description="CEC device address (0-15)")
    name: str | None = Field(None, description="Device name (substring match)")


@app.get("/v1/cec/available")
async def check_cec_available():
    """Check if CEC is available on this system.

    Returns:
        CEC availability status
    """
    cec = get_cec_helper()
    available = await cec.is_available()

    return {"available": available, "client_path": cec.cec_client_path}


@app.get("/v1/cec/devices", response_model=list[CecDeviceResponse])
async def list_cec_devices():
    """Scan and list all CEC devices on the HDMI bus.

    Returns:
        List of detected CEC devices
    """
    cec = get_cec_helper()
    devices = await cec.scan_devices()

    return [
        CecDeviceResponse(
            address=dev.address,
            name=dev.name,
            vendor=dev.vendor,
            deviceType=dev.device_type.value,
            activeSource=dev.active_source,
            physicalAddress=dev.physical_address,
        )
        for dev in devices
    ]


@app.get("/v1/cec/tv", response_model=CecDeviceResponse | None)
async def get_tv_device():
    """Get the TV device (CEC address 0).

    Returns:
        TV device information, or null if not found
    """
    cec = get_cec_helper()
    tv = await cec.get_tv()

    if not tv:
        return None

    return CecDeviceResponse(
        address=tv.address,
        name=tv.name,
        vendor=tv.vendor,
        deviceType=tv.device_type.value,
        activeSource=tv.active_source,
        physicalAddress=tv.physical_address,
    )


@app.get("/v1/cec/active", response_model=CecDeviceResponse | None)
async def get_active_source():
    """Get the currently active CEC source device.

    Returns:
        Active device information, or null if none active
    """
    cec = get_cec_helper()
    active = await cec.get_active_source()

    if not active:
        return None

    return CecDeviceResponse(
        address=active.address,
        name=active.name,
        vendor=active.vendor,
        deviceType=active.device_type.value,
        activeSource=active.active_source,
        physicalAddress=active.physical_address,
    )


@app.post("/v1/cec/switch")
async def switch_cec_input(request: CecSwitchRequest):
    """Switch TV input to a specific CEC device.

    Args:
        request: Switch request with either address or name

    Returns:
        Success status
    """
    cec = get_cec_helper()

    if request.address is not None:
        success = await cec.switch_to_device(request.address)
    elif request.name:
        success = await cec.switch_to_device_by_name(request.name)
    else:
        raise HTTPException(
            status_code=400, detail="Must provide either 'address' or 'name'"
        )

    if not success:
        raise HTTPException(status_code=500, detail="CEC switch command failed")

    return {"success": True, "message": f"Switched to device"}


@app.post("/v1/cec/activate")
async def activate_womcast():
    """Make WomCast the active source (switch TV input to us).

    Returns:
        Success status
    """
    cec = get_cec_helper()
    success = await cec.make_active_source()

    if not success:
        raise HTTPException(status_code=500, detail="CEC activate command failed")

    return {"success": True, "message": "Made WomCast active source"}


@app.get("/v1/cec/status")
async def get_cec_status():
    """Get current CEC status and device list.

    Returns:
        CEC status with all devices
    """
    cec = get_cec_helper()
    return cec.to_dict()

