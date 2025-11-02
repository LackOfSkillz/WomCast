"""Tests for media file indexer service."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite
import pytest

from ..common.database import init_database
from ..metadata.indexer import (
    detect_deleted_files,
    get_media_type,
    index_file,
    initialize_mount_point,
    scan_directory,
    scan_mount_point,
)


def test_get_media_type():
    """Test media type detection from file extensions."""
    assert get_media_type(Path("/test/movie.mkv")) == "video"
    assert get_media_type(Path("/test/song.mp3")) == "audio"
    assert get_media_type(Path("/test/photo.jpg")) == "photo"
    assert get_media_type(Path("/test/game.iso")) == "game"
    assert get_media_type(Path("/test/document.txt")) is None


@pytest.mark.asyncio
async def test_initialize_mount_point():
    """Test mount point registration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Initialize new mount point
        mount_id = await initialize_mount_point(
            db_path, "/media/usb", "USB Drive"
        )
        assert mount_id is not None

        # Verify mount point exists
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT mount_path, label, is_active FROM mount_points WHERE id = ?",
                (mount_id,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                mount_path, label, is_active = row
                assert mount_path == "/media/usb"
                assert label == "USB Drive"
                assert is_active == 1

        # Initialize same mount point again (should reuse)
        mount_id2 = await initialize_mount_point(
            db_path, "/media/usb", "USB Drive"
        )
        assert mount_id2 == mount_id


@pytest.mark.asyncio
async def test_scan_directory():
    """Test directory scanning for media files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create test directory structure
        (root / "videos").mkdir()
        (root / "videos" / "movie1.mkv").touch()
        (root / "videos" / "movie2.mp4").touch()
        (root / "videos" / "readme.txt").touch()

        (root / "music").mkdir()
        (root / "music" / "song1.mp3").touch()
        (root / "music" / "song2.flac").touch()

        (root / "photos").mkdir()
        (root / "photos" / "pic1.jpg").touch()

        # Scan for all media files
        files = []
        async for file_path in scan_directory(root):
            files.append(file_path.relative_to(root))

        # Should find 5 media files, not readme.txt
        assert len(files) == 5
        assert Path("videos/movie1.mkv") in files
        assert Path("videos/movie2.mp4") in files
        assert Path("music/song1.mp3") in files
        assert Path("music/song2.flac") in files
        assert Path("photos/pic1.jpg") in files
        assert Path("videos/readme.txt") not in files


@pytest.mark.asyncio
async def test_index_file():
    """Test indexing a single media file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Create test file
        test_file = Path(tmpdir) / "test_video.mkv"
        test_file.write_text("fake video content")

        # Initialize mount point
        mount_id = await initialize_mount_point(db_path, tmpdir, "Test Mount")

        # Index the file
        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            media_file_id = await index_file(db, test_file, mount_id)
            await db.commit()

            assert media_file_id is not None

            # Verify file was indexed
            async with db.execute(
                """
                SELECT file_name, file_size, media_type, mount_point_id
                FROM media_files
                WHERE id = ?
                """,
                (media_file_id,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                file_name, file_size, media_type, mp_id = row
                assert file_name == "test_video.mkv"
                assert file_size > 0
                assert media_type == "video"
                assert mp_id == mount_id


@pytest.mark.asyncio
async def test_index_file_update():
    """Test that re-indexing unchanged file updates timestamp only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Create test file
        test_file = Path(tmpdir) / "test_video.mkv"
        test_file.write_text("fake video content")

        # Initialize mount point
        mount_id = await initialize_mount_point(db_path, tmpdir, "Test Mount")

        # Index the file twice
        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            media_file_id1 = await index_file(db, test_file, mount_id)
            await db.commit()

            # Get initial indexed_at timestamp
            async with db.execute(
                "SELECT indexed_at FROM media_files WHERE id = ?",
                (media_file_id1,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                indexed_at1 = row[0]

            # Index again (file unchanged)
            media_file_id2 = await index_file(db, test_file, mount_id)
            await db.commit()

            # Should return same ID
            assert media_file_id2 == media_file_id1

            # indexed_at should be updated
            async with db.execute(
                "SELECT indexed_at FROM media_files WHERE id = ?",
                (media_file_id1,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                indexed_at2 = row[0]

            # Timestamps should be different (within reason)
            assert indexed_at2 >= indexed_at1


@pytest.mark.asyncio
async def test_scan_mount_point():
    """Test full mount point scanning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Create test directory structure
        root = Path(tmpdir) / "media"
        root.mkdir()
        (root / "movie1.mkv").write_text("movie 1")
        (root / "movie2.mp4").write_text("movie 2")
        (root / "song.mp3").write_text("song")
        (root / "readme.txt").write_text("readme")

        # Initialize mount point
        mount_id = await initialize_mount_point(db_path, str(root), "Test Media")

        # Scan mount point
        scanned, indexed = await scan_mount_point(db_path, root, mount_id)

        # Should scan 4 files, index 3 media files
        assert scanned == 3  # Only media files are scanned
        assert indexed == 3

        # Verify scan_history was recorded
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                """
                SELECT status, files_scanned, files_indexed
                FROM scan_history
                WHERE mount_point_id = ?
                """,
                (mount_id,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                status, files_scanned, files_indexed = row
                assert status == "completed"
                assert files_scanned == 3
                assert files_indexed == 3


@pytest.mark.asyncio
async def test_detect_deleted_files():
    """Test detection and removal of deleted files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        await init_database(db_path)

        # Create test files
        root = Path(tmpdir) / "media"
        root.mkdir()
        file1 = root / "movie1.mkv"
        file2 = root / "movie2.mp4"
        file1.write_text("movie 1")
        file2.write_text("movie 2")

        # Initialize mount point and scan
        mount_id = await initialize_mount_point(db_path, str(root), "Test Media")
        await scan_mount_point(db_path, root, mount_id)

        # Verify both files are indexed
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM media_files WHERE mount_point_id = ?",
                (mount_id,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                count = row[0]
                assert count == 2

        # Delete one file
        file1.unlink()

        # Force old indexed_at timestamp for testing
        async with aiosqlite.connect(db_path) as db:
            old_timestamp = datetime.now(UTC).replace(year=2020).isoformat()
            await db.execute(
                "UPDATE media_files SET indexed_at = ?", (old_timestamp,)
            )
            await db.commit()

        # Detect deleted files
        deleted = await detect_deleted_files(db_path, mount_id, scan_threshold_hours=1)
        assert deleted == 1

        # Verify only one file remains
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT file_name FROM media_files WHERE mount_point_id = ?",
                (mount_id,),
            ) as cursor:
                row = await cursor.fetchone()
                assert row is not None
                file_name = row[0]
                assert file_name == "movie2.mp4"
