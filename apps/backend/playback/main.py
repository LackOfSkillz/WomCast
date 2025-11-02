"""
Playback Service - Manages media playback via Kodi bridge or mpv.
"""

from fastapi import FastAPI

from common.health import create_health_router

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast Playback Service",
    description="Media playback control via Kodi/mpv",
    version=__version__,
)

create_health_router(app, "playback-service", __version__)
