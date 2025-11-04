"""Intent recognition powered by local Ollama models."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from common.settings import SettingsManager

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_INTENT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL") or os.getenv(
    "OLLAMA_MODEL", "llama3.2:1b"
)
REQUEST_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))

_INTENT_PROMPT = """
You are the intent router for the WomCast media hub. The user will provide a
voice transcript. Your job is to classify the intent and produce JSON that the
application can use to act. Respond with a *single* JSON object matching this
schema:
{{
    "action": "<string>",
    "args": {{"key": "value"}},
    "confidence": <float between 0 and 1>
}}

Guidelines:
- Choose action from: "play_media", "search", "open_connector", "navigate",
  "show_settings", "unknown".
- When unsure, use action "search" and include the original query in
  args.query.
- For playback requests, include args.title and any other helpful metadata.
- For connector requests, include args.connector with a short identifier
  (e.g. "netflix", "jamendo").
- Never include explanations, markdown, or additional text. Output JSON only.

Context (optional): {context}
User query: {query}
""".strip()


@dataclass
class OllamaModelInfo:
    """Metadata about an Ollama model."""

    name: str
    size: int | None = None
    digest: str | None = None
    modified_at: str | None = None


@dataclass
class IntentPrediction:
    """Structured prediction returned by the intent engine."""

    action: str
    args: dict[str, Any]
    confidence: float
    model: str
    latency_ms: float
    raw_response: str


class IntentParseError(RuntimeError):
    """Raised when the LLM response cannot be parsed into structured data."""


class IntentEngine:
    """Facade around the Ollama HTTP API for intent classification."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        *,
        base_url: str | None = None,
    request_timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._settings_manager = settings_manager
        self._base_url = base_url or OLLAMA_BASE_URL
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self._timeout = request_timeout

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._client_lock:
            if self._client is None:
                logger.debug("Creating Ollama AsyncClient for %s", self._base_url)
                self._client = httpx.AsyncClient(
                    base_url=self._base_url, timeout=self._timeout
                )
        assert self._client is not None  # mypy: help
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def list_models(self) -> list[OllamaModelInfo]:
        """Return the models available in the local Ollama instance."""

        client = await self._get_client()
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network issues
            logger.warning("Failed to list Ollama models: %s", exc)
            return []

        payload = response.json()
        models: list[OllamaModelInfo] = []
        for item in payload.get("models", []):
            models.append(
                OllamaModelInfo(
                    name=item.get("name", ""),
                    size=_safe_cast_int(item.get("size")),
                    digest=item.get("digest"),
                    modified_at=item.get("modified_at"),
                )
            )
        return [m for m in models if m.name]

    async def predict_intent(
        self,
        text: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> IntentPrediction:
        """Run the LLM to classify intent for the supplied transcript."""

        await self._settings_manager.refresh()
        model = str(
            self._settings_manager.get("llm_model", DEFAULT_INTENT_MODEL)
            or DEFAULT_INTENT_MODEL
        )

        prompt = self._build_prompt(text=text, context=context)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            },
        }

        client = await self._get_client()
        started = time.perf_counter()
        try:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Intent request to Ollama failed: %s", exc)
            raise IntentParseError("Failed to contact intent model") from exc

        latency_ms = (time.perf_counter() - started) * 1000

        data = response.json()
        raw = str(data.get("response", "")).strip()

        try:
            parsed = _extract_json_object(raw)
        except IntentParseError as exc:
            logger.warning("Intent response parsing failed, falling back: %s", exc)
            return IntentPrediction(
                action="search",
                args={"query": text},
                confidence=0.0,
                model=model,
                latency_ms=latency_ms,
                raw_response=raw,
            )

        action = str(parsed.get("action", "search")).strip() or "search"
        args_obj = parsed.get("args")
        if not isinstance(args_obj, dict):
            args_obj = {}
        # Ensure the original query is at least available for downstream usage
        args_obj.setdefault("query", text)

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0
        confidence_value = max(0.0, min(1.0, confidence_value))

        return IntentPrediction(
            action=action,
            args=args_obj,
            confidence=confidence_value,
            model=model,
            latency_ms=latency_ms,
            raw_response=raw,
        )

    @staticmethod
    def _build_prompt(text: str, context: dict[str, Any] | None = None) -> str:
        context_json = "{}"
        if context:
            try:
                context_json = json.dumps(context, ensure_ascii=True)
            except (TypeError, ValueError):
                logger.debug("Failed to JSON encode context for prompt; using empty context")
                context_json = "{}"
        return _INTENT_PROMPT.format(query=text.strip(), context=context_json)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract and decode the first JSON object contained in text."""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise IntentParseError("No JSON object found in response")

    candidate = cleaned[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise IntentParseError("Response JSON malformed") from exc


def _safe_cast_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
