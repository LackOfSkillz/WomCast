"""Test database schema creation and integrity."""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite
import pytest

from common.database import SCHEMA_VERSION, get_schema_version, init_database


@pytest.mark.asyncio
async def test_database_initialization() -> None:
    """Test that database initializes with correct schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        # Initialize database
        await init_database(db_path)

        # Verify schema version
        version = await get_schema_version(db_path)
        assert version == SCHEMA_VERSION

        # Verify all tables exist
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ) as cursor:
                tables = [row[0] async for row in cursor]

            expected_tables = [
                "albums",
                "artists",
                "audio_tracks",
                "episodes",
                "games",
                "media_files",
                "mount_points",
                "photos",
                "playlist_items",
                "playlists",
                "scan_history",
                "schema_metadata",
                "videos",
            ]

            assert sorted(tables) == sorted(expected_tables)

    finally:
        db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_media_file_constraints() -> None:
    """Test media_files table constraints."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        await init_database(db_path)

        async with aiosqlite.connect(db_path) as db:
            # Insert valid media file
            await db.execute(
                """
                INSERT INTO media_files
                (file_path, file_name, file_size, media_type, created_at, modified_at, indexed_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """,
                ("/media/test/movie.mkv", "movie.mkv", 1024 * 1024 * 1024, "video"),
            )
            await db.commit()

            # Verify insert
            async with db.execute(
                "SELECT COUNT(*) FROM media_files WHERE media_type = 'video'"
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                count = row[0]
                assert count == 1

            # Test unique constraint on file_path
            with pytest.raises(aiosqlite.IntegrityError):
                await db.execute(
                    """
                    INSERT INTO media_files
                    (file_path, file_name, file_size, media_type, created_at, modified_at, indexed_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                    """,
                    (
                        "/media/test/movie.mkv",
                        "movie.mkv",
                        1024 * 1024 * 1024,
                        "video",
                    ),
                )
                await db.commit()

            # Test media_type constraint
            with pytest.raises(aiosqlite.IntegrityError):
                await db.execute(
                    """
                    INSERT INTO media_files
                    (file_path, file_name, file_size, media_type, created_at, modified_at, indexed_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                    """,
                    (
                        "/media/test/invalid.bin",
                        "invalid.bin",
                        1024,
                        "invalid_type",
                    ),
                )
                await db.commit()

    finally:
        db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_foreign_key_cascade() -> None:
    """Test foreign key cascades on media_files deletion."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        await init_database(db_path)

        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            # Insert media file
            await db.execute(
                """
                INSERT INTO media_files
                (file_path, file_name, file_size, media_type, created_at, modified_at, indexed_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """,
                ("/media/test/movie.mkv", "movie.mkv", 1024 * 1024 * 1024, "video"),
            )

            # Get media file ID
            async with db.execute(
                "SELECT id FROM media_files WHERE file_path = ?",
                ("/media/test/movie.mkv",),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                media_file_id = row[0]

            # Insert video metadata
            await db.execute(
                """
                INSERT INTO videos (media_file_id, title, year)
                VALUES (?, ?, ?)
                """,
                (media_file_id, "Test Movie", 2025),
            )
            await db.commit()

            # Verify video exists
            async with db.execute("SELECT COUNT(*) FROM videos") as cursor:
                row = await cursor.fetchone()
                assert row is not None
                count = row[0]
                assert count == 1

            # Delete media file
            await db.execute(
                "DELETE FROM media_files WHERE id = ?", (media_file_id,)
            )
            await db.commit()

            # Verify video was cascade deleted
            async with db.execute("SELECT COUNT(*) FROM videos") as cursor:
                row = await cursor.fetchone()
                assert row is not None
                count = row[0]
                assert count == 0

    finally:
        db_path.unlink(missing_ok=True)
