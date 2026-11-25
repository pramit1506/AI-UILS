"""
LLM provider factory — builds and caches the configured provider singleton.

The provider instance (and any underlying LiteLLM Router / httpx / openai
clients it owns) is created exactly once per process and reused for every
request. Use `get_llm_provider()` anywhere you need the provider — it always
returns the same cached object.

`shutdown_llm_clients()` closes any network clients the providers own. It is
safe to call repeatedly and must be invoked from the app lifespan on shutdown.
"""

import threading
from typing import Optional

from app.llm.base import BaseLLMProvider
from app.core.config import settings

# Module-level singleton cache (async single-process app; a simple lock is
# sufficient protection for the rare first-time init and test re-imports).
_PROVIDER: Optional[BaseLLMProvider] = None
_PROVIDER_LOCK = threading.Lock()


def _build_provider() -> BaseLLMProvider:
    """
    Construct a fresh provider instance based on the configured LLM_PROVIDER.
    """
    provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()

    if provider == "ollama":
        from app.llm.providers.ollama_provider import OllamaProvider
        return OllamaProvider()

    if provider == "multi":
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        return ResiliencyProvider()

    # Default: Groq single-key cloud provider
    from app.llm.providers.groq_provider import GroqProvider
    return GroqProvider()


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to get the configured — and CACHED — LLM provider.

    The provider is created on first call and reused for the lifetime of the
    process, so callers never pay client-construction cost per request
    (chat.py passes `llm_provider=get_llm_provider()` into every
    ToolExecutionContext; this returns the same instance each time).

    Multi mode uses confirmed free Gemini and Groq accounts, followed by
    explicitly free OpenRouter endpoints. Groq and Ollama single-provider
    modes remain available through LLM_PROVIDER.
    """
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    with _PROVIDER_LOCK:
        if _PROVIDER is None:
            _PROVIDER = _build_provider()
    return _PROVIDER


def reset_llm_provider_cache() -> None:
    """
    Drop the cached provider singleton so the next `get_llm_provider()` call
    rebuilds it. Intended for tests / config changes — not for runtime use.
    """
    global _PROVIDER
    with _PROVIDER_LOCK:
        _PROVIDER = None


async def shutdown_llm_clients() -> None:
    """
    Close any underlying network clients owned by the provider modules
    (httpx AsyncClients, AsyncGroq, …). Safe to call repeatedly (and when no
    provider was ever created) — every cleanup step is idempotent and
    exception-tolerant.
    """
    for module_name in ("groq_provider", "ollama_provider", "resiliency_provider"):
        try:
            import importlib
            module = importlib.import_module(f"app.llm.providers.{module_name}")
        except (ImportError, ModuleNotFoundError):
            continue  # optional provider not installed (e.g. litellm)
        try:
            shutdown = getattr(module, "shutdown_llm_clients", None)
            if shutdown is not None:
                await shutdown()
        except Exception:  # pragma: no cover — shutdown must never raise
            pass
    reset_llm_provider_cache()
