"""
OllamaProvider — local LLM provider for fully private, self-hosted inference.

Usage: Set LLM_PROVIDER=ollama and OLLAMA_BASE_URL in your .env file.
The provider uses the Ollama REST API (/api/chat) which is compatible with
any model pulled via `ollama pull <model>` (e.g. llama3, mistral, phi3).

No API key required — Ollama runs entirely on your local machine.
"""

import json
import re
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel

from app.llm.base import BaseLLMProvider, T
from app.core.config import settings
from app.exceptions.base import (
    ProviderException,
    TimeoutException,
    ModelUnavailableException,
)


class OllamaProvider(BaseLLMProvider):
    """
    LLM provider that talks to a locally-running Ollama server.
    Implements the same BaseLLMProvider interface as GroqProvider so it is
    a drop-in replacement — no other code needs to change.
    """

    def __init__(self):
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = getattr(settings, "OLLAMA_MODEL", None) or settings.DEFAULT_MODEL
        self.timeout = settings.MODEL_TIMEOUT
        # httpx async client — reused for the lifetime of the provider instance
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_think_tags(text: str) -> str:
        """Strip <think>…</think> reasoning traces produced by some models."""
        if not text:
            return ""
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

    def _translate_exception(self, exc: Exception) -> Exception:
        if isinstance(exc, httpx.TimeoutException):
            return TimeoutException(f"Ollama timed out: {exc}")
        if isinstance(exc, httpx.ConnectError):
            return ProviderException(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running (`ollama serve`).",
                status_code=503,
            )
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 404:
                return ModelUnavailableException(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Pull it first: `ollama pull {self.model}`"
                )
            return ProviderException(f"Ollama HTTP error {exc.response.status_code}: {exc}", status_code=502)
        return ProviderException(f"Ollama error: {exc}", status_code=500)

    # ── core API calls ───────────────────────────────────────────────────────

    async def _chat(
        self,
        messages: list[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> str:
        """Low-level POST to /api/chat and return the assistant content string."""
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.TEMPERATURE,
                "num_predict": settings.MAX_TOKENS,
            },
        }
        if json_mode:
            payload["format"] = "json"

        try:
            resp = await self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            raise self._translate_exception(exc) from exc
        except Exception as exc:
            raise ProviderException(f"Unexpected Ollama error: {exc}", status_code=500) from exc

    # ── BaseLLMProvider interface ─────────────────────────────────────────────

    async def generate_response(
        self,
        messages: list[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        raw = await self._chat(messages, model=model, temperature=temperature)
        return self._clean_think_tags(raw)

    async def generate_structured(
        self,
        messages: list[Dict[str, Any]],
        schema: Type[T],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        raw = await self._chat(messages, model=model, temperature=0.0, json_mode=True)
        cleaned = self._clean_think_tags(raw)

        # Ollama JSON mode usually returns a clean object; extract if wrapped in markdown
        if not cleaned.strip().startswith("{"):
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                cleaned = match.group(0)

        return schema.model_validate_json(cleaned)
