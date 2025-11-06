"""API Gateway Service - Main entry point for all backend requests.

Routes requests to appropriate microservices and exposes consolidated endpoints.
"""

import os
from contextlib import asynccontextmanager
from typing import Iterable

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from common.health import create_health_router
from connectors.internet_archive import main as ia_connector
from connectors.jamendo import main as jamendo_connector
from connectors.nasa import main as nasa_connector
from connectors.pbs import main as pbs_connector
from livetv import main as livetv
from playback.cec_routes import router as cec_router

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

_default_origins = (
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
)
allowed_origins = (
    os.getenv("GATEWAY_CORS_ORIGINS")
    or os.getenv("WOMCAST_CORS_ORIGINS")
    or _default_origins
)
cors_origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

create_health_router(app, "api-gateway", __version__)

# Service endpoints used for proxying
PLAYBACK_SERVICE_URL = os.getenv("PLAYBACK_SERVICE_URL", "http://localhost:3002")

# Include connector routers
app.include_router(ia_connector.router)
app.include_router(pbs_connector.router)
app.include_router(nasa_connector.router)
app.include_router(jamendo_connector.router)

# Include live TV router
app.include_router(livetv.app.router)

# Include playback CEC router
app.include_router(cec_router)


def _filtered_response_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    """Filter hop-by-hop headers that should not be forwarded."""

    excluded = {"content-length", "transfer-encoding", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade"}
    return {key: value for key, value in headers if key.lower() not in excluded}


@app.api_route("/v1/playback/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_playback(path: str, request: Request) -> Response:
    """Proxy playback requests to the playback service.

    This keeps existing clients working while the frontend transitions to direct service calls.
    """

    target_url = f"{PLAYBACK_SERVICE_URL}/v1/{path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            proxied = await client.request(
                request.method,
                target_url,
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                content=await request.body(),
                params=request.query_params,
            )
    except httpx.RequestError as exc:  # pragma: no cover - network failure handling
        raise HTTPException(status_code=502, detail=f"Playback service unreachable: {exc}") from exc

    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers=_filtered_response_headers(proxied.headers.multi_items()),
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with service information."""

    return {
        "service": "womcast-api-gateway",
        "version": __version__,
        "status": "operational",
    }
