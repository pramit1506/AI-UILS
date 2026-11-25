import re
import httpx
from typing import Any, Dict, List, Optional, Type
import groq
from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.llm.base import BaseLLMProvider, T
from app.llm.output_parser import extract_json_block, strip_markdown_fences
from app.core.config import settings
from app.exceptions.base import (
    ProviderException,
    RateLimitException,
    TimeoutException,
    InvalidAPIKeyException,
    ModelUnavailableException,
)

# Reasoning-trace tags are assembled at runtime to keep the source readable.
_THINK_OPEN = "<" + "VoidThink" + ">"
_THINK_CLOSE = "</" + "VoidThink" + ">"
_THINK_RE = re.compile(re.escape(_THINK_OPEN) + r"[\s\S]*?" + re.escape(_THINK_CLOSE))

def _clean_think_tags(text: str) -> str:
    """Removes reasoning-trace tags (e.g. <VoidThink>...</VoidThink>) from LLM responses."""
    if not text:
        return ""
    cleaned = _THINK_RE.sub("", text)
    return cleaned.strip()

# AsyncGroq clients created by this module — closed by shutdown_llm_clients().
_active_clients: List[AsyncGroq] = []

async def shutdown_llm_clients() -> None:
    """
    Close every AsyncGroq network client this module created. Idempotent and
    safe to call repeatedly (including when no client was ever created).
    """
    for client in list(_active_clients):
        try:
            if hasattr(client, "aclose"):
                await client.aclose()
            elif hasattr(client, "close"):
                client.close()
        except Exception:  # pragma: no cover — best-effort shutdown
            pass
    _active_clients.clear()

class GroqProvider(BaseLLMProvider):
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise InvalidAPIKeyException("GROQ_API_KEY is not configured")

        self.client = AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=settings.MODEL_TIMEOUT,
            max_retries=0
        )
        _active_clients.append(self.client)

    def _translate_exception(self, e: Exception) -> Exception:
        if isinstance(e, groq.RateLimitError):
            return RateLimitException(str(e))
        if isinstance(e, groq.APITimeoutError):
            return TimeoutException(str(e))
        if isinstance(e, groq.AuthenticationError):
            return InvalidAPIKeyException(str(e))
        if isinstance(e, groq.NotFoundError) and "model" in str(e).lower():
            return ModelUnavailableException(str(e))
        if isinstance(e, groq.APIConnectionError) or isinstance(e, httpx.RequestError):
            return ProviderException(f"Network error connecting to Groq: {e}", status_code=503)
        if isinstance(e, groq.APIError):
            return ProviderException(f"Groq API Error: {e}", status_code=502)
        return e

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((groq.APIConnectionError, groq.RateLimitError, groq.InternalServerError, httpx.RequestError)),
        reraise=True
    )
    async def _create_chat_completion(self, **kwargs):
        try:
            return await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            translated_exc = self._translate_exception(e)
            if isinstance(translated_exc, (RateLimitException, ProviderException)):
                raise e # Raise original for tenacity to catch
            raise translated_exc

    async def generate_response(
        self,
        messages: list[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        try:
            response = await self._create_chat_completion(
                messages=messages,
                model=model or settings.DEFAULT_MODEL,
                temperature=temperature if temperature is not None else settings.TEMPERATURE,
                max_tokens=max_tokens or settings.MAX_TOKENS,
            )
            raw_content = response.choices[0].message.content or ""
            return _clean_think_tags(raw_content)
        except Exception as e:
            raise self._translate_exception(e)

    async def generate_structured(
        self,
        messages: list[Dict[str, Any]],
        schema: Type[T],
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> T:
        try:
            response = await self._create_chat_completion(
                messages=messages,
                model=model or settings.DEFAULT_MODEL,
                temperature=temperature if temperature is not None else 0.0,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content or ""
            cleaned = _clean_think_tags(raw_content)

            # Robust extraction: markdown fences, prose before/after, nested
            # braces and truncated output are all handled by the deterministic
            # balanced scanner in app.llm.output_parser (replaces the old
            # greedy re.search(r'{[\s\S]*}', ...) approach).
            candidate = extract_json_block(cleaned)
            if candidate is None:
                candidate = strip_markdown_fences(cleaned).strip() or cleaned

            return schema.model_validate_json(candidate)
        except Exception as e:
            raise self._translate_exception(e)
