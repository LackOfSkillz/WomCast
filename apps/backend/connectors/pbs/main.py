"""PBS REST API endpoints for WomCast."""

import logging

from fastapi import APIRouter, HTTPException, Query

from common.resilience import with_resilience

from . import PBSConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/connectors/pbs", tags=["connectors"])

# Global connector instance
_connector: PBSConnector | None = None


async def get_connector() -> PBSConnector:
    """Get the global connector instance."""
    if _connector is None:
        raise HTTPException(status_code=503, detail="Connector not initialized")
    return _connector


@router.get("/featured")
async def get_featured(limit: int = Query(20, ge=1, le=100)):
    """Get featured PBS content.

    Args:
        limit: Maximum number of items to return

    Returns:
        List of featured PBS items
    """
    connector = await get_connector()

    try:
        async def _get_featured():
            return await connector.get_featured(limit=limit)

        items = await with_resilience("pbs", _get_featured)

        return {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "duration": item.duration,
                    "thumbnail_url": item.thumbnail_url,
                    "stream_url": item.stream_url,
                    "show_title": item.show_title,
                    "season": item.season,
                    "episode": item.episode,
                    "premiered_on": item.premiered_on,
                }
                for item in items
            ],
            "count": len(items),
        }

    except Exception as e:
        logger.error(f"Get featured error: {e}")
        # Graceful degradation
        return {"items": [], "count": 0}


@router.get("/search")
async def search_items(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search PBS content.

    Args:
        q: Search query string
        limit: Maximum number of results

    Returns:
        List of items matching the search
    """
    connector = await get_connector()

    try:
        async def _search():
            return await connector.search(query=q, limit=limit)

        items = await with_resilience("pbs", _search)

        return {
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "duration": item.duration,
                    "thumbnail_url": item.thumbnail_url,
                    "stream_url": item.stream_url,
                    "show_title": item.show_title,
                    "season": item.season,
                    "episode": item.episode,
                    "premiered_on": item.premiered_on,
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


@router.get("/items/{item_id}")
async def get_item_details(item_id: str):
    """Get detailed information for a PBS item.

    Args:
        item_id: PBS item identifier

    Returns:
        Item details with stream URL
    """
    connector = await get_connector()

    try:
        async def _get_item():
            return await connector.get_item_details(item_id)

        item = await with_resilience("pbs", _get_item)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "duration": item.duration,
            "thumbnail_url": item.thumbnail_url,
            "stream_url": item.stream_url,
            "show_title": item.show_title,
            "season": item.season,
            "episode": item.episode,
            "premiered_on": item.premiered_on,
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
    _connector = PBSConnector()
    await _connector.__aenter__()
    logger.info("PBS connector initialized")


async def shutdown():
    """Cleanup connector on shutdown."""
    global _connector
    if _connector:
        await _connector.__aexit__(None, None, None)
        _connector = None
        logger.info("PBS connector shut down")
