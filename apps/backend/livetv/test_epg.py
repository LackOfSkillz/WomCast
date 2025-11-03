"""Tests for EPG (Electronic Program Guide) functionality."""

from datetime import UTC, datetime

import pytest

from livetv.epg import EPGManager, Program


@pytest.fixture
def epg_manager():
    """Create EPG manager instance."""
    return EPGManager()


@pytest.fixture
def sample_xmltv():
    """Sample XMLTV EPG data."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="test1">
    <display-name>Test Channel 1</display-name>
  </channel>
  <programme start="20250102120000 +0000" stop="20250102130000 +0000" channel="test1">
    <title>Test Program 1</title>
    <desc>Test description 1</desc>
    <category>News</category>
  </programme>
  <programme start="20250102130000 +0000" stop="20250102140000 +0000" channel="test1">
    <title>Test Program 2</title>
    <desc>Test description 2</desc>
    <category>Sports</category>
    <episode-num>S01E01</episode-num>
  </programme>
</tv>"""


def test_program_dataclass():
    """Test Program dataclass creation."""
    program = Program(
        channel_id="test1",
        title="Test Program",
        start_time=datetime(2025, 1, 2, 12, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 1, 2, 13, 0, 0, tzinfo=UTC),
        description="Test description",
        category="News",
    )

    assert program.channel_id == "test1"
    assert program.title == "Test Program"
    assert program.description == "Test description"
    assert program.category == "News"


def test_program_to_dict():
    """Test Program serialization to dictionary."""
    program = Program(
        channel_id="test1",
        title="Test Program",
        start_time=datetime(2025, 1, 2, 12, 0, 0, tzinfo=UTC),
        end_time=datetime(2025, 1, 2, 13, 0, 0, tzinfo=UTC),
        description="Test description",
    )

    data = program.to_dict()
    assert data["channel_id"] == "test1"
    assert data["title"] == "Test Program"
    assert data["description"] == "Test description"
    assert "start_time" in data
    assert "end_time" in data


def test_xmltv_time_parsing(epg_manager):
    """Test XMLTV time format parsing."""
    # Test valid format
    time_str = "20250102120000 +0000"
    dt = epg_manager._parse_xmltv_time(time_str)
    assert dt.year == 2025
    assert dt.month == 1
    assert dt.day == 2
    assert dt.hour == 12
    assert dt.minute == 0
    assert dt.second == 0

    # Test with timezone offset
    time_str_tz = "20250102120000 +0500"
    dt_tz = epg_manager._parse_xmltv_time(time_str_tz)
    assert dt_tz.hour == 7  # 12:00 - 5:00 = 07:00 UTC


def test_xmltv_time_parsing_invalid(epg_manager):
    """Test XMLTV time parsing with invalid input."""
    with pytest.raises(ValueError):
        epg_manager._parse_xmltv_time("invalid")

    with pytest.raises(ValueError):
        epg_manager._parse_xmltv_time("20250102")  # Too short


@pytest.mark.asyncio
async def test_parse_xmltv(epg_manager, sample_xmltv):
    """Test XMLTV parsing."""
    await epg_manager._parse_xmltv(sample_xmltv)

    # Check programs were parsed
    assert "test1" in epg_manager._programs
    programs = epg_manager._programs["test1"]
    assert len(programs) == 2

    # Check first program
    program1 = programs[0]
    assert program1.title == "Test Program 1"
    assert program1.description == "Test description 1"
    assert program1.category == "News"

    # Check second program
    program2 = programs[1]
    assert program2.title == "Test Program 2"
    assert program2.episode == "S01E01"


@pytest.mark.asyncio
async def test_get_programs(epg_manager):
    """Test getting programs for a channel."""
    # Add test programs
    now = datetime.now(UTC)
    from datetime import timedelta

    program1 = Program(
        channel_id="test1",
        title="Past Program",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
    )
    program2 = Program(
        channel_id="test1",
        title="Current Program",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30),
    )
    program3 = Program(
        channel_id="test1",
        title="Next Program",
        start_time=now + timedelta(minutes=30),
        end_time=now + timedelta(hours=1, minutes=30),
    )

    epg_manager._programs["test1"] = [program1, program2, program3]

    # Get upcoming programs
    upcoming = epg_manager.get_programs("test1", limit=10)
    assert len(upcoming) == 2  # Current and next
    assert upcoming[0].title == "Current Program"
    assert upcoming[1].title == "Next Program"


def test_get_current_program(epg_manager):
    """Test getting current program for a channel."""
    now = datetime.now(UTC)
    from datetime import timedelta

    # Add test programs
    program1 = Program(
        channel_id="test1",
        title="Current Program",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30),
    )
    program2 = Program(
        channel_id="test1",
        title="Next Program",
        start_time=now + timedelta(minutes=30),
        end_time=now + timedelta(hours=1, minutes=30),
    )

    epg_manager._programs["test1"] = [program1, program2]

    # Get current program
    current = epg_manager.get_current_program("test1")
    assert current is not None
    assert current.title == "Current Program"
    assert current.is_current is True


def test_get_next_program(epg_manager):
    """Test getting next program for a channel."""
    now = datetime.now(UTC)
    from datetime import timedelta

    # Add test programs
    program1 = Program(
        channel_id="test1",
        title="Current Program",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30),
    )
    program2 = Program(
        channel_id="test1",
        title="Next Program",
        start_time=now + timedelta(minutes=30),
        end_time=now + timedelta(hours=1, minutes=30),
    )

    epg_manager._programs["test1"] = [program1, program2]

    # Get next program
    next_prog = epg_manager.get_next_program("test1")
    assert next_prog is not None
    assert next_prog.title == "Next Program"


def test_get_all_current_programs(epg_manager):
    """Test getting current programs for all channels."""
    now = datetime.now(UTC)
    from datetime import timedelta

    # Add programs for multiple channels
    program1 = Program(
        channel_id="test1",
        title="Current Program 1",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30),
    )
    program2 = Program(
        channel_id="test2",
        title="Current Program 2",
        start_time=now - timedelta(minutes=15),
        end_time=now + timedelta(minutes=45),
    )

    epg_manager._programs["test1"] = [program1]
    epg_manager._programs["test2"] = [program2]

    # Get all current programs
    current_programs = epg_manager.get_all_current_programs()
    assert len(current_programs) == 2
    assert "test1" in current_programs
    assert "test2" in current_programs
    assert current_programs["test1"].title == "Current Program 1"
    assert current_programs["test2"].title == "Current Program 2"


def test_program_progress_percent():
    """Test program progress percentage calculation."""
    now = datetime.now(UTC)
    from datetime import timedelta

    # Program that is 50% complete
    program = Program(
        channel_id="test1",
        title="Test Program",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30),
    )

    progress = program.progress_percent
    assert 45 <= progress <= 55  # Allow small time delta variance

    # Program that hasn't started
    future_program = Program(
        channel_id="test1",
        title="Future Program",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
    )

    assert future_program.progress_percent == 0.0


def test_has_epg_data(epg_manager):
    """Test checking if EPG data is available."""
    assert epg_manager.has_epg_data is False

    # Add program
    epg_manager._programs["test1"] = [
        Program(
            channel_id="test1",
            title="Test",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
        )
    ]

    assert epg_manager.has_epg_data is True


def test_no_epg_for_channel(epg_manager):
    """Test behavior when no EPG data exists for channel."""
    current = epg_manager.get_current_program("nonexistent")
    assert current is None

    next_prog = epg_manager.get_next_program("nonexistent")
    assert next_prog is None

    programs = epg_manager.get_programs("nonexistent")
    assert programs == []
