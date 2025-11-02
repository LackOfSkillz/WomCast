"""
API Gateway Service - Main entry point for all backend requests.
Routes requests to appropriate microservices.
"""

from fastapi import FastAPI

from common.health import create_health_router

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast API Gateway",
    description="Central API gateway for WomCast backend services",
    version=__version__,
)

create_health_router(app, "api-gateway", __version__)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "womcast-api-gateway",
        "version": __version__,
        "status": "operational",
    }
