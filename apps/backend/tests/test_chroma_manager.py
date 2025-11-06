import sqlite3
from pathlib import Path

import pytest

from ai.chroma.manager import ChromaManager


class _DeterministicEmbedding:
    def __call__(self, input):
        return [[self._encode(text)] for text in input]

    def name(self) -> str:
        return "deterministic"

    def is_legacy(self) -> bool:
        # Match Chroma's legacy embedding contract for custom callables
        return True

    def embed_documents(self, input):
        return self.__call__(input)

    def embed_query(self, input):
        if isinstance(input, str):
            return [[self._encode(input)]]
        if isinstance(input, list):
            return [[self._encode(input[0] if input else "")]]
        return [[self._encode(str(input))]]

    @staticmethod
    def _encode(text: str) -> float:
        return float(len(text or ""))


def _prepare_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE media_files (
                id INTEGER PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                media_type TEXT NOT NULL,
                duration_seconds INTEGER,
                play_count INTEGER,
                resume_position_seconds INTEGER,
                created_at TEXT,
                modified_at TEXT,
                indexed_at TEXT
            );

            CREATE TABLE videos (
                media_file_id INTEGER PRIMARY KEY,
                title TEXT,
                genre TEXT,
                plot TEXT,
                director TEXT,
                cast TEXT
            );

            CREATE TABLE audio_tracks (
                media_file_id INTEGER PRIMARY KEY,
                title TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                year INTEGER
            );

            CREATE TABLE games (
                media_file_id INTEGER PRIMARY KEY,
                title TEXT,
                platform TEXT,
                genre TEXT
            );

            CREATE TABLE photos (
                media_file_id INTEGER PRIMARY KEY,
                title TEXT,
                description TEXT
            );
            """
        )

        connection.execute(
            """
            INSERT INTO media_files (
                id, file_name, file_path, media_type, duration_seconds,
                play_count, resume_position_seconds, created_at,
                modified_at, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "chill_jazz.mp3",
                "/media/music/chill_jazz.mp3",
                "audio",
                200,
                0,
                0,
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
                "2025-01-01T00:00:00Z",
            ),
        )

        connection.execute(
            """
            INSERT INTO audio_tracks (
                media_file_id, title, artist, album, genre, year
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "Chill Jazz",
                "Various Artists",
                "Jazz Lounge",
                "Jazz",
                2024,
            ),
        )

        connection.commit()
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_rebuild_and_search(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    persist_path = tmp_path / "chroma"
    _prepare_database(db_path)

    manager = ChromaManager(
        persist_path=persist_path,
        db_path=db_path,
        embedding_function=_DeterministicEmbedding(),
    )

    rebuilt = await manager.rebuild_media_index()
    assert rebuilt == 1

    results = await manager.search_media("smooth jazz soundtrack", limit=5)
    assert results, "Expected at least one semantic result"
    assert results[0].media_id == 1
    assert results[0].metadata["media_type"] == "audio"
    assert "Chill Jazz" in (results[0].title or "")
