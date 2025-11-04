"""Search Service - Semantic search via ChromaDB and LLM-powered queries."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ai.chroma import ChromaManager, SemanticSearchHit
from common.health import create_health_router

__version__ = "0.2.0"

logger = logging.getLogger(__name__)

chroma_manager: ChromaManager | None = None


class SemanticSearchResult(BaseModel):
    """Response payload for a single semantic search hit."""

    media_id: int | None = Field(default=None)
    title: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    score: float | None = Field(default=None)
    document: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemanticSearchResponse(BaseModel):
    """Aggregated response returned by the semantic search endpoint."""

    count: int
    latency_ms: float
    results: list[SemanticSearchResult]


class RebuildResponse(BaseModel):
    """Payload returned after rebuilding the semantic media index."""

    indexed_count: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Chroma manager and ensure the media index is ready."""

    global chroma_manager

    chroma_manager = ChromaManager()
    try:
        await chroma_manager.ensure_media_index()
    except Exception as exc:  # pragma: no cover - logging safety
        logger.warning("Semantic media index could not be prepared: %s", exc)
    yield


app = FastAPI(
    title="WomCast Search Service",
    description="Semantic search and LLM-powered media queries",
    version=__version__,
    lifespan=lifespan,
)

create_health_router(app, "search-service", __version__)


def _require_chroma() -> ChromaManager:
    if chroma_manager is None:
        raise HTTPException(status_code=503, detail="Semantic search not initialized")
    return chroma_manager


def _serialize_hit(hit: SemanticSearchHit) -> SemanticSearchResult:
    return SemanticSearchResult(
        media_id=hit.media_id,
        title=hit.title,
        media_type=hit.media_type,
        score=hit.score,
        document=hit.document,
        metadata=hit.metadata,
    )


@app.get("/v1/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
) -> SemanticSearchResponse:
    """Return semantically ranked media results for the supplied query."""

    manager = _require_chroma()

    started = time.perf_counter()
    try:
        hits = await manager.search_media(q, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    latency_ms = (time.perf_counter() - started) * 1000

    return SemanticSearchResponse(
        count=len(hits),
        latency_ms=latency_ms,
        results=[_serialize_hit(hit) for hit in hits],
    )


@app.post("/v1/search/semantic/rebuild", response_model=RebuildResponse)
async def rebuild_semantic_index() -> RebuildResponse:
    """Rebuild the semantic media index from the SQLite catalog."""

    manager = _require_chroma()
    try:
        count = await manager.rebuild_media_index()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RebuildResponse(indexed_count=count)
