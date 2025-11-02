"""
WomCast Live TV Module
M3U/HLS/DASH ingest for live streaming channels.

This module provides legal live TV streaming support through:
- M3U/M3U8 playlist parsing
- HLS (HTTP Live Streaming) validation
- DASH (Dynamic Adaptive Streaming over HTTP) validation
- Channel persistence to SQLite database
- REST API for playlist management

All content is user-provided. No third-party streaming services are
included by default. Users must supply their own legal M3U playlists.
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp


@dataclass
class Channel:
    """Live TV channel from M3U playlist."""

    name: str
    stream_url: str
    logo_url: str | None = None
    group_title: str | None = None
    language: str | None = None
    tvg_id: str | None = None  # EPG ID for future EPG integration
    codec_info: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "stream_url": self.stream_url,
            "logo_url": self.logo_url,
            "group_title": self.group_title,
            "language": self.language,
            "tvg_id": self.tvg_id,
            "codec_info": self.codec_info,
        }


class M3UParser:
    """Parser for M3U/M3U8 playlist files."""

    # EXTINF line format: #EXTINF:duration tvg-id="..." tvg-name="..." tvg-logo="..." group-title="...",Channel Name
    EXTINF_PATTERN = re.compile(
        r'#EXTINF:(?P<duration>-?\d+)'
        r'(?:\s+tvg-id="(?P<tvg_id>[^"]*)")?'
        r'(?:\s+tvg-name="(?P<tvg_name>[^"]*)")?'
        r'(?:\s+tvg-logo="(?P<logo>[^"]*)")?'
        r'(?:\s+group-title="(?P<group>[^"]*)")?'
        r'(?:\s+language="(?P<language>[^"]*)")?'
        r'(?:\s+CUID="(?P<cuid>[^"]*)")?'
        r'(?:\s+CODEC="(?P<codec>[^"]*)")?'
        r',(?P<name>.*)',
        re.IGNORECASE,
    )

    @staticmethod
    def parse(content: str) -> list[Channel]:
        """
        Parse M3U playlist content into list of channels.

        Args:
            content: M3U file content as string

        Returns:
            List of Channel objects
        """
        channels: list[Channel] = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and comments (except EXTINF)
            if not line or (line.startswith("#") and not line.startswith("#EXTINF")):
                i += 1
                continue

            # Parse EXTINF directive
            if line.startswith("#EXTINF"):
                match = M3UParser.EXTINF_PATTERN.match(line)
                if match:
                    # Get stream URL from next non-empty, non-comment line
                    stream_url = ""
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith("#"):
                            stream_url = next_line
                            break
                        j += 1

                    if stream_url:
                        channel = Channel(
                            name=match.group("name").strip(),
                            stream_url=stream_url,
                            logo_url=match.group("logo") or None,
                            group_title=match.group("group") or None,
                            language=match.group("language") or None,
                            tvg_id=match.group("tvg_id") or None,
                            codec_info=match.group("codec") or None,
                        )
                        channels.append(channel)
                        i = j + 1
                        continue

            i += 1

        return channels


class StreamValidator:
    """Validates HLS and DASH stream URLs."""

    HLS_EXTENSIONS = [".m3u8", ".m3u"]
    DASH_EXTENSIONS = [".mpd"]

    @staticmethod
    def is_hls(url: str) -> bool:
        """Check if URL is HLS stream."""
        return any(url.lower().endswith(ext) for ext in StreamValidator.HLS_EXTENSIONS)

    @staticmethod
    def is_dash(url: str) -> bool:
        """Check if URL is DASH stream."""
        return any(url.lower().endswith(ext) for ext in StreamValidator.DASH_EXTENSIONS)

    @staticmethod
    def is_supported(url: str) -> bool:
        """Check if URL is a supported stream format."""
        return StreamValidator.is_hls(url) or StreamValidator.is_dash(url)

    @staticmethod
    async def validate_url(url: str, timeout: int = 5) -> bool:
        """
        Validate stream URL is reachable.

        Args:
            url: Stream URL to validate
            timeout: Request timeout in seconds

        Returns:
            True if URL is reachable, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url, timeout=aiohttp.ClientTimeout(total=timeout), allow_redirects=True
                ) as response:
                    return response.status == 200
        except Exception:
            return False


class LiveTVManager:
    """Manages live TV channels and playlists."""

    def __init__(self, db_path: Path):
        """
        Initialize LiveTV manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

    async def init_database(self) -> None:
        """Initialize channels table in database."""
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    stream_url TEXT NOT NULL UNIQUE,
                    logo_url TEXT,
                    group_title TEXT,
                    language TEXT,
                    tvg_id TEXT,
                    codec_info TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_validated_at TEXT,
                    UNIQUE(stream_url)
                )
            """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_channels_name ON channels(name)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_channels_group ON channels(group_title)"
            )
            await db.commit()

    async def add_playlist(
        self, content: str, validate_streams: bool = False
    ) -> dict[str, Any]:
        """
        Parse and persist M3U playlist.

        Args:
            content: M3U file content
            validate_streams: Whether to validate stream URLs

        Returns:
            Dictionary with added/updated/skipped counts
        """
        import aiosqlite

        channels = M3UParser.parse(content)
        added = 0
        updated = 0
        skipped = 0

        async with aiosqlite.connect(self.db_path) as db:
            for channel in channels:
                # Validate stream format
                if not StreamValidator.is_supported(channel.stream_url):
                    skipped += 1
                    continue

                # Optional URL validation
                if validate_streams:
                    if not await StreamValidator.validate_url(channel.stream_url):
                        skipped += 1
                        continue

                # Insert or update channel
                now = datetime.now(timezone.UTC).isoformat()
                try:
                    await db.execute(
                        """
                        INSERT INTO channels (name, stream_url, logo_url, group_title, language, tvg_id, codec_info, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(stream_url) DO UPDATE SET
                            name = excluded.name,
                            logo_url = excluded.logo_url,
                            group_title = excluded.group_title,
                            language = excluded.language,
                            tvg_id = excluded.tvg_id,
                            codec_info = excluded.codec_info
                    """,
                        (
                            channel.name,
                            channel.stream_url,
                            channel.logo_url,
                            channel.group_title,
                            channel.language,
                            channel.tvg_id,
                            channel.codec_info,
                            now,
                        ),
                    )
                    if db.total_changes > 0:
                        added += 1
                    else:
                        updated += 1
                except Exception:
                    skipped += 1

            await db.commit()

        return {"added": added, "updated": updated, "skipped": skipped}

    async def get_channels(
        self, group_title: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get list of channels.

        Args:
            group_title: Optional filter by group title
            limit: Maximum number of channels to return

        Returns:
            List of channel dictionaries
        """
        import aiosqlite

        query = "SELECT id, name, stream_url, logo_url, group_title, language, tvg_id, codec_info FROM channels WHERE is_active = 1"
        params: list[Any] = []

        if group_title:
            query += " AND group_title = ?"
            params.append(group_title)

        query += " ORDER BY name ASC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_channel(self, channel_id: int) -> dict[str, Any] | None:
        """
        Get single channel by ID.

        Args:
            channel_id: Channel ID

        Returns:
            Channel dictionary or None if not found
        """
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, stream_url, logo_url, group_title, language, tvg_id, codec_info FROM channels WHERE id = ? AND is_active = 1",
                (channel_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None


# CLI for testing
if __name__ == "__main__":
    import sys

    async def test_parser():
        """Test M3U parser with sample content."""
        sample_m3u = """#EXTM3U
#EXTINF:-1 tvg-id="news1" tvg-name="News Channel" tvg-logo="http://example.com/logo.png" group-title="News" language="en",News Channel
https://example.com/news/playlist.m3u8
#EXTINF:-1 tvg-id="sports1" tvg-name="Sports Channel" group-title="Sports",Sports Channel
https://example.com/sports/manifest.mpd
"""
        channels = M3UParser.parse(sample_m3u)
        print(f"Parsed {len(channels)} channels:")
        for ch in channels:
            print(f"  - {ch.name}: {ch.stream_url}")
            print(f"    Group: {ch.group_title}, Logo: {ch.logo_url}")

    asyncio.run(test_parser())
