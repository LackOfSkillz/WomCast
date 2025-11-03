"""Tests for HDMI-CEC helper functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from playback.cec_helper import (
    CecDevice,
    CecDeviceType,
    CecHelper,
    get_cec_helper,
)


# Sample cec-client scan output for testing
SAMPLE_SCAN_OUTPUT = """
libCEC version: 6.0.2
Found devices: 2

device #0: TV
 address:       0.0.0.0
 active source: yes
 vendor:        Samsung
 osd string:    TV
 CEC version:   1.4
 power status:  on
 language:      eng

device #1: Playback 1
 address:       1.0.0.0
 active source: no
 vendor:        Roku
 osd string:    Roku Streaming Stick
 CEC version:   1.4
 power status:  standby
 language:      eng

device #4: Playback 2
 address:       2.0.0.0
 active source: no
 vendor:        Amazon
 osd string:    Fire TV Stick
 CEC version:   1.3a
 power status:  standby
 language:      eng
"""


@pytest.fixture
def cec_helper():
    """Create CEC helper instance for testing."""
    return CecHelper(cec_client_path="cec-client")


# ============================================================================
# Availability Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cec_available(cec_helper):
    """Test CEC availability check when cec-client is present."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"Found devices: 2\ndevice #0: TV\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        available = await cec_helper.is_available()

    assert available is True


@pytest.mark.asyncio
async def test_cec_not_available_no_command(cec_helper):
    """Test CEC availability when cec-client command not found."""
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
        available = await cec_helper.is_available()

    assert available is False


@pytest.mark.asyncio
async def test_cec_not_available_no_devices(cec_helper):
    """Test CEC availability when no devices detected."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"Found devices: 0\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        available = await cec_helper.is_available()

    assert available is False


@pytest.mark.asyncio
async def test_cec_not_available_error(cec_helper):
    """Test CEC availability when command fails."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"CEC adapter not found\n"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        available = await cec_helper.is_available()

    assert available is False


# ============================================================================
# Device Scanning Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scan_devices(cec_helper):
    """Test scanning for CEC devices."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        devices = await cec_helper.scan_devices()

    assert len(devices) == 3
    assert devices[0].address == 0
    assert devices[0].name == "TV"
    assert devices[0].vendor == "Samsung"
    assert devices[0].device_type == CecDeviceType.TV
    assert devices[0].active_source is True


@pytest.mark.asyncio
async def test_scan_devices_timeout(cec_helper):
    """Test scan timeout handling."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(side_effect=TimeoutError())

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", side_effect=TimeoutError()):
            devices = await cec_helper.scan_devices()

    assert devices == []


@pytest.mark.asyncio
async def test_parse_scan_output(cec_helper):
    """Test parsing cec-client scan output."""
    devices = cec_helper._parse_scan_output(SAMPLE_SCAN_OUTPUT)

    assert len(devices) == 3

    # TV device
    tv = devices[0]
    assert tv.address == 0
    assert tv.name == "TV"
    assert tv.vendor == "Samsung"
    assert tv.device_type == CecDeviceType.TV
    assert tv.physical_address == "0.0.0.0"
    assert tv.active_source is True

    # Roku device
    roku = devices[1]
    assert roku.address == 1
    assert roku.name == "Playback 1"
    assert roku.vendor == "Roku"
    assert roku.device_type == CecDeviceType.PLAYBACK_DEVICE
    assert roku.active_source is False

    # Fire TV device
    fire = devices[2]
    assert fire.address == 4
    assert fire.name == "Playback 2"
    assert fire.vendor == "Amazon"
    assert fire.device_type == CecDeviceType.PLAYBACK_DEVICE


# ============================================================================
# Device Type Mapping Tests
# ============================================================================


def test_map_device_type_tv(cec_helper):
    """Test device type mapping for TV."""
    assert cec_helper._map_device_type("TV", "Samsung TV") == CecDeviceType.TV
    assert cec_helper._map_device_type("Unknown", "LG TV") == CecDeviceType.TV


def test_map_device_type_playback(cec_helper):
    """Test device type mapping for playback devices."""
    assert cec_helper._map_device_type("Playback Device", "Roku") == CecDeviceType.PLAYBACK_DEVICE
    assert cec_helper._map_device_type("Unknown", "Fire TV") == CecDeviceType.PLAYBACK_DEVICE
    assert cec_helper._map_device_type("Unknown", "Apple TV") == CecDeviceType.PLAYBACK_DEVICE
    assert cec_helper._map_device_type("Unknown", "Chromecast") == CecDeviceType.PLAYBACK_DEVICE


def test_map_device_type_audio(cec_helper):
    """Test device type mapping for audio systems."""
    assert cec_helper._map_device_type("Audio System", "Receiver") == CecDeviceType.AUDIO_SYSTEM
    assert cec_helper._map_device_type("Unknown", "AV Receiver") == CecDeviceType.AUDIO_SYSTEM


def test_map_device_type_unknown(cec_helper):
    """Test device type mapping for unknown devices."""
    assert cec_helper._map_device_type("Unknown", "Mystery Device") == CecDeviceType.UNKNOWN


# ============================================================================
# Device Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_tv(cec_helper):
    """Test getting TV device (address 0)."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        tv = await cec_helper.get_tv()

    assert tv is not None
    assert tv.address == 0
    assert tv.device_type == CecDeviceType.TV
    assert tv.name == "TV"


@pytest.mark.asyncio
async def test_get_tv_not_found(cec_helper):
    """Test getting TV when no TV detected."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"Found devices: 0\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        tv = await cec_helper.get_tv()

    assert tv is None


@pytest.mark.asyncio
async def test_get_active_source(cec_helper):
    """Test getting currently active source."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        active = await cec_helper.get_active_source()

    assert active is not None
    assert active.address == 0  # TV is active in sample
    assert active.active_source is True


@pytest.mark.asyncio
async def test_get_active_source_none(cec_helper):
    """Test getting active source when none active."""
    output = b"device #0: TV\n active source: no\n"

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(output, b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        active = await cec_helper.get_active_source()

    assert active is None


# ============================================================================
# Input Switching Tests
# ============================================================================


@pytest.mark.asyncio
async def test_switch_to_device(cec_helper):
    """Test switching to a specific device by address."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"command sent\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        success = await cec_helper.switch_to_device(1)

    assert success is True
    assert not cec_helper._cache_valid  # Cache should be invalidated


@pytest.mark.asyncio
async def test_switch_to_device_failure(cec_helper):
    """Test switch failure handling."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Command failed\n"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        success = await cec_helper.switch_to_device(1)

    assert success is False


@pytest.mark.asyncio
async def test_switch_to_device_timeout(cec_helper):
    """Test switch timeout handling."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(side_effect=TimeoutError())

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("asyncio.wait_for", side_effect=TimeoutError()):
            success = await cec_helper.switch_to_device(1)

    assert success is False


@pytest.mark.asyncio
async def test_switch_by_name(cec_helper):
    """Test switching by device name."""
    mock_scan_proc = AsyncMock()
    mock_scan_proc.returncode = 0
    mock_scan_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    mock_switch_proc = AsyncMock()
    mock_switch_proc.returncode = 0
    mock_switch_proc.communicate = AsyncMock(return_value=(b"command sent\n", b""))

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_scan_proc, mock_switch_proc]):
        success = await cec_helper.switch_to_device_by_name("Playback 1")

    assert success is True


@pytest.mark.asyncio
async def test_switch_by_name_not_found(cec_helper):
    """Test switching by name when device not found."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        success = await cec_helper.switch_to_device_by_name("Xbox")

    assert success is False


@pytest.mark.asyncio
async def test_make_active_source(cec_helper):
    """Test making WomCast the active source."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"active source\n", b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        success = await cec_helper.make_active_source()

    assert success is True
    assert not cec_helper._cache_valid


@pytest.mark.asyncio
async def test_make_active_source_failure(cec_helper):
    """Test make active source failure."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Failed\n"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        success = await cec_helper.make_active_source()

    assert success is False


# ============================================================================
# State Export Tests
# ============================================================================


@pytest.mark.asyncio
async def test_to_dict(cec_helper):
    """Test exporting CEC state as dictionary."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        await cec_helper.scan_devices()

    state = cec_helper.to_dict()

    assert state["cache_valid"] is True
    assert len(state["devices"]) == 3
    assert state["devices"][0]["address"] == 0
    assert state["devices"][0]["device_type"] == "TV"


# ============================================================================
# Singleton Tests
# ============================================================================


def test_get_cec_helper_singleton():
    """Test that get_cec_helper returns singleton instance."""
    helper1 = get_cec_helper()
    helper2 = get_cec_helper()

    assert helper1 is helper2


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow(cec_helper):
    """Test complete CEC workflow: scan, query, switch."""
    # Clear any cache from previous tests
    cec_helper._devices_cache = {}
    cec_helper._cache_valid = False
    
    mock_scan_proc = AsyncMock()
    mock_scan_proc.returncode = 0
    mock_scan_proc.communicate = AsyncMock(return_value=(SAMPLE_SCAN_OUTPUT.encode(), b""))

    mock_switch_proc = AsyncMock()
    mock_switch_proc.returncode = 0
    mock_switch_proc.communicate = AsyncMock(return_value=(b"switched\n", b""))

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_exec.side_effect = [mock_scan_proc, mock_scan_proc, mock_switch_proc]
        
        # Scan devices
        devices = await cec_helper.scan_devices()
        assert len(devices) == 3

        # Get TV
        tv = await cec_helper.get_tv()
        assert tv is not None

        # Switch to Playback 1 (Roku)
        success = await cec_helper.switch_to_device_by_name("Playback 1")
        assert success is True
