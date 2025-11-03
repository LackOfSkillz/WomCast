"""NASA REST API endpoints for WomCast."""

import logging

from fastapi import APIRouter, HTTPException, Query

from common.resilience import with_resilience

from . import NASAConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/connectors/nasa", tags=["connectors"])

# Global connector instance
_connector: NASAConnector | None = None


async def get_connector() -> NASAConnector:
    """Get the global connector instance."""
    if _connector is None:
        raise HTTPException(status_code=503, detail="Connector not initialized")
    return _connector


@router.get("/live")
async def get_live_streams():
    """Get NASA TV live streams.

    Returns:
        List of NASA TV live stream channels
    """
    connector = await get_connector()

    try:
        async def _get_streams():
            return await connector.get_live_streams()

        streams = await with_resilience("nasa", _get_streams)

        return {
            "streams": [
                {
                    "id": stream.id,
                    "title": stream.title,
                    "description": stream.description,
                    "media_type": stream.media_type,
                    "stream_url": stream.stream_url,
                    "is_live": stream.is_live,
                }
                for stream in streams
            ],
            "count": len(streams),
        }

    except Exception as e:
        logger.error(f"Get live streams error: {e}")
        # Graceful degradation
        return {"streams": [], "count": 0}


@router.get("/search")
async def search_items(
    q: str = Query("apollo", description="Search query"),
    media_type: str = Query("video", description="Media type (video, image, audio)"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search NASA media archive.

    Args:
        q: Search query string
        media_type: Filter by media type
        limit: Maximum number of results

    Returns:
        List of items matching the search
    """
    connector = await get_connector()

    try:
        async def _search():
            return await connector.search(query=q, media_type=media_type, limit=limit)

        items = await with_resilience("nasa", _search)

        return {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "media_type": item.media_type,
                    "duration": item.duration,
                    "thumbnail_url": item.thumbnail_url,
                    "stream_url": item.stream_url,
                    "date_created": item.date_created,
                    "photographer": item.photographer,
                    "keywords": item.keywords,
                    "is_live": item.is_live,
                }
                for item in items
            ],
            "count": len(items),
            "query": q,
        }

    except Exception as e:
        logger.error(f"Search error: {e}")
        # Graceful degradation
        return {"items": [], "count": 0, "query": q}
        raise HTTPException(status_code=500, detail="Search failed") from e


@router.get("/items/{item_id}")
async def get_item_details(item_id: str):
    """Get detailed information for a NASA item.

    Args:
        item_id: NASA item identifier

    Returns:
        Item details with stream URL
    """
    connector = await get_connector()

    try:
        async def _get_item():
            return await connector.get_item_details(item_id)

        item = await with_resilience("nasa", _get_item)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "media_type": item.media_type,
            "duration": item.duration,
            "thumbnail_url": item.thumbnail_url,
            "stream_url": item.stream_url,
            "date_created": item.date_created,
            "photographer": item.photographer,
            "keywords": item.keywords,
            "is_live": item.is_live,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get item error: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e


# Lifespan management
async def startup():
    """Initialize connector on startup."""
    global _connector
    _connector = NASAConnector()
    await _connector.__aenter__()
    logger.info("NASA connector initialized")


async def shutdown():
    """Cleanup connector on shutdown."""
    global _connector
    if _connector:
        await _connector.__aexit__(None, None, None)
        _connector = None
        logger.info("NASA connector shut down")
