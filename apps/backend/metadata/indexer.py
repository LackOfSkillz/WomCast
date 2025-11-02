"""Media file indexer service.

Scans mount points for media files, extracts metadata, and updates the database.
Implements efficient scanning with change detection and progress reporting.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from ..common.database import init_database

logger = logging.getLogger(__name__)

# Supported media file extensions
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma", ".opus"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}
GAME_EXTENSIONS = {".iso", ".cue", ".bin", ".chd", ".7z", ".zip"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa", ".sub"}

ALL_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | PHOTO_EXTENSIONS | GAME_EXTENSIONS


def get_media_type(file_path: Path) -> str | None:
    """Determine media type from file extension."""
    ext = file_path.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in PHOTO_EXTENSIONS:
        return "photo"
    elif ext in GAME_EXTENSIONS:
        return "game"
    return None


async def scan_directory(
    directory: Path, extensions: set[str] | None = None
) -> AsyncIterator[Path]:
    """Recursively scan directory for media files.

    Args:
        directory: Root directory to scan
        extensions: Set of file extensions to match (including dot), or None for all

    Yields:
        Path objects for matching files
    """
    if extensions is None:
        extensions = ALL_EXTENSIONS

    try:
        for item in directory.iterdir():
            if item.is_dir():
                # Recursively scan subdirectories
                async for file_path in scan_directory(item, extensions):
                    yield file_path
            elif item.is_file():
                if item.suffix.lower() in extensions:
                    yield item
    except PermissionError:
        logger.warning(f"Permission denied: {directory}")
    except OSError as e:
        logger.error(f"Error scanning {directory}: {e}")


async def get_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Generate fast hash for file change detection.

    Uses file size + mtime as a simple hash for now.
    Could be enhanced with actual content hashing if needed.
    """
    stat = file_path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def detect_subtitle_files(media_file_path: Path) -> list[dict]:
    """Detect external subtitle files for a media file.

    Looks for subtitle files with the same base name as the media file,
    optionally with language codes (e.g., movie.en.srt, movie.srt).

    Args:
        media_file_path: Path to the media file

    Returns:
        List of subtitle track dictionaries with 'path', 'language', and 'format' keys
    """
    subtitles = []
    base_name = media_file_path.stem  # filename without extension
    parent_dir = media_file_path.parent

    # Common language codes
    lang_codes = {
        "en",
        "eng",
        "english",
        "es",
        "spa",
        "spanish",
        "fr",
        "fra",
        "french",
        "de",
        "ger",
        "german",
        "it",
        "ita",
        "italian",
        "pt",
        "por",
        "portuguese",
        "ja",
        "jpn",
        "japanese",
        "zh",
        "chi",
        "chinese",
        "ko",
        "kor",
        "korean",
        "ru",
        "rus",
        "russian",
    }

    try:
        # Look for subtitle files in the same directory
        for item in parent_dir.iterdir():
            if item.suffix.lower() in SUBTITLE_EXTENSIONS:
                # Check if the subtitle file matches the media file
                if item.stem.startswith(base_name):
                    # Extract language from filename (e.g., movie.en.srt -> en)
                    parts = item.stem.split(".")
                    language = "unknown"

                    if len(parts) > 1:
                        # Check if last part before extension is a language code
                        potential_lang = parts[-1].lower()
                        if potential_lang in lang_codes:
                            language = potential_lang

                    subtitles.append(
                        {
                            "path": str(item),
                            "language": language,
                            "format": item.suffix[1:].lower(),  # Remove the dot
                        }
                    )
    except OSError as e:
        logger.warning(f"Error scanning for subtitles in {parent_dir}: {e}")

    return subtitles


async def index_file(
    db: aiosqlite.Connection,
    file_path: Path,
    mount_point_id: int,
) -> int | None:
    """Index a single media file.

    Args:
        db: Database connection
        file_path: Path to media file
        mount_point_id: ID of the mount point containing this file

    Returns:
        media_file_id if successful, None if file should be skipped
    """
    media_type = get_media_type(file_path)
    if not media_type:
        return None

    try:
        stat = file_path.stat()
        file_hash = await get_file_hash(file_path)
        now = datetime.now(UTC).isoformat()

        # Detect subtitle files for video content
        subtitle_tracks = []
        if media_type == "video":
            subtitle_tracks = detect_subtitle_files(file_path)

        subtitle_tracks_json = json.dumps(subtitle_tracks) if subtitle_tracks else None

        # Check if file already exists
        async with db.execute(
            "SELECT id, file_hash FROM media_files WHERE file_path = ?",
            (str(file_path),),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            existing_id, existing_hash = existing
            if existing_hash == file_hash:
                # File unchanged, update indexed_at timestamp and subtitle tracks
                await db.execute(
                    """
                    UPDATE media_files
                    SET indexed_at = ?,
                        subtitle_tracks = ?
                    WHERE id = ?
                    """,
                    (now, subtitle_tracks_json, existing_id),
                )
                return existing_id
            else:
                # File changed, update metadata
                await db.execute(
                    """
                    UPDATE media_files
                    SET file_size = ?,
                        file_hash = ?,
                        modified_at = ?,
                        indexed_at = ?,
                        subtitle_tracks = ?
                    WHERE id = ?
                    """,
                    (
                        stat.st_size,
                        file_hash,
                        datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                        now,
                        subtitle_tracks_json,
                        existing_id,
                    ),
                )
                return existing_id
        else:
            # New file, insert
            cursor = await db.execute(
                """
                INSERT INTO media_files
                (file_path, file_name, file_size, media_type, file_hash,
                 mount_point_id, created_at, modified_at, indexed_at, subtitle_tracks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(file_path),
                    file_path.name,
                    stat.st_size,
                    media_type,
                    file_hash,
                    mount_point_id,
                    datetime.fromtimestamp(stat.st_ctime, UTC).isoformat(),
                    datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    now,
                    subtitle_tracks_json,
                ),
            )
            return cursor.lastrowid

    except OSError as e:
        logger.error(f"Error indexing {file_path}: {e}")
        return None


async def scan_mount_point(
    db_path: Path,
    mount_path: Path,
    mount_point_id: int,
) -> tuple[int, int]:
    """Scan a mount point and index all media files.

    Args:
        db_path: Path to SQLite database
        mount_path: Path to mount point root
        mount_point_id: Database ID of the mount point

    Returns:
        Tuple of (files_scanned, files_indexed)
    """
    scan_start = datetime.now(UTC)
    files_scanned = 0
    files_indexed = 0

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # Record scan start
        cursor = await db.execute(
            """
            INSERT INTO scan_history
            (mount_point_id, started_at, status)
            VALUES (?, ?, ?)
            """,
            (mount_point_id, scan_start.isoformat(), "running"),
        )
        scan_id = cursor.lastrowid
        await db.commit()

        try:
            # Scan all media files
            async for file_path in scan_directory(mount_path):
                files_scanned += 1
                media_file_id = await index_file(db, file_path, mount_point_id)
                if media_file_id:
                    files_indexed += 1

                # Commit in batches for performance
                if files_scanned % 100 == 0:
                    await db.commit()
                    logger.info(
                        f"Scanned {files_scanned} files, indexed {files_indexed}"
                    )

            # Final commit
            await db.commit()

            # Update scan history
            scan_end = datetime.now(UTC)
            await db.execute(
                """
                UPDATE scan_history
                SET completed_at = ?,
                    status = ?,
                    files_scanned = ?,
                    files_indexed = ?
                WHERE id = ?
                """,
                (
                    scan_end.isoformat(),
                    "completed",
                    files_scanned,
                    files_indexed,
                    scan_id,
                ),
            )
            await db.commit()

            logger.info(
                f"Scan completed: {files_indexed}/{files_scanned} files indexed "
                f"in {(scan_end - scan_start).total_seconds():.1f}s"
            )

        except Exception as e:
            # Mark scan as failed
            await db.execute(
                """
                UPDATE scan_history
                SET status = ?,
                    error_message = ?
                WHERE id = ?
                """,
                ("failed", str(e), scan_id),
            )
            await db.commit()
            raise

    return files_scanned, files_indexed


async def detect_deleted_files(
    db_path: Path, mount_point_id: int, scan_threshold_hours: int = 24
) -> int:
    """Remove database entries for files that no longer exist.

    Args:
        db_path: Path to SQLite database
        mount_point_id: Database ID of the mount point to check
        scan_threshold_hours: Only check files not scanned in this many hours

    Returns:
        Number of files removed
    """
    threshold = datetime.now(UTC).replace(
        hour=datetime.now(UTC).hour - scan_threshold_hours
    ).isoformat()

    deleted_count = 0

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # Get all files for this mount point that haven't been seen recently
        async with db.execute(
            """
            SELECT id, file_path
            FROM media_files
            WHERE mount_point_id = ?
              AND indexed_at < ?
            """,
            (mount_point_id, threshold),
        ) as cursor:
            files = await cursor.fetchall()

        for file_id, file_path in files:
            if not Path(file_path).exists():
                await db.execute("DELETE FROM media_files WHERE id = ?", (file_id,))
                deleted_count += 1
                logger.info(f"Removed deleted file: {file_path}")

        await db.commit()

    return deleted_count


async def get_mount_points(db_path: Path) -> list[tuple[int, str, str]]:
    """Get all active mount points from database.

    Returns:
        List of (id, mount_path, label) tuples
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT id, mount_path, label FROM mount_points WHERE is_active = 1"
        ) as cursor:
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2]) for row in rows]


async def initialize_mount_point(
    db_path: Path, mount_path: str, label: str | None = None
) -> int:
    """Register a mount point in the database.

    Args:
        db_path: Path to SQLite database
        mount_path: Filesystem path to mount point
        label: Optional label for the mount point

    Returns:
        Database ID of the mount point
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # Check if mount point already exists
        async with db.execute(
            "SELECT id FROM mount_points WHERE mount_path = ?", (mount_path,)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            mount_id = existing[0]
            # Update is_active flag
            await db.execute(
                "UPDATE mount_points SET is_active = 1 WHERE id = ?", (mount_id,)
            )
        else:
            # Insert new mount point
            cursor = await db.execute(
                """
                INSERT INTO mount_points (mount_path, label, is_active)
                VALUES (?, ?, 1)
                """,
                (mount_path, label or Path(mount_path).name),
            )
            mount_id = cursor.lastrowid

        await db.commit()
        return mount_id


if __name__ == "__main__":
    # Example usage for testing
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python -m backend.metadata.indexer <mount_path>")
            sys.exit(1)

        mount_path = Path(sys.argv[1])
        if not mount_path.exists():
            print(f"Error: {mount_path} does not exist")
            sys.exit(1)

        db_path = Path("womcast.db")
        await init_database(db_path)

        mount_id = await initialize_mount_point(
            db_path, str(mount_path), mount_path.name
        )
        logger.info(f"Initialized mount point {mount_path} (ID: {mount_id})")

        scanned, indexed = await scan_mount_point(db_path, mount_path, mount_id)
        logger.info(f"Scan complete: {indexed}/{scanned} files indexed")

        deleted = await detect_deleted_files(db_path, mount_id)
        logger.info(f"Cleanup: {deleted} deleted files removed")

    asyncio.run(main())
