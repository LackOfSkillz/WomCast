"""
mDNS service advertisement for WomCast casting.

Advertises the casting service on the local network using Zeroconf/Bonjour.
Allows phones and tablets to discover WomCast without manual IP entry.
"""

import logging
import socket

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


class MDNSAdvertiser:
    """mDNS service advertiser for casting service."""

    def __init__(
        self,
        service_name: str = "WomCast",
        service_type: str = "_womcast-cast._tcp.local.",
        port: int = 3005,
        properties: dict[str, str] | None = None,
    ):
        """Initialize mDNS advertiser.

        Args:
            service_name: Human-readable service name
            service_type: Service type (must end with .local.)
            port: Service port number
            properties: Optional service properties (version, features, etc.)
        """
        self.service_name = service_name
        self.service_type = service_type
        self.port = port
        self.properties = properties or {}

        self.zeroconf: Zeroconf | None = None
        self.service_info: ServiceInfo | None = None

    def start(self) -> None:
        """Start mDNS advertisement."""
        try:
            # Get local IP addresses
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            # Create service info
            self.service_info = ServiceInfo(
                self.service_type,
                f"{self.service_name}.{self.service_type}",
                port=self.port,
                addresses=[socket.inet_aton(local_ip)],
                properties={
                    "version": "0.3.0",
                    "service": "womcast-cast",
                    **self.properties,
                },
                server=f"{hostname}.local.",
            )

            # Register service
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)

            logger.info(
                f"mDNS service advertised: {self.service_name} at {local_ip}:{self.port}"
            )

        except Exception as e:
            logger.error(f"Failed to start mDNS advertisement: {e}")

    def stop(self) -> None:
        """Stop mDNS advertisement."""
        if self.zeroconf and self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
                logger.info(f"mDNS service unregistered: {self.service_name}")
            except Exception as e:
                logger.error(f"Failed to stop mDNS advertisement: {e}")
            finally:
                self.zeroconf = None
                self.service_info = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
