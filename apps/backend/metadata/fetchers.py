"""Metadata fetchers for artwork and media information.

Uses only legal, publicly accessible APIs:
- TMDB (The Movie Database) for movies/TV shows
- MusicBrainz for music metadata
- Open-source, free APIs with proper attribution

All fetchers respect opt-out settings and rate limits.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Legal metadata sources
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"

# Rate limiting (requests per second)
TMDB_RATE_LIMIT = 4  # 40 requests per 10 seconds
MUSICBRAINZ_RATE_LIMIT = 1  # 1 request per second


@dataclass
class MetadataConfig:
    """Configuration for metadata fetching."""

    enabled: bool = True
    tmdb_api_key: str | None = None
    use_tmdb: bool = True
    use_musicbrainz: bool = True
    cache_ttl_days: int = 90
    rate_limit_enabled: bool = True


@dataclass
class VideoMetadata:
    """Video metadata from TMDB."""

    title: str | None = None
    year: int | None = None
    genre: str | None = None
    director: str | None = None
    cast: list[str] | None = None
    plot: str | None = None
    rating: float | None = None
    imdb_id: str | None = None
    tmdb_id: int | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    language: str | None = None


@dataclass
class AudioMetadata:
    """Music metadata from MusicBrainz."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    year: int | None = None
    genre: str | None = None
    musicbrainz_id: str | None = None


class MetadataFetcher:
    """Base class for metadata fetchers."""

    def __init__(self, config: MetadataConfig):
        self.config = config
        self.session: aiohttp.ClientSession | None = None
        self._last_request_time = 0.0
        self._rate_limit = 1.0

    async def __aenter__(self) -> "MetadataFetcher":
        """Create HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                "User-Agent": "WomCast/1.0 (https://github.com/LackOfSkillz/WomCast)"
            },
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _rate_limit_wait(self) -> None:
        """Wait to respect rate limits."""
        if not self.config.rate_limit_enabled:
            return

        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time

        if time_since_last < self._rate_limit:
            wait_time = self._rate_limit - time_since_last
            await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()


class TMDBFetcher(MetadataFetcher):
    """Fetches movie/TV metadata from TMDB API.

    Requires API key: https://www.themoviedb.org/settings/api
    Free tier: 40 requests per 10 seconds
    """

    def __init__(self, config: MetadataConfig):
        super().__init__(config)
        self._rate_limit = 1.0 / TMDB_RATE_LIMIT

    async def __aenter__(self) -> "TMDBFetcher":
        """Create HTTP session."""
        await super().__aenter__()
        return self

    async def search_movie(self, title: str, year: int | None = None) -> list[dict[str, Any]]:
        """Search for movies by title.

        Args:
            title: Movie title to search for
            year: Optional year to narrow results

        Returns:
            List of search results with id, title, year, poster_path
        """
        if not self.config.use_tmdb or not self.config.tmdb_api_key:
            logger.warning("TMDB disabled or API key not configured")
            return []

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        params: dict[str, Any] = {
            "api_key": self.config.tmdb_api_key,
            "query": title,
        }
        if year:
            params["year"] = year

        try:
            async with self.session.get(
                f"{TMDB_API_BASE}/search/movie", params=params
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("results", [])  # type: ignore
                else:
                    logger.error(f"TMDB search failed: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"TMDB search error: {e}")
            return []

    async def get_movie_details(self, tmdb_id: int) -> VideoMetadata | None:
        """Get detailed movie information.

        Args:
            tmdb_id: TMDB movie ID

        Returns:
            VideoMetadata object or None if not found
        """
        if not self.config.use_tmdb or not self.config.tmdb_api_key:
            return None

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        try:
            async with self.session.get(
                f"{TMDB_API_BASE}/movie/{tmdb_id}",
                params={
                    "api_key": self.config.tmdb_api_key,
                    "append_to_response": "credits,external_ids",
                },
            ) as resp:
                if resp.status != 200:
                    logger.error(f"TMDB details failed: {resp.status}")
                    return None

                data = await resp.json()

                # Extract cast (first 10 actors)
                cast = []
                if "credits" in data and "cast" in data["credits"]:
                    cast = [actor["name"] for actor in data["credits"]["cast"][:10]]

                # Extract director
                director = None
                if "credits" in data and "crew" in data["credits"]:
                    for crew in data["credits"]["crew"]:
                        if crew["job"] == "Director":
                            director = crew["name"]
                            break

                # Build poster/backdrop URLs
                poster_url = None
                if data.get("poster_path"):
                    poster_url = f"{TMDB_IMAGE_BASE}/w500{data['poster_path']}"

                backdrop_url = None
                if data.get("backdrop_path"):
                    backdrop_url = f"{TMDB_IMAGE_BASE}/original{data['backdrop_path']}"

                # Extract genre (first one)
                genre = None
                if data.get("genres") and len(data["genres"]) > 0:
                    genre = data["genres"][0]["name"]

                # Extract year from release_date
                year = None
                if data.get("release_date"):
                    try:
                        year = int(data["release_date"][:4])
                    except (ValueError, IndexError):
                        pass

                # Get IMDb ID from external_ids
                imdb_id = None
                if "external_ids" in data:
                    imdb_id = data["external_ids"].get("imdb_id")

                return VideoMetadata(
                    title=data.get("title"),
                    year=year,
                    genre=genre,
                    director=director,
                    cast=cast if cast else None,
                    plot=data.get("overview"),
                    rating=data.get("vote_average"),
                    imdb_id=imdb_id,
                    tmdb_id=tmdb_id,
                    poster_url=poster_url,
                    backdrop_url=backdrop_url,
                    language=data.get("original_language"),
                )

        except Exception as e:
            logger.error(f"TMDB details error: {e}")
            return None

    async def search_and_fetch(
        self, title: str, year: int | None = None
    ) -> VideoMetadata | None:
        """Search for a movie and fetch its details.

        Args:
            title: Movie title
            year: Optional year to narrow results

        Returns:
            VideoMetadata for the best match, or None
        """
        results = await self.search_movie(title, year)
        if not results:
            return None

        # Use the first result (best match)
        best_match = results[0]
        return await self.get_movie_details(best_match["id"])


class MusicBrainzFetcher(MetadataFetcher):
    """Fetches music metadata from MusicBrainz API.

    Free, open-source music encyclopedia.
    Rate limit: 1 request per second (respectful crawling)
    """

    def __init__(self, config: MetadataConfig):
        super().__init__(config)
        self._rate_limit = 1.0 / MUSICBRAINZ_RATE_LIMIT

    async def __aenter__(self) -> "MusicBrainzFetcher":
        """Create HTTP session."""
        await super().__aenter__()
        return self

    async def search_recording(
        self, title: str, artist: str | None = None
    ) -> list[dict[str, Any]]:
        """Search for music recordings.

        Args:
            title: Track title
            artist: Optional artist name to narrow results

        Returns:
            List of search results
        """
        if not self.config.use_musicbrainz:
            logger.warning("MusicBrainz disabled")
            return []

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        # Build search query
        query = f'recording:"{title}"'
        if artist:
            query += f' AND artist:"{artist}"'

        try:
            async with self.session.get(
                f"{MUSICBRAINZ_API_BASE}/recording",
                params={"query": query, "fmt": "json", "limit": 5},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("recordings", [])  # type: ignore
                else:
                    logger.error(f"MusicBrainz search failed: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"MusicBrainz search error: {e}")
            return []

    async def get_recording_details(self, mbid: str) -> AudioMetadata | None:
        """Get detailed recording information.

        Args:
            mbid: MusicBrainz recording ID

        Returns:
            AudioMetadata object or None
        """
        if not self.config.use_musicbrainz:
            return None

        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        try:
            async with self.session.get(
                f"{MUSICBRAINZ_API_BASE}/recording/{mbid}",
                params={"fmt": "json", "inc": "artists+releases+genres"},
            ) as resp:
                if resp.status != 200:
                    logger.error(f"MusicBrainz details failed: {resp.status}")
                    return None

                data = await resp.json()

                # Extract artist
                artist = None
                if data.get("artist-credit"):
                    artist = data["artist-credit"][0]["artist"]["name"]

                # Extract album from first release
                album = None
                album_artist = None
                year = None
                if data.get("releases") and len(data["releases"]) > 0:
                    release = data["releases"][0]
                    album = release.get("title")
                    if release.get("date"):
                        try:
                            year = int(release["date"][:4])
                        except (ValueError, IndexError):
                            pass

                # Extract genre (first one)
                genre = None
                if data.get("genres") and len(data["genres"]) > 0:
                    genre = data["genres"][0]["name"]

                return AudioMetadata(
                    title=data.get("title"),
                    artist=artist,
                    album=album,
                    album_artist=album_artist or artist,
                    year=year,
                    genre=genre,
                    musicbrainz_id=mbid,
                )

        except Exception as e:
            logger.error(f"MusicBrainz details error: {e}")
            return None


async def load_config(config_path: Path) -> MetadataConfig:
    """Load metadata fetcher configuration from JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        MetadataConfig object
    """
    if not config_path.exists():
        # Return default config
        return MetadataConfig()

    try:
        with open(config_path) as f:
            data = json.load(f)
            return MetadataConfig(**data)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return MetadataConfig()


async def save_config(config: MetadataConfig, config_path: Path) -> None:
    """Save metadata fetcher configuration to JSON file.

    Args:
        config: MetadataConfig object
        config_path: Path to save configuration
    """
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(
                {
                    "enabled": config.enabled,
                    "tmdb_api_key": config.tmdb_api_key,
                    "use_tmdb": config.use_tmdb,
                    "use_musicbrainz": config.use_musicbrainz,
                    "cache_ttl_days": config.cache_ttl_days,
                    "rate_limit_enabled": config.rate_limit_enabled,
                },
                f,
                indent=2,
            )
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")


async def sanitize_cache(
    db_path: Path, older_than_days: int = 90
) -> tuple[int, int]:
    """Remove old metadata cache entries.

    Args:
        db_path: Path to SQLite database
        older_than_days: Remove entries older than this many days

    Returns:
        Tuple of (videos_cleared, audio_cleared)
    """
    import aiosqlite

    threshold = datetime.now(UTC).replace(
        day=datetime.now(UTC).day - older_than_days
    ).isoformat()

    videos_cleared = 0
    audio_cleared = 0

    try:
        async with aiosqlite.connect(db_path) as db:
            # Clear old video metadata
            cursor = await db.execute(
                """
                UPDATE videos
                SET poster_url = NULL,
                    backdrop_url = NULL,
                    plot = NULL,
                    director = NULL,
                    cast = NULL,
                    genre = NULL,
                    rating = NULL
                WHERE id IN (
                    SELECT v.id FROM videos v
                    JOIN media_files mf ON v.media_file_id = mf.id
                    WHERE mf.indexed_at < ?
                )
                """,
                (threshold,),
            )
            videos_cleared = cursor.rowcount

            # No need to clear audio metadata as MusicBrainz data is stable
            # and doesn't have artwork URLs

            await db.commit()

            logger.info(
                f"Cache sanitization: {videos_cleared} video entries, "
                f"{audio_cleared} audio entries"
            )

    except Exception as e:
        logger.error(f"Cache sanitization error: {e}")

    return videos_cleared, audio_cleared


if __name__ == "__main__":
    # Example usage for testing
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def main() -> None:
        if len(sys.argv) < 2:
            print("Usage: python -m metadata.fetchers <command> [args]")
            print("Commands:")
            print("  search-movie <title> [year]")
            print("  search-music <title> [artist]")
            print("  sanitize <db_path> [days]")
            sys.exit(1)

        command = sys.argv[1]

        if command == "search-movie":
            title = sys.argv[2]
            year = int(sys.argv[3]) if len(sys.argv) > 3 else None

            config = await load_config(Path("metadata_config.json"))
            if not config.tmdb_api_key:
                print("Error: TMDB API key not configured")
                print("Set TMDB_API_KEY in metadata_config.json")
                sys.exit(1)

            async with TMDBFetcher(config) as fetcher:
                metadata = await fetcher.search_and_fetch(title, year)
                if metadata:
                    print(f"Title: {metadata.title}")
                    print(f"Year: {metadata.year}")
                    print(f"Genre: {metadata.genre}")
                    print(f"Director: {metadata.director}")
                    print(f"Rating: {metadata.rating}")
                    print(f"TMDB ID: {metadata.tmdb_id}")
                    print(f"IMDb ID: {metadata.imdb_id}")
                    print(f"Poster: {metadata.poster_url}")
                else:
                    print("No results found")

        elif command == "search-music":
            title = sys.argv[2]
            artist = sys.argv[3] if len(sys.argv) > 3 else None

            config = await load_config(Path("metadata_config.json"))

            async with MusicBrainzFetcher(config) as fetcher:
                results = await fetcher.search_recording(title, artist)
                if results:
                    print(f"Found {len(results)} results:")
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. {result.get('title', 'Unknown')}")
                        if result.get("artist-credit"):
                            artist_name = result["artist-credit"][0]["artist"]["name"]
                            print(f"   Artist: {artist_name}")
                        print(f"   MBID: {result['id']}")
                else:
                    print("No results found")

        elif command == "sanitize":
            db_path = Path(sys.argv[2])
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 90

            videos, audio = await sanitize_cache(db_path, days)
            print(f"Sanitized: {videos} videos, {audio} audio entries")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    asyncio.run(main())
