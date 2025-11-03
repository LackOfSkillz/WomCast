"""HDMI-CEC input switching helper for WomCast.

Provides automatic TV input switching when launching cloud streaming services,
allowing seamless transition from WomCast to Netflix/Disney+/etc. apps on smart TVs.

This module uses libcec (via cec-client command) to communicate with HDMI-CEC
capable TVs and streaming devices (Roku, Fire TV, Apple TV, etc.).

Requirements:
- libcec installed (cec-client command available)
- HDMI cable with CEC support
- TV with HDMI-CEC enabled (may be called Anynet+, Simplink, Bravia Sync, etc.)
"""

import asyncio
import json
import logging
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CecDeviceType(str, Enum):
    """CEC device types."""

    TV = "TV"
    RECORDING_DEVICE = "Recording Device"
    PLAYBACK_DEVICE = "Playback Device"
    TUNER = "Tuner"
    AUDIO_SYSTEM = "Audio System"
    UNKNOWN = "Unknown"


@dataclass
class CecDevice:
    """CEC device information."""

    address: int  # CEC logical address (0-15)
    name: str  # Device name (e.g., "TV", "Roku", "Fire TV")
    vendor: str  # Vendor name (e.g., "Samsung", "LG", "Sony")
    device_type: CecDeviceType
    active_source: bool = False  # Whether this device is currently active
    physical_address: str = "0.0.0.0"  # Physical HDMI address


class CecHelper:
    """Helper for HDMI-CEC communication.

    Provides methods to detect CEC devices, switch TV inputs, and query
    the current active source.
    """

    def __init__(self, cec_client_path: str = "cec-client"):
        """Initialize CEC helper.

        Args:
            cec_client_path: Path to cec-client executable (default: "cec-client" in PATH)
        """
        self.cec_client_path = cec_client_path
        self._devices_cache: dict[int, CecDevice] = {}
        self._cache_valid = False

    async def is_available(self) -> bool:
        """Check if CEC is available on this system.

        Returns:
            True if cec-client is available and can communicate with CEC devices
        """
        try:
            result = await asyncio.create_subprocess_exec(
                self.cec_client_path,
                "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.warning(f"CEC not available: {stderr.decode()}")
                return False

            # Check if any devices found
            output = stdout.decode()
            has_devices = "device #" in output.lower() or ("found devices" in output.lower() and "found devices: 0" not in output.lower())
            return has_devices

        except FileNotFoundError:
            logger.warning(f"CEC client not found: {self.cec_client_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking CEC availability: {e}")
            return False

    async def scan_devices(self) -> list[CecDevice]:
        """Scan for CEC devices on the HDMI bus.

        Returns:
            List of detected CEC devices
        """
        try:
            result = await asyncio.create_subprocess_exec(
                self.cec_client_path,
                "-s",
                "-d",
                "1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send scan command and wait for output
            stdout, stderr = await asyncio.wait_for(
                result.communicate(input=b"scan\nq\n"), timeout=10.0
            )

            devices = self._parse_scan_output(stdout.decode())
            self._devices_cache = {dev.address: dev for dev in devices}
            self._cache_valid = True

            logger.info(f"Detected {len(devices)} CEC devices")
            return devices

        except asyncio.TimeoutError:
            logger.error("CEC scan timeout")
            return []
        except Exception as e:
            logger.error(f"Error scanning CEC devices: {e}")
            return []

    def _parse_scan_output(self, output: str) -> list[CecDevice]:
        """Parse cec-client scan output.

        Args:
            output: Output from cec-client -s command

        Returns:
            List of CecDevice objects
        """
        devices = []

        # Pattern: "device #0: TV"
        device_pattern = re.compile(r"device #(\d+):\s+(.+?)(?:\s+\(([^)]+)\))?$", re.MULTILINE)
        # Pattern: "address: 0.0.0.0"
        addr_pattern = re.compile(r"address:\s+([\d.]+)")
        # Pattern: "vendor: Samsung"
        vendor_pattern = re.compile(r"vendor:\s+(.+?)$", re.MULTILINE)
        # Pattern: "active source: yes"
        active_pattern = re.compile(r"active source:\s+(yes|no)", re.IGNORECASE)

        matches = device_pattern.finditer(output)

        for match in matches:
            address = int(match.group(1))
            name = match.group(2).strip()
            device_type_str = match.group(3) or "Unknown"

            # Extract additional info from surrounding lines
            start_pos = match.start()
            end_pos = output.find("device #", start_pos + 1)
            if end_pos == -1:
                end_pos = len(output)
            device_block = output[start_pos:end_pos]

            # Parse vendor
            vendor_match = vendor_pattern.search(device_block)
            vendor = vendor_match.group(1).strip() if vendor_match else "Unknown"

            # Parse physical address
            addr_match = addr_pattern.search(device_block)
            physical_address = addr_match.group(1) if addr_match else "0.0.0.0"

            # Parse active source
            active_match = active_pattern.search(device_block)
            active_source = active_match and active_match.group(1).lower() == "yes"

            # Map device type
            device_type = self._map_device_type(device_type_str, name)

            devices.append(
                CecDevice(
                    address=address,
                    name=name,
                    vendor=vendor,
                    device_type=device_type,
                    active_source=active_source,
                    physical_address=physical_address,
                )
            )

        return devices

    def _map_device_type(self, type_str: str, name: str) -> CecDeviceType:
        """Map device type string to enum.

        Args:
            type_str: Device type string from cec-client
            name: Device name for additional hints

        Returns:
            CecDeviceType enum value
        """
        type_lower = type_str.lower()
        name_lower = name.lower()

        # TV always takes precedence
        if "tv" in type_lower and "tv" not in name_lower.replace("tv", "", 1):
            # Don't match "Fire TV" or "Apple TV" as TV device
            return CecDeviceType.TV
        elif "tv" in name_lower and not any(x in name_lower for x in ["fire", "apple", "roku"]):
            return CecDeviceType.TV
        elif "playback" in type_lower or any(
            x in name_lower for x in ["roku", "fire", "apple tv", "chromecast", "player", "playback"]
        ):
            return CecDeviceType.PLAYBACK_DEVICE
        elif "recording" in type_lower or "recorder" in name_lower:
            return CecDeviceType.RECORDING_DEVICE
        elif "tuner" in type_lower:
            return CecDeviceType.TUNER
        elif "audio" in type_lower or "receiver" in name_lower:
            return CecDeviceType.AUDIO_SYSTEM
        else:
            return CecDeviceType.UNKNOWN

    async def get_tv(self) -> Optional[CecDevice]:
        """Get the TV device (address 0).

        Returns:
            CecDevice for TV, or None if not found
        """
        if not self._cache_valid:
            await self.scan_devices()

        # TV is always at address 0
        return self._devices_cache.get(0)

    async def get_active_source(self) -> Optional[CecDevice]:
        """Get the currently active source device.

        Returns:
            CecDevice that is currently active, or None
        """
        devices = await self.scan_devices()
        for device in devices:
            if device.active_source:
                return device
        return None

    async def switch_to_device(self, device_address: int) -> bool:
        """Switch TV input to a specific CEC device.

        Args:
            device_address: CEC logical address (0-15) to switch to

        Returns:
            True if command succeeded
        """
        try:
            # Command: "tx 4F:82:{address}0:00"
            # 4F = source (our address), 82 = Active Source, {address} = target device
            command = f"tx 4F:82:{device_address:X}0:00"

            result = await asyncio.create_subprocess_exec(
                self.cec_client_path,
                "-s",
                "-d",
                "1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(input=f"{command}\nq\n".encode()), timeout=5.0
            )

            if result.returncode != 0:
                logger.error(f"CEC switch failed: {stderr.decode()}")
                return False

            logger.info(f"Switched to CEC device #{device_address}")
            self._cache_valid = False  # Invalidate cache after change
            return True

        except asyncio.TimeoutError:
            logger.error("CEC switch timeout")
            return False
        except Exception as e:
            logger.error(f"Error switching CEC input: {e}")
            return False

    async def switch_to_device_by_name(self, name: str) -> bool:
        """Switch TV input to a device by name.

        Args:
            name: Device name (case-insensitive substring match)

        Returns:
            True if command succeeded
        """
        devices = await self.scan_devices()
        name_lower = name.lower()

        for device in devices:
            if name_lower in device.name.lower():
                return await self.switch_to_device(device.address)

        logger.warning(f"CEC device not found: {name}")
        return False

    async def make_active_source(self) -> bool:
        """Make WomCast the active source (switch input to us).

        Returns:
            True if command succeeded
        """
        try:
            result = await asyncio.create_subprocess_exec(
                self.cec_client_path,
                "-s",
                "-d",
                "1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(input=b"as\nq\n"), timeout=5.0
            )

            if result.returncode != 0:
                logger.error(f"CEC make active source failed: {stderr.decode()}")
                return False

            logger.info("Made WomCast active source via CEC")
            self._cache_valid = False
            return True

        except asyncio.TimeoutError:
            logger.error("CEC make active source timeout")
            return False
        except Exception as e:
            logger.error(f"Error making active source: {e}")
            return False

    def to_dict(self) -> dict:
        """Export CEC state as dictionary.

        Returns:
            Dictionary with CEC status and devices
        """
        return {
            "cache_valid": self._cache_valid,
            "devices": [
                {
                    "address": dev.address,
                    "name": dev.name,
                    "vendor": dev.vendor,
                    "device_type": dev.device_type.value,
                    "active_source": dev.active_source,
                    "physical_address": dev.physical_address,
                }
                for dev in self._devices_cache.values()
            ],
        }


# Global CEC helper instance
_cec_helper: Optional[CecHelper] = None


def get_cec_helper() -> CecHelper:
    """Get the global CEC helper instance.

    Returns:
        CecHelper singleton
    """
    global _cec_helper
    if _cec_helper is None:
        _cec_helper = CecHelper()
    return _cec_helper
