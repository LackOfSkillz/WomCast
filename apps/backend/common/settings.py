"""Settings persistence service.

Manages user preferences and application settings in JSON format.
Includes settings for models, shares, privacy flags, theme, and more.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    # Voice/AI models
    "voice_model": "vosk-model-small-en-us-0.15",
    "llm_model": None,  # Local LLM for search assistance
    "stt_enabled": True,  # Speech-to-text
    "tts_enabled": True,  # Text-to-speech
    # Network shares
    "auto_mount_shares": True,
    "auto_index_shares": True,
    # Privacy flags
    "analytics_enabled": False,
    "crash_reporting": False,
    "metadata_fetching_enabled": True,
    # UI preferences
    "theme": "dark",  # dark, light, auto
    "language": "en",
    "grid_size": "medium",  # small, medium, large
    "autoplay_next": True,
    "show_subtitles": True,
    # Playback settings
    "default_volume": 80,
    "resume_threshold_seconds": 60,  # Don't resume if <60s remaining
    "skip_intro_seconds": 0,  # Auto-skip intro (0 = disabled)
    # Performance
    "cache_size_mb": 500,
    "thumbnail_quality": "medium",  # low, medium, high
    # Notifications
    "show_notifications": True,
    "notification_duration_ms": 3000,
}


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, settings_path: Path):
        self.settings_path = settings_path
        self._settings: dict[str, Any] = {}
        self._loaded = False

    async def load(self) -> None:
        """Load settings from JSON file."""
        if not self.settings_path.exists():
            # Initialize with defaults
            self._settings = DEFAULT_SETTINGS.copy()
            self._loaded = True  # Mark as loaded before save
            await self.save()
            logger.info(f"Created default settings at {self.settings_path}")
        else:
            try:
                with open(self.settings_path) as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    self._settings = DEFAULT_SETTINGS.copy()
                    self._settings.update(loaded)
                logger.info(f"Loaded settings from {self.settings_path}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self._settings = DEFAULT_SETTINGS.copy()

            self._loaded = True

    async def save(self) -> None:
        """Save settings to JSON file."""
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w") as f:
                json.dump(self._settings, f, indent=2)
            logger.info(f"Saved settings to {self.settings_path}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        return self._settings.get(key, default)

    def get_all(self) -> dict[str, Any]:
        """Get all settings.

        Returns:
            Dictionary of all settings
        """
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        return self._settings.copy()

    async def set(self, key: str, value: Any) -> None:
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value
        """
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        self._settings[key] = value
        await self.save()
        logger.info(f"Updated setting: {key} = {value}")

    async def update(self, updates: dict[str, Any]) -> None:
        """Update multiple settings.

        Args:
            updates: Dictionary of setting updates
        """
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        self._settings.update(updates)
        await self.save()
        logger.info(f"Updated {len(updates)} settings")

    async def reset(self) -> None:
        """Reset all settings to defaults."""
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        self._settings = DEFAULT_SETTINGS.copy()
        await self.save()
        logger.info("Reset all settings to defaults")

    async def delete(self, key: str) -> None:
        """Delete a setting (reverts to default if it exists).

        Args:
            key: Setting key to delete
        """
        if not self._loaded:
            raise RuntimeError("Settings not loaded. Call load() first.")

        if key in self._settings:
            # Revert to default if it exists
            if key in DEFAULT_SETTINGS:
                self._settings[key] = DEFAULT_SETTINGS[key]
            else:
                del self._settings[key]
            await self.save()
            logger.info(f"Deleted setting: {key}")


# Global settings manager instance
_settings_manager: SettingsManager | None = None


def get_settings_manager(settings_path: Path | None = None) -> SettingsManager:
    """Get the global settings manager instance.

    Args:
        settings_path: Path to settings file (default: ./settings.json)

    Returns:
        SettingsManager instance
    """
    global _settings_manager

    if _settings_manager is None:
        if settings_path is None:
            settings_path = Path("settings.json")
        _settings_manager = SettingsManager(settings_path)

    return _settings_manager


if __name__ == "__main__":
    # Example usage for testing
    import asyncio
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def main() -> None:
        if len(sys.argv) < 2:
            print("Usage: python -m common.settings <command> [args]")
            print("Commands:")
            print("  init                    - Initialize settings with defaults")
            print("  get <key>              - Get a setting value")
            print("  set <key> <value>      - Set a setting value")
            print("  list                   - List all settings")
            print("  reset                  - Reset all settings to defaults")
            sys.exit(1)

        command = sys.argv[1]
        manager = get_settings_manager(Path("settings.json"))
        await manager.load()

        if command == "init":
            print("Settings initialized with defaults")

        elif command == "get":
            key = sys.argv[2]
            value = manager.get(key)
            print(f"{key} = {value}")

        elif command == "set":
            key = sys.argv[2]
            value = sys.argv[3]
            # Try to parse as JSON for complex types
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Keep as string
            await manager.set(key, value)
            print(f"Set {key} = {value}")

        elif command == "list":
            settings = manager.get_all()
            print(json.dumps(settings, indent=2))

        elif command == "reset":
            await manager.reset()
            print("Reset all settings to defaults")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    asyncio.run(main())
