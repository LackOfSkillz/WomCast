"""FastAPI router exposing HDMI-CEC helper endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .cec_helper import get_cec_helper

router = APIRouter(prefix="/v1/cec", tags=["cec"])


class CecDeviceResponse(BaseModel):
    """CEC device information response."""

    model_config = ConfigDict(populate_by_name=True)

    address: int = Field(..., description="CEC logical address (0-15)")
    name: str = Field(..., description="Device name")
    vendor: str = Field(..., description="Vendor name")
    device_type: str = Field(..., alias="deviceType", description="Device type")
    active_source: bool = Field(..., alias="activeSource", description="Is active source")
    physical_address: str = Field(..., alias="physicalAddress", description="HDMI physical address")


class CecSwitchRequest(BaseModel):
    """Request to switch CEC input."""

    model_config = ConfigDict(populate_by_name=True)

    address: int | None = Field(None, description="CEC device address (0-15)")
    name: str | None = Field(None, description="Device name (substring match)")


@router.get("/available")
async def check_cec_available():
    """Check if CEC is available on this system."""

    cec = get_cec_helper()
    available = await cec.is_available()

    return {"available": available, "client_path": cec.cec_client_path}


@router.get("/devices", response_model=list[CecDeviceResponse])
async def list_cec_devices():
    """Scan and list all CEC devices on the HDMI bus."""

    cec = get_cec_helper()
    devices = await cec.scan_devices()

    return [
        CecDeviceResponse(
            address=dev.address,
            name=dev.name,
            vendor=dev.vendor,
            deviceType=dev.device_type.value,
            activeSource=dev.active_source,
            physicalAddress=dev.physical_address,
        )
        for dev in devices
    ]


@router.get("/tv", response_model=CecDeviceResponse | None)
async def get_tv_device():
    """Get the TV device (CEC address 0)."""

    cec = get_cec_helper()
    tv = await cec.get_tv()

    if not tv:
        return None

    return CecDeviceResponse(
        address=tv.address,
        name=tv.name,
        vendor=tv.vendor,
        deviceType=tv.device_type.value,
        activeSource=tv.active_source,
        physicalAddress=tv.physical_address,
    )


@router.get("/active", response_model=CecDeviceResponse | None)
async def get_active_source():
    """Get the currently active CEC source device."""

    cec = get_cec_helper()
    active = await cec.get_active_source()

    if not active:
        return None

    return CecDeviceResponse(
        address=active.address,
        name=active.name,
        vendor=active.vendor,
        deviceType=active.device_type.value,
        activeSource=active.active_source,
        physicalAddress=active.physical_address,
    )


@router.post("/switch")
async def switch_cec_input(request: CecSwitchRequest):
    """Switch TV input to a specific CEC device."""

    cec = get_cec_helper()

    if request.address is not None:
        success = await cec.switch_to_device(request.address)
    elif request.name:
        success = await cec.switch_to_device_by_name(request.name)
    else:
        raise HTTPException(status_code=400, detail="Must provide either 'address' or 'name'")

    if not success:
        raise HTTPException(status_code=500, detail="CEC switch command failed")

    return {"success": True, "message": "Switched to device"}


@router.post("/activate")
async def activate_womcast():
    """Make WomCast the active source (switch TV input to us)."""

    cec = get_cec_helper()
    success = await cec.make_active_source()

    if not success:
        raise HTTPException(status_code=500, detail="CEC activate command failed")

    return {"success": True, "message": "Made WomCast active source"}


@router.get("/status")
async def get_cec_status():
    """Get current CEC status and device list."""

    cec = get_cec_helper()
    return cec.to_dict()
