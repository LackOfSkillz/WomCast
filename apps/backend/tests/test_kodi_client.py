"""Tests for Kodi JSON-RPC client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ..playback.kodi_client import KodiClient, KodiConfig


@pytest.fixture
def kodi_config():
    """Kodi configuration for testing."""
    return KodiConfig(host="localhost", port=9090)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.mark.asyncio
async def test_kodi_config():
    """Test Kodi configuration."""
    config = KodiConfig()
    assert config.host == "localhost"
    assert config.port == 9090
    assert config.base_url == "http://localhost:9090/jsonrpc"

    config_with_auth = KodiConfig(
        host="192.168.1.100", port=8080, username="kodi", password="pass"
    )
    assert config_with_auth.base_url == "http://192.168.1.100:8080/jsonrpc"


@pytest.mark.asyncio
async def test_kodi_ping_success(kodi_config, mock_httpx_client):
    """Test successful Kodi ping."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "pong", "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.ping()
            assert result is True
            mock_httpx_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_kodi_ping_failure(kodi_config, mock_httpx_client):
    """Test failed Kodi ping."""
    mock_httpx_client.post.side_effect = httpx.HTTPError("Connection failed")

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.ping()
            assert result is False


@pytest.mark.asyncio
async def test_play_file_success(kodi_config, mock_httpx_client):
    """Test successful file playback."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.play_file("/media/test/movie.mkv")
            assert result is True
            assert mock_httpx_client.post.called


@pytest.mark.asyncio
async def test_play_file_error(kodi_config, mock_httpx_client):
    """Test file playback error."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "error": {"message": "File not found"},
        "id": 1,
    }
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.play_file("/invalid/path.mkv")
            assert result is False


@pytest.mark.asyncio
async def test_stop_playback(kodi_config, mock_httpx_client):
    """Test stopping playback."""
    mock_response_players = MagicMock()
    mock_response_players.json.return_value = {
        "jsonrpc": "2.0",
        "result": [{"playerid": 1, "type": "video"}],
        "id": 1,
    }

    mock_response_stop = MagicMock()
    mock_response_stop.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 2}

    mock_httpx_client.post.side_effect = [mock_response_players, mock_response_stop]

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.stop()
            assert result is True
            assert mock_httpx_client.post.call_count == 2


@pytest.mark.asyncio
async def test_pause_playback(kodi_config, mock_httpx_client):
    """Test pausing playback."""
    mock_response_players = MagicMock()
    mock_response_players.json.return_value = {
        "jsonrpc": "2.0",
        "result": [{"playerid": 1, "type": "video"}],
        "id": 1,
    }

    mock_response_pause = MagicMock()
    mock_response_pause.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 2}

    mock_httpx_client.post.side_effect = [mock_response_players, mock_response_pause]

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.pause()
            assert result is True


@pytest.mark.asyncio
async def test_pause_no_active_players(kodi_config, mock_httpx_client):
    """Test pausing when no players are active."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": [], "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.pause()
            assert result is False


@pytest.mark.asyncio
async def test_seek_playback(kodi_config, mock_httpx_client):
    """Test seeking to a position."""
    mock_response_players = MagicMock()
    mock_response_players.json.return_value = {
        "jsonrpc": "2.0",
        "result": [{"playerid": 1, "type": "video"}],
        "id": 1,
    }

    mock_response_seek = MagicMock()
    mock_response_seek.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 2}

    mock_httpx_client.post.side_effect = [mock_response_players, mock_response_seek]

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            # Seek to 1 hour, 30 minutes, 45 seconds (5445 seconds)
            result = await client.seek(5445.5)
            assert result is True


@pytest.mark.asyncio
async def test_get_player_state_active(kodi_config, mock_httpx_client):
    """Test getting player state when playing."""
    mock_response_players = MagicMock()
    mock_response_players.json.return_value = {
        "jsonrpc": "2.0",
        "result": [{"playerid": 1, "type": "video"}],
        "id": 1,
    }

    mock_response_properties = MagicMock()
    mock_response_properties.json.return_value = {
        "jsonrpc": "2.0",
        "result": {
            "speed": 1,
            "time": {"hours": 0, "minutes": 5, "seconds": 30, "milliseconds": 500},
            "totaltime": {"hours": 1, "minutes": 30, "seconds": 0, "milliseconds": 0},
            "position": 0,
        },
        "id": 2,
    }

    mock_response_item = MagicMock()
    mock_response_item.json.return_value = {
        "jsonrpc": "2.0",
        "result": {
            "item": {"title": "Test Movie", "file": "/media/test/movie.mkv"}
        },
        "id": 3,
    }

    mock_httpx_client.post.side_effect = [
        mock_response_players,
        mock_response_properties,
        mock_response_item,
    ]

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            state = await client.get_player_state()
            assert state.player_id == 1
            assert state.playing is True
            assert state.paused is False
            assert state.position_seconds == 330.5  # 5m 30.5s
            assert state.duration_seconds == 5400.0  # 1h 30m
            assert state.title == "Test Movie"
            assert state.file_path == "/media/test/movie.mkv"


@pytest.mark.asyncio
async def test_get_player_state_inactive(kodi_config, mock_httpx_client):
    """Test getting player state when no players are active."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": [], "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            state = await client.get_player_state()
            assert state.player_id is None
            assert state.playing is False
            assert state.paused is False
            assert state.position_seconds == 0.0


@pytest.mark.asyncio
async def test_set_volume(kodi_config, mock_httpx_client):
    """Test setting volume."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": 75, "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.set_volume(75)
            assert result is True


@pytest.mark.asyncio
async def test_set_volume_invalid(kodi_config, mock_httpx_client):
    """Test setting invalid volume."""
    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            result = await client.set_volume(150)  # Invalid: > 100
            assert result is False


@pytest.mark.asyncio
async def test_get_volume(kodi_config, mock_httpx_client):
    """Test getting current volume."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "result": {"volume": 85},
        "id": 1,
    }
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            volume = await client.get_volume()
            assert volume == 85


@pytest.mark.asyncio
async def test_context_manager_without_context():
    """Test that calling methods outside context manager raises error."""
    client = KodiClient()
    with pytest.raises(RuntimeError, match="Client not initialized"):
        await client._call("JSONRPC.Ping")


@pytest.mark.asyncio
async def test_input_action_success(kodi_config, mock_httpx_client):
    """Input action should call Kodi JSON-RPC method."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            with patch.object(client, "_call", new=AsyncMock(return_value="OK")) as rpc_mock:
                result = await client.input_action("up")
                assert result is True
                rpc_mock.assert_awaited_once_with("Input.Up")


@pytest.mark.asyncio
async def test_input_action_play_pause_uses_pause_method(kodi_config, mock_httpx_client):
    """Play/pause action should delegate to KodiClient.pause()."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 1}
    mock_httpx_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            with patch.object(client, "pause", new=AsyncMock(return_value=True)) as pause_mock:
                result = await client.input_action("play_pause")
                assert result is True
                pause_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_input_action_invalid(kodi_config, mock_httpx_client):
    """Unsupported actions raise ValueError."""
    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            with pytest.raises(ValueError):
                await client.input_action("spin")


@pytest.mark.asyncio
async def test_input_action_failure_logged(kodi_config, mock_httpx_client):
    """If Kodi RPC call fails, input_action returns False."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"jsonrpc": "2.0", "result": "OK", "id": 1}
    mock_httpx_client.post.return_value = mock_response

    failing_call = AsyncMock(side_effect=ValueError("boom"))

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        async with KodiClient(kodi_config) as client:
            with patch.object(client, "_call", new=failing_call):
                result = await client.input_action("left")
                assert result is False
