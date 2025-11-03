"""
STUN/TURN ICE server configuration for WebRTC.
Provides default public STUN servers and optional TURN server configuration.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IceServer(BaseModel):
    """ICE server configuration (STUN or TURN)."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=lambda x: x)

    urls: list[str] | str = Field(..., description="STUN/TURN server URL(s)")
    username: str | None = Field(None, description="Username for TURN authentication")
    credential: str | None = Field(None, description="Credential for TURN authentication")


class IceConfiguration(BaseModel):
    """WebRTC ICE configuration."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        ),
    )

    ice_servers: list[IceServer] = Field(
        default_factory=lambda: [
            IceServer(urls="stun:stun.l.google.com:19302"),
            IceServer(urls="stun:stun1.l.google.com:19302"),
        ],
        description="List of ICE servers (STUN/TURN)",
        alias="iceServers",
    )
    ice_transport_policy: str = Field(
        default="all",
        description="ICE transport policy: 'all' or 'relay'",
        alias="iceTransportPolicy",
    )
    bundle_policy: str = Field(
        default="balanced",
        description="Bundle policy: 'balanced', 'max-compat', or 'max-bundle'",
        alias="bundlePolicy",
    )


# Default configuration - LAN-first with public STUN servers
DEFAULT_ICE_CONFIG = IceConfiguration()


def get_ice_configuration(
    custom_stun_urls: list[str] | None = None,
    turn_urls: list[str] | None = None,
    turn_username: str | None = None,
    turn_credential: str | None = None,
) -> dict[str, Any]:
    """
    Get ICE configuration for WebRTC peer connection.

    Args:
        custom_stun_urls: Optional custom STUN server URLs
        turn_urls: Optional TURN server URLs
        turn_username: Username for TURN authentication
        turn_credential: Credential for TURN authentication

    Returns:
        ICE configuration dict suitable for RTCPeerConnection
    """
    ice_servers: list[IceServer] = []

    # Add STUN servers
    if custom_stun_urls:
        ice_servers.extend([IceServer(urls=url) for url in custom_stun_urls])
    else:
        # Use default public STUN servers
        ice_servers.extend(DEFAULT_ICE_CONFIG.ice_servers)

    # Add TURN servers if configured
    if turn_urls:
        for url in turn_urls:
            ice_servers.append(
                IceServer(
                    urls=url,
                    username=turn_username,
                    credential=turn_credential,
                )
            )

    config = IceConfiguration(ice_servers=ice_servers)
    return config.model_dump(by_alias=True)
