"""Settings Service - User preferences and application configuration."""

import asyncio
import base64
import io
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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
DATABASE_PATH = Path(
    os.getenv("MEDIA_DB_PATH", Path(__file__).parent.parent / "womcast.db")
)
VOICE_SERVICE_URL = os.getenv("VOICE_SERVICE_URL", "http://localhost:3003")
CAST_SERVICE_URL = os.getenv("CAST_SERVICE_URL", "http://localhost:3005")

logger = logging.getLogger(__name__)


class SettingUpdate(BaseModel):
    """Request model for updating a single setting"""

    key: str
    value: Any


class SettingsUpdate(BaseModel):
    """Request model for updating multiple settings"""

    settings: dict[str, Any]


async def _fetch_voice_history() -> dict[str, Any]:
    """Retrieve voice history via voice service API."""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{VOICE_SERVICE_URL}/v1/voice/history")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - remote service issues
        logger.warning("Voice history export failed: %s", exc)
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": payload}


async def _delete_voice_history() -> dict[str, Any]:
    """Delete voice history via voice service API."""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{VOICE_SERVICE_URL}/v1/voice/history")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - remote service issues
        logger.warning("Voice history deletion failed: %s", exc)
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": payload}


async def _fetch_cast_sessions() -> dict[str, Any]:
    """Retrieve cast sessions via cast service API."""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CAST_SERVICE_URL}/v1/cast/sessions")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - remote service issues
        logger.warning("Cast session export failed: %s", exc)
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": payload}


async def _reset_cast_sessions() -> dict[str, Any]:
    """Reset cast sessions via cast service API."""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(f"{CAST_SERVICE_URL}/v1/cast/sessions")
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - remote service issues
        logger.warning("Cast session reset failed: %s", exc)
        return {"success": False, "error": str(exc)}

    return {"success": True, "data": payload}


def _serialize_sqlite_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert sqlite3.Row to JSON-serializable dict."""

    serialized: dict[str, Any] = {}
    for key in row.keys():
        value = row[key]
        if isinstance(value, bytes):
            serialized[key] = base64.b64encode(value).decode("ascii")
        else:
            serialized[key] = value
    return serialized


async def _export_database() -> dict[str, Any]:
    """Export relevant SQLite tables to JSON structure."""

    if not DATABASE_PATH.exists():
        return {"available": False, "reason": "database-not-found"}

    def _export() -> dict[str, Any]:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            dump: dict[str, Any] = {"available": True, "tables": {}, "table_count": len(tables)}

            for table in tables:
                rows = connection.execute(f"SELECT * FROM {table}").fetchall()
                dump["tables"][table] = {
                    "rows": [_serialize_sqlite_row(row) for row in rows],
                    "row_count": len(rows),
                }

            return dump
        finally:
            connection.close()

    return await asyncio.to_thread(_export)


async def _purge_database() -> dict[str, Any]:
    """Delete data from user tables in SQLite database."""

    if not DATABASE_PATH.exists():
        return {
            "available": False,
            "reason": "database-not-found",
            "tables": {},
            "total_rows_deleted": 0,
        }

    def _purge() -> dict[str, Any]:
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            cursor = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            deleted_counts: dict[str, int] = {}
            total = 0
            for table in tables:
                count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                connection.execute(f"DELETE FROM {table}")
                deleted_counts[table] = count
                total += count

            connection.commit()
            return {
                "available": True,
                "tables": deleted_counts,
                "total_rows_deleted": total,
            }
        finally:
            connection.close()

    return await asyncio.to_thread(_purge)


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


@app.get("/v1/privacy/export")
async def export_privacy_data() -> StreamingResponse:
    """Aggregate privacy-related data and return as downloadable JSON."""

    manager = get_settings_manager(SETTINGS_PATH)
    await manager.refresh()
    settings_data = manager.get_all()

    voice_history_task = asyncio.create_task(_fetch_voice_history())
    cast_sessions_task = asyncio.create_task(_fetch_cast_sessions())
    database_dump = await _export_database()
    voice_history = await voice_history_task
    cast_sessions = await cast_sessions_task

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "settings": settings_data,
        "voice_history": voice_history,
        "cast_sessions": cast_sessions,
        "database": database_dump,
    }

    json_bytes = json.dumps(payload, indent=2).encode("utf-8")
    filename = f"womcast-privacy-export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/v1/privacy/delete")
async def delete_privacy_data() -> dict[str, Any]:
    """Reset settings and purge cached personal data."""

    manager = get_settings_manager(SETTINGS_PATH)
    await manager.reset()

    voice_result, cast_result, db_result = await asyncio.gather(
        _delete_voice_history(), _reset_cast_sessions(), _purge_database()
    )

    summary = {
        "settings_reset": True,
        "voice_history": voice_result,
        "cast_sessions": cast_result,
        "database": db_result,
    }

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": summary,
        "message": "Privacy data purged and settings reset",
    }
