"""Tests for cloud streaming service integration.

Tests cover:
- Service registry functionality
- Link generation
- Regional availability
- QR code generation
- FastAPI endpoints
"""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from connectors.cloud import (
    CloudLink,
    CloudProvider,
    CloudService,
    create_cloud_link,
    get_all_services,
    get_service,
    is_available_in_region,
)
from connectors.cloud.main import app

# ============================================================================
# Service Registry Tests
# ============================================================================


def test_get_all_services():
    """Test getting all cloud services."""
    services = get_all_services()

    assert len(services) == 10
    assert all(isinstance(svc, CloudService) for svc in services)

    # Check that services are sorted by name
    names = [svc.name for svc in services]
    assert names == sorted(names)

    # Verify key providers exist
    provider_values = {svc.provider for svc in services}
    assert CloudProvider.NETFLIX in provider_values
    assert CloudProvider.DISNEY_PLUS in provider_values
    assert CloudProvider.YOUTUBE in provider_values


def test_get_service():
    """Test getting a specific service."""
    service = get_service(CloudProvider.NETFLIX)

    assert service is not None
    assert service.provider == CloudProvider.NETFLIX
    assert service.name == "Netflix"
    assert service.requires_subscription is True
    assert "US" in service.regions
    assert "netflix://" in service.deep_link_template


def test_get_service_disney():
    """Test getting Disney+ service."""
    service = get_service(CloudProvider.DISNEY_PLUS)

    assert service is not None
    assert service.provider == CloudProvider.DISNEY_PLUS
    assert service.name == "Disney+"
    assert "disneyplus://" in service.deep_link_template


def test_is_available_in_region():
    """Test regional availability checking."""
    # Netflix is available in US
    assert is_available_in_region(CloudProvider.NETFLIX, "US") is True
    assert is_available_in_region(CloudProvider.NETFLIX, "us") is True  # Case insensitive

    # Hulu is only in US/JP
    assert is_available_in_region(CloudProvider.HULU, "US") is True
    assert is_available_in_region(CloudProvider.HULU, "JP") is True
    assert is_available_in_region(CloudProvider.HULU, "GB") is False

    # YouTube is global
    assert is_available_in_region(CloudProvider.YOUTUBE, "ZZ") is True
    assert is_available_in_region(CloudProvider.YOUTUBE, "ANY") is True


def test_create_cloud_link():
    """Test creating a cloud link."""
    link = create_cloud_link(CloudProvider.NETFLIX, "Stranger Things", "80057281")

    assert isinstance(link, CloudLink)
    assert link.provider == CloudProvider.NETFLIX
    assert link.title == "Stranger Things"
    assert link.content_id == "80057281"
    assert link.deep_link == "netflix://title/80057281"
    assert link.web_link == "https://www.netflix.com/title/80057281"
    assert "/v1/cloud/qr" in link.qr_code_url


def test_create_cloud_link_disney():
    """Test creating Disney+ link."""
    link = create_cloud_link(CloudProvider.DISNEY_PLUS, "The Mandalorian", "4JV6KzVD4f8l")

    assert link.provider == CloudProvider.DISNEY_PLUS
    assert link.deep_link == "disneyplus://content/4JV6KzVD4f8l"
    assert "disneyplus.com" in link.web_link


def test_create_cloud_link_youtube():
    """Test creating YouTube link."""
    link = create_cloud_link(CloudProvider.YOUTUBE, "Cool Video", "dQw4w9WgXcQ")

    assert link.provider == CloudProvider.YOUTUBE
    assert link.deep_link == "vnd.youtube://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert "youtube.com/watch?v=" in link.web_link


def test_free_services():
    """Test identifying free services."""
    get_all_services()

    # YouTube and Peacock have free tiers
    youtube = get_service(CloudProvider.YOUTUBE)
    peacock = get_service(CloudProvider.PEACOCK)

    assert youtube.requires_subscription is False
    assert peacock.requires_subscription is False

    # Netflix requires subscription
    netflix = get_service(CloudProvider.NETFLIX)
    assert netflix.requires_subscription is True


# ============================================================================
# FastAPI Endpoint Tests
# ============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "cloud-services"


def test_list_services_endpoint(client):
    """Test listing all services."""
    response = client.get("/v1/cloud/services")
    assert response.status_code == 200

    services = response.json()
    assert len(services) == 10
    assert all("provider" in svc for svc in services)
    assert all("name" in svc for svc in services)
    assert all("iconUrl" in svc for svc in services)

    # Check Netflix is in list
    netflix = next((s for s in services if s["provider"] == "netflix"), None)
    assert netflix is not None
    assert netflix["name"] == "Netflix"
    assert netflix["requiresSubscription"] is True


def test_list_services_region_filter(client):
    """Test listing services filtered by region."""
    # Get US-available services
    response = client.get("/v1/cloud/services?region=US")
    assert response.status_code == 200

    us_services = response.json()
    assert len(us_services) > 0

    # Hulu should be in US list
    hulu = next((s for s in us_services if s["provider"] == "hulu"), None)
    assert hulu is not None

    # Get GB services (Hulu should not be present)
    response = client.get("/v1/cloud/services?region=GB")
    assert response.status_code == 200

    gb_services = response.json()
    hulu_gb = next((s for s in gb_services if s["provider"] == "hulu"), None)
    assert hulu_gb is None  # Hulu not available in GB


def test_get_service_endpoint(client):
    """Test getting specific service details."""
    response = client.get("/v1/cloud/services/netflix")
    assert response.status_code == 200

    service = response.json()
    assert service["provider"] == "netflix"
    assert service["name"] == "Netflix"
    assert service["requiresSubscription"] is True
    assert "US" in service["regions"]


def test_get_service_not_found(client):
    """Test getting non-existent service."""
    response = client.get("/v1/cloud/services/invalid_provider")
    assert response.status_code == 404


def test_create_link_endpoint(client):
    """Test creating a cloud link."""
    request = {
        "provider": "netflix",
        "title": "Stranger Things",
        "contentId": "80057281",
    }

    response = client.post("/v1/cloud/links", json=request)
    assert response.status_code == 200

    link = response.json()
    assert link["provider"] == "netflix"
    assert link["title"] == "Stranger Things"
    assert link["contentId"] == "80057281"
    assert link["deepLink"] == "netflix://title/80057281"
    assert "netflix.com" in link["webLink"]
    assert "/v1/cloud/qr" in link["qrCodeUrl"]


def test_create_link_invalid_provider(client):
    """Test creating link with invalid provider."""
    request = {
        "provider": "invalid_service",
        "title": "Test",
        "contentId": "12345",
    }

    response = client.post("/v1/cloud/links", json=request)
    assert response.status_code == 400


def test_generate_qr_code(client):
    """Test QR code generation."""
    response = client.get(
        "/v1/cloud/qr?provider=netflix&content_id=80057281&title=Stranger%20Things"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Verify it's a valid PNG image
    img_bytes = response.content
    img = Image.open(io.BytesIO(img_bytes))
    assert img.format == "PNG"
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_generate_qr_code_custom_size(client):
    """Test QR code generation with custom size."""
    response = client.get(
        "/v1/cloud/qr?provider=youtube&content_id=dQw4w9WgXcQ&size=500"
    )
    assert response.status_code == 200

    img_bytes = response.content
    img = Image.open(io.BytesIO(img_bytes))
    # Size should be approximately 500x500 (may vary slightly due to QR structure)
    assert 400 < img.size[0] < 600


def test_generate_qr_invalid_provider(client):
    """Test QR generation with invalid provider."""
    response = client.get("/v1/cloud/qr?provider=invalid&content_id=123")
    assert response.status_code == 400


def test_check_availability_endpoint(client):
    """Test availability check endpoint."""
    # Netflix in US
    response = client.get("/v1/cloud/availability/netflix?region=US")
    assert response.status_code == 200

    data = response.json()
    assert data["provider"] == "netflix"
    assert data["region"] == "US"
    assert data["available"] is True
    assert data["service_name"] == "Netflix"

    # Hulu in GB (not available)
    response = client.get("/v1/cloud/availability/hulu?region=GB")
    assert response.status_code == 200

    data = response.json()
    assert data["available"] is False


def test_check_availability_invalid_provider(client):
    """Test availability check with invalid provider."""
    response = client.get("/v1/cloud/availability/invalid?region=US")
    assert response.status_code == 404


# ============================================================================
# Legal Compliance Tests
# ============================================================================


def test_no_drm_bypass():
    """Test that all links are official (no DRM bypass)."""
    all_services = get_all_services()

    for service in all_services:
        # All deep links should use official app protocols
        assert (
            service.deep_link_template.startswith("https://")
            or "://" in service.deep_link_template
        )

        # All web links should point to official domains
        assert service.web_url_template.startswith("https://")

        # Check for official domains
        official_domains = [
            "netflix.com",
            "disneyplus.com",
            "hbomax.com",
            "primevideo.com",
            "amazon.com",
            "hulu.com",
            "apple.com",
            "peacocktv.com",
            "paramountplus.com",
            "youtube.com",
        ]
        assert any(domain in service.web_url_template for domain in official_domains)


def test_subscription_transparency():
    """Test that subscription requirements are clearly indicated."""
    all_services = get_all_services()

    for service in all_services:
        # Subscription requirement must be explicitly set
        assert isinstance(service.requires_subscription, bool)

        # Description should be clear
        assert len(service.description) > 0


def test_region_restrictions_honored():
    """Test that regional restrictions are respected."""
    # Hulu is only in US/JP
    hulu = get_service(CloudProvider.HULU)
    assert set(hulu.regions) == {"US", "JP"}

    # YouTube TV is US-only
    youtube_tv = get_service(CloudProvider.YOUTUBE_TV)
    assert youtube_tv.regions == ["US"]

    # YouTube is global
    youtube = get_service(CloudProvider.YOUTUBE)
    assert youtube.regions == ["*"]
