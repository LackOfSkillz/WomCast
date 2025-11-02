"""
Search Service - Semantic search via ChromaDB and LLM-powered queries.
"""

from fastapi import FastAPI

from common.health import create_health_router

__version__ = "0.1.0"

app = FastAPI(
    title="WomCast Search Service",
    description="Semantic search and LLM-powered media queries",
    version=__version__,
)

create_health_router(app, "search-service", __version__)
