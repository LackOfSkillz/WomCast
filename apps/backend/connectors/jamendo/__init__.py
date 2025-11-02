"""Jamendo connector for WomCast.

Provides access to free Creative Commons music from Jamendo.
Uses Jamendo API: https://developer.jamendo.com/v3.0

Legal compliance:
- Only accesses music licensed under Creative Commons
- Respects Jamendo API terms and rate limits
- Attribution preserved in metadata
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Jamendo API endpoints
JAMENDO_API_BASE = "https://api.jamendo.com/v3.0"
JAMENDO_TRACKS_URL = f"{JAMENDO_API_BASE}/tracks"
JAMENDO_ALBUMS_URL = f"{JAMENDO_API_BASE}/albums"

# Jamendo API client ID (public demo key - replace with your own for production)
# Get your own key at: https://developer.jamendo.com/v3.0/docs
JAMENDO_CLIENT_ID = "56d30c95"  # Demo client ID

# Rate limiting (requests per second)
JAMENDO_RATE_LIMIT = 2.0


@dataclass
class JamendoTrack:
    """Jamendo music track metadata."""

    id: str
    name: str
    artist_name: str
    album_name: str | None = None
    duration: int | None = None  # seconds
    license_ccurl: str | None = None
    audio_url: str | None = None  # Stream URL
    image_url: str | None = None
    releasedate: str | None = None
    genre: str | None = None


class JamendoConnector:
    """Connector to Jamendo free Creative Commons music."""

    def __init__(self, client_id: str = JAMENDO_CLIENT_ID):
        self.client_id = client_id
        self.session: aiohttp.ClientSession | None = None
        self._last_request_time = 0.0
        self._rate_limit = 1.0 / JAMENDO_RATE_LIMIT

    async def __aenter__(self) -> "JamendoConnector":
        """Create HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "WomCast/1.0 (https://github.com/LackOfSkillz/WomCast)"},
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _rate_limit_wait(self) -> None:
        """Wait to respect rate limits."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time

        if time_since_last < self._rate_limit:
            wait_time = self._rate_limit - time_since_last
            await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()

    async def get_popular(self, limit: int = 20) -> list[JamendoTrack]:
        """Get popular tracks from Jamendo.

        Args:
            limit: Maximum number of tracks to return

        Returns:
            List of JamendoTrack objects
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        params = {
            "client_id": self.client_id,
            "format": "json",
            "limit": limit,
            "order": "popularity_total",
            "include": "licenses",
            "audioformat": "mp31",  # MP3 128kbps
        }

        try:
            async with self.session.get(JAMENDO_TRACKS_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Jamendo popular tracks failed: {resp.status}")
                    return []

                data = await resp.json()
                tracks_data = data.get("results", [])

                tracks = []
                for track in tracks_data:
                    tracks.append(
                        JamendoTrack(
                            id=str(track.get("id", "")),
                            name=track.get("name", "Unknown"),
                            artist_name=track.get("artist_name", "Unknown Artist"),
                            album_name=track.get("album_name"),
                            duration=track.get("duration"),
                            license_ccurl=track.get("license_ccurl"),
                            audio_url=track.get("audio"),
                            image_url=track.get("image"),
                            releasedate=track.get("releasedate"),
                        )
                    )

                logger.info(f"Retrieved {len(tracks)} popular Jamendo tracks")
                return tracks

        except Exception as e:
            logger.error(f"Jamendo popular tracks error: {e}")
            return []

    async def search(
        self, query: str, limit: int = 20, genre: str | None = None
    ) -> list[JamendoTrack]:
        """Search Jamendo tracks.

        Args:
            query: Search query string
            limit: Maximum number of results
            genre: Optional genre filter

        Returns:
            List of JamendoTrack objects matching the query
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        params = {
            "client_id": self.client_id,
            "format": "json",
            "limit": limit,
            "search": query,
            "include": "licenses",
            "audioformat": "mp31",
        }

        if genre:
            params["tags"] = genre

        try:
            async with self.session.get(JAMENDO_TRACKS_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Jamendo search failed: {resp.status}")
                    return []

                data = await resp.json()
                tracks_data = data.get("results", [])

                tracks = []
                for track in tracks_data:
                    tracks.append(
                        JamendoTrack(
                            id=str(track.get("id", "")),
                            name=track.get("name", "Unknown"),
                            artist_name=track.get("artist_name", "Unknown Artist"),
                            album_name=track.get("album_name"),
                            duration=track.get("duration"),
                            license_ccurl=track.get("license_ccurl"),
                            audio_url=track.get("audio"),
                            image_url=track.get("image"),
                            releasedate=track.get("releasedate"),
                        )
                    )

                logger.info(f"Found {len(tracks)} Jamendo tracks for query: {query}")
                return tracks

        except Exception as e:
            logger.error(f"Jamendo search error: {e}")
            return []

    async def get_track_details(self, track_id: str) -> JamendoTrack | None:
        """Get detailed information for a specific track.

        Args:
            track_id: Jamendo track identifier

        Returns:
            JamendoTrack with full details, or None if not found
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        params = {
            "client_id": self.client_id,
            "format": "json",
            "id": track_id,
            "include": "licenses",
            "audioformat": "mp31",
        }

        try:
            async with self.session.get(JAMENDO_TRACKS_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Jamendo track details failed: {resp.status}")
                    return None

                data = await resp.json()
                tracks_data = data.get("results", [])

                if not tracks_data:
                    return None

                track = tracks_data[0]
                return JamendoTrack(
                    id=str(track.get("id", "")),
                    name=track.get("name", "Unknown"),
                    artist_name=track.get("artist_name", "Unknown Artist"),
                    album_name=track.get("album_name"),
                    duration=track.get("duration"),
                    license_ccurl=track.get("license_ccurl"),
                    audio_url=track.get("audio"),
                    image_url=track.get("image"),
                    releasedate=track.get("releasedate"),
                )

        except Exception as e:
            logger.error(f"Jamendo track details error: {e}")
            return None


if __name__ == "__main__":
    # Example usage for testing
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def main() -> None:
        if len(sys.argv) < 2:
            print("Usage: python -m connectors.jamendo <command> [args]")
            print("Commands:")
            print("  popular [limit]    - Get popular tracks")
            print("  search <query>     - Search tracks")
            print("  details <id>       - Get track details")
            sys.exit(1)

        command = sys.argv[1]

        async with JamendoConnector() as connector:
            if command == "popular":
                limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
                tracks = await connector.get_popular(limit=limit)

                print(f"\nPopular Jamendo Tracks ({len(tracks)}):\n")
                for i, track in enumerate(tracks, 1):
                    print(f"{i}. {track.name}")
                    print(f"   Artist: {track.artist_name}")
                    if track.album_name:
                        print(f"   Album: {track.album_name}")
                    if track.duration:
                        mins = track.duration // 60
                        secs = track.duration % 60
                        print(f"   Duration: {mins}:{secs:02d}")
                    print(f"   License: {track.license_ccurl}")
                    print()

            elif command == "search":
                if len(sys.argv) < 3:
                    print("Error: search query required")
                    sys.exit(1)

                query = sys.argv[2]
                tracks = await connector.search(query=query, limit=10)

                print(f"\nJamendo Search: '{query}' ({len(tracks)} results)\n")
                for i, track in enumerate(tracks, 1):
                    print(f"{i}. {track.name} - {track.artist_name}")
                    if track.duration:
                        mins = track.duration // 60
                        secs = track.duration % 60
                        print(f"   Duration: {mins}:{secs:02d}")
                    print()

            elif command == "details":
                if len(sys.argv) < 3:
                    print("Error: track ID required")
                    sys.exit(1)

                track_id = sys.argv[2]
                track = await connector.get_track_details(track_id)

                if track:
                    print(f"\nTrack: {track.name}")
                    print(f"Artist: {track.artist_name}")
                    if track.album_name:
                        print(f"Album: {track.album_name}")
                    if track.duration:
                        mins = track.duration // 60
                        secs = track.duration % 60
                        print(f"Duration: {mins}:{secs:02d}")
                    print(f"License: {track.license_ccurl}")
                    print(f"Audio URL: {track.audio_url}")
                else:
                    print(f"Track not found: {track_id}")

            else:
                print(f"Unknown command: {command}")
                sys.exit(1)

    asyncio.run(main())
