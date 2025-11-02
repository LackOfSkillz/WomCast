"""Network share mounting service.

Provides SMB/NFS mount management for network storage devices.
Supports user-configured shares with credential management.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NetworkShare:
    """Network share configuration."""

    id: str
    name: str
    protocol: str  # "smb" or "nfs"
    host: str
    share_path: str
    mount_point: Path
    username: str | None = None
    password: str | None = None
    enabled: bool = True
    auto_index: bool = False


class NetworkShareManager:
    """Manages network share mounting and configuration."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.shares: dict[str, NetworkShare] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load share configuration from JSON file."""
        if not self.config_path.exists():
            logger.info(f"No config file found at {self.config_path}, starting fresh")
            return

        try:
            with open(self.config_path) as f:
                data = json.load(f)
                for share_data in data.get("shares", []):
                    share = NetworkShare(
                        id=share_data["id"],
                        name=share_data["name"],
                        protocol=share_data["protocol"],
                        host=share_data["host"],
                        share_path=share_data["share_path"],
                        mount_point=Path(share_data["mount_point"]),
                        username=share_data.get("username"),
                        password=share_data.get("password"),
                        enabled=share_data.get("enabled", True),
                        auto_index=share_data.get("auto_index", False),
                    )
                    self.shares[share.id] = share
            logger.info(f"Loaded {len(self.shares)} network shares from config")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def _save_config(self) -> None:
        """Save share configuration to JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "shares": [
                    {
                        "id": share.id,
                        "name": share.name,
                        "protocol": share.protocol,
                        "host": share.host,
                        "share_path": share.share_path,
                        "mount_point": str(share.mount_point),
                        "username": share.username,
                        "password": share.password,
                        "enabled": share.enabled,
                        "auto_index": share.auto_index,
                    }
                    for share in self.shares.values()
                ]
            }
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.shares)} network shares to config")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def add_share(
        self,
        share_id: str,
        name: str,
        protocol: str,
        host: str,
        share_path: str,
        mount_point: str,
        username: str | None = None,
        password: str | None = None,
        enabled: bool = True,
        auto_index: bool = False,
    ) -> NetworkShare:
        """Add a new network share configuration."""
        if protocol not in ("smb", "nfs"):
            raise ValueError(f"Unsupported protocol: {protocol}")

        share = NetworkShare(
            id=share_id,
            name=name,
            protocol=protocol,
            host=host,
            share_path=share_path,
            mount_point=Path(mount_point),
            username=username,
            password=password,
            enabled=enabled,
            auto_index=auto_index,
        )
        self.shares[share_id] = share
        self._save_config()
        logger.info(f"Added network share: {name} ({protocol}://{host}{share_path})")
        return share

    def remove_share(self, share_id: str) -> bool:
        """Remove a network share configuration."""
        if share_id not in self.shares:
            return False

        share = self.shares[share_id]
        if self.is_mounted(share_id):
            asyncio.create_task(self.unmount(share_id))

        del self.shares[share_id]
        self._save_config()
        logger.info(f"Removed network share: {share.name}")
        return True

    def update_share(self, share_id: str, **kwargs: Any) -> NetworkShare | None:
        """Update network share configuration."""
        if share_id not in self.shares:
            return None

        share = self.shares[share_id]
        for key, value in kwargs.items():
            if hasattr(share, key):
                setattr(share, key, value)

        self._save_config()
        logger.info(f"Updated network share: {share.name}")
        return share

    def get_share(self, share_id: str) -> NetworkShare | None:
        """Get network share by ID."""
        return self.shares.get(share_id)

    def list_shares(self) -> list[NetworkShare]:
        """List all configured network shares."""
        return list(self.shares.values())

    def is_mounted(self, share_id: str) -> bool:
        """Check if a network share is currently mounted."""
        share = self.shares.get(share_id)
        if not share:
            return False

        return share.mount_point.exists() and share.mount_point.is_mount()

    async def mount(self, share_id: str) -> bool:
        """Mount a network share."""
        share = self.shares.get(share_id)
        if not share:
            logger.error(f"Share not found: {share_id}")
            return False

        if not share.enabled:
            logger.warning(f"Share disabled: {share.name}")
            return False

        if self.is_mounted(share_id):
            logger.info(f"Share already mounted: {share.name}")
            return True

        # Create mount point
        share.mount_point.mkdir(parents=True, exist_ok=True)

        # Build mount command
        if share.protocol == "smb":
            cmd = ["mount", "-t", "cifs"]
            source = f"//{share.host}{share.share_path}"
            options = []
            if share.username:
                options.append(f"username={share.username}")
            if share.password:
                options.append(f"password={share.password}")
            if options:
                cmd.extend(["-o", ",".join(options)])
            cmd.extend([source, str(share.mount_point)])
        elif share.protocol == "nfs":
            cmd = ["mount", "-t", "nfs"]
            source = f"{share.host}:{share.share_path}"
            cmd.extend([source, str(share.mount_point)])
        else:
            logger.error(f"Unsupported protocol: {share.protocol}")
            return False

        # Execute mount command
        try:
            logger.info(f"Mounting {share.name}: {' '.join(cmd[:-2])} ...")
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                logger.info(f"Successfully mounted: {share.name}")
                return True
            else:
                logger.error(
                    f"Mount failed: {share.name} - {stderr.decode().strip()}"
                )
                return False
        except Exception as e:
            logger.error(f"Mount exception: {share.name} - {e}")
            return False

    async def unmount(self, share_id: str) -> bool:
        """Unmount a network share."""
        share = self.shares.get(share_id)
        if not share:
            logger.error(f"Share not found: {share_id}")
            return False

        if not self.is_mounted(share_id):
            logger.info(f"Share not mounted: {share.name}")
            return True

        # Execute unmount command
        try:
            logger.info(f"Unmounting {share.name}")
            result = await asyncio.create_subprocess_exec(
                "umount",
                str(share.mount_point),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                logger.info(f"Successfully unmounted: {share.name}")
                return True
            else:
                logger.error(
                    f"Unmount failed: {share.name} - {stderr.decode().strip()}"
                )
                return False
        except Exception as e:
            logger.error(f"Unmount exception: {share.name} - {e}")
            return False

    async def mount_all(self) -> dict[str, bool]:
        """Mount all enabled network shares."""
        results = {}
        for share_id, share in self.shares.items():
            if share.enabled:
                results[share_id] = await self.mount(share_id)
        return results

    async def unmount_all(self) -> dict[str, bool]:
        """Unmount all network shares."""
        results = {}
        for share_id in self.shares:
            if self.is_mounted(share_id):
                results[share_id] = await self.unmount(share_id)
        return results
