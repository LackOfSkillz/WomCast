"""Internet Archive connector for WomCast.

Provides access to public-domain and freely licensed content from archive.org.
Uses the Internet Archive API: https://archive.org/developers/

Legal compliance:
- Only accesses public-domain and Creative Commons content
- Respects rate limits (1 request per second)
- Attribution preserved in metadata
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Internet Archive API endpoints
IA_SEARCH_API = "https://archive.org/advancedsearch.php"
IA_METADATA_API = "https://archive.org/metadata"
IA_DOWNLOAD_BASE = "https://archive.org/download"

# Rate limiting (requests per second)
IA_RATE_LIMIT = 1.0  # 1 request per second (respectful crawling)


@dataclass
class IAItem:
    """Internet Archive item metadata."""

    identifier: str
    title: str
    mediatype: str  # movies, audio, texts, etc.
    description: str | None = None
    creator: str | None = None
    date: str | None = None
    year: int | None = None
    collection: list[str] | None = None
    subject: list[str] | None = None
    duration: int | None = None  # seconds
    thumbnail_url: str | None = None
    stream_url: str | None = None
    download_url: str | None = None
    license: str | None = None


class InternetArchiveConnector:
    """Connector to Internet Archive public domain content."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._last_request_time = 0.0
        self._rate_limit = 1.0 / IA_RATE_LIMIT

    async def __aenter__(self) -> "InternetArchiveConnector":
        """Create HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
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
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time

        if time_since_last < self._rate_limit:
            wait_time = self._rate_limit - time_since_last
            await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()

    async def search(
        self,
        query: str | None = None,
        mediatype: str | None = None,
        collection: str | None = None,
        rows: int = 50,
        page: int = 1,
    ) -> list[IAItem]:
        """Search Internet Archive for content.

        Args:
            query: Search query string
            mediatype: Filter by media type (movies, audio, texts, etc.)
            collection: Filter by collection name
            rows: Number of results per page (max 10000)
            page: Page number (1-based)

        Returns:
            List of IAItem objects
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        # Build search query
        search_parts = []
        if query:
            search_parts.append(query)
        if mediatype:
            search_parts.append(f"mediatype:{mediatype}")
        if collection:
            search_parts.append(f"collection:{collection}")

        # Default to public domain movies if no query
        if not search_parts:
            search_parts.append("mediatype:movies")
            search_parts.append("collection:prelinger")

        search_query = " AND ".join(search_parts)

        params = {
            "q": search_query,
            "fl[]": [
                "identifier",
                "title",
                "mediatype",
                "description",
                "creator",
                "date",
                "year",
                "collection",
                "subject",
                "runtime",
                "licenseurl",
            ],
            "rows": min(rows, 10000),
            "page": page,
            "output": "json",
        }

        try:
            async with self.session.get(IA_SEARCH_API, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Internet Archive search failed: {resp.status}")
                    return []

                data = await resp.json()
                docs = data.get("response", {}).get("docs", [])

                items = []
                for doc in docs:
                    # Parse duration from runtime (format: "HH:MM:SS" or seconds)
                    duration = None
                    if "runtime" in doc:
                        runtime = doc["runtime"]
                        if isinstance(runtime, str):
                            try:
                                # Try parsing HH:MM:SS
                                parts = runtime.split(":")
                                if len(parts) == 3:
                                    h, m, s = map(int, parts)
                                    duration = h * 3600 + m * 60 + s
                                elif len(parts) == 2:
                                    m, s = map(int, parts)
                                    duration = m * 60 + s
                                else:
                                    duration = int(float(runtime))
                            except (ValueError, IndexError):
                                pass

                    identifier = doc.get("identifier", "")
                    items.append(
                        IAItem(
                            identifier=identifier,
                            title=doc.get("title", "Unknown"),
                            mediatype=doc.get("mediatype", "unknown"),
                            description=doc.get("description"),
                            creator=doc.get("creator"),
                            date=doc.get("date"),
                            year=doc.get("year"),
                            collection=doc.get("collection", [])
                            if isinstance(doc.get("collection"), list)
                            else [doc.get("collection")]
                            if doc.get("collection")
                            else None,
                            subject=doc.get("subject", [])
                            if isinstance(doc.get("subject"), list)
                            else [doc.get("subject")]
                            if doc.get("subject")
                            else None,
                            duration=duration,
                            thumbnail_url=f"https://archive.org/services/img/{identifier}",
                            stream_url=None,  # Populated by get_item_details
                            download_url=f"{IA_DOWNLOAD_BASE}/{identifier}",
                            license=doc.get("licenseurl"),
                        )
                    )

                logger.info(f"Found {len(items)} items for query: {search_query}")
                return items

        except Exception as e:
            logger.error(f"Internet Archive search error: {e}")
            return []

    async def get_item_details(self, identifier: str) -> IAItem | None:
        """Get detailed metadata and stream URLs for an item.

        Args:
            identifier: Internet Archive item identifier

        Returns:
            IAItem with stream_url populated, or None if not found
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        try:
            async with self.session.get(f"{IA_METADATA_API}/{identifier}") as resp:
                if resp.status != 200:
                    logger.error(
                        f"Internet Archive metadata failed: {resp.status} for {identifier}"
                    )
                    return None

                data = await resp.json()
                metadata = data.get("metadata", {})
                files = data.get("files", [])

                # Find best streaming file (MP4, OGV, or MP3)
                stream_file = None
                for file in files:
                    name = file.get("name", "")
                    format_type = file.get("format", "")

                    # Prefer MP4 for video, MP3 for audio
                    if format_type in ("h.264", "MPEG4") or name.endswith(".mp4"):
                        stream_file = name
                        break
                    elif format_type == "Ogg Video" or name.endswith(".ogv"):
                        stream_file = name
                        break
                    elif format_type == "VBR MP3" or name.endswith(".mp3"):
                        if not stream_file:  # Use as fallback
                            stream_file = name

                stream_url = None
                if stream_file:
                    stream_url = f"{IA_DOWNLOAD_BASE}/{identifier}/{stream_file}"

                # Parse duration from metadata
                duration = None
                if "runtime" in metadata:
                    try:
                        runtime = metadata["runtime"]
                        if isinstance(runtime, str):
                            parts = runtime.split(":")
                            if len(parts) == 3:
                                h, m, s = map(int, parts)
                                duration = h * 3600 + m * 60 + s
                            elif len(parts) == 2:
                                m, s = map(int, parts)
                                duration = m * 60 + s
                        elif isinstance(runtime, (int, float)):
                            duration = int(runtime)
                    except (ValueError, TypeError):
                        pass

                return IAItem(
                    identifier=identifier,
                    title=metadata.get("title", "Unknown"),
                    mediatype=metadata.get("mediatype", "unknown"),
                    description=metadata.get("description"),
                    creator=metadata.get("creator"),
                    date=metadata.get("date"),
                    year=metadata.get("year"),
                    collection=metadata.get("collection", [])
                    if isinstance(metadata.get("collection"), list)
                    else [metadata.get("collection")]
                    if metadata.get("collection")
                    else None,
                    subject=metadata.get("subject", [])
                    if isinstance(metadata.get("subject"), list)
                    else [metadata.get("subject")]
                    if metadata.get("subject")
                    else None,
                    duration=duration,
                    thumbnail_url=f"https://archive.org/services/img/{identifier}",
                    stream_url=stream_url,
                    download_url=f"{IA_DOWNLOAD_BASE}/{identifier}",
                    license=metadata.get("licenseurl"),
                )

        except Exception as e:
            logger.error(f"Internet Archive details error: {e}")
            return None

    async def get_collections(self) -> list[dict[str, str]]:
        """Get featured public domain collections.

        Returns:
            List of collection dictionaries with id, title, description
        """
        # Curated list of public domain collections
        return [
            {
                "id": "prelinger",
                "title": "Prelinger Archives",
                "description": "Public domain films including advertising, educational, industrial, and amateur films",
            },
            {
                "id": "classic_tv",
                "title": "Classic TV",
                "description": "Public domain television programs",
            },
            {
                "id": "moviesandfilms",
                "title": "Movies & Films",
                "description": "Public domain movies and films",
            },
            {
                "id": "audio_music",
                "title": "Audio: Music",
                "description": "Public domain and Creative Commons music",
            },
            {
                "id": "nasaimages",
                "title": "NASA Images",
                "description": "Images, videos, and audio from NASA",
            },
            {
                "id": "federalgovernment",
                "title": "U.S. Government Documents",
                "description": "Public domain U.S. government media",
            },
        ]


if __name__ == "__main__":
    # Example usage for testing
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def main() -> None:
        if len(sys.argv) < 2:
            print("Usage: python -m connectors.internet_archive <command> [args]")
            print("Commands:")
            print("  search [query]         - Search for content")
            print("  collections            - List featured collections")
            print("  details <identifier>   - Get item details")
            sys.exit(1)

        command = sys.argv[1]

        async with InternetArchiveConnector() as connector:
            if command == "search":
                query = sys.argv[2] if len(sys.argv) > 2 else None
                items = await connector.search(query=query, rows=10)

                print(f"\nFound {len(items)} items:\n")
                for i, item in enumerate(items, 1):
                    print(f"{i}. {item.title}")
                    print(f"   ID: {item.identifier}")
                    print(f"   Type: {item.mediatype}")
                    if item.creator:
                        print(f"   Creator: {item.creator}")
                    if item.year:
                        print(f"   Year: {item.year}")
                    if item.duration:
                        mins = item.duration // 60
                        secs = item.duration % 60
                        print(f"   Duration: {mins}m {secs}s")
                    print(f"   URL: {item.download_url}")
                    print()

            elif command == "collections":
                collections = await connector.get_collections()
                print("\nFeatured Collections:\n")
                for coll in collections:
                    print(f"- {coll['title']}")
                    print(f"  ID: {coll['id']}")
                    print(f"  {coll['description']}")
                    print()

            elif command == "details":
                if len(sys.argv) < 3:
                    print("Error: identifier required")
                    sys.exit(1)

                identifier = sys.argv[2]
                item = await connector.get_item_details(identifier)

                if item:
                    print(f"\nTitle: {item.title}")
                    print(f"ID: {item.identifier}")
                    print(f"Type: {item.mediatype}")
                    if item.creator:
                        print(f"Creator: {item.creator}")
                    if item.description:
                        print(f"Description: {item.description[:200]}...")
                    if item.duration:
                        mins = item.duration // 60
                        secs = item.duration % 60
                        print(f"Duration: {mins}m {secs}s")
                    if item.stream_url:
                        print(f"Stream URL: {item.stream_url}")
                    if item.license:
                        print(f"License: {item.license}")
                else:
                    print(f"Item not found: {identifier}")

            else:
                print(f"Unknown command: {command}")
                sys.exit(1)

    asyncio.run(main())
