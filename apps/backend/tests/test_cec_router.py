"""Tests for HDMI-CEC FastAPI router."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from playback.cec_helper import CecDevice, CecDeviceType
from playback.cec_routes import router


@pytest.fixture()
def app_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, AsyncMock]:
    """Create a TestClient with a mocked CEC helper instance."""

    helper = AsyncMock()
    helper.cec_client_path = "cec-client"

    monkeypatch.setattr("playback.cec_routes.get_cec_helper", lambda: helper)

    app = FastAPI()
    app.include_router(router)

    return TestClient(app), helper


def test_check_cec_available(app_client: tuple[TestClient, AsyncMock]) -> None:
    """CEC availability endpoint returns helper status."""

    client, helper = app_client
    helper.is_available.return_value = True

    response = client.get("/v1/cec/available")

    assert response.status_code == 200
    helper.is_available.assert_awaited_once()
    assert response.json() == {"available": True, "client_path": "cec-client"}


def test_list_devices(app_client: tuple[TestClient, AsyncMock]) -> None:
    """Devices endpoint returns serialized helper data."""

    client, helper = app_client
    helper.scan_devices.return_value = [
        CecDevice(
            address=1,
            name="Roku",
            vendor="Roku",
            device_type=CecDeviceType.PLAYBACK_DEVICE,
            active_source=False,
            physical_address="1.0.0.0",
        )
    ]

    response = client.get("/v1/cec/devices")

    assert response.status_code == 200
    helper.scan_devices.assert_awaited_once()
    assert response.json() == [
        {
            "address": 1,
            "name": "Roku",
            "vendor": "Roku",
            "deviceType": "Playback Device",
            "activeSource": False,
            "physicalAddress": "1.0.0.0",
        }
    ]


def test_switch_requires_parameters(app_client: tuple[TestClient, AsyncMock]) -> None:
    """Switch endpoint validates request body and triggers helper methods."""

    client, helper = app_client
    helper.switch_to_device.return_value = True

    response = client.post("/v1/cec/switch", json={"address": 4})

    assert response.status_code == 200
    helper.switch_to_device.assert_awaited_once_with(4)
    assert response.json()["success"] is True

    response_missing = client.post("/v1/cec/switch", json={})
    assert response_missing.status_code == 400