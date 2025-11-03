"""
Tests for QR code generation endpoint.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from cast.main import app
from cast.sessions import SessionManager


@pytest.fixture(autouse=True)
async def setup_globals():
    """Initialize session manager for tests."""
    from cast import main

    main.session_manager = SessionManager(session_ttl=300, cleanup_interval=60)
    await main.session_manager.start()
    yield
    await main.session_manager.stop()


client = TestClient(app)


def test_get_session_qr_success():
    """Test successful QR code generation for active session."""
    # Create a session first
    response = client.post(
        "/v1/cast/session",
        json={"device_type": "phone", "user_agent": "TestAgent"},
    )
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["session_id"]

    # Request QR code
    response = client.get(f"/v1/cast/session/{session_id}/qr")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Verify it's a valid PNG image
    img = Image.open(BytesIO(response.content))
    assert img.format == "PNG"
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_get_session_qr_not_found():
    """Test QR code request for non-existent session."""
    response = client.get("/v1/cast/session/nonexistent123/qr")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_session_qr_after_pairing():
    """Test QR code still works after session is paired."""
    # Create and pair session
    response = client.post(
        "/v1/cast/session",
        json={"device_type": "phone"},
    )
    session_data = response.json()
    session_id = session_data["session_id"]
    pin = session_data["pin"]

    # Pair the session
    client.post(
        "/v1/cast/session/pair",
        json={"pin": pin, "device_info": {"model": "TestPhone"}},
    )

    # QR should still be accessible
    response = client.get(f"/v1/cast/session/{session_id}/qr")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

