import json
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from voice import main as voice_main


@contextmanager
def override_history_dir(tmp_path: Path):
    original_dir = voice_main.VOICE_HISTORY_DIR
    original_file = voice_main.VOICE_HISTORY_FILE
    try:
        voice_main.VOICE_HISTORY_DIR = tmp_path
        voice_main.VOICE_HISTORY_FILE = tmp_path / "history.jsonl"
        yield
    finally:
        voice_main.VOICE_HISTORY_DIR = original_dir
        voice_main.VOICE_HISTORY_FILE = original_file


def test_voice_history_endpoints(tmp_path):
    with override_history_dir(tmp_path):
        with TestClient(voice_main.app) as client:
            response = client.get("/v1/voice/history")
            payload = response.json()
            assert response.status_code == 200
            assert payload["entries"] == []
            assert payload["total_entries"] == 0

            voice_main.VOICE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            voice_main.VOICE_HISTORY_FILE.write_text(
                json.dumps({"text": "hello", "timestamp": "2025-11-04T00:00:00Z"}) + "\n",
                encoding="utf-8",
            )

            response = client.get("/v1/voice/history")
            payload = response.json()
            assert response.status_code == 200
            assert payload["total_entries"] == 1
            assert payload["entries"][0]["text"] == "hello"

            response = client.delete("/v1/voice/history")
            payload = response.json()
            assert response.status_code == 200
            assert payload["deleted_entries"] == 1

            assert not voice_main.VOICE_HISTORY_FILE.exists()
