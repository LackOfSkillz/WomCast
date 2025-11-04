import json
from typing import Any

from fastapi.testclient import TestClient

from settings import main as settings_main
from common import settings as common_settings


def _reset_settings_manager(original_manager: Any) -> None:
    common_settings._settings_manager = original_manager


def test_privacy_export_endpoint(tmp_path, monkeypatch):
    original_settings_path = settings_main.SETTINGS_PATH
    original_database_path = settings_main.DATABASE_PATH
    original_manager = common_settings._settings_manager

    settings_main.SETTINGS_PATH = tmp_path / "settings.json"
    settings_main.DATABASE_PATH = tmp_path / "womcast.db"
    common_settings._settings_manager = None

    async def fake_voice_history() -> dict[str, Any]:  # type: ignore[override]
        return {"success": True, "data": {"entries": [], "total_entries": 0}}

    async def fake_cast_sessions() -> dict[str, Any]:  # type: ignore[override]
        return {"success": True, "data": {"sessions": []}}

    async def fake_export_database() -> dict[str, Any]:  # type: ignore[override]
        return {"available": False, "reason": "database-not-found"}

    monkeypatch.setattr(settings_main, "_fetch_voice_history", fake_voice_history)
    monkeypatch.setattr(settings_main, "_fetch_cast_sessions", fake_cast_sessions)
    monkeypatch.setattr(settings_main, "_export_database", fake_export_database)

    try:
        with TestClient(settings_main.app) as client:
            response = client.get("/v1/privacy/export")
            assert response.status_code == 200

            payload = json.loads(response.content.decode("utf-8"))
            assert "exported_at" in payload
            assert payload["voice_history"]["success"] is True
            assert payload["cast_sessions"]["success"] is True
            assert payload["database"]["available"] is False
            assert payload["settings"]["voice_model"] == "small"
    finally:
        settings_main.SETTINGS_PATH = original_settings_path
        settings_main.DATABASE_PATH = original_database_path
        _reset_settings_manager(original_manager)


def test_privacy_delete_endpoint(tmp_path, monkeypatch):
    original_settings_path = settings_main.SETTINGS_PATH
    original_database_path = settings_main.DATABASE_PATH
    original_manager = common_settings._settings_manager

    settings_main.SETTINGS_PATH = tmp_path / "settings.json"
    settings_main.DATABASE_PATH = tmp_path / "womcast.db"
    common_settings._settings_manager = None

    async def fake_delete_voice_history() -> dict[str, Any]:  # type: ignore[override]
        return {"success": True, "data": {"deleted_entries": 5}}

    async def fake_reset_cast_sessions() -> dict[str, Any]:  # type: ignore[override]
        return {"success": True, "data": {"removed_sessions": 2}}

    async def fake_purge_database() -> dict[str, Any]:  # type: ignore[override]
        return {"available": True, "tables": {"media_files": 10}, "total_rows_deleted": 10}

    monkeypatch.setattr(settings_main, "_delete_voice_history", fake_delete_voice_history)
    monkeypatch.setattr(settings_main, "_reset_cast_sessions", fake_reset_cast_sessions)
    monkeypatch.setattr(settings_main, "_purge_database", fake_purge_database)

    try:
        with TestClient(settings_main.app) as client:
            response = client.post("/v1/privacy/delete")
            assert response.status_code == 200
            payload = response.json()

            assert payload["status"] == "ok"
            assert payload["results"]["voice_history"]["data"]["deleted_entries"] == 5
            assert payload["results"]["cast_sessions"]["data"]["removed_sessions"] == 2
            assert payload["results"]["database"]["total_rows_deleted"] == 10

            manager = common_settings.get_settings_manager(settings_main.SETTINGS_PATH)
            assert manager.get("voice_model") == "small"
    finally:
        settings_main.SETTINGS_PATH = original_settings_path
        settings_main.DATABASE_PATH = original_database_path
        _reset_settings_manager(original_manager)
