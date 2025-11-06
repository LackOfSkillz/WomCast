"""Embedding helpers backed by Ollama's local embedding API."""

from __future__ import annotations

import logging
import os
from typing import Sequence

import httpx

logger = logging.getLogger(__name__)


class OllamaEmbeddingFunction:
    """Callable embedding function compatible with ChromaDB."""

    def __init__(
        self,
        model: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._model = model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._timeout = timeout
        # Chroma inspects embedding functions for a human-readable name.
        self._name = f"ollama:{self._model}"

    def name(self) -> str:
        """Return a human-readable identifier for this embedding function."""

        return self._name

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        texts = list(input)
        if not texts:
            return []

        embeddings: list[list[float]] = []
        url = f"{self._base_url.rstrip('/')}/api/embeddings"

        with httpx.Client(timeout=self._timeout) as client:
            for text in texts:
                payload = {
                    "model": self._model,
                    "input": text or "",
                }

                try:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                except httpx.HTTPError as exc:  # pragma: no cover - network issues
                    logger.error("Ollama embedding request failed: %s", exc)
                    raise RuntimeError("Failed to retrieve embeddings from Ollama") from exc

                data = response.json()
                vector = data.get("embedding")
                if vector is None:
                    # Some Ollama builds wrap the vector in "data" list
                    if isinstance(data.get("data"), list) and data["data"]:
                        vector = data["data"][0].get("embedding")

                if not isinstance(vector, list):
                    raise RuntimeError("Ollama embedding response missing vector data")

                embeddings.append(vector)

        return embeddings
