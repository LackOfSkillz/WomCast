from fastapi.testclient import TestClient

from settings import main as settings_main
from common import settings as common_settings


def _reset_settings_manager(original_manager):
    common_settings._settings_manager = original_manager


def test_get_legal_terms_default(tmp_path):
    original_settings_path = settings_main.SETTINGS_PATH
    original_manager = common_settings._settings_manager

    settings_main.SETTINGS_PATH = tmp_path / "settings.json"
    common_settings._settings_manager = None

    try:
        with TestClient(settings_main.app) as client:
            response = client.get("/v1/legal/terms")
            assert response.status_code == 200
            payload = response.json()

            assert payload["version"] == settings_main.LEGAL_TERMS_VERSION
            assert payload["accepted"]["version"] is None
            assert payload["accepted"]["accepted_at"] is None
            assert payload["title"]
            assert payload["providers"]
    finally:
        settings_main.SETTINGS_PATH = original_settings_path
        _reset_settings_manager(original_manager)


def test_acknowledge_legal_terms(tmp_path):
    original_settings_path = settings_main.SETTINGS_PATH
    original_manager = common_settings._settings_manager

    settings_main.SETTINGS_PATH = tmp_path / "settings.json"
    common_settings._settings_manager = None

    try:
        with TestClient(settings_main.app) as client:
            ack_response = client.post(
                "/v1/legal/ack",
                json={"version": settings_main.LEGAL_TERMS_VERSION},
            )
            assert ack_response.status_code == 200
            ack_payload = ack_response.json()
            assert ack_payload["status"] == "ok"
            assert ack_payload["version"] == settings_main.LEGAL_TERMS_VERSION
            assert ack_payload["accepted_at"]

            terms_response = client.get("/v1/legal/terms")
            assert terms_response.status_code == 200
            terms_payload = terms_response.json()
            assert (
                terms_payload["accepted"]["version"]
                == settings_main.LEGAL_TERMS_VERSION
            )
            assert terms_payload["accepted"]["accepted_at"] == ack_payload["accepted_at"]
    finally:
        settings_main.SETTINGS_PATH = original_settings_path
        _reset_settings_manager(original_manager)
