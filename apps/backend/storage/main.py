"""Network storage service - SMB/NFS share management.

Provides REST API for configuring and mounting network shares.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..common.health import create_health_router
from ..storage.network import NetworkShareManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="WomCast Storage Service",
    description="Network share management (SMB/NFS)",
    version="0.2.0",
)

# Health check endpoints
create_health_router(app, "storage", "0.2.0")

# Initialize network share manager
CONFIG_PATH = Path("/opt/womcast/data/network-shares.json")
if not CONFIG_PATH.parent.exists():
    # Development fallback
    CONFIG_PATH = Path("network-shares.json")

share_manager = NetworkShareManager(CONFIG_PATH)


# Request/Response Models
class ShareCreateRequest(BaseModel):
    """Request to create a new network share."""

    name: str = Field(..., description="Human-readable share name")
    protocol: str = Field(..., pattern="^(smb|nfs)$", description="Protocol: smb or nfs")
    host: str = Field(..., description="Server hostname or IP address")
    share_path: str = Field(..., description="Share path (e.g., /media or /shared)")
    mount_point: str = Field(..., description="Local mount point path")
    username: str | None = Field(None, description="Username (SMB only)")
    password: str | None = Field(None, description="Password (SMB only)")
    enabled: bool = Field(True, description="Enable auto-mount on boot")
    auto_index: bool = Field(False, description="Include in media library indexing")


class ShareUpdateRequest(BaseModel):
    """Request to update network share configuration."""

    name: str | None = None
    enabled: bool | None = None
    auto_index: bool | None = None
    username: str | None = None
    password: str | None = None


class ShareResponse(BaseModel):
    """Network share configuration response."""

    id: str
    name: str
    protocol: str
    host: str
    share_path: str
    mount_point: str
    username: str | None
    enabled: bool
    auto_index: bool
    is_mounted: bool


# API Endpoints
@app.get("/v1/shares", response_model=list[ShareResponse])
async def list_shares() -> list[ShareResponse]:
    """List all configured network shares."""
    shares = share_manager.list_shares()
    return [
        ShareResponse(
            id=share.id,
            name=share.name,
            protocol=share.protocol,
            host=share.host,
            share_path=share.share_path,
            mount_point=str(share.mount_point),
            username=share.username,
            enabled=share.enabled,
            auto_index=share.auto_index,
            is_mounted=share_manager.is_mounted(share.id),
        )
        for share in shares
    ]


@app.post("/v1/shares", response_model=ShareResponse, status_code=201)
async def create_share(request: ShareCreateRequest) -> ShareResponse:
    """Create a new network share configuration."""
    # Generate unique ID
    import uuid

    share_id = str(uuid.uuid4())

    # Add share
    share = share_manager.add_share(
        share_id=share_id,
        name=request.name,
        protocol=request.protocol,
        host=request.host,
        share_path=request.share_path,
        mount_point=request.mount_point,
        username=request.username,
        password=request.password,
        enabled=request.enabled,
        auto_index=request.auto_index,
    )

    return ShareResponse(
        id=share.id,
        name=share.name,
        protocol=share.protocol,
        host=share.host,
        share_path=share.share_path,
        mount_point=str(share.mount_point),
        username=share.username,
        enabled=share.enabled,
        auto_index=share.auto_index,
        is_mounted=share_manager.is_mounted(share.id),
    )


@app.get("/v1/shares/{share_id}", response_model=ShareResponse)
async def get_share(share_id: str) -> ShareResponse:
    """Get network share details by ID."""
    share = share_manager.get_share(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    return ShareResponse(
        id=share.id,
        name=share.name,
        protocol=share.protocol,
        host=share.host,
        share_path=share.share_path,
        mount_point=str(share.mount_point),
        username=share.username,
        enabled=share.enabled,
        auto_index=share.auto_index,
        is_mounted=share_manager.is_mounted(share.id),
    )


@app.put("/v1/shares/{share_id}", response_model=ShareResponse)
async def update_share(share_id: str, request: ShareUpdateRequest) -> ShareResponse:
    """Update network share configuration."""
    # Filter out None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}

    share = share_manager.update_share(share_id, **updates)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    return ShareResponse(
        id=share.id,
        name=share.name,
        protocol=share.protocol,
        host=share.host,
        share_path=share.share_path,
        mount_point=str(share.mount_point),
        username=share.username,
        enabled=share.enabled,
        auto_index=share.auto_index,
        is_mounted=share_manager.is_mounted(share.id),
    )


@app.delete("/v1/shares/{share_id}", status_code=204)
async def delete_share(share_id: str) -> None:
    """Delete network share configuration."""
    if not share_manager.remove_share(share_id):
        raise HTTPException(status_code=404, detail="Share not found")


@app.post("/v1/shares/{share_id}/mount")
async def mount_share(share_id: str) -> dict[str, Any]:
    """Mount a network share."""
    share = share_manager.get_share(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    success = await share_manager.mount(share_id)
    if not success:
        raise HTTPException(status_code=500, detail="Mount failed")

    return {"success": True, "message": f"Mounted {share.name}"}


@app.post("/v1/shares/{share_id}/unmount")
async def unmount_share(share_id: str) -> dict[str, Any]:
    """Unmount a network share."""
    share = share_manager.get_share(share_id)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")

    success = await share_manager.unmount(share_id)
    if not success:
        raise HTTPException(status_code=500, detail="Unmount failed")

    return {"success": True, "message": f"Unmounted {share.name}"}


@app.post("/v1/shares/mount-all")
async def mount_all_shares() -> dict[str, Any]:
    """Mount all enabled network shares."""
    results = await share_manager.mount_all()
    success_count = sum(1 for success in results.values() if success)
    return {
        "success": True,
        "mounted": success_count,
        "total": len(results),
        "details": results,
    }


@app.post("/v1/shares/unmount-all")
async def unmount_all_shares() -> dict[str, Any]:
    """Unmount all network shares."""
    results = await share_manager.unmount_all()
    success_count = sum(1 for success in results.values() if success)
    return {
        "success": True,
        "unmounted": success_count,
        "total": len(results),
        "details": results,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3005)
