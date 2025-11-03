"""
Tests for WebRTC ICE server configuration.
"""

from cast.ice_config import (
    DEFAULT_ICE_CONFIG,
    IceConfiguration,
    IceServer,
    get_ice_configuration,
)


def test_default_ice_config():
    """Test default ICE configuration has public STUN servers."""
    assert len(DEFAULT_ICE_CONFIG.ice_servers) >= 2
    assert any("stun" in server.urls for server in DEFAULT_ICE_CONFIG.ice_servers)
    assert DEFAULT_ICE_CONFIG.ice_transport_policy == "all"
    assert DEFAULT_ICE_CONFIG.bundle_policy == "balanced"


def test_ice_server_stun_only():
    """Test ICE server configuration for STUN only."""
    server = IceServer(urls="stun:stun.example.com:19302")
    assert server.urls == "stun:stun.example.com:19302"
    assert server.username is None
    assert server.credential is None


def test_ice_server_turn_with_auth():
    """Test ICE server configuration for TURN with authentication."""
    server = IceServer(
        urls="turn:turn.example.com:3478",
        username="testuser",
        credential="testpass",
    )
    assert server.urls == "turn:turn.example.com:3478"
    assert server.username == "testuser"
    assert server.credential == "testpass"


def test_ice_server_multiple_urls():
    """Test ICE server with multiple URLs."""
    urls = ["stun:stun1.example.com:19302", "stun:stun2.example.com:19302"]
    server = IceServer(urls=urls)
    assert server.urls == urls


def test_get_ice_configuration_default():
    """Test getting default ICE configuration."""
    config = get_ice_configuration()

    assert "iceServers" in config
    assert len(config["iceServers"]) >= 2

    # Check that default STUN servers are present
    stun_urls = [
        server["urls"]
        for server in config["iceServers"]
        if isinstance(server["urls"], str) and "stun" in server["urls"]
    ]
    assert len(stun_urls) >= 2


def test_get_ice_configuration_custom_stun():
    """Test getting ICE configuration with custom STUN servers."""
    custom_stun = [
        "stun:custom1.example.com:19302",
        "stun:custom2.example.com:19302",
    ]

    config = get_ice_configuration(custom_stun_urls=custom_stun)

    assert "iceServers" in config
    assert len(config["iceServers"]) == 2

    urls = [server["urls"] for server in config["iceServers"]]
    assert "stun:custom1.example.com:19302" in urls
    assert "stun:custom2.example.com:19302" in urls


def test_get_ice_configuration_with_turn():
    """Test getting ICE configuration with TURN server."""
    config = get_ice_configuration(
        turn_urls=["turn:turn.example.com:3478"],
        turn_username="testuser",
        turn_credential="testpass",
    )

    assert "iceServers" in config
    # Should have default STUN servers + 1 TURN server
    assert len(config["iceServers"]) >= 3

    # Find TURN server
    turn_servers = [
        server
        for server in config["iceServers"]
        if isinstance(server["urls"], str) and "turn" in server["urls"]
    ]
    assert len(turn_servers) == 1
    assert turn_servers[0]["username"] == "testuser"
    assert turn_servers[0]["credential"] == "testpass"


def test_get_ice_configuration_stun_and_turn():
    """Test getting ICE configuration with custom STUN and TURN."""
    config = get_ice_configuration(
        custom_stun_urls=["stun:custom.example.com:19302"],
        turn_urls=["turn:turn.example.com:3478", "turns:turn.example.com:5349"],
        turn_username="user",
        turn_credential="pass",
    )

    assert "iceServers" in config
    # 1 STUN + 2 TURN servers
    assert len(config["iceServers"]) == 3

    # Verify STUN server
    stun_servers = [
        s for s in config["iceServers"] if "stun" in str(s["urls"])
    ]
    assert len(stun_servers) == 1

    # Verify TURN servers
    turn_servers = [
        s for s in config["iceServers"] if "turn" in str(s["urls"])
    ]
    assert len(turn_servers) == 2
    assert all(s["username"] == "user" for s in turn_servers)
    assert all(s["credential"] == "pass" for s in turn_servers)


def test_ice_configuration_model():
    """Test IceConfiguration model."""
    config = IceConfiguration(
        ice_servers=[
            IceServer(urls="stun:stun.example.com:19302"),
            IceServer(
                urls="turn:turn.example.com:3478",
                username="user",
                credential="pass",
            ),
        ],
        ice_transport_policy="relay",
        bundle_policy="max-bundle",
    )

    assert len(config.ice_servers) == 2
    assert config.ice_transport_policy == "relay"
    assert config.bundle_policy == "max-bundle"

    # Test serialization with aliases (for WebRTC compatibility)
    config_dict = config.model_dump(by_alias=True)
    assert "iceServers" in config_dict
    assert config_dict["iceTransportPolicy"] == "relay"
    assert config_dict["bundlePolicy"] == "max-bundle"
