"""NASA TV connector for WomCast.

Provides access to free NASA live streams and archived content.
Uses NASA Image and Video Library API: https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf

Legal compliance:
- All NASA content is in the public domain (U.S. government work)
- No copyright restrictions (17 U.S.C. § 105)
- Attribution encouraged but not required
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# NASA API endpoints
NASA_IMAGES_API = "https://images-api.nasa.gov"
NASA_VIDEO_SEARCH = f"{NASA_IMAGES_API}/search"

# NASA TV live streams (public domain)
NASA_TV_STREAMS = {
    "nasa-tv-public": {
        "title": "NASA TV Public",
        "description": "NASA TV Public Channel - Live coverage of NASA missions and events",
        "stream_url": "https://ntv1.akamaized.net/hls/live/2014075/NASA-NTV1-HLS/master.m3u8",
    },
    "nasa-tv-media": {
        "title": "NASA TV Media",
        "description": "NASA TV Media Channel - Press conferences and media events",
        "stream_url": "https://ntv2.akamaized.net/hls/live/2013923/NASA-NTV2-HLS/master.m3u8",
    },
    "iss-hdev": {
        "title": "ISS HD Earth Viewing",
        "description": "Live view of Earth from the International Space Station",
        "stream_url": "https://isp.iss.gov/ISS/api/liveStreams/url/iss_hdev",
    },
}

# Rate limiting (requests per second)
NASA_RATE_LIMIT = 2.0


@dataclass
class NASAItem:
    """NASA media item metadata."""

    id: str
    title: str
    description: str | None = None
    media_type: str = "video"  # video, image, audio
    duration: int | None = None  # seconds (if video/audio)
    thumbnail_url: str | None = None
    stream_url: str | None = None
    date_created: str | None = None
    photographer: str | None = None
    keywords: list[str] | None = None
    is_live: bool = False


class NASAConnector:
    """Connector to NASA free content (live streams and archives)."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._last_request_time = 0.0
        self._rate_limit = 1.0 / NASA_RATE_LIMIT

    async def __aenter__(self) -> "NASAConnector":
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

    async def get_live_streams(self) -> list[NASAItem]:
        """Get NASA TV live streams.

        Returns:
            List of live stream NASAItem objects
        """
        items = []
        for stream_id, stream_data in NASA_TV_STREAMS.items():
            items.append(
                NASAItem(
                    id=stream_id,
                    title=stream_data["title"],
                    description=stream_data["description"],
                    media_type="video",
                    stream_url=stream_data["stream_url"],
                    is_live=True,
                )
            )

        logger.info(f"Retrieved {len(items)} NASA TV live streams")
        return items

    async def search(
        self, query: str = "apollo", media_type: str = "video", limit: int = 20
    ) -> list[NASAItem]:
        """Search NASA media archive.

        Args:
            query: Search query string
            media_type: Filter by media type (video, image, audio)
            limit: Maximum number of results

        Returns:
            List of NASAItem objects matching the query
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        params = {
            "q": query,
            "media_type": media_type,
            "page_size": limit,
        }

        try:
            async with self.session.get(NASA_VIDEO_SEARCH, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"NASA search failed: {resp.status}")
                    return []

                data = await resp.json()
                items_data = data.get("collection", {}).get("items", [])

                items = []
                for item_data in items_data:
                    item_info = item_data.get("data", [{}])[0]
                    links = item_data.get("links", [])

                    # Get thumbnail URL
                    thumbnail_url = None
                    for link in links:
                        if link.get("render") == "image":
                            thumbnail_url = link.get("href")
                            break

                    # Parse keywords
                    keywords = item_info.get("keywords", [])
                    if isinstance(keywords, list):
                        pass  # Already a list
                    elif isinstance(keywords, str):
                        keywords = [k.strip() for k in keywords.split(",")]
                    else:
                        keywords = []

                    nasa_id = item_info.get("nasa_id", "")
                    items.append(
                        NASAItem(
                            id=nasa_id,
                            title=item_info.get("title", "Unknown"),
                            description=item_info.get("description"),
                            media_type=item_info.get("media_type", media_type),
                            thumbnail_url=thumbnail_url,
                            date_created=item_info.get("date_created"),
                            photographer=item_info.get("photographer"),
                            keywords=keywords if keywords else None,
                            is_live=False,
                        )
                    )

                logger.info(f"Found {len(items)} NASA items for query: {query}")
                return items

        except Exception as e:
            logger.error(f"NASA search error: {e}")
            return []

    async def get_item_details(self, item_id: str) -> NASAItem | None:
        """Get detailed information and stream URL for an item.

        Args:
            item_id: NASA item identifier

        Returns:
            NASAItem with stream URL, or None if not found
        """
        # Check if it's a live stream
        if item_id in NASA_TV_STREAMS:
            stream_data = NASA_TV_STREAMS[item_id]
            return NASAItem(
                id=item_id,
                title=stream_data["title"],
                description=stream_data["description"],
                media_type="video",
                stream_url=stream_data["stream_url"],
                is_live=True,
            )

        # For archived content, get metadata and asset manifest
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        await self._rate_limit_wait()

        try:
            # Get asset manifest
            manifest_url = f"{NASA_IMAGES_API}/asset/{item_id}"
            async with self.session.get(manifest_url) as resp:
                if resp.status != 200:
                    logger.error(f"NASA asset manifest failed: {resp.status} for {item_id}")
                    return None

                data = await resp.json()
                items = data.get("collection", {}).get("items", [])

                # Find best video file (prefer MP4)
                video_url = None
                for item in items:
                    href = item.get("href", "")
                    if "orig.mp4" in href or ".mp4" in href:
                        video_url = href
                        break

                # If no MP4, try other formats
                if not video_url:
                    for item in items:
                        href = item.get("href", "")
                        if any(ext in href for ext in [".mov", ".avi", ".wmv"]):
                            video_url = href
                            break

                return NASAItem(
                    id=item_id,
                    title=item_id,  # Would be populated from search results
                    media_type="video",
                    stream_url=video_url,
                    is_live=False,
                )

        except Exception as e:
            logger.error(f"NASA item details error: {e}")
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
            print("Usage: python -m connectors.nasa <command> [args]")
            print("Commands:")
            print("  live               - Get NASA TV live streams")
            print("  search [query]     - Search NASA video archive")
            print("  details <id>       - Get item details")
            sys.exit(1)

        command = sys.argv[1]

        async with NASAConnector() as connector:
            if command == "live":
                streams = await connector.get_live_streams()
                print(f"\nNASA TV Live Streams ({len(streams)}):\n")
                for stream in streams:
                    print(f"- {stream.title}")
                    print(f"  {stream.description}")
                    print(f"  Stream: {stream.stream_url}\n")

            elif command == "search":
                query = sys.argv[2] if len(sys.argv) > 2 else "apollo"
                items = await connector.search(query=query, limit=5)
                print(f"\nNASA Video Search: '{query}' ({len(items)} results)\n")
                for item in items:
                    print(f"- {item.title}")
                    print(f"  ID: {item.id}")
                    if item.description:
                        print(f"  {item.description[:100]}...")
                    print()

            elif command == "details":
                if len(sys.argv) < 3:
                    print("Error: item ID required")
                    sys.exit(1)

                item_id = sys.argv[2]
                item = await connector.get_item_details(item_id)

                if item:
                    print(f"\nTitle: {item.title}")
                    print(f"ID: {item.id}")
                    print(f"Type: {item.media_type}")
                    print(f"Live: {item.is_live}")
                    if item.stream_url:
                        print(f"Stream: {item.stream_url}")
                else:
                    print(f"Item not found: {item_id}")

            else:
                print(f"Unknown command: {command}")
                sys.exit(1)

    asyncio.run(main())
