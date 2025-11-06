"""Tests for model management endpoints in the voice service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from voice import main as voice_main
from voice.model_manager import (
	DiskInfo,
	DownloadJobInfo,
	JobState,
	ModelGroupStatus,
	ModelStatusEnvelope,
	ModelType,
	ModelVariant,
	VariantStatus,
)


class DummyManager:
	"""Simple stub used to capture calls from the API layer."""

	def __init__(self) -> None:
		voice_group = ModelGroupStatus(
			kind=ModelType.VOICE,
			active_model="small",
			disk=DiskInfo(path="/voice", total_bytes=1_000_000_000, free_bytes=500_000_000),
			models=[
				ModelVariant(
					name="small",
					display_name="Whisper Small",
					estimated_size_bytes=250_000_000,
					installed_size_bytes=249_000_000,
					installed=True,
					active=True,
					status=VariantStatus.READY,
					download_job_id=None,
					error=None,
				)
			],
		)

		llm_group = ModelGroupStatus(
			kind=ModelType.LLM,
			active_model="llama3.2:1b",
			disk=DiskInfo(path="/ollama", total_bytes=4_000_000_000, free_bytes=2_500_000_000),
			models=[
				ModelVariant(
					name="llama3.2:1b",
					display_name="Llama 3.2 1B",
					estimated_size_bytes=1_400_000_000,
					installed_size_bytes=1_350_000_000,
					installed=True,
					active=True,
					status=VariantStatus.READY,
					download_job_id=None,
					error=None,
				)
			],
		)

		self.status = ModelStatusEnvelope(voice=voice_group, llm=llm_group, jobs=[], active_job=None)
		self.started: list[tuple[ModelType, str]] = []
		self.cancelled: list[str] = []

	async def get_status(self) -> ModelStatusEnvelope:
		return self.status

	async def start_download(self, kind: ModelType, model: str) -> DownloadJobInfo:
		self.started.append((kind, model))
		job = DownloadJobInfo(
			id="job-123",
			model=model,
			model_type=kind,
			display_name=model,
			status=JobState.PENDING,
			progress=0.0,
			downloaded_bytes=0,
			total_bytes=100,
			error=None,
			started_at=datetime.now(timezone.utc),
			completed_at=None,
		)
		self.status.jobs.append(job)
		self.status.active_job = job
		return job

	async def cancel_download(self, job_id: str) -> DownloadJobInfo:
		self.cancelled.append(job_id)
		return DownloadJobInfo(
			id=job_id,
			model="demo",
			model_type=ModelType.VOICE,
			display_name="demo",
			status=JobState.CANCELLED,
			progress=None,
			downloaded_bytes=0,
			total_bytes=None,
			error=None,
			started_at=datetime.now(timezone.utc),
			completed_at=datetime.now(timezone.utc),
		)

	async def aclose(self) -> None:  # pragma: no cover - invoked by lifespan cleanup
		return


@pytest.fixture(name="client")
def client_fixture(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, DummyManager]:
	"""Provide a TestClient with the model manager swapped for a stub."""

	manager = DummyManager()

	def fake_manager(*args: Any, **kwargs: Any) -> DummyManager:  # noqa: ANN401 - generic factory
		return manager

	monkeypatch.setattr(voice_main, "ModelDownloadManager", fake_manager)

	with TestClient(voice_main.app) as test_client:
		yield test_client, manager


def test_get_model_status_returns_payload(client: tuple[TestClient, DummyManager]) -> None:
	test_client, manager = client

	response = test_client.get("/v1/voice/models/status")

	assert response.status_code == 200
	payload = response.json()
	assert payload["voice"]["active_model"] == manager.status.voice.active_model
	assert payload["llm"]["models"][0]["name"] == manager.status.llm.models[0].name


def test_start_model_download_invokes_manager(client: tuple[TestClient, DummyManager]) -> None:
	test_client, manager = client

	response = test_client.post(
		"/v1/voice/models/download",
		json={"kind": "voice", "model": "medium"},
	)

	assert response.status_code == 200
	assert manager.started == [(ModelType.VOICE, "medium")]
	assert response.json()["status"] == JobState.PENDING.value


def test_cancel_model_download_invokes_manager(client: tuple[TestClient, DummyManager]) -> None:
	test_client, manager = client

	response = test_client.post(
		"/v1/voice/models/cancel",
		json={"job_id": "job-xyz"},
	)

	assert response.status_code == 200
	assert manager.cancelled == ["job-xyz"]
	assert response.json()["status"] == JobState.CANCELLED.value
