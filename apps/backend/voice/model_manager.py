"""Model download orchestration for Whisper and Ollama assets."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Iterable

import httpx
from pydantic import BaseModel

from common.settings import SettingsManager
from ai.intent.engine import IntentEngine, OllamaModelInfo

logger = logging.getLogger(__name__)


class ModelManagerError(RuntimeError):
	"""Base exception for model manager failures."""


class ModelNotFoundError(ModelManagerError):
	"""Raised when a requested model is unknown."""


class ModelAlreadyInstalledError(ModelManagerError):
	"""Raised when attempting to download an already installed model."""


class DownloadInProgressError(ModelManagerError):
	"""Raised when a conflicting download is already running."""


class InsufficientSpaceError(ModelManagerError):
	"""Raised when there is not enough free disk space for a download."""


class ExternalServiceError(ModelManagerError):
	"""Raised when an external dependency (e.g. Ollama) fails."""


class DownloadCancelled(ModelManagerError):
	"""Raised when a download is cancelled."""


class ModelType(str, Enum):
	"""Supported model categories."""

	VOICE = "voice"
	LLM = "llm"


class JobState(str, Enum):
	"""Lifecycle states for download jobs."""

	PENDING = "pending"
	RUNNING = "running"
	COMPLETED = "completed"
	FAILED = "failed"
	CANCELLED = "cancelled"


class VariantStatus(str, Enum):
	"""High-level availability flags for a model variant."""

	READY = "ready"
	MISSING = "missing"
	DOWNLOADING = "downloading"
	FAILED = "failed"
	CANCELLED = "cancelled"


@dataclass(slots=True)
class ModelDescriptor:
	"""Static metadata for a model option."""

	name: str
	display_name: str
	size_bytes: int | None
	model_type: ModelType


@dataclass(slots=True)
class ModelDownloadJob:
	"""Tracks an in-flight or completed download."""

	id: str
	model: str
	display_name: str
	model_type: ModelType
	status: JobState = JobState.PENDING
	progress: float | None = None
	downloaded_bytes: int = 0
	total_bytes: int | None = None
	error: str | None = None
	started_at: datetime | None = None
	completed_at: datetime | None = None
	cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

	def is_active(self) -> bool:
		return self.status in {JobState.PENDING, JobState.RUNNING}

	def snapshot(self) -> "DownloadJobInfo":
		return DownloadJobInfo(
			id=self.id,
			model=self.model,
			model_type=self.model_type,
			display_name=self.display_name,
			status=self.status,
			progress=self.progress,
			downloaded_bytes=self.downloaded_bytes,
			total_bytes=self.total_bytes,
			error=self.error,
			started_at=self.started_at,
			completed_at=self.completed_at,
		)

	def cancel(self) -> None:
		self.cancel_event.set()


class DiskInfo(BaseModel):
	"""Disk usage summary for a storage directory."""

	path: str
	total_bytes: int
	free_bytes: int


class ModelVariant(BaseModel):
	"""Status information for a specific model option."""

	name: str
	display_name: str
	estimated_size_bytes: int | None = None
	installed_size_bytes: int | None = None
	installed: bool
	active: bool
	status: VariantStatus
	download_job_id: str | None = None
	error: str | None = None


class ModelGroupStatus(BaseModel):
	"""Aggregated view of models for a category."""

	kind: ModelType
	active_model: str | None
	disk: DiskInfo
	models: list[ModelVariant]


class DownloadJobInfo(BaseModel):
	"""Serializable representation of a download job."""

	id: str
	model: str
	model_type: ModelType
	display_name: str
	status: JobState
	progress: float | None = None
	downloaded_bytes: int | None = None
	total_bytes: int | None = None
	error: str | None = None
	started_at: datetime | None = None
	completed_at: datetime | None = None


class ModelStatusEnvelope(BaseModel):
	"""Full status payload returned to the frontend."""

	voice: ModelGroupStatus
	llm: ModelGroupStatus
	jobs: list[DownloadJobInfo]
	active_job: DownloadJobInfo | None = None


def _default_voice_models_dir() -> Path:
	base = Path(
		os.getenv("VOICE_MODELS_DIR")
		or (Path(__file__).resolve().parent / "models")
	)
	return base.resolve()


def _default_ollama_models_dir() -> Path:
	ollama_home = Path(os.getenv("OLLAMA_HOME", Path.home() / ".ollama"))
	models_dir = Path(os.getenv("OLLAMA_MODELS_DIR", ollama_home / "models"))
	return models_dir.resolve()


VOICE_MODEL_CATALOG: tuple[ModelDescriptor, ...] = (
	ModelDescriptor("tiny", "Whisper Tiny", 40_943_616, ModelType.VOICE),
	ModelDescriptor("base", "Whisper Base", 77_070_336, ModelType.VOICE),
	ModelDescriptor("small", "Whisper Small", 255_852_544, ModelType.VOICE),
	ModelDescriptor("medium", "Whisper Medium", 806_354_944, ModelType.VOICE),
	ModelDescriptor("large", "Whisper Large", 1_625_702_400, ModelType.VOICE),
)


LLM_MODEL_CATALOG: tuple[ModelDescriptor, ...] = (
	ModelDescriptor("llama3.2:1b", "Llama 3.2 1B", 1_400_000_000, ModelType.LLM),
	ModelDescriptor("llama2", "Llama 2 7B", 3_900_000_000, ModelType.LLM),
	ModelDescriptor("llama2:13b", "Llama 2 13B", 6_900_000_000, ModelType.LLM),
	ModelDescriptor("mistral", "Mistral 7B", 4_000_000_000, ModelType.LLM),
	ModelDescriptor("mixtral", "Mixtral 8x7B", 26_000_000_000, ModelType.LLM),
	ModelDescriptor("codellama", "Code Llama 7B", 3_600_000_000, ModelType.LLM),
	ModelDescriptor("phi", "Phi 2.7B", 1_800_000_000, ModelType.LLM),
	ModelDescriptor("gemma", "Gemma 7B", 5_200_000_000, ModelType.LLM),
)


class ModelDownloadManager:
	"""Coordinates model inventory, downloads, and disk usage."""

	def __init__(
		self,
		*,
		settings_manager: SettingsManager,
		intent_engine_provider: Callable[[], Awaitable[IntentEngine]],
		voice_models_dir: Path | None = None,
		ollama_models_dir: Path | None = None,
		voice_catalog: Iterable[ModelDescriptor] = VOICE_MODEL_CATALOG,
		llm_catalog: Iterable[ModelDescriptor] = LLM_MODEL_CATALOG,
		ollama_base_url: str | None = None,
	) -> None:
		self._settings_manager = settings_manager
		self._intent_engine_provider = intent_engine_provider

		self._voice_models_dir = (voice_models_dir or _default_voice_models_dir()).resolve()
		self._voice_models_dir.mkdir(parents=True, exist_ok=True)

		self._ollama_models_dir = (ollama_models_dir or _default_ollama_models_dir()).resolve()
		self._ollama_models_dir.mkdir(parents=True, exist_ok=True)

		self._voice_catalog = tuple(voice_catalog)
		self._llm_catalog = tuple(llm_catalog)

		self._jobs: dict[str, ModelDownloadJob] = {}
		self._jobs_lock = asyncio.Lock()

		self._ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
		self._ollama_client: httpx.AsyncClient | None = None

	async def aclose(self) -> None:
		"""Cleanup resources and cancel outstanding jobs."""

		async with self._jobs_lock:
			for job in self._jobs.values():
				job.cancel()

		if self._ollama_client:
			await self._ollama_client.aclose()
			self._ollama_client = None

	async def get_status(self) -> ModelStatusEnvelope:
		"""Return aggregated status for both model categories."""

		voice_group = await self._build_voice_group()
		llm_group = await self._build_llm_group()

		async with self._jobs_lock:
			jobs = [job.snapshot() for job in self._jobs.values()]
			active_job = next((job.snapshot() for job in self._jobs.values() if job.is_active()), None)

		return ModelStatusEnvelope(
			voice=voice_group,
			llm=llm_group,
			jobs=jobs,
			active_job=active_job,
		)

	async def start_download(self, model_type: ModelType, model_name: str) -> DownloadJobInfo:
		"""Queue a new download for the requested model."""

		descriptor = self._lookup_descriptor(model_type, model_name)
		if descriptor is None:
			if model_type is ModelType.VOICE:
				raise ModelNotFoundError(f"Voice model '{model_name}' is not supported")
			descriptor = ModelDescriptor(model_name, model_name, None, ModelType.LLM)

		if model_type is ModelType.VOICE and self._is_voice_model_installed(model_name):
			raise ModelAlreadyInstalledError(f"Voice model '{model_name}' already installed")

		if model_type is ModelType.LLM and await self._is_llm_model_installed(model_name):
			raise ModelAlreadyInstalledError(f"LLM model '{model_name}' already installed")

		async with self._jobs_lock:
			existing = self._job_for(model_type, model_name)
			if existing and existing.is_active():
				raise DownloadInProgressError(f"Download already in progress for '{model_name}'")

		self._ensure_free_space(model_type, descriptor.size_bytes)

		job = ModelDownloadJob(
			id=uuid.uuid4().hex,
			model=model_name,
			display_name=descriptor.display_name,
			model_type=model_type,
			total_bytes=descriptor.size_bytes,
		)

		async with self._jobs_lock:
			self._jobs[job.id] = job

		asyncio.create_task(self._run_job(job))
		return job.snapshot()

	async def cancel_download(self, job_id: str) -> DownloadJobInfo:
		"""Signal cancellation for an active job."""

		async with self._jobs_lock:
			job = self._jobs.get(job_id)

		if job is None:
			raise ModelNotFoundError(f"Download job '{job_id}' not found")

		job.cancel()
		return job.snapshot()

	def _lookup_descriptor(self, model_type: ModelType, model_name: str) -> ModelDescriptor | None:
		catalog = self._voice_catalog if model_type is ModelType.VOICE else self._llm_catalog
		for descriptor in catalog:
			if descriptor.name == model_name:
				return descriptor
		return None

	def _job_for(self, model_type: ModelType, model_name: str) -> ModelDownloadJob | None:
		for job in self._jobs.values():
			if job.model_type is model_type and job.model == model_name:
				return job
		return None

	def _ensure_free_space(self, model_type: ModelType, estimated_size: int | None) -> None:
		if estimated_size is None or estimated_size <= 0:
			return

		disk = self._disk_info(
			self._voice_models_dir if model_type is ModelType.VOICE else self._ollama_models_dir
		)

		if disk.free_bytes < estimated_size:
			raise InsufficientSpaceError(
				f"Not enough space in {disk.path} (free {disk.free_bytes} bytes, requires {estimated_size} bytes)"
			)

	async def _run_job(self, job: ModelDownloadJob) -> None:
		job.started_at = datetime.now(timezone.utc)
		job.status = JobState.RUNNING

		try:
			if job.model_type is ModelType.VOICE:
				await self._download_voice_model(job)
			else:
				await self._download_llm_model(job)
		except DownloadCancelled:
			job.status = JobState.CANCELLED
			job.completed_at = datetime.now(timezone.utc)
			job.progress = None
			job.downloaded_bytes = 0
			job.total_bytes = job.total_bytes
			job.error = None
		except Exception as exc:  # pragma: no cover - unexpected runtime issues
			logger.error("Model download failed for %s: %s", job.model, exc)
			job.status = JobState.FAILED
			job.error = str(exc)
			job.completed_at = datetime.now(timezone.utc)
		else:
			job.status = JobState.COMPLETED
			job.progress = 1.0
			job.completed_at = datetime.now(timezone.utc)
		finally:
			# Leave job record for status queries; cleanup handled elsewhere if needed.
			return

	async def _download_voice_model(self, job: ModelDownloadJob) -> None:
		target_dir = self._voice_models_dir / job.model
		tmp_dir = target_dir.parent / f".{job.model}.tmp-{job.id}"

		if target_dir.exists():
			shutil.rmtree(target_dir, ignore_errors=True)
		if tmp_dir.exists():
			shutil.rmtree(tmp_dir, ignore_errors=True)
		tmp_dir.mkdir(parents=True, exist_ok=True)

		def _download() -> None:
			try:
				from faster_whisper.utils import download_model as download_whisper_model  # type: ignore import
			except ImportError as exc:  # pragma: no cover - dependency missing
				raise ExternalServiceError("faster-whisper not installed") from exc

			download_whisper_model(job.model, output_dir=str(tmp_dir))

		await asyncio.to_thread(_download)

		if job.cancel_event.is_set():
			shutil.rmtree(tmp_dir, ignore_errors=True)
			raise DownloadCancelled

		if target_dir.exists():
			shutil.rmtree(target_dir, ignore_errors=True)
		tmp_dir.rename(target_dir)

		size = self._compute_directory_size(target_dir)
		job.total_bytes = size
		job.downloaded_bytes = size

	async def _download_llm_model(self, job: ModelDownloadJob) -> None:
		client = await self._get_ollama_client()

		try:
			async with client.stream("POST", "/api/pull", json={"model": job.model}, timeout=None) as response:
				if response.status_code != 200:
					body = await response.aread()
					raise ExternalServiceError(
						f"Ollama pull failed with status {response.status_code}: {body.decode(errors='ignore')[:200]}"
					)

				async for line in response.aiter_lines():
					if not line:
						if job.cancel_event.is_set():
							raise DownloadCancelled
						continue

					try:
						payload = json.loads(line)
					except json.JSONDecodeError:
						continue

					if "total" in payload:
						try:
							job.total_bytes = int(payload["total"])
						except (TypeError, ValueError):
							job.total_bytes = job.total_bytes

					if "completed" in payload:
						try:
							job.downloaded_bytes = int(payload["completed"])
						except (TypeError, ValueError):
							pass
						else:
							if job.total_bytes and job.total_bytes > 0:
								job.progress = min(1.0, job.downloaded_bytes / job.total_bytes)

					if payload.get("status") == "success" or payload.get("done") is True:
						break

					if payload.get("error"):
						raise ExternalServiceError(payload["error"])

					if job.cancel_event.is_set():
						await self._cancel_ollama_pull(job.model)
						raise DownloadCancelled
		except httpx.HTTPError as exc:
			raise ExternalServiceError(f"Failed to contact Ollama: {exc}") from exc

	async def _cancel_ollama_pull(self, model: str) -> None:
		client = await self._get_ollama_client()
		try:
			await client.post("/api/cancel", json={"model": model}, timeout=5.0)
		except httpx.HTTPError:  # pragma: no cover - best effort
			logger.debug("Ollama cancel request failed for model %s", model)

	async def _get_ollama_client(self) -> httpx.AsyncClient:
		if self._ollama_client is None:
			self._ollama_client = httpx.AsyncClient(base_url=self._ollama_base_url, timeout=None)
		return self._ollama_client

	async def _build_voice_group(self) -> ModelGroupStatus:
		await self._settings_manager.refresh()
		active_model = str(self._settings_manager.get("voice_model", "small"))

		variants: list[ModelVariant] = []
		for descriptor in self._voice_catalog:
			installed = self._is_voice_model_installed(descriptor.name)
			job = self._job_for(ModelType.VOICE, descriptor.name)
			installed_size = self._voice_model_size(descriptor.name) if installed else None

			status = VariantStatus.READY if installed else VariantStatus.MISSING
			error: str | None = None

			if job is not None:
				if job.status is JobState.FAILED:
					status = VariantStatus.FAILED
					error = job.error
				elif job.status is JobState.CANCELLED:
					status = VariantStatus.CANCELLED
				elif job.is_active():
					status = VariantStatus.DOWNLOADING

			variants.append(
				ModelVariant(
					name=descriptor.name,
					display_name=descriptor.display_name,
					estimated_size_bytes=descriptor.size_bytes,
					installed_size_bytes=installed_size,
					installed=installed,
					active=descriptor.name == active_model,
					status=status,
					download_job_id=job.id if job else None,
					error=error,
				)
			)

		variants.sort(key=lambda variant: variant.display_name.lower())

		return ModelGroupStatus(
			kind=ModelType.VOICE,
			active_model=active_model,
			disk=self._disk_info(self._voice_models_dir),
			models=variants,
		)

	async def _build_llm_group(self) -> ModelGroupStatus:
		await self._settings_manager.refresh()
		active_model = self._settings_manager.get("llm_model")
		active_model_str = str(active_model) if active_model else None

		installed_map = await self._installed_llm_models()

		variants: list[ModelVariant] = []
		processed: set[str] = set()

		for descriptor in self._llm_catalog:
			info = installed_map.pop(descriptor.name, None)
			processed.add(descriptor.name)
			installed = info is not None
			installed_size = info.size if info and info.size else None
			job = self._job_for(ModelType.LLM, descriptor.name)

			status = VariantStatus.READY if installed else VariantStatus.MISSING
			error: str | None = None

			if job is not None:
				if job.status is JobState.FAILED:
					status = VariantStatus.FAILED
					error = job.error
				elif job.status is JobState.CANCELLED:
					status = VariantStatus.CANCELLED
				elif job.is_active():
					status = VariantStatus.DOWNLOADING

			variants.append(
				ModelVariant(
					name=descriptor.name,
					display_name=descriptor.display_name,
					estimated_size_bytes=descriptor.size_bytes,
					installed_size_bytes=installed_size,
					installed=installed,
					active=descriptor.name == active_model_str,
					status=status,
					download_job_id=job.id if job else None,
					error=error,
				)
			)

		# Include additional installed models not in the curated catalog.
		for name, info in installed_map.items():
			job = self._job_for(ModelType.LLM, name)
			status = VariantStatus.READY
			error: str | None = None

			if job is not None:
				if job.status is JobState.FAILED:
					status = VariantStatus.FAILED
					error = job.error
				elif job.status is JobState.CANCELLED:
					status = VariantStatus.CANCELLED
				elif job.is_active():
					status = VariantStatus.DOWNLOADING

			variants.append(
				ModelVariant(
					name=name,
					display_name=name,
					estimated_size_bytes=info.size,
					installed_size_bytes=info.size,
					installed=True,
					active=name == active_model_str,
					status=status,
					download_job_id=job.id if job else None,
					error=error,
				)
			)

		variants.sort(key=lambda variant: variant.display_name.lower())

		return ModelGroupStatus(
			kind=ModelType.LLM,
			active_model=active_model_str,
			disk=self._disk_info(self._ollama_models_dir),
			models=variants,
		)

	def _disk_info(self, directory: Path) -> DiskInfo:
		directory.mkdir(parents=True, exist_ok=True)
		usage = shutil.disk_usage(directory)
		return DiskInfo(path=str(directory), total_bytes=usage.total, free_bytes=usage.free)

	def _is_voice_model_installed(self, name: str) -> bool:
		target = self._voice_models_dir / name
		if not target.exists() or not target.is_dir():
			return False
		try:
			next(target.iterdir())
		except StopIteration:
			return False
		return True

	def _voice_model_size(self, name: str) -> int | None:
		path = self._voice_models_dir / name
		if not path.exists():
			return None
		return self._compute_directory_size(path)

	async def _is_llm_model_installed(self, name: str) -> bool:
		installed = await self._installed_llm_models()
		return name in installed

	async def _installed_llm_models(self) -> dict[str, OllamaModelInfo]:
		try:
			engine = await self._intent_engine_provider()
		except Exception as exc:  # pragma: no cover - dependency bootstrap issues
			logger.debug("Intent engine unavailable while listing models: %s", exc)
			return {}

		try:
			models = await engine.list_models()
		except Exception as exc:  # pragma: no cover - Ollama errors
			logger.debug("Failed to fetch Ollama model list: %s", exc)
			return {}

		return {model.name: model for model in models}

	@staticmethod
	def _compute_directory_size(path: Path) -> int:
		total = 0
		for file in path.rglob("*"):
			if file.is_file():
				try:
					total += file.stat().st_size
				except OSError:  # pragma: no cover - race conditions
					continue
		return total

