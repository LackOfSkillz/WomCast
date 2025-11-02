"""
Metadata Service - Handles media library indexing and metadata management.
"""


from pathlib import Path

import aiosqlite
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from common.database import get_db_path, init_database
from common.health import create_health_router
from metadata.fetchers import (
    load_config,
    sanitize_cache,
    save_config,
)

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast Metadata Service",
    description="Media library indexing and metadata management",
    version=__version__,
)

create_health_router(app, "metadata-service", __version__)

# Configuration file path
CONFIG_PATH = Path(__file__).parent / "metadata_config.json"


class ResumePositionUpdate(BaseModel):
    """Request model for updating resume position"""

    position_seconds: float


class MetadataConfigUpdate(BaseModel):
    """Request model for updating metadata configuration"""

    enabled: bool | None = None
    tmdb_api_key: str | None = None
    use_tmdb: bool | None = None
    use_musicbrainz: bool | None = None
    cache_ttl_days: int | None = None
    rate_limit_enabled: bool | None = None


@app.on_event("startup")
async def startup() -> None:
    """Initialize database on startup"""
    await init_database()


@app.get("/v1/media")
async def get_media_files(type: str | None = None) -> list[dict]:
    """
    Get all media files, optionally filtered by type.

    Args:
        type: Optional media type filter (video, audio, photo, game)

    Returns:
        List of media file records
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        if type:
            cursor = await db.execute(
                """
                SELECT id, file_path, file_name, file_size, media_type,
                       duration_seconds, width, height, created_at, modified_at,
                       indexed_at, play_count, resume_position_seconds
                FROM media_files
                WHERE media_type = ?
                ORDER BY file_name
                """,
                (type,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, file_path, file_name, file_size, media_type,
                       duration_seconds, width, height, created_at, modified_at,
                       indexed_at, play_count, resume_position_seconds
                FROM media_files
                ORDER BY file_name
                """
            )

        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]


@app.get("/v1/media/search")
async def search_media_files(q: str) -> list[dict]:
    """
    Search media files by name.

    Args:
        q: Search query string

    Returns:
        List of matching media file records
    """
    if not q.strip():
        return []

    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            SELECT id, file_path, file_name, file_size, media_type,
                   duration_seconds, width, height, created_at, modified_at,
                   indexed_at, play_count, resume_position_seconds
            FROM media_files
            WHERE file_name LIKE ?
            ORDER BY file_name
            """,
            (f"%{q}%",),
        )

        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]


@app.get("/v1/media/{media_id}")
async def get_media_item(media_id: int) -> dict:
    """
    Get detailed media information with metadata.

    Args:
        media_id: Media file ID

    Returns:
        Media file record with video/audio metadata if available
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        # Get media file
        cursor = await db.execute(
            """
            SELECT id, file_path, file_name, file_size, media_type,
                   duration_seconds, width, height, created_at, modified_at,
                   indexed_at, play_count, resume_position_seconds, subtitle_tracks
            FROM media_files
            WHERE id = ?
            """,
            (media_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media file not found")

        columns = [desc[0] for desc in cursor.description]
        media = dict(zip(columns, row, strict=True))

        # Get video metadata if available
        if media["media_type"] == "video":
            cursor = await db.execute(
                """
                SELECT id, media_file_id, title, year, genre, director, plot, rating, poster_url
                FROM video_metadata
                WHERE media_file_id = ?
                """,
                (media_id,),
            )
            video_row = await cursor.fetchone()
            if video_row:
                video_columns = [desc[0] for desc in cursor.description]
                media["video_metadata"] = dict(zip(video_columns, video_row, strict=True))

        # Get audio metadata if available
        if media["media_type"] == "audio":
            cursor = await db.execute(
                """
                SELECT id, media_file_id, title, artist, album, year, genre, track_number, artwork_url
                FROM audio_metadata
                WHERE media_file_id = ?
                """,
                (media_id,),
            )
            audio_row = await cursor.fetchone()
            if audio_row:
                audio_columns = [desc[0] for desc in cursor.description]
                media["audio_metadata"] = dict(zip(audio_columns, audio_row, strict=True))

        return media


@app.put("/v1/media/{media_id}/resume")
async def update_resume_position(
    media_id: int, update: ResumePositionUpdate
) -> dict:
    """
    Update resume position for a media file.

    Args:
        media_id: Media file ID
        update: Resume position update data

    Returns:
        Updated media file record
    """
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        # Check if media file exists
        cursor = await db.execute(
            "SELECT id FROM media_files WHERE id = ?", (media_id,)
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Media file not found")

        # Update resume position
        await db.execute(
            """
            UPDATE media_files
            SET resume_position_seconds = ?
            WHERE id = ?
            """,
            (int(update.position_seconds), media_id),
        )
        await db.commit()

        # Return updated record
        cursor = await db.execute(
            """
            SELECT id, file_path, file_name, file_size, media_type,
                   duration_seconds, width, height, created_at, modified_at,
                   indexed_at, play_count, resume_position_seconds
            FROM media_files
            WHERE id = ?
            """,
            (media_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated record")
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row, strict=True))


@app.get("/v1/metadata/config")
async def get_metadata_config() -> dict:
    """
    Get current metadata fetcher configuration.

    Returns:
        Configuration settings
    """
    config = await load_config(CONFIG_PATH)
    return {
        "enabled": config.enabled,
        "tmdb_api_key": "***" if config.tmdb_api_key else None,
        "use_tmdb": config.use_tmdb,
        "use_musicbrainz": config.use_musicbrainz,
        "cache_ttl_days": config.cache_ttl_days,
        "rate_limit_enabled": config.rate_limit_enabled,
    }


@app.put("/v1/metadata/config")
async def update_metadata_config(update: MetadataConfigUpdate) -> dict:
    """
    Update metadata fetcher configuration.

    Args:
        update: Configuration update data

    Returns:
        Updated configuration settings
    """
    config = await load_config(CONFIG_PATH)

    # Update only provided fields
    if update.enabled is not None:
        config.enabled = update.enabled
    if update.tmdb_api_key is not None:
        config.tmdb_api_key = update.tmdb_api_key
    if update.use_tmdb is not None:
        config.use_tmdb = update.use_tmdb
    if update.use_musicbrainz is not None:
        config.use_musicbrainz = update.use_musicbrainz
    if update.cache_ttl_days is not None:
        config.cache_ttl_days = update.cache_ttl_days
    if update.rate_limit_enabled is not None:
        config.rate_limit_enabled = update.rate_limit_enabled

    # Save updated configuration
    await save_config(config, CONFIG_PATH)

    return {
        "enabled": config.enabled,
        "tmdb_api_key": "***" if config.tmdb_api_key else None,
        "use_tmdb": config.use_tmdb,
        "use_musicbrainz": config.use_musicbrainz,
        "cache_ttl_days": config.cache_ttl_days,
        "rate_limit_enabled": config.rate_limit_enabled,
    }


@app.post("/v1/metadata/cache/sanitize")
async def sanitize_metadata_cache(older_than_days: int = 90) -> dict:
    """
    Remove old metadata cache entries.

    Args:
        older_than_days: Remove entries older than this many days (default: 90)

    Returns:
        Statistics about sanitization
    """
    db_path = get_db_path()
    videos_cleared, audio_cleared = await sanitize_cache(db_path, older_than_days)

    return {
        "videos_cleared": videos_cleared,
        "audio_cleared": audio_cleared,
        "older_than_days": older_than_days,
    }
