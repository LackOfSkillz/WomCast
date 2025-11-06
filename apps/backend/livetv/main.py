"""
WomCast Live TV REST API
Endpoints for M3U playlist management and channel browsing.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from livetv import LiveTVManager
from livetv.epg import EPGManager


class PlaylistUploadRequest(BaseModel):
    """Request model for playlist URL upload."""

    url: str


class PlaylistUploadResponse(BaseModel):
    """Response model for playlist upload."""

    added: int
    updated: int
    skipped: int
    message: str


class ChannelResponse(BaseModel):
    """Response model for channel data."""

    id: int
    name: str
    stream_url: str
    logo_url: str | None
    group_title: str | None
    language: str | None
    tvg_id: str | None
    codec_info: str | None


class EPGRequest(BaseModel):
    """Request model for EPG URL configuration."""

    url: str


class ProgramResponse(BaseModel):
    """Response model for program data."""

    channel_id: str
    title: str
    start_time: str
    end_time: str
    description: str | None
    category: str | None
    episode: str | None
    icon: str | None
    is_current: bool
    progress_percent: float


class EPGResponse(BaseModel):
    """Response model for EPG data."""

    channel_id: str
    current_program: ProgramResponse | None
    next_program: ProgramResponse | None


# Global manager instance
manager: LiveTVManager | None = None
epg_manager: EPGManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LiveTV manager on startup."""
    global manager, epg_manager
    db_path = Path(__file__).parent.parent / "womcast.db"
    manager = LiveTVManager(db_path)
    await manager.init_database()
    epg_manager = EPGManager()
    yield


app = FastAPI(title="WomCast LiveTV API", version="0.2.0", lifespan=lifespan)

_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
)
allowed_origins = (
    os.getenv("LIVETV_CORS_ORIGINS")
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


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/version")
async def version():
    """Version endpoint."""
    return {"version": "0.2.0", "service": "livetv"}


@app.post("/v1/livetv/playlists/file", response_model=PlaylistUploadResponse)
async def upload_playlist_file(file: UploadFile):
    """
    Upload M3U playlist file.

    Args:
        file: M3U/M3U8 file upload

    Returns:
        Upload result with counts

    Raises:
        HTTPException: 400 if file is not M3U format
        HTTPException: 500 if processing fails
    """
    if manager is None:
        raise HTTPException(status_code=500, detail="LiveTV manager not initialized")

    # Validate file extension
    if not file.filename or not (
        file.filename.lower().endswith(".m3u") or file.filename.lower().endswith(".m3u8")
    ):
        raise HTTPException(
            status_code=400, detail="File must be .m3u or .m3u8 format"
        )

    try:
        content = await file.read()
        content_str = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}") from e

    try:
        result = await manager.add_playlist(content_str, validate_streams=False)
        return PlaylistUploadResponse(
            added=result["added"],
            updated=result["updated"],
            skipped=result["skipped"],
            message=f"Processed {result['added'] + result['updated'] + result['skipped']} channels",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process playlist: {e}") from e


@app.post("/v1/livetv/playlists/url", response_model=PlaylistUploadResponse)
async def upload_playlist_url(request: PlaylistUploadRequest):
    """
    Import M3U playlist from URL.

    Args:
        request: Playlist URL request

    Returns:
        Upload result with counts

    Raises:
        HTTPException: 400 if URL is invalid
        HTTPException: 500 if download or processing fails
    """
    if manager is None:
        raise HTTPException(status_code=500, detail="LiveTV manager not initialized")

    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                request.url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to download playlist: HTTP {response.status}",
                    )
                content = await response.text()
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download playlist: {e}") from e

    try:
        result = await manager.add_playlist(content, validate_streams=False)
        return PlaylistUploadResponse(
            added=result["added"],
            updated=result["updated"],
            skipped=result["skipped"],
            message=f"Processed {result['added'] + result['updated'] + result['skipped']} channels",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process playlist: {e}") from e


@app.get("/v1/livetv/channels", response_model=list[ChannelResponse])
async def get_channels(group: str | None = None, limit: int = 100):
    """
    Get list of all channels.

    Args:
        group: Optional filter by group title
        limit: Maximum number of channels to return (default 100)

    Returns:
        List of channels

    Raises:
        HTTPException: 500 if retrieval fails
    """
    if manager is None:
        raise HTTPException(status_code=500, detail="LiveTV manager not initialized")

    try:
        channels = await manager.get_channels(group_title=group, limit=limit)
        return [ChannelResponse(**ch) for ch in channels]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {e}") from e


@app.get("/v1/livetv/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: int):
    """
    Get single channel by ID.

    Args:
        channel_id: Channel ID

    Returns:
        Channel details

    Raises:
        HTTPException: 404 if channel not found
        HTTPException: 500 if retrieval fails
    """
    if manager is None:
        raise HTTPException(status_code=500, detail="LiveTV manager not initialized")

    try:
        channel = await manager.get_channel(channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        return ChannelResponse(**channel)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channel: {e}") from e


@app.post("/v1/livetv/epg/url")
async def set_epg_url(request: EPGRequest):
    """
    Configure external XMLTV EPG URL.

    Args:
        request: EPG URL request

    Returns:
        Success status

    Raises:
        HTTPException: 400 if URL is invalid
        HTTPException: 500 if EPG manager not initialized
    """
    if epg_manager is None:
        raise HTTPException(status_code=500, detail="EPG manager not initialized")

    success = await epg_manager.set_epg_url(request.url)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to fetch EPG from URL")

    return {"status": "ok", "message": f"EPG updated from {request.url}"}


@app.get("/v1/livetv/epg", response_model=list[EPGResponse])
async def get_all_epg():
    """
    Get EPG data for all channels.

    Returns:
        List of EPG entries with current/next programs

    Raises:
        HTTPException: 500 if EPG manager not initialized
    """
    if epg_manager is None:
        raise HTTPException(status_code=500, detail="EPG manager not initialized")

    if not epg_manager.has_epg_data:
        return []

    try:
        current_programs = epg_manager.get_all_current_programs()
        epg_data = []

        for channel_id, current_program in current_programs.items():
            next_program = epg_manager.get_next_program(channel_id)

            current_response = ProgramResponse(
                channel_id=current_program.channel_id,
                title=current_program.title,
                start_time=current_program.start_time.isoformat(),
                end_time=current_program.end_time.isoformat(),
                description=current_program.description,
                category=current_program.category,
                episode=current_program.episode,
                icon=current_program.icon,
                is_current=current_program.is_current,
                progress_percent=current_program.progress_percent,
            )

            next_response = None
            if next_program:
                next_response = ProgramResponse(
                    channel_id=next_program.channel_id,
                    title=next_program.title,
                    start_time=next_program.start_time.isoformat(),
                    end_time=next_program.end_time.isoformat(),
                    description=next_program.description,
                    category=next_program.category,
                    episode=next_program.episode,
                    icon=next_program.icon,
                    is_current=next_program.is_current,
                    progress_percent=next_program.progress_percent,
                )

            epg_data.append(
                EPGResponse(
                    channel_id=channel_id,
                    current_program=current_response,
                    next_program=next_response,
                )
            )

        return epg_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get EPG data: {e}") from e


@app.get("/v1/livetv/epg/{channel_id}", response_model=EPGResponse)
async def get_channel_epg(channel_id: str):
    """
    Get EPG data for specific channel.

    Args:
        channel_id: Channel tvg_id

    Returns:
        EPG entry with current/next programs

    Raises:
        HTTPException: 404 if no EPG data for channel
        HTTPException: 500 if EPG manager not initialized
    """
    if epg_manager is None:
        raise HTTPException(status_code=500, detail="EPG manager not initialized")

    try:
        current_program = epg_manager.get_current_program(channel_id)
        next_program = epg_manager.get_next_program(channel_id)

        if not current_program and not next_program:
            raise HTTPException(status_code=404, detail="No EPG data for channel")

        current_response = None
        if current_program:
            current_response = ProgramResponse(
                channel_id=current_program.channel_id,
                title=current_program.title,
                start_time=current_program.start_time.isoformat(),
                end_time=current_program.end_time.isoformat(),
                description=current_program.description,
                category=current_program.category,
                episode=current_program.episode,
                icon=current_program.icon,
                is_current=current_program.is_current,
                progress_percent=current_program.progress_percent,
            )

        next_response = None
        if next_program:
            next_response = ProgramResponse(
                channel_id=next_program.channel_id,
                title=next_program.title,
                start_time=next_program.start_time.isoformat(),
                end_time=next_program.end_time.isoformat(),
                description=next_program.description,
                category=next_program.category,
                episode=next_program.episode,
                icon=next_program.icon,
                is_current=next_program.is_current,
                progress_percent=next_program.progress_percent,
            )

        return EPGResponse(
            channel_id=channel_id,
            current_program=current_response,
            next_program=next_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channel EPG: {e}") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3007)
