"""Test suite for common health endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.health import create_health_router


def test_health_check() -> None:
    """Test health check endpoint returns healthy status."""
    app = FastAPI()
    create_health_router(app, "test-service", "1.0.0")
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "test-service"


def test_version_info() -> None:
    """Test version endpoint returns correct service info."""
    app = FastAPI()
    create_health_router(app, "test-service", "1.0.0")
    client = TestClient(app)

    response = client.get("/version")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "test-service"
    assert data["version"] == "1.0.0"
