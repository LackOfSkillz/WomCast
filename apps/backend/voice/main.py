"""
Voice Service - Handles speech recognition and voice commands via Whisper.
"""

from fastapi import FastAPI

from common.health import create_health_router

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast Voice Service",
    description="Speech recognition and voice command processing",
    version=__version__,
)

create_health_router(app, "voice-service", __version__)
