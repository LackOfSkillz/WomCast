"""
WomCast Live TV REST API
Endpoints for M3U playlist management and channel browsing.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from livetv import LiveTVManager


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


# Global manager instance
manager: LiveTVManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize LiveTV manager on startup."""
    global manager
    db_path = Path(__file__).parent.parent / "womcast.db"
    manager = LiveTVManager(db_path)
    await manager.init_database()
    yield


app = FastAPI(title="WomCast LiveTV API", version="0.2.0", lifespan=lifespan)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3007)
