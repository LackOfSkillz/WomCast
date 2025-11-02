"""Jamendo REST API endpoints for WomCast."""

import logging

from fastapi import APIRouter, HTTPException, Query

from . import JamendoConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/connectors/jamendo", tags=["connectors"])

# Global connector instance
_connector: JamendoConnector | None = None


async def get_connector() -> JamendoConnector:
    """Get the global connector instance."""
    if _connector is None:
        raise HTTPException(status_code=503, detail="Connector not initialized")
    return _connector


@router.get("/popular")
async def get_popular(limit: int = Query(20, ge=1, le=100)):
    """Get popular tracks from Jamendo.

    Args:
        limit: Maximum number of tracks to return

    Returns:
        List of popular tracks
    """
    connector = await get_connector()

    try:
        tracks = await connector.get_popular(limit=limit)

        return {
            "tracks": [
                {
                    "id": track.id,
                    "name": track.name,
                    "artist_name": track.artist_name,
                    "album_name": track.album_name,
                    "duration": track.duration,
                    "license_ccurl": track.license_ccurl,
                    "audio_url": track.audio_url,
                    "image_url": track.image_url,
                    "releasedate": track.releasedate,
                    "genre": track.genre,
                }
                for track in tracks
            ],
            "count": len(tracks),
        }

    except Exception as e:
        logger.error(f"Get popular error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get popular tracks") from e


@router.get("/search")
async def search_tracks(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    genre: str | None = Query(None, description="Genre filter"),
):
    """Search Jamendo tracks.

    Args:
        q: Search query string
        limit: Maximum number of results
        genre: Optional genre filter

    Returns:
        List of tracks matching the search
    """
    connector = await get_connector()

    try:
        tracks = await connector.search(query=q, limit=limit, genre=genre)

        return {
            "tracks": [
                {
                    "id": track.id,
                    "name": track.name,
                    "artist_name": track.artist_name,
                    "album_name": track.album_name,
                    "duration": track.duration,
                    "license_ccurl": track.license_ccurl,
                    "audio_url": track.audio_url,
                    "image_url": track.image_url,
                    "releasedate": track.releasedate,
                    "genre": track.genre,
                }
                for track in tracks
            ],
            "count": len(tracks),
            "query": q,
        }

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed") from e


@router.get("/tracks/{track_id}")
async def get_track_details(track_id: str):
    """Get detailed information for a Jamendo track.

    Args:
        track_id: Jamendo track identifier

    Returns:
        Track details with audio URL
    """
    connector = await get_connector()

    try:
        track = await connector.get_track_details(track_id)

        if not track:
            raise HTTPException(status_code=404, detail="Track not found")

        return {
            "id": track.id,
            "name": track.name,
            "artist_name": track.artist_name,
            "album_name": track.album_name,
            "duration": track.duration,
            "license_ccurl": track.license_ccurl,
            "audio_url": track.audio_url,
            "image_url": track.image_url,
            "releasedate": track.releasedate,
            "genre": track.genre,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get track error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get track details") from e


# Lifespan management
async def startup():
    """Initialize connector on startup."""
    global _connector
    _connector = JamendoConnector()
    await _connector.__aenter__()
    logger.info("Jamendo connector initialized")


async def shutdown():
    """Cleanup connector on shutdown."""
    global _connector
    if _connector:
        await _connector.__aexit__(None, None, None)
        _connector = None
        logger.info("Jamendo connector shut down")
