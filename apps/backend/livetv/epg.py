"""
EPG (Electronic Program Guide) module for Live TV.

Provides Now/Next program information from:
1. M3U EXTINF hints (embedded program data)
2. XMLTV format EPG URLs (external program guides)
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class Program:
    """TV program information for EPG."""

    channel_id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: str | None = None
    category: str | None = None
    episode: str | None = None
    icon: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "channel_id": self.channel_id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "description": self.description,
            "category": self.category,
            "episode": self.episode,
            "icon": self.icon,
        }

    @property
    def is_current(self) -> bool:
        """Check if program is currently airing."""
        now = datetime.now(UTC)
        return self.start_time <= now < self.end_time

    @property
    def progress_percent(self) -> float:
        """Get program progress as percentage (0-100)."""
        if not self.is_current:
            return 0.0

        now = datetime.now(UTC)
        total_duration = (self.end_time - self.start_time).total_seconds()
        elapsed = (now - self.start_time).total_seconds()

        if total_duration <= 0:
            return 0.0

        return min(100.0, (elapsed / total_duration) * 100.0)


class EPGManager:
    """Manages EPG data from multiple sources."""

    def __init__(self):
        """Initialize EPG manager."""
        self._programs: dict[str, list[Program]] = {}  # channel_id -> programs
        self._epg_url: str | None = None
        self._last_update: datetime | None = None

    async def set_epg_url(self, url: str) -> bool:
        """Set external XMLTV EPG URL and fetch data.

        Args:
            url: XMLTV EPG URL

        Returns:
            True if successful, False otherwise
        """
        try:
            self._epg_url = url
            await self._fetch_xmltv(url)
            return True
        except Exception as e:
            logger.error(f"Failed to set EPG URL: {e}")
            return False

    async def _fetch_xmltv(self, url: str) -> None:
        """Fetch and parse XMLTV EPG data.

        Args:
            url: XMLTV EPG URL
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(f"EPG fetch failed: HTTP {response.status}")
                        return

                    xml_content = await response.text()
                    await self._parse_xmltv(xml_content)

            self._last_update = datetime.now(UTC)
            logger.info(f"EPG updated from {url}")

        except Exception as e:
            logger.error(f"Failed to fetch XMLTV: {e}")

    async def _parse_xmltv(self, xml_content: str) -> None:
        """Parse XMLTV format EPG data.

        XMLTV format:
        <tv>
          <channel id="channel1">
            <display-name>Channel Name</display-name>
          </channel>
          <programme start="20250102120000 +0000" stop="20250102130000 +0000" channel="channel1">
            <title>Program Title</title>
            <desc>Program description</desc>
            <category>News</category>
            <icon src="http://example.com/icon.png"/>
          </programme>
        </tv>

        Args:
            xml_content: XMLTV XML content
        """
        try:
            root = ET.fromstring(xml_content)

            # Clear existing programs
            self._programs.clear()

            # Parse programme elements
            for programme in root.findall("programme"):
                channel_id = programme.get("channel")
                if not channel_id:
                    continue

                # Parse times (XMLTV format: YYYYMMDDHHmmss +HHMM)
                start_str = programme.get("start")
                stop_str = programme.get("stop")
                if not start_str or not stop_str:
                    continue

                try:
                    start_time = self._parse_xmltv_time(start_str)
                    end_time = self._parse_xmltv_time(stop_str)
                except ValueError as e:
                    logger.warning(f"Failed to parse time: {e}")
                    continue

                # Extract program details
                title_elem = programme.find("title")
                title = title_elem.text if title_elem is not None else "Unknown"

                desc_elem = programme.find("desc")
                description = desc_elem.text if desc_elem is not None else None

                category_elem = programme.find("category")
                category = category_elem.text if category_elem is not None else None

                episode_elem = programme.find("episode-num")
                episode = episode_elem.text if episode_elem is not None and episode_elem.text else None

                icon_elem = programme.find("icon")
                icon = icon_elem.get("src") if icon_elem is not None else None

                # Create program
                program = Program(
                    channel_id=channel_id,
                    title=title,
                    start_time=start_time,
                    end_time=end_time,
                    description=description,
                    category=category,
                    episode=episode,
                    icon=icon,
                )

                # Store program
                if channel_id not in self._programs:
                    self._programs[channel_id] = []
                self._programs[channel_id].append(program)

            # Sort programs by start time for each channel
            for channel_programs in self._programs.values():
                channel_programs.sort(key=lambda p: p.start_time)

            logger.info(f"Parsed {sum(len(p) for p in self._programs.values())} programs for {len(self._programs)} channels")

        except ET.ParseError as e:
            logger.error(f"Failed to parse XMLTV: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing XMLTV: {e}")

    @staticmethod
    def _parse_xmltv_time(time_str: str) -> datetime:
        """Parse XMLTV time format to datetime.

        Args:
            time_str: XMLTV time string (YYYYMMDDHHmmss +HHMM)

        Returns:
            Parsed datetime with timezone

        Raises:
            ValueError: If time format is invalid
        """
        # XMLTV format: 20250102120000 +0000
        # Split timestamp and timezone
        parts = time_str.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid XMLTV time format: {time_str}")

        timestamp_str, tz_str = parts

        # Parse timestamp
        if len(timestamp_str) < 14:
            raise ValueError(f"Invalid timestamp length: {timestamp_str}")

        year = int(timestamp_str[0:4])
        month = int(timestamp_str[4:6])
        day = int(timestamp_str[6:8])
        hour = int(timestamp_str[8:10])
        minute = int(timestamp_str[10:12])
        second = int(timestamp_str[12:14])

        # Parse timezone offset
        tz_sign = 1 if tz_str[0] == "+" else -1
        tz_hours = int(tz_str[1:3])
        tz_minutes = int(tz_str[3:5])
        tz_offset_seconds = tz_sign * (tz_hours * 3600 + tz_minutes * 60)

        # Create datetime with UTC, then adjust for timezone
        from datetime import timedelta

        dt = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
        dt = dt - timedelta(seconds=tz_offset_seconds)

        return dt

    def get_current_program(self, channel_id: str) -> Program | None:
        """Get currently airing program for channel.

        Args:
            channel_id: Channel ID (tvg_id from M3U)

        Returns:
            Current program or None if no program is airing
        """
        if channel_id not in self._programs:
            return None

        now = datetime.now(UTC)
        for program in self._programs[channel_id]:
            if program.start_time <= now < program.end_time:
                return program

        return None

    def get_next_program(self, channel_id: str) -> Program | None:
        """Get next program for channel.

        Args:
            channel_id: Channel ID (tvg_id from M3U)

        Returns:
            Next program or None if no upcoming program
        """
        if channel_id not in self._programs:
            return None

        now = datetime.now(UTC)
        for program in self._programs[channel_id]:
            if program.start_time > now:
                return program

        return None

    def get_programs(self, channel_id: str, limit: int = 10) -> list[Program]:
        """Get upcoming programs for channel.

        Args:
            channel_id: Channel ID (tvg_id from M3U)
            limit: Maximum number of programs to return

        Returns:
            List of upcoming programs
        """
        if channel_id not in self._programs:
            return []

        now = datetime.now(UTC)
        upcoming = [p for p in self._programs[channel_id] if p.end_time > now]
        return upcoming[:limit]

    def get_all_current_programs(self) -> dict[str, Program]:
        """Get currently airing programs for all channels.

        Returns:
            Dictionary mapping channel_id to current program
        """
        current_programs = {}
        for channel_id in self._programs:
            program = self.get_current_program(channel_id)
            if program:
                current_programs[channel_id] = program

        return current_programs

    @property
    def has_epg_data(self) -> bool:
        """Check if EPG data is available."""
        return len(self._programs) > 0

    @property
    def last_update_time(self) -> datetime | None:
        """Get last EPG update time."""
        return self._last_update
