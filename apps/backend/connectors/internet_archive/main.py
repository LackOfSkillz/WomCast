"""Internet Archive REST API endpoints for WomCast."""

import logging

from fastapi import APIRouter, HTTPException, Query

from common.resilience import with_resilience

from . import InternetArchiveConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/connectors/internet-archive", tags=["connectors"])

# Global connector instance (context manager in lifespan)
_connector: InternetArchiveConnector | None = None


async def get_connector() -> InternetArchiveConnector:
    """Get the global connector instance."""
    if _connector is None:
        raise HTTPException(status_code=503, detail="Connector not initialized")
    return _connector


@router.get("/collections")
async def get_collections():
    """Get featured public domain collections.

    Returns:
        List of collection objects with id, title, description
    """
    connector = await get_connector()

    try:
        async def _get_collections():
            return await connector.get_collections()

        collections = await with_resilience("internet_archive", _get_collections)
        return {"collections": collections}
    except Exception as e:
        logger.error(f"Collections error: {e}")
        # Graceful degradation: return empty list
        return {"collections": []}


@router.get("/search")
async def search_items(
    q: str | None = Query(None, description="Search query"),
    mediatype: str | None = Query(None, description="Media type (movies, audio, texts)"),
    collection: str | None = Query(None, description="Collection ID"),
    rows: int = Query(50, ge=1, le=10000, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number"),
):
    """Search Internet Archive for public domain content.

    Args:
        q: Search query string
        mediatype: Filter by media type
        collection: Filter by collection
        rows: Number of results per page
        page: Page number (1-based)

    Returns:
        List of items matching the search
    """
    connector = await get_connector()

    try:
        async def _search():
            return await connector.search(
                query=q, mediatype=mediatype, collection=collection, rows=rows, page=page
            )

        items = await with_resilience("internet_archive", _search)

        # Convert dataclass to dict
        return {
            "items": [
                {
                    "identifier": item.identifier,
                    "title": item.title,
                    "mediatype": item.mediatype,
                    "description": item.description,
                    "creator": item.creator,
                    "date": item.date,
                    "year": item.year,
                    "collection": item.collection,
                    "subject": item.subject,
                    "duration": item.duration,
                    "thumbnail_url": item.thumbnail_url,
                    "download_url": item.download_url,
                    "license": item.license,
                }
                for item in items
            ],
            "count": len(items),
            "page": page,
            "rows": rows,
        }

    except Exception as e:
        logger.error(f"Search error: {e}")
        # Graceful degradation: return empty results
        return {"items": [], "count": 0, "page": page, "rows": rows}


@router.get("/items/{identifier}")
async def get_item_details(identifier: str):
    """Get detailed metadata and stream URL for an item.

    Args:
        identifier: Internet Archive item identifier

    Returns:
        Item details with stream URL
    """
    connector = await get_connector()

    try:
        async def _get_item():
            return await connector.get_item_details(identifier)

        item = await with_resilience("internet_archive", _get_item)

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        return {
            "identifier": item.identifier,
            "title": item.title,
            "mediatype": item.mediatype,
            "description": item.description,
            "creator": item.creator,
            "date": item.date,
            "year": item.year,
            "collection": item.collection,
            "subject": item.subject,
            "duration": item.duration,
            "thumbnail_url": item.thumbnail_url,
            "stream_url": item.stream_url,
            "download_url": item.download_url,
            "license": item.license,
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
    _connector = InternetArchiveConnector()
    await _connector.__aenter__()
    logger.info("Internet Archive connector initialized")


async def shutdown():
    """Cleanup connector on shutdown."""
    global _connector
    if _connector:
        await _connector.__aexit__(None, None, None)
        _connector = None
        logger.info("Internet Archive connector shut down")
