"""
API Gateway Service - Main entry point for all backend requests.
Routes requests to appropriate microservices.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.health import create_health_router
from connectors.internet_archive import main as ia_connector
from connectors.jamendo import main as jamendo_connector
from connectors.nasa import main as nasa_connector
from connectors.pbs import main as pbs_connector
from livetv import main as livetv

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    await ia_connector.startup()
    await pbs_connector.startup()
    await nasa_connector.startup()
    await jamendo_connector.startup()

    yield

    # Shutdown
    await ia_connector.shutdown()
    await pbs_connector.shutdown()
    await nasa_connector.shutdown()
    await jamendo_connector.shutdown()


app = FastAPI(
    title="WomCast API Gateway",
    description="Central API gateway for WomCast backend services",
    version=__version__,
    lifespan=lifespan,
)

create_health_router(app, "api-gateway", __version__)

# Include connector routers
app.include_router(ia_connector.router)
app.include_router(pbs_connector.router)
app.include_router(nasa_connector.router)
app.include_router(jamendo_connector.router)

# Include live TV router
app.include_router(livetv.app.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "womcast-api-gateway",
        "version": __version__,
        "status": "operational",
    }
