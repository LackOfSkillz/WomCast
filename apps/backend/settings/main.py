"""
Settings Service - User preferences and application configuration.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from common.health import create_health_router
from common.settings import get_settings_manager

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast Settings Service",
    description="User preferences and application configuration management",
    version=__version__,
)

create_health_router(app, "settings-service", __version__)

# Settings file path
SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"


class SettingUpdate(BaseModel):
    """Request model for updating a single setting"""

    key: str
    value: Any


class SettingsUpdate(BaseModel):
    """Request model for updating multiple settings"""

    settings: dict[str, Any]


@app.on_event("startup")
async def startup() -> None:
    """Initialize settings on startup"""
    manager = get_settings_manager(SETTINGS_PATH)
    await manager.load()


@app.get("/v1/settings")
async def get_settings() -> dict[str, Any]:
    """
    Get all settings.

    Returns:
        Dictionary of all settings
    """
    manager = get_settings_manager(SETTINGS_PATH)
    return manager.get_all()


@app.get("/v1/settings/{key}")
async def get_setting(key: str) -> dict[str, Any]:
    """
    Get a specific setting value.

    Args:
        key: Setting key

    Returns:
        Dictionary with key and value
    """
    manager = get_settings_manager(SETTINGS_PATH)
    value = manager.get(key)

    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return {"key": key, "value": value}


@app.put("/v1/settings/{key}")
async def update_setting(key: str, update: SettingUpdate) -> dict[str, Any]:
    """
    Update a single setting.

    Args:
        key: Setting key (must match body key)
        update: Setting update data

    Returns:
        Updated setting
    """
    if update.key != key:
        raise HTTPException(
            status_code=400,
            detail="Key in path must match key in request body",
        )

    manager = get_settings_manager(SETTINGS_PATH)
    await manager.set(key, update.value)

    return {"key": key, "value": update.value}


@app.put("/v1/settings")
async def update_settings(update: SettingsUpdate) -> dict[str, Any]:
    """
    Update multiple settings at once.

    Args:
        update: Settings update data

    Returns:
        All updated settings
    """
    manager = get_settings_manager(SETTINGS_PATH)
    await manager.update(update.settings)

    return manager.get_all()


@app.delete("/v1/settings/{key}")
async def delete_setting(key: str) -> dict[str, str]:
    """
    Delete a setting (reverts to default if it exists).

    Args:
        key: Setting key to delete

    Returns:
        Success message
    """
    manager = get_settings_manager(SETTINGS_PATH)
    await manager.delete(key)

    return {"message": f"Setting '{key}' deleted (reverted to default if applicable)"}


@app.post("/v1/settings/reset")
async def reset_settings() -> dict[str, Any]:
    """
    Reset all settings to defaults.

    Returns:
        All settings after reset
    """
    manager = get_settings_manager(SETTINGS_PATH)
    await manager.reset()

    return manager.get_all()
