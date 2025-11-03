"""Cloud streaming service API for WomCast.

Provides endpoints for discovering legal streaming services and generating
QR codes for deep links to native apps.

Legal compliance:
- NO DRM circumvention
- NO unauthorized content access
- Only provides links to official services
"""

import io
import logging

import qrcode
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from connectors.cloud import (
    CloudProvider,
    create_cloud_link,
    get_all_services,
    get_service,
    is_available_in_region,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="WomCast Cloud Services API", version="1.0.0")


# ============================================================================
# Pydantic Models (for API responses)
# ============================================================================


class CloudServiceResponse(BaseModel):
    """Cloud service metadata response."""

    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(..., description="Provider identifier (e.g., 'netflix')")
    name: str = Field(..., description="Service display name")
    description: str = Field(..., description="Service description")
    icon_url: str = Field(..., alias="iconUrl", description="Service icon URL")
    requires_subscription: bool = Field(
        ..., alias="requiresSubscription", description="Whether subscription is required"
    )
    regions: list[str] = Field(..., description="Supported ISO country codes")


class CloudLinkRequest(BaseModel):
    """Request to create a cloud service link."""

    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(..., description="Provider identifier")
    title: str = Field(..., description="Content title")
    content_id: str = Field(..., alias="contentId", description="Provider content ID")


class CloudLinkResponse(BaseModel):
    """Cloud service deep link response."""

    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(..., description="Provider identifier")
    title: str = Field(..., description="Content title")
    content_id: str = Field(..., alias="contentId", description="Provider content ID")
    deep_link: str = Field(..., alias="deepLink", description="Native app deep link")
    web_link: str = Field(..., alias="webLink", description="Web browser fallback URL")
    qr_code_url: str = Field(..., alias="qrCodeUrl", description="QR code endpoint URL")


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "cloud-services"}


@app.get("/v1/cloud/services", response_model=list[CloudServiceResponse])
async def list_services(
    region: str | None = Query(None, description="Filter by ISO country code")
):
    """List all available cloud streaming services.

    Args:
        region: Optional ISO country code to filter by region availability

    Returns:
        List of cloud services
    """
    services = get_all_services()

    # Filter by region if specified
    if region:
        services = [
            svc for svc in services if is_available_in_region(svc.provider, region)
        ]

    return [
        CloudServiceResponse(
            provider=svc.provider.value,
            name=svc.name,
            description=svc.description,
            iconUrl=svc.icon_url,
            requiresSubscription=svc.requires_subscription,
            regions=svc.regions,
        )
        for svc in services
    ]


@app.get("/v1/cloud/services/{provider}", response_model=CloudServiceResponse)
async def get_service_details(provider: str):
    """Get details for a specific cloud service.

    Args:
        provider: Provider identifier (e.g., 'netflix', 'disney_plus')

    Returns:
        Cloud service details

    Raises:
        HTTPException: 404 if provider not found
    """
    try:
        provider_enum = CloudProvider(provider)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider}")

    service = get_service(provider_enum)
    if not service:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider}")

    return CloudServiceResponse(
        provider=service.provider.value,
        name=service.name,
        description=service.description,
        iconUrl=service.icon_url,
        requiresSubscription=service.requires_subscription,
        regions=service.regions,
    )


@app.post("/v1/cloud/links", response_model=CloudLinkResponse)
async def create_link(request: CloudLinkRequest):
    """Create a deep link to cloud service content.

    Args:
        request: CloudLinkRequest with provider, title, and content ID

    Returns:
        CloudLinkResponse with deep link, web link, and QR code URL

    Raises:
        HTTPException: 400 if provider invalid or link creation fails
    """
    try:
        provider_enum = CloudProvider(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid provider: {request.provider}"
        )

    link = create_cloud_link(provider_enum, request.title, request.content_id)
    if not link:
        raise HTTPException(
            status_code=400, detail=f"Failed to create link for provider: {request.provider}"
        )

    # Generate QR code URL endpoint
    qr_url = f"/v1/cloud/qr?provider={request.provider}&content_id={request.content_id}"

    logger.info(
        f"Created cloud link: {request.provider} - {request.title} ({request.content_id})"
    )

    return CloudLinkResponse(
        provider=link.provider.value,
        title=link.title,
        contentId=link.content_id,
        deepLink=link.deep_link,
        webLink=link.web_link,
        qrCodeUrl=qr_url,
    )


@app.get("/v1/cloud/qr")
async def generate_qr_code(
    provider: str = Query(..., description="Provider identifier"),
    content_id: str = Query(..., alias="content_id", description="Content ID"),
    title: str = Query("Content", description="Content title for link"),
    size: int = Query(300, ge=100, le=1000, description="QR code size in pixels"),
):
    """Generate QR code for cloud service deep link.

    Args:
        provider: Provider identifier
        content_id: Provider-specific content ID
        title: Content title (optional)
        size: QR code image size in pixels (100-1000)

    Returns:
        PNG image of QR code

    Raises:
        HTTPException: 400 if provider invalid or QR generation fails
    """
    try:
        provider_enum = CloudProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    # Create cloud link
    link = create_cloud_link(provider_enum, title, content_id)
    if not link:
        raise HTTPException(
            status_code=400, detail=f"Failed to create link for provider: {provider}"
        )

    # Generate QR code
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size // 30,  # Adjust box size based on target size
            border=2,
        )
        qr.add_data(link.deep_link)
        qr.make(fit=True)

        # Create PIL image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to PNG bytes
        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        logger.info(f"Generated QR code for {provider} - {title} ({size}x{size}px)")

        return StreamingResponse(
            img_io,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'inline; filename="cloud_{provider}_{content_id}.png"',
            },
        )

    except Exception as e:
        logger.error(f"QR code generation failed: {e}")
        raise HTTPException(status_code=500, detail="QR code generation failed")


@app.get("/v1/cloud/availability/{provider}")
async def check_availability(
    provider: str, region: str = Query(..., description="ISO country code")
):
    """Check if a cloud service is available in a region.

    Args:
        provider: Provider identifier
        region: ISO country code (e.g., 'US', 'GB')

    Returns:
        Availability status

    Raises:
        HTTPException: 404 if provider not found
    """
    try:
        provider_enum = CloudProvider(provider)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider}")

    service = get_service(provider_enum)
    if not service:
        raise HTTPException(status_code=404, detail=f"Provider not found: {provider}")

    available = is_available_in_region(provider_enum, region)

    return {
        "provider": provider,
        "region": region.upper(),
        "available": available,
        "service_name": service.name,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
