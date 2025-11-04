"""
WomCast Media Database Schema
SQLite database for local media library indexing and metadata.
"""

import os
from pathlib import Path

import aiosqlite

# Schema version for migrations
SCHEMA_VERSION = 1

# SQL schema definition
SCHEMA_SQL = """
-- Media Files (all types: video, audio, photos, games)
CREATE TABLE IF NOT EXISTS media_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT,  -- Fast hash for change detection (size:mtime)
    media_type TEXT NOT NULL CHECK(media_type IN ('video', 'audio', 'photo', 'game')),
    mime_type TEXT,
    mount_point_id INTEGER,  -- NULL for local files, ID for USB files
    duration_seconds INTEGER,  -- For video/audio
    width INTEGER,  -- For video/photo
    height INTEGER,  -- For video/photo
    bitrate INTEGER,  -- For video/audio
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    last_played_at TEXT,
    play_count INTEGER DEFAULT 0,
    resume_position_seconds INTEGER DEFAULT 0,
    UNIQUE(file_path),
    FOREIGN KEY (mount_point_id) REFERENCES mount_points(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_media_files_type ON media_files(media_type);
CREATE INDEX IF NOT EXISTS idx_media_files_name ON media_files(file_name);
CREATE INDEX IF NOT EXISTS idx_media_files_indexed ON media_files(indexed_at DESC);

-- Video Metadata
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY,
    media_file_id INTEGER NOT NULL UNIQUE,
    title TEXT,
    year INTEGER,
    genre TEXT,
    director TEXT,
    cast TEXT,  -- JSON array
    plot TEXT,
    rating REAL,
    imdb_id TEXT,
    tmdb_id INTEGER,
    poster_url TEXT,
    backdrop_url TEXT,
    video_codec TEXT,
    audio_codec TEXT,
    subtitle_tracks TEXT,  -- JSON array
    language TEXT,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_videos_title ON videos(title);
CREATE INDEX IF NOT EXISTS idx_videos_year ON videos(year);
CREATE INDEX IF NOT EXISTS idx_videos_genre ON videos(genre);

-- TV Episodes
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    media_file_id INTEGER NOT NULL UNIQUE,
    series_title TEXT NOT NULL,
    season_number INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    episode_title TEXT,
    air_date TEXT,
    plot TEXT,
    tvdb_id INTEGER,
    tmdb_id INTEGER,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_title);
CREATE INDEX IF NOT EXISTS idx_episodes_season ON episodes(series_title, season_number);

-- Audio Tracks (Music)
CREATE TABLE IF NOT EXISTS audio_tracks (
    id INTEGER PRIMARY KEY,
    media_file_id INTEGER NOT NULL UNIQUE,
    title TEXT NOT NULL,
    artist TEXT,
    album TEXT,
    album_artist TEXT,
    track_number INTEGER,
    disc_number INTEGER,
    year INTEGER,
    genre TEXT,
    duration_ms INTEGER,
    musicbrainz_id TEXT,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_audio_artist ON audio_tracks(artist);
CREATE INDEX IF NOT EXISTS idx_audio_album ON audio_tracks(album);
CREATE INDEX IF NOT EXISTS idx_audio_title ON audio_tracks(title);

-- Albums
CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    year INTEGER,
    genre TEXT,
    cover_url TEXT,
    musicbrainz_id TEXT,
    UNIQUE(title, artist)
);

CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist);

-- Artists
CREATE TABLE IF NOT EXISTS artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    bio TEXT,
    photo_url TEXT,
    musicbrainz_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_artists_name ON artists(name);

-- Photos
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    media_file_id INTEGER NOT NULL UNIQUE,
    title TEXT,
    description TEXT,
    date_taken TEXT,
    camera_make TEXT,
    camera_model TEXT,
    latitude REAL,
    longitude REAL,
    orientation INTEGER,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_photos_date ON photos(date_taken DESC);

-- Games (ROMs/ISOs)
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    media_file_id INTEGER NOT NULL UNIQUE,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,  -- nes, snes, genesis, ps1, etc.
    year INTEGER,
    publisher TEXT,
    genre TEXT,
    box_art_url TEXT,
    last_save_state TEXT,  -- Path to save state file
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_games_platform ON games(platform);
CREATE INDEX IF NOT EXISTS idx_games_title ON games(title);

-- Mount Points (USB drives)
CREATE TABLE IF NOT EXISTS mount_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mount_path TEXT NOT NULL UNIQUE,
    label TEXT,
    device TEXT,
    filesystem TEXT,
    total_bytes INTEGER,
    used_bytes INTEGER,
    mounted_at TEXT,
    last_scanned_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1  -- 0=unmounted, 1=active
);

-- Scan History
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mount_point_id INTEGER,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    files_scanned INTEGER DEFAULT 0,
    files_indexed INTEGER DEFAULT 0,
    files_added INTEGER DEFAULT 0,
    files_updated INTEGER DEFAULT 0,
    files_removed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
    error_message TEXT,
    FOREIGN KEY (mount_point_id) REFERENCES mount_points(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_scan_history_started ON scan_history(started_at DESC);

-- Playlists
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Playlist Items
CREATE TABLE IF NOT EXISTS playlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    media_file_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE CASCADE,
    UNIQUE(playlist_id, position)
);

-- Schema Metadata
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_metadata (key, value) VALUES ('version', '1');
INSERT OR IGNORE INTO schema_metadata (key, value) VALUES ('created_at', datetime('now'));
"""


def get_db_path() -> Path:
    """Resolve path to the metadata database."""

    env_path = os.environ.get("MEDIA_DB_PATH") or os.environ.get("METADATA_DB_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).parent.parent / "womcast.db"


async def init_database(db_path: Path | None = None) -> None:
    """Initialize database with schema and enable WAL mode."""
    resolved_path = db_path or get_db_path()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(resolved_path) as db:
        # Enable WAL mode for better concurrency and crash recovery
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA wal_autocheckpoint=1000")
        await db.execute("PRAGMA auto_vacuum=FULL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.executescript(SCHEMA_SQL)
        await db.commit()


async def get_schema_version(db_path: Path) -> int | None:
    """Get current schema version."""
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT value FROM schema_metadata WHERE key = 'version'"
            ) as cursor:
                row = await cursor.fetchone()
                return int(row[0]) if row else None
    except Exception:
        return None


async def migrate_schema(db_path: Path, from_version: int, to_version: int) -> None:
    """Run schema migrations."""
    # Placeholder for future migrations
    # Example: if from_version == 1 and to_version == 2: ...
    pass
