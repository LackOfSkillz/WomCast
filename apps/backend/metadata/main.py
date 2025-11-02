"""
Metadata Service - Handles media library indexing and metadata management.
"""

from fastapi import FastAPI

from common.health import create_health_router

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast Metadata Service",
    description="Media library indexing and metadata management",
    version=__version__,
)

create_health_router(app, "metadata-service", __version__)
