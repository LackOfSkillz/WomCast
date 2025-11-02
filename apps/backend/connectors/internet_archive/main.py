"""Internet Archive REST API endpoints for WomCast."""

import logging

from fastapi import APIRouter, HTTPException, Query

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
    collections = await connector.get_collections()
    return {"collections": collections}


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
        items = await connector.search(
            query=q, mediatype=mediatype, collection=collection, rows=rows, page=page
        )

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
        raise HTTPException(status_code=500, detail="Search failed") from e


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
        item = await connector.get_item_details(identifier)

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
        raise HTTPException(status_code=500, detail="Failed to get item details") from e


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
