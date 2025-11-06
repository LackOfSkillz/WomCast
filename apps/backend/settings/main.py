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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from common.health import create_health_router
from common.settings import get_settings_manager

__version__ = "0.1.0"

LEGAL_TERMS_VERSION = os.getenv("LEGAL_TERMS_VERSION", "2025-11-cloud-v1")
LEGAL_TERMS_LAST_UPDATED = "2025-11-05"
LEGAL_TERMS_CONTENT = {
    "title": "WomCast Legal Notice & Provider Terms",
    "intro": (
        "WomCast links to third-party streaming providers using their official applications and "
        "public APIs. You must have the rights to access each service and you agree to comply "
        "with provider terms and the law when launching connectors from WomCast."
    ),
    "sections": [
        {
            "title": "Usage Guidelines",
            "items": [
                "Only access services for which you currently hold a valid subscription or the content is free/legal in your region.",
                "Do not attempt to bypass DRM, geo-restrictions, or authentication that providers enforce.",
                "Respect provider rate limits and API usage policies when browsing catalog data.",
                "You are responsible for ensuring that any custom playlists or connectors comply with copyright and licensing obligations.",
            ],
        },
        {
            "title": "Data & Privacy",
            "items": [
                "Connector requests are proxied through WomCast. Account credentials for third-party providers are never stored by WomCast.",
                "Provider apps that you launch may collect their own telemetry subject to their privacy policies.",
                "WomCast only retains connector session logs locally to troubleshoot failures; you can purge them from Settings → Privacy.",
            ],
        },
        {
            "title": "Third-Party Services",
            "items": [
                "Providers may change APIs or availability at any time. WomCast does not guarantee uptime for external services.",
                "Some providers restrict commercial or public display usage. Ensure your deployment scenario conforms to those terms.",
            ],
        },
    ],
    "providers": [
        {
            "name": "Netflix",
            "terms_url": "https://help.netflix.com/legal/termsofuse",
            "privacy_url": "https://help.netflix.com/legal/privacy",
            "notes": "Streaming content available only in participating regions with an active membership.",
        },
        {
            "name": "Disney+",
            "terms_url": "https://www.disneyplus.com/legal/subscriber-agreement",
            "privacy_url": "https://privacy.thewaltdisneycompany.com/en/current-privacy-policy/",
            "notes": "Includes Disney+, Hulu, and ESPN+ bundles where applicable.",
        },
        {
            "name": "HBO Max / Max",
            "terms_url": "https://www.max.com/terms-of-use",
            "privacy_url": "https://www.warnermediaprivacy.com/policycenter/b2c/en-us/",
            "notes": "Available content, devices, and features vary by territory.",
        },
        {
            "name": "YouTube",
            "terms_url": "https://www.youtube.com/t/terms",
            "privacy_url": "https://policies.google.com/privacy",
            "notes": "YouTube terms also apply to YouTube TV and YouTube Music experiences.",
        },
        {
            "name": "PBS",
            "terms_url": "https://www.pbs.org/about/about-pbs/terms-of-use/",
            "privacy_url": "https://www.pbs.org/about/about-pbs/privacy-policy/",
            "notes": "Content is made available for personal, non-commercial use.",
        },
        {
            "name": "NASA",
            "terms_url": "https://www.nasa.gov/multimedia/guidelines/index.html",
            "privacy_url": "https://www.nasa.gov/privacy/",
            "notes": "NASA imagery is in the public domain; some logos and insignia remain restricted.",
        },
        {
            "name": "Jamendo",
            "terms_url": "https://www.jamendo.com/legal/terms-of-use",
            "privacy_url": "https://www.jamendo.com/legal/privacy",
            "notes": "Tracks are distributed under Creative Commons or Jamendo licensing.",
        },
    ],
}

app = FastAPI(
    title="WomCast Settings Service",
    description="User preferences and application configuration management",
    version=__version__,
)

allowed_origins = os.getenv(
    "SETTINGS_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
)

cors_origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
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


class LegalProvider(BaseModel):
    name: str
    terms_url: str
    privacy_url: str | None = None
    notes: str | None = None


class LegalSection(BaseModel):
    title: str
    items: list[str]


class LegalAcknowledgement(BaseModel):
    version: str | None = None
    accepted_at: str | None = None


class LegalTermsResponse(BaseModel):
    version: str
    last_updated: str
    title: str
    intro: str
    sections: list[LegalSection]
    providers: list[LegalProvider]
    accepted: LegalAcknowledgement


class LegalAckRequest(BaseModel):
    version: str


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


@app.get("/v1/legal/terms", response_model=LegalTermsResponse)
async def get_legal_terms() -> LegalTermsResponse:
    """Return current legal notice content and acknowledgement state."""

    manager = get_settings_manager(SETTINGS_PATH)
    accepted_version = manager.get("legal_terms_version") or None
    accepted_at = manager.get("legal_terms_accepted_at")

    sections = [LegalSection(**section) for section in LEGAL_TERMS_CONTENT["sections"]]
    providers = [LegalProvider(**provider) for provider in LEGAL_TERMS_CONTENT["providers"]]

    return LegalTermsResponse(
        version=LEGAL_TERMS_VERSION,
        last_updated=LEGAL_TERMS_LAST_UPDATED,
        title=LEGAL_TERMS_CONTENT["title"],
        intro=LEGAL_TERMS_CONTENT["intro"],
        sections=sections,
        providers=providers,
        accepted=LegalAcknowledgement(version=accepted_version, accepted_at=accepted_at),
    )


@app.post("/v1/legal/ack")
async def acknowledge_legal_terms(payload: LegalAckRequest) -> dict[str, Any]:
    """Persist acknowledgement for the current legal notice version."""

    if payload.version != LEGAL_TERMS_VERSION:
        raise HTTPException(
            status_code=400,
            detail="Legal terms version mismatch. Refresh terms and try again.",
        )

    accepted_at = datetime.now(timezone.utc).isoformat()

    manager = get_settings_manager(SETTINGS_PATH)
    await manager.update(
        {
            "legal_terms_version": payload.version,
            "legal_terms_accepted_at": accepted_at,
        }
    )

    return {
        "status": "ok",
        "version": payload.version,
        "accepted_at": accepted_at,
    }
