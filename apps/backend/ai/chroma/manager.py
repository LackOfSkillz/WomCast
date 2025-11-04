"""Utilities for managing ChromaDB collections used by WomCast."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import chromadb
from chromadb.api.models.Collection import Collection

from common.database import get_db_path
from .embedding import OllamaEmbeddingFunction

logger = logging.getLogger(__name__)

MEDIA_COLLECTION_NAME = "media_index"
VOICE_COLLECTION_NAME = "voice_queries"
DEFAULT_LIMIT = 10


@dataclass
class MediaDocument:
    """Structured representation for a media item destined for Chroma."""

    doc_id: str
    document: str
    metadata: dict[str, Any]


@dataclass
class SemanticSearchHit:
    """Result returned from a semantic media query."""

    media_id: int | None
    title: str | None
    media_type: str | None
    score: float | None
    document: str | None
    metadata: dict[str, Any]


class ChromaManager:
    """Wrapper around ChromaDB persistent collections."""

    def __init__(
        self,
        *,
        persist_path: str | Path | None = None,
        db_path: Path | None = None,
        embedding_function: Any | None = None,
    ) -> None:
        base_dir = Path(persist_path or os.getenv("CHROMA_PERSIST_PATH", ""))
        if not base_dir:
            base_dir = Path(__file__).resolve().parents[4] / ".data" / "chroma"
        self._persist_path = base_dir.resolve()
        self._persist_path.mkdir(parents=True, exist_ok=True)

        self._client: chromadb.ClientAPI = chromadb.PersistentClient(
            path=str(self._persist_path)
        )

        self._embedding_function = embedding_function or OllamaEmbeddingFunction()
        self._media_collection = self._get_or_create_collection(MEDIA_COLLECTION_NAME)
        self._voice_collection = self._get_or_create_collection(VOICE_COLLECTION_NAME)

        self._db_path = (db_path or get_db_path()).resolve()
        self._rebuild_lock = asyncio.Lock()

    def _get_or_create_collection(self, name: str) -> Collection:
        return self._client.get_or_create_collection(
            name=name,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    async def ensure_media_index(self) -> int:
        """Ensure the media collection has embeddings, rebuilding if empty."""

        count = await asyncio.to_thread(self._media_collection.count)
        if count == 0:
            logger.info("Media semantic index empty; rebuilding from database")
            await self.rebuild_media_index()
            count = await asyncio.to_thread(self._media_collection.count)
        return count

    async def rebuild_media_index(self) -> int:
        """Recreate the media collection from the SQLite catalog."""

        async with self._rebuild_lock:
            documents = await asyncio.to_thread(self._load_media_documents)
            await asyncio.to_thread(self._replace_media_documents, documents)
            logger.info("Media semantic index rebuilt with %d documents", len(documents))
            return len(documents)

    async def search_media(
        self, query: str, *, limit: int = DEFAULT_LIMIT
    ) -> list[SemanticSearchHit]:
        """Run a semantic search against the media collection."""

        query = query.strip()
        if not query:
            return []

        limit = max(1, min(limit, 50))

        try:
            results = await asyncio.to_thread(
                self._media_collection.query,
                query_texts=[query],
                n_results=limit,
                include=["metadatas", "documents", "distances"],
            )
        except Exception as exc:  # pragma: no cover - Chroma internal errors
            logger.error("Chroma media query failed: %s", exc)
            raise RuntimeError("Semantic search unavailable") from exc

        hits: list[SemanticSearchHit] = []
        ids = results.get("ids") or [[]]
        metadatas = results.get("metadatas") or [[]]
        documents = results.get("documents") or [[]]
        distances = results.get("distances") or [[]]

        if not ids or not metadatas:
            return hits

        for index, metadata in enumerate(metadatas[0]):
            if metadata is None:
                continue

            document = documents[0][index] if documents and documents[0] else None
            distance = None
            if distances and distances[0]:
                try:
                    distance = float(distances[0][index])
                except (TypeError, ValueError, IndexError):  # pragma: no cover - corrupted data
                    distance = None

            score = None
            if distance is not None:
                score = max(0.0, min(1.0, 1.0 - distance))

            metadata_dict = dict(metadata)
            hits.append(
                SemanticSearchHit(
                    media_id=_as_int(metadata_dict.get("media_id")),
                    title=_as_str(
                        metadata_dict.get("title") or metadata_dict.get("file_name")
                    ),
                    media_type=_as_str(metadata_dict.get("media_type")),
                    score=score,
                    document=document,
                    metadata=metadata_dict,
                )
            )

        return hits

    async def store_voice_query(self, text: str, *, metadata: dict[str, Any] | None = None) -> None:
        """Persist a voice query transcript into the voice collection."""

        payload_meta = dict(metadata or {})
        payload_meta.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

        doc_id = f"voice-{uuid.uuid4().hex}"

        def _store() -> None:
            try:
                self._voice_collection.add(
                    ids=[doc_id],
                    documents=[text or ""],
                    metadatas=[payload_meta],
                )
            except Exception as exc:  # pragma: no cover - Chroma internal errors
                logger.warning("Failed to persist voice query: %s", exc)

        await asyncio.to_thread(_store)

    # ------------------------------------------------------------------
    # Internal helpers

    def _replace_media_documents(self, documents: Sequence[MediaDocument]) -> None:
        try:
            self._media_collection.delete(where={})
            if documents:
                self._media_collection.add(
                    ids=[doc.doc_id for doc in documents],
                    documents=[doc.document for doc in documents],
                    metadatas=[doc.metadata for doc in documents],
                )
        except Exception as exc:  # pragma: no cover - Chroma internal errors
            logger.error("Failed to update media semantic index: %s", exc)
            raise

    def _load_media_documents(self) -> list[MediaDocument]:
        if not self._db_path.exists():
            logger.debug("Media database missing at %s; skipping semantic index rebuild", self._db_path)
            return []

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row

        sql = """
            SELECT
                mf.id AS media_id,
                mf.file_name,
                mf.file_path,
                mf.media_type,
                mf.duration_seconds,
                mf.play_count,
                mf.resume_position_seconds,
                mf.created_at,
                mf.modified_at,
                mf.indexed_at,
                v.title AS video_title,
                v.genre AS video_genre,
                v.plot AS video_plot,
                v.director AS video_director,
                v.cast AS video_cast,
                a.title AS audio_title,
                a.artist AS audio_artist,
                a.album AS audio_album,
                a.genre AS audio_genre,
                a.year AS audio_year,
                g.title AS game_title,
                g.platform AS game_platform,
                g.genre AS game_genre,
                p.title AS photo_title,
                p.description AS photo_description
            FROM media_files mf
            LEFT JOIN videos v ON v.media_file_id = mf.id
            LEFT JOIN audio_tracks a ON a.media_file_id = mf.id
            LEFT JOIN games g ON g.media_file_id = mf.id
            LEFT JOIN photos p ON p.media_file_id = mf.id
        """

        try:
            rows = connection.execute(sql).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning("Semantic index rebuild skipped: %s", exc)
            return []
        finally:
            connection.close()

        documents: list[MediaDocument] = []
        for row in rows:
            metadata = {
                "media_id": row["media_id"],
                "file_name": row["file_name"],
                "file_path": row["file_path"],
                "media_type": row["media_type"],
                "duration_seconds": row["duration_seconds"],
                "play_count": row["play_count"],
                "resume_position_seconds": row["resume_position_seconds"],
                "created_at": row["created_at"],
                "modified_at": row["modified_at"],
                "indexed_at": row["indexed_at"],
            }

            summary_lines = _build_summary_lines(row)
            metadata.update(_collect_optional_metadata(row))

            documents.append(
                MediaDocument(
                    doc_id=f"media-{row['media_id']}",
                    document="\n".join(summary_lines),
                    metadata={k: v for k, v in metadata.items() if v is not None},
                )
            )

        return documents


def _build_summary_lines(row: sqlite3.Row) -> list[str]:
    title = (
        row["video_title"]
        or row["audio_title"]
        or row["game_title"]
        or row["photo_title"]
        or row["file_name"]
    )

    lines = [f"Title: {title}", f"Type: {row['media_type']}"]

    if row["audio_artist"]:
        lines.append(f"Artist: {row['audio_artist']}")
    if row["audio_album"]:
        lines.append(f"Album: {row['audio_album']}")
    if row["audio_genre"]:
        lines.append(f"Genre: {row['audio_genre']}")
    if row["audio_year"]:
        lines.append(f"Year: {row['audio_year']}")

    if row["video_genre"]:
        lines.append(f"Genre: {row['video_genre']}")
    if row["video_director"]:
        lines.append(f"Director: {row['video_director']}")
    if row["video_cast"]:
        lines.append(f"Cast: {row['video_cast']}")
    if row["video_plot"]:
        lines.append(f"Synopsis: {row['video_plot']}")

    if row["game_platform"]:
        lines.append(f"Platform: {row['game_platform']}")
    if row["game_genre"]:
        lines.append(f"Genre: {row['game_genre']}")

    if row["photo_description"]:
        lines.append(f"Description: {row['photo_description']}")

    lines.append(f"File: {row['file_name']}")
    lines.append(f"Path: {row['file_path']}")

    return [line for line in lines if line.strip()]


def _collect_optional_metadata(row: sqlite3.Row) -> dict[str, Any]:
    optional: dict[str, Any] = {}

    mappings = {
        "title": row["video_title"]
        or row["audio_title"]
        or row["game_title"]
        or row["photo_title"],
        "audio_artist": row["audio_artist"],
        "audio_album": row["audio_album"],
        "audio_genre": row["audio_genre"],
        "audio_year": row["audio_year"],
        "video_genre": row["video_genre"],
        "video_director": row["video_director"],
        "video_cast": row["video_cast"],
        "video_plot": row["video_plot"],
        "game_title": row["game_title"],
        "game_platform": row["game_platform"],
        "game_genre": row["game_genre"],
        "photo_title": row["photo_title"],
        "photo_description": row["photo_description"],
    }

    for key, value in mappings.items():
        if value not in (None, ""):
            optional[key] = value

    return optional


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
