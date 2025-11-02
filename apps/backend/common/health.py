"""Common health check endpoint for all services."""

from fastapi import FastAPI


def create_health_router(app: FastAPI, service_name: str, version: str = "0.1.0") -> None:
    """Add health check and version endpoints to a FastAPI app.

    Args:
        app: FastAPI application instance
        service_name: Name of the service (e.g., "indexer", "media")
        version: Service version string
    """

    @app.get("/healthz")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": service_name}

    @app.get("/version")
    async def version_info() -> dict[str, str]:
        """Version information endpoint."""
        return {"service": service_name, "version": version}
