"""Kodi JSON-RPC client for media playback control.

Implements a bridge to Kodi's JSON-RPC API for controlling playback.
Supports play, pause, stop, seek, and state queries.
"""

import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KodiConfig(BaseModel):
    """Kodi connection configuration."""

    host: str = Field(default="localhost", description="Kodi hostname or IP")
    port: int = Field(default=9090, description="Kodi JSON-RPC port")
    username: str | None = Field(default=None, description="Kodi username (if auth enabled)")
    password: str | None = Field(default=None, description="Kodi password (if auth enabled)")

    @property
    def base_url(self) -> str:
        """Get the base JSON-RPC URL."""
        return f"http://{self.host}:{self.port}/jsonrpc"


class PlayerState(BaseModel):
    """Current player state."""

    player_id: int | None = Field(default=None, description="Active player ID")
    playing: bool = Field(default=False, description="Whether media is currently playing")
    paused: bool = Field(default=False, description="Whether playback is paused")
    position_seconds: float = Field(default=0.0, description="Current position in seconds")
    duration_seconds: float = Field(default=0.0, description="Total duration in seconds")
    speed: int = Field(default=0, description="Playback speed (0=stopped, 1=playing, 2=fast forward)")
    media_type: str | None = Field(default=None, description="Type of media (video, audio, etc.)")
    title: str | None = Field(default=None, description="Title of current media")
    file_path: str | None = Field(default=None, description="Path to media file")


class KodiClient:
    """Client for communicating with Kodi via JSON-RPC."""

    def __init__(self, config: KodiConfig | None = None):
        """Initialize Kodi client.

        Args:
            config: Kodi configuration. If None, uses defaults.
        """
        self.config = config or KodiConfig()
        self._request_id = 0
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Context manager entry."""
        auth = None
        if self.config.username and self.config.password:
            auth = httpx.BasicAuth(self.config.username, self.config.password)

        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            auth=auth,
            timeout=10.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client:
            await self._client.aclose()

    async def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Call a Kodi JSON-RPC method.

        Args:
            method: The JSON-RPC method name
            params: Optional parameters dictionary

        Returns:
            The result from Kodi

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If Kodi returns an error
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._request_id,
        }
        if params:
            payload["params"] = params

        logger.debug(f"Kodi RPC call: {method} with params {params}")
        response = await self._client.post("", json=payload)
        response.raise_for_status()

        result = response.json()
        if "error" in result:
            error = result["error"]
            raise ValueError(f"Kodi error: {error.get('message', 'Unknown error')}")

        return result.get("result")

    async def application_quit(self) -> bool:
        """Request Kodi to terminate the application."""

        try:
            await self._call("Application.Quit")
            logger.info("Kodi quit command delivered")
            return True
        except Exception as exc:  # pragma: no cover - just surface RPC failures
            logger.error("Failed to quit Kodi: %s", exc)
            return False

    async def ping(self) -> bool:
        """Test connection to Kodi.

        Returns:
            True if Kodi responds, False otherwise
        """
        try:
            result = await self._call("JSONRPC.Ping")
            return result == "pong"
        except Exception as e:
            logger.warning(f"Kodi ping failed: {e}")
            return False

    async def get_active_players(self) -> list[dict[str, Any]]:
        """Get list of active players.

        Returns:
            List of player info dictionaries
        """
        return await self._call("Player.GetActivePlayers") or []

    async def play_file(self, file_path: str) -> bool:
        """Play a media file.

        Args:
            file_path: Path to the media file

        Returns:
            True if playback started successfully
        """
        try:
            await self._call("Player.Open", {"item": {"file": file_path}})
            logger.info(f"Started playback: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            return False

    async def stop(self) -> bool:
        """Stop all active players.

        Returns:
            True if stopped successfully
        """
        try:
            players = await self.get_active_players()
            for player in players:
                player_id = player["playerid"]
                await self._call("Player.Stop", {"playerid": player_id})
                logger.info(f"Stopped player {player_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop playback: {e}")
            return False

    async def pause(self) -> bool:
        """Pause/unpause the active player.

        Returns:
            True if paused/unpaused successfully
        """
        try:
            players = await self.get_active_players()
            if not players:
                logger.warning("No active players to pause")
                return False

            player_id = players[0]["playerid"]
            await self._call("Player.PlayPause", {"playerid": player_id})
            logger.info(f"Toggled pause on player {player_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
            return False

    async def seek(self, position_seconds: float) -> bool:
        """Seek to a specific position.

        Args:
            position_seconds: Position to seek to in seconds

        Returns:
            True if seek successful
        """
        try:
            players = await self.get_active_players()
            if not players:
                logger.warning("No active players to seek")
                return False

            player_id = players[0]["playerid"]
            # Convert seconds to Kodi's time format (hours, minutes, seconds, milliseconds)
            hours = int(position_seconds // 3600)
            minutes = int((position_seconds % 3600) // 60)
            seconds = int(position_seconds % 60)
            milliseconds = int((position_seconds % 1) * 1000)

            await self._call(
                "Player.Seek",
                {
                    "playerid": player_id,
                    "value": {
                        "hours": hours,
                        "minutes": minutes,
                        "seconds": seconds,
                        "milliseconds": milliseconds,
                    },
                },
            )
            logger.info(f"Seeked to {position_seconds}s on player {player_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to seek: {e}")
            return False

    async def get_player_state(self) -> PlayerState:
        """Get current player state.

        Returns:
            PlayerState object with current playback information
        """
        try:
            players = await self.get_active_players()
            if not players:
                return PlayerState()

            player = players[0]
            player_id = player["playerid"]

            # Get player properties
            properties = await self._call(
                "Player.GetProperties",
                {
                    "playerid": player_id,
                    "properties": ["speed", "time", "totaltime", "position"],
                },
            )

            # Get current item info
            item = await self._call(
                "Player.GetItem",
                {"playerid": player_id, "properties": ["title", "file"]},
            )

            # Calculate position in seconds
            time_info = properties.get("time", {})
            position_seconds = (
                time_info.get("hours", 0) * 3600
                + time_info.get("minutes", 0) * 60
                + time_info.get("seconds", 0)
                + time_info.get("milliseconds", 0) / 1000
            )

            # Calculate duration in seconds
            total_time = properties.get("totaltime", {})
            duration_seconds = (
                total_time.get("hours", 0) * 3600
                + total_time.get("minutes", 0) * 60
                + total_time.get("seconds", 0)
                + total_time.get("milliseconds", 0) / 1000
            )

            speed = properties.get("speed", 0)

            return PlayerState(
                player_id=player_id,
                playing=speed > 0,
                paused=speed == 0,
                position_seconds=position_seconds,
                duration_seconds=duration_seconds,
                speed=speed,
                media_type=player.get("type"),
                title=item.get("item", {}).get("title"),
                file_path=item.get("item", {}).get("file"),
            )
        except Exception as e:
            logger.error(f"Failed to get player state: {e}")
            return PlayerState()

    async def set_volume(self, volume: int) -> bool:
        """Set the volume level.

        Args:
            volume: Volume level (0-100)

        Returns:
            True if volume set successfully
        """
        try:
            if not 0 <= volume <= 100:
                raise ValueError("Volume must be between 0 and 100")

            await self._call("Application.SetVolume", {"volume": volume})
            logger.info(f"Set volume to {volume}")
            return True
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False

    async def get_volume(self) -> int:
        """Get the current volume level.

        Returns:
            Volume level (0-100), or 0 if unavailable
        """
        try:
            result = await self._call(
                "Application.GetProperties", {"properties": ["volume"]}
            )
            return result.get("volume", 0)
        except Exception as e:
            logger.error(f"Failed to get volume: {e}")
            return 0

    async def input_action(self, action: str) -> bool:
        """Send a remote input action to Kodi.

        Args:
            action: Remote action keyword (up, down, select, etc.)

        Returns:
            True if the action was delivered, False otherwise
        """
        normalized = action.strip().lower()
        input_methods: dict[str, str] = {
            "up": "Input.Up",
            "down": "Input.Down",
            "left": "Input.Left",
            "right": "Input.Right",
            "select": "Input.Select",
            "back": "Input.Back",
            "context": "Input.ContextMenu",
            "info": "Input.Info",
            "home": "Input.Home",
            "menu": "Input.ShowOSD",
        }

        if normalized == "play_pause":
            return await self.pause()

        method = input_methods.get(normalized)
        if method is None:
            raise ValueError(f"Unsupported input action '{action}'")

        try:
            await self._call(method)
            logger.debug("Sent Kodi input action '%s'", normalized)
            return True
        except Exception as exc:
            logger.error("Failed to send input action '%s': %s", normalized, exc)
            return False

    async def get_subtitles(self) -> list[dict]:
        """Get available subtitle tracks.

        Returns:
            List of subtitle track dictionaries with 'index', 'language', and 'name' keys
        """
        try:
            players = await self.get_active_players()
            if not players:
                return []

            player_id = players[0]["playerid"]

            # Get available subtitles
            result = await self._call(
                "Player.GetProperties",
                {"playerid": player_id, "properties": ["subtitles", "currentsubtitle"]},
            )

            subtitles = result.get("subtitles", [])
            current = result.get("currentsubtitle", {})

            # Add current subtitle indicator
            for _, sub in enumerate(subtitles):
                sub["current"] = sub.get("index") == current.get("index")

            return subtitles
        except Exception as e:
            logger.error(f"Failed to get subtitles: {e}")
            return []

    async def set_subtitle(self, subtitle_index: int) -> bool:
        """Set the active subtitle track.

        Args:
            subtitle_index: Index of the subtitle track to activate

        Returns:
            True if subtitle set successfully
        """
        try:
            players = await self.get_active_players()
            if not players:
                logger.warning("No active players for subtitle selection")
                return False

            player_id = players[0]["playerid"]

            await self._call(
                "Player.SetSubtitle",
                {"playerid": player_id, "subtitle": subtitle_index},
            )
            logger.info(f"Set subtitle track to index {subtitle_index}")
            return True
        except Exception as e:
            logger.error(f"Failed to set subtitle: {e}")
            return False

    async def toggle_subtitles(self) -> bool:
        """Toggle subtitles on/off.

        Returns:
            True if toggle successful
        """
        try:
            players = await self.get_active_players()
            if not players:
                logger.warning("No active players for subtitle toggle")
                return False

            player_id = players[0]["playerid"]

            await self._call(
                "Player.SetSubtitle", {"playerid": player_id, "subtitle": "on"}
            )
            logger.info("Toggled subtitles")
            return True
        except Exception as e:
            logger.error(f"Failed to toggle subtitles: {e}")
            return False
