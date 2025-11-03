"""Integration tests for all WomCast connectors.

Tests cover:
- Internet Archive (public domain content)
- PBS (free streaming)
- NASA TV (public domain streams and archives)
- Jamendo (Creative Commons music)

Tests validate:
- Connector initialization and session management
- Search functionality with various queries
- Item detail retrieval
- Rate limiting compliance
- Error handling and resilience
- Legal compliance (attribution, licensing)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from connectors.internet_archive import InternetArchiveConnector
from connectors.jamendo import JamendoConnector
from connectors.nasa import NASAConnector, NASAItem
from connectors.pbs import PBSConnector, PBSItem

# ============================================================================
# Helper Functions
# ============================================================================


def mock_aiohttp_response(status: int, json_data: dict):
    """Create a mock aiohttp response that works with async context managers."""
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data)

    mock_ctx_manager = MagicMock()
    mock_ctx_manager.__aenter__ = AsyncMock(return_value=mock_response)
    mock_ctx_manager.__aexit__ = AsyncMock(return_value=None)

    return mock_ctx_manager


# ============================================================================
# Internet Archive Connector Tests
# ============================================================================


@pytest.mark.asyncio
async def test_ia_connector_context_manager():
    """Test Internet Archive connector session lifecycle."""
    async with InternetArchiveConnector() as connector:
        assert connector.session is not None
        assert not connector.session.closed
    # Session should be closed after context exit
    assert connector.session.closed


@pytest.mark.asyncio
async def test_ia_search_default_query():
    """Test Internet Archive search with default parameters."""
    mock_data = {
        "response": {
            "docs": [
                {
                    "identifier": "test-movie-1",
                    "title": "Test Movie",
                    "mediatype": "movies",
                    "description": "A test movie",
                    "creator": "Test Creator",
                    "year": 1950,
                    "runtime": "01:30:00",
                }
            ]
        }
    }

    async with InternetArchiveConnector() as connector:
        with patch.object(connector.session, "get", return_value=mock_aiohttp_response(200, mock_data)):
            items = await connector.search(query="test", rows=10)

    assert len(items) == 1
    assert items[0].identifier == "test-movie-1"
    assert items[0].title == "Test Movie"
    assert items[0].mediatype == "movies"
    assert items[0].year == 1950
    assert items[0].duration == 5400  # 1:30:00 = 5400 seconds
    assert items[0].thumbnail_url == "https://archive.org/services/img/test-movie-1"


@pytest.mark.asyncio
async def test_ia_search_with_filters():
    """Test Internet Archive search with mediatype and collection filters."""
    mock_data = {"response": {"docs": []}}

    async with InternetArchiveConnector() as connector:
        with patch.object(connector.session, "get", return_value=mock_aiohttp_response(200, mock_data)) as mock_get:
            await connector.search(query="space", mediatype="movies", collection="prelinger")

            # Verify search parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert "mediatype:movies" in params["q"]
            assert "collection:prelinger" in params["q"]
            assert params["rows"] == 50  # Default


@pytest.mark.asyncio
async def test_ia_get_item_details():
    """Test Internet Archive item detail retrieval."""
    mock_data = {
        "metadata": {
            "identifier": "test-item",
            "title": "Test Item",
            "mediatype": "movies",
            "description": "Test description",
            "runtime": "45:30",
        },
        "files": [
            {"name": "test-item.mp4", "format": "h.264"},
            {"name": "test-item.ogv", "format": "Ogg Video"},
        ],
    }

    async with InternetArchiveConnector() as connector:
        with patch.object(connector.session, "get", return_value=mock_aiohttp_response(200, mock_data)):
            item = await connector.get_item_details("test-item")

    assert item is not None
    assert item.identifier == "test-item"
    assert item.title == "Test Item"
    assert item.duration == 2730  # 45:30 = 2730 seconds
    assert item.stream_url == "https://archive.org/download/test-item/test-item.mp4"


@pytest.mark.asyncio
async def test_ia_rate_limiting():
    """Test Internet Archive rate limiting behavior."""
    connector = InternetArchiveConnector()
    connector.session = MagicMock()

    # Set last request time to now
    connector._last_request_time = asyncio.get_event_loop().time()

    # Rate limit wait should introduce delay
    start_time = asyncio.get_event_loop().time()
    await connector._rate_limit_wait()
    end_time = asyncio.get_event_loop().time()

    # Should wait approximately 1 second (1 req/sec limit)
    elapsed = end_time - start_time
    assert elapsed >= 0.9  # Allow some timing variance


@pytest.mark.asyncio
async def test_ia_get_collections():
    """Test Internet Archive featured collections."""
    connector = InternetArchiveConnector()

    collections = await connector.get_collections()

    assert len(collections) > 0
    assert all("id" in coll for coll in collections)
    assert all("title" in coll for coll in collections)
    assert any(coll["id"] == "prelinger" for coll in collections)


@pytest.mark.asyncio
async def test_ia_search_error_handling():
    """Test Internet Archive search error handling."""
    async with InternetArchiveConnector() as connector:
        with patch.object(connector.session, "get", return_value=mock_aiohttp_response(500, {})):
            items = await connector.search(query="test")

    # Should return empty list on error, not raise exception
    assert items == []


# ============================================================================
# PBS Connector Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pbs_connector_context_manager():
    """Test PBS connector session lifecycle."""
    async with PBSConnector() as connector:
        assert connector.session is not None
        assert not connector.session.closed
    assert connector.session.closed


@pytest.mark.asyncio
async def test_pbs_get_featured():
    """Test PBS featured content retrieval."""
    async with PBSConnector() as connector:
        items = await connector.get_featured(limit=5)

        # PBS connector returns placeholder data (API key required)
        assert isinstance(items, list)
        assert len(items) <= 5
        if items:
            assert all(isinstance(item, PBSItem) for item in items)
            assert all(item.title for item in items)


@pytest.mark.asyncio
async def test_pbs_search():
    """Test PBS search functionality."""
    async with PBSConnector() as connector:
        items = await connector.search(query="news", limit=10)

        assert isinstance(items, list)
        # PBS connector returns placeholder data
        assert len(items) <= 10


@pytest.mark.asyncio
async def test_pbs_get_item_details():
    """Test PBS item detail retrieval."""
    async with PBSConnector() as connector:
        # Test with known placeholder ID
        item = await connector.get_item_details("pbs-demo-1")

        assert item is not None
        assert item.id == "pbs-demo-1"
        assert item.title
        assert item.duration is not None


@pytest.mark.asyncio
async def test_pbs_rate_limiting():
    """Test PBS rate limiting behavior."""
    connector = PBSConnector()
    connector.session = MagicMock()

    connector._last_request_time = asyncio.get_event_loop().time()

    start_time = asyncio.get_event_loop().time()
    await connector._rate_limit_wait()
    end_time = asyncio.get_event_loop().time()

    # PBS rate limit is 2 req/sec = 0.5 second between requests
    elapsed = end_time - start_time
    assert elapsed >= 0.4  # Allow timing variance


# ============================================================================
# NASA Connector Tests
# ============================================================================


@pytest.mark.asyncio
async def test_nasa_connector_context_manager():
    """Test NASA connector session lifecycle."""
    async with NASAConnector() as connector:
        assert connector.session is not None
        assert not connector.session.closed
    assert connector.session.closed


@pytest.mark.asyncio
async def test_nasa_get_live_streams():
    """Test NASA TV live stream retrieval."""
    async with NASAConnector() as connector:
        streams = await connector.get_live_streams()

        assert len(streams) > 0
        assert all(isinstance(stream, NASAItem) for stream in streams)
        assert all(stream.is_live for stream in streams)
        assert all(stream.stream_url for stream in streams)

        # Verify known NASA TV streams
        stream_ids = [s.id for s in streams]
        assert "nasa-tv-public" in stream_ids
        assert "nasa-tv-media" in stream_ids


@pytest.mark.asyncio
async def test_nasa_search():
    """Test NASA archive search."""
    connector = NASAConnector()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "collection": {
                "items": [
                    {
                        "data": [
                            {
                                "nasa_id": "apollo11_launch",
                                "title": "Apollo 11 Launch",
                                "description": "Apollo 11 Saturn V launch",
                                "media_type": "video",
                                "date_created": "1969-07-16T00:00:00Z",
                                "keywords": ["apollo", "saturn v", "launch"],
                            }
                        ],
                        "links": [
                            {
                                "render": "image",
                                "href": "https://images-assets.nasa.gov/image/apollo11.jpg",
                            }
                        ],
                    }
                ]
            }
        }
    )

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    items = await connector.search(query="apollo", limit=10)

    assert len(items) == 1
    assert items[0].id == "apollo11_launch"
    assert items[0].title == "Apollo 11 Launch"
    assert items[0].media_type == "video"
    assert items[0].thumbnail_url is not None
    assert items[0].keywords == ["apollo", "saturn v", "launch"]


@pytest.mark.asyncio
async def test_nasa_get_item_details_live_stream():
    """Test NASA item details for live streams."""
    async with NASAConnector() as connector:
        item = await connector.get_item_details("nasa-tv-public")

        assert item is not None
        assert item.id == "nasa-tv-public"
        assert item.is_live
        assert item.stream_url is not None
        assert "nasa" in item.stream_url.lower() or "ntv" in item.stream_url.lower()


@pytest.mark.asyncio
async def test_nasa_get_item_details_archived():
    """Test NASA item details for archived content."""
    connector = NASAConnector()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "collection": {
                "items": [
                    {"href": "https://images-assets.nasa.gov/video/test/test~orig.mp4"},
                    {"href": "https://images-assets.nasa.gov/video/test/test.jpg"},
                ]
            }
        }
    )

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    item = await connector.get_item_details("test_video")

    assert item is not None
    assert item.stream_url == "https://images-assets.nasa.gov/video/test/test~orig.mp4"
    assert not item.is_live


@pytest.mark.asyncio
async def test_nasa_rate_limiting():
    """Test NASA rate limiting behavior."""
    connector = NASAConnector()
    connector.session = MagicMock()

    connector._last_request_time = asyncio.get_event_loop().time()

    start_time = asyncio.get_event_loop().time()
    await connector._rate_limit_wait()
    end_time = asyncio.get_event_loop().time()

    # NASA rate limit is 2 req/sec = 0.5 second between requests
    elapsed = end_time - start_time
    assert elapsed >= 0.4


# ============================================================================
# Jamendo Connector Tests
# ============================================================================


@pytest.mark.asyncio
async def test_jamendo_connector_context_manager():
    """Test Jamendo connector session lifecycle."""
    async with JamendoConnector() as connector:
        assert connector.session is not None
        assert not connector.session.closed
    assert connector.session.closed


@pytest.mark.asyncio
async def test_jamendo_get_popular():
    """Test Jamendo popular tracks retrieval."""
    connector = JamendoConnector()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 12345,
                    "name": "Test Track",
                    "artist_name": "Test Artist",
                    "album_name": "Test Album",
                    "duration": 180,
                    "license_ccurl": "https://creativecommons.org/licenses/by-sa/3.0/",
                    "audio": "https://mp3d.jamendo.com/download/track/12345/mp31",
                    "image": "https://usercontent.jamendo.com/test.jpg",
                }
            ]
        }
    )

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    tracks = await connector.get_popular(limit=10)

    assert len(tracks) == 1
    assert tracks[0].id == "12345"
    assert tracks[0].name == "Test Track"
    assert tracks[0].artist_name == "Test Artist"
    assert tracks[0].duration == 180
    assert tracks[0].audio_url is not None
    assert "creativecommons.org" in tracks[0].license_ccurl


@pytest.mark.asyncio
async def test_jamendo_search():
    """Test Jamendo search functionality."""
    connector = JamendoConnector()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 54321,
                    "name": "Jazz Track",
                    "artist_name": "Jazz Artist",
                    "duration": 240,
                    "license_ccurl": "https://creativecommons.org/licenses/by/3.0/",
                    "audio": "https://mp3d.jamendo.com/download/track/54321/mp31",
                }
            ]
        }
    )

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    tracks = await connector.search(query="jazz", limit=5)

    assert len(tracks) == 1
    assert tracks[0].id == "54321"
    assert tracks[0].name == "Jazz Track"


@pytest.mark.asyncio
async def test_jamendo_search_with_genre():
    """Test Jamendo search with genre filter."""
    connector = JamendoConnector()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"results": []})

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    await connector.search(query="music", genre="rock", limit=10)

    # Verify genre filter is applied
    call_args = mock_session.get.call_args
    params = call_args[1]["params"]
    assert params["tags"] == "rock"


@pytest.mark.asyncio
async def test_jamendo_get_track_details():
    """Test Jamendo track detail retrieval."""
    connector = JamendoConnector()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 99999,
                    "name": "Detailed Track",
                    "artist_name": "Detailed Artist",
                    "album_name": "Detailed Album",
                    "duration": 300,
                    "license_ccurl": "https://creativecommons.org/licenses/by-nc/3.0/",
                    "audio": "https://mp3d.jamendo.com/download/track/99999/mp31",
                    "image": "https://usercontent.jamendo.com/detail.jpg",
                    "releasedate": "2024-01-01",
                }
            ]
        }
    )

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    track = await connector.get_track_details("99999")

    assert track is not None
    assert track.id == "99999"
    assert track.name == "Detailed Track"
    assert track.album_name == "Detailed Album"
    assert track.releasedate == "2024-01-01"
    assert track.license_ccurl is not None


@pytest.mark.asyncio
async def test_jamendo_rate_limiting():
    """Test Jamendo rate limiting behavior."""
    connector = JamendoConnector()
    connector.session = MagicMock()

    connector._last_request_time = asyncio.get_event_loop().time()

    start_time = asyncio.get_event_loop().time()
    await connector._rate_limit_wait()
    end_time = asyncio.get_event_loop().time()

    # Jamendo rate limit is 2 req/sec = 0.5 second between requests
    elapsed = end_time - start_time
    assert elapsed >= 0.4


@pytest.mark.asyncio
async def test_jamendo_error_handling():
    """Test Jamendo error handling."""
    connector = JamendoConnector()

    mock_response = AsyncMock()
    mock_response.status = 403  # API key error

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    connector.session = mock_session

    tracks = await connector.get_popular(limit=10)

    # Should return empty list on error
    assert tracks == []


# ============================================================================
# Cross-Connector Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_all_connectors_legal_compliance():
    """Verify all connectors preserve legal attribution and licensing."""
    # Internet Archive
    ia_connector = InternetArchiveConnector()

    mock_ia_response = AsyncMock()
    mock_ia_response.status = 200
    mock_ia_response.json = AsyncMock(
        return_value={
            "response": {
                "docs": [
                    {
                        "identifier": "test",
                        "title": "Test",
                        "mediatype": "movies",
                        "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
                    }
                ]
            }
        }
    )

    mock_ia_session = AsyncMock()
    mock_ia_session.get.return_value.__aenter__.return_value = mock_ia_response
    ia_connector.session = mock_ia_session

    ia_items = await ia_connector.search(query="test")
    assert len(ia_items) > 0
    assert ia_items[0].license is not None

    # Jamendo
    jamendo_connector = JamendoConnector()

    mock_jamendo_response = AsyncMock()
    mock_jamendo_response.status = 200
    mock_jamendo_response.json = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 1,
                    "name": "Test",
                    "artist_name": "Test",
                    "license_ccurl": "https://creativecommons.org/licenses/by-sa/3.0/",
                    "audio": "test.mp3",
                }
            ]
        }
    )

    mock_jamendo_session = AsyncMock()
    mock_jamendo_session.get.return_value.__aenter__.return_value = mock_jamendo_response
    jamendo_connector.session = mock_jamendo_session

    jamendo_tracks = await jamendo_connector.get_popular(limit=1)
    assert len(jamendo_tracks) > 0
    assert jamendo_tracks[0].license_ccurl is not None
    assert "creativecommons.org" in jamendo_tracks[0].license_ccurl


@pytest.mark.asyncio
async def test_all_connectors_rate_limit_compliance():
    """Verify all connectors respect rate limits."""
    connectors = [
        InternetArchiveConnector(),
        PBSConnector(),
        NASAConnector(),
        JamendoConnector(),
    ]

    for connector in connectors:
        connector.session = MagicMock()
        connector._last_request_time = asyncio.get_event_loop().time()

        start_time = asyncio.get_event_loop().time()
        await connector._rate_limit_wait()
        end_time = asyncio.get_event_loop().time()

        # All connectors should introduce delay
        elapsed = end_time - start_time
        assert elapsed >= 0.4  # Minimum rate limit delay


@pytest.mark.asyncio
async def test_all_connectors_session_management():
    """Verify all connectors properly manage HTTP sessions."""
    connectors = [
        InternetArchiveConnector(),
        PBSConnector(),
        NASAConnector(),
        JamendoConnector(),
    ]

    for connector in connectors:
        # Test context manager
        async with connector as conn:
            assert conn.session is not None
            assert not conn.session.closed

        # Session should be closed after exit
        assert connector.session.closed
