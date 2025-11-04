import pytest
from fastapi.testclient import TestClient

from ai.chroma.manager import SemanticSearchHit
from search import main as search_main


class _StubChromaManager:
    async def ensure_media_index(self) -> int:
        return 1

    async def search_media(self, query: str, *, limit: int = 10) -> list[SemanticSearchHit]:
        return [
            SemanticSearchHit(
                media_id=7,
                title="Sample Track",
                media_type="audio",
                score=0.87,
                document="Sample Track by Example Artist",
                metadata={"media_id": 7, "media_type": "audio", "title": "Sample Track"},
            )
        ]

    async def rebuild_media_index(self) -> int:
        return 1


@pytest.fixture
def test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    stub = _StubChromaManager()
    monkeypatch.setattr(search_main, "ChromaManager", lambda *args, **kwargs: stub)
    with TestClient(search_main.app) as client:
        yield client
    search_main.chroma_manager = None


def test_semantic_search_endpoint_returns_results(test_client: TestClient) -> None:
    response = test_client.get("/v1/search/semantic", params={"q": "find sample"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["media_id"] == 7
    assert payload["results"][0]["media_type"] == "audio"


def test_semantic_rebuild_endpoint(test_client: TestClient) -> None:
    response = test_client.post("/v1/search/semantic/rebuild")
    assert response.status_code == 200
    payload = response.json()
    assert payload["indexed_count"] == 1
