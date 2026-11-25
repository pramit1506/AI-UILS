"""Priority-ordered, multi-key LLM routing for extraction and lightweight tasks."""

from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional, Type

from loguru import logger
from pydantic import ValidationError

from app.core.config import settings
from app.exceptions.base import (
    AllProvidersExhaustedException,
    InvalidAPIKeyException,
    ModelUnavailableException,
    ProviderException,
    RateLimitException,
    TimeoutException,
)
from app.llm.base import BaseLLMProvider, T
from app.llm.output_parser import extract_json_block

# ---------------------------------------------------------------------------
# LiteLLM import — fail loud at startup if the package is missing
# ---------------------------------------------------------------------------
try:
    from litellm import Router
    import litellm

    # Suppress verbose litellm internal logging; keep only WARNING+
    litellm.set_verbose = False
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "litellm is required for LLM_PROVIDER=multi. "
        "Install it with: pip install -r requirements.txt"
    ) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_keys(attr_prefix: str) -> List[str]:
    """
    Collect all non-empty numbered keys for a provider (1 through 10).
    Checks both settings and os.environ directly to support any number of keys.
    """
    import os
    keys: List[str] = []
    # Legacy bare key (Groq only — kept for backward compat)
    if attr_prefix == "GROQ_API_KEY":
        bare = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        if bare and bare not in keys:
            keys.append(bare)
    # Numbered keys: _1 through _10
    for idx in range(1, 11):
        val = getattr(settings, f"{attr_prefix}_{idx}", "") or os.getenv(f"{attr_prefix}_{idx}", "")
        if val and val not in keys:
            keys.append(val)
    return keys


def _build_model_list() -> List[Dict[str, Any]]:
    """Use each distinct key once per role and balance keys within each priority."""
    roles = ("agent-core", "fast-router")
    routes = [
        ("openrouter", 0, (settings.OPENROUTER_MODEL, settings.OPENROUTER_FAST_MODEL)),
        ("openrouter", 1, ("google/gemma-4-31b-it:free", "google/gemma-4-26b-a4b-it:free")),
    ]
    if settings.GEMINI_FREE_TIER_CONFIRMED:
        routes.extend([
            ("gemini", 2, (settings.GEMINI_MODEL, settings.GEMINI_FAST_MODEL)),
            ("gemini", 3, (settings.GEMINI_FAST_MODEL, None)),
        ])
    if settings.GROQ_FREE_TIER_CONFIRMED:
        routes.append(("groq", 4, (settings.DEFAULT_MODEL, settings.GROQ_FAST_MODEL)))

    deployments = []
    seen = set()
    for provider, priority, models in routes:
        keys = _collect_keys(f"{provider.upper()}_API_KEY")
        for role, model in zip(roles, models):
            if model is None or (provider, role, model) in seen:
                continue
            seen.add((provider, role, model))
            if provider == "openrouter" and not model.endswith(":free"):
                raise ValueError("OpenRouter requires an explicit :free model for both roles.")
            for key in keys:
                params = {
                    "model": f"{provider}/{model}",
                    "api_key": key,
                    "order": priority,
                    "timeout": settings.MODEL_TIMEOUT,
                }
                if provider == "openrouter":
                    params["extra_body"] = {
                        "provider": {
                            "max_price": {"prompt": 0, "completion": 0, "request": 0},
                            "require_parameters": True,
                        }
                    }
                deployments.append({"model_name": role, "litellm_params": params})
    return deployments


def _is_exhaustion_error(exc: Exception) -> bool:
    """
    Return True when the exception indicates a terminal failure (all slots
    failed, not a transient error on a single slot).
    """
    msg = str(exc).lower()
    exhaustion_signals = [
        "all retries",
        "no healthy deployment",
        "no models available",
        "all deployments",
        "provider list exhausted",
    ]
    return any(signal in msg for signal in exhaustion_signals)


def _translate_litellm_exc(exc: Exception) -> Exception:
    """Map LiteLLM exceptions to our internal exception hierarchy."""
    msg = str(exc)
    msg_lower = msg.lower()

    if _is_exhaustion_error(exc):
        return AllProvidersExhaustedException("No configured free deployment is available.")
    if "429" in msg or "rate limit" in msg_lower:
        return RateLimitException("The configured providers reached their rate limits.")
    if "401" in msg or "authentication" in msg_lower or "invalid api key" in msg_lower:
        return InvalidAPIKeyException("A provider rejected its API key.")
    if "timeout" in msg_lower:
        return TimeoutException("The provider timed out.")
    if "model" in msg_lower and ("not found" in msg_lower or "unavailable" in msg_lower):
        return ModelUnavailableException("The configured model is unavailable.")
    return ProviderException("The model router could not complete the request.", status_code=502)


def _should_add_jitter(messages: List[Dict[str, Any]]) -> bool:
    """
    Heuristic: add a 250–500ms random jitter before concurrent calls to avoid
    burst rate-limit triggers. Applied when the message list looks like it's
    part of a parallel branch (no prior assistant turn in the last 2 messages).
    """
    if len(messages) < 2:
        return False
    recent_roles = {m.get("role") for m in messages[-2:]}
    return "assistant" not in recent_roles


# ---------------------------------------------------------------------------
# ResiliencyProvider
# ---------------------------------------------------------------------------

class ResiliencyProvider(BaseLLMProvider):
    """
    Multi-provider resilient LLM provider using LiteLLM Router.

    Replaces GroqProvider when LLM_PROVIDER=multi is set. Zero changes
    required in orchestrator code — implements the same BaseLLMProvider
    interface (generate_response / generate_structured).
    """

    def __init__(self) -> None:
        model_list = _build_model_list()

        if not model_list:
            raise AllProvidersExhaustedException(
                "No eligible cloud keys. Configure an OpenRouter key or confirm "
                "the Gemini or Groq free account plan in backend/.env."
            )

        agent_core_slots = [m for m in model_list if m["model_name"] == "agent-core"]
        fast_router_slots = [m for m in model_list if m["model_name"] == "fast-router"]

        logger.info(
            f"[ResiliencyProvider] Initialised with "
            f"{len(agent_core_slots)} agent-core slots and "
            f"{len(fast_router_slots)} fast-router slots across all configured keys."
        )

        # Use one model group per priority so structured responses can fail over
        # after validation, even when the provider returned HTTP 200.
        self._model_groups: dict[str, list[str]] = {}
        self._group_sizes: dict[str, int] = {}
        for deployment in model_list:
            role = deployment["model_name"]
            params = deployment["litellm_params"]
            group = f"{role}-{params.pop('order')}"
            if group not in self._group_sizes:
                self._model_groups.setdefault(role, []).append(group)
                self._group_sizes[group] = 0
            self._group_sizes[group] += 1
            deployment["model_name"] = group
        self._router = Router(
            model_list=model_list,
            num_retries=settings.ROUTER_NUM_RETRIES,
            retry_after=settings.ROUTER_RETRY_AFTER,
            routing_strategy=settings.ROUTER_STRATEGY,
            allowed_fails=0,
            cooldown_time=60,
            fallbacks=[{groups[0]: groups[1:]} for groups in self._model_groups.values() if len(groups) > 1],
        )

        # Compression threshold in message count (turns × 2 messages/turn)
        self._compression_threshold = settings.CONTEXT_COMPRESSION_THRESHOLD * 2

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _acompletion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        """
        Wrapper around router.acompletion with jitter injection and
        unified exception translation.
        """
        if _should_add_jitter(messages):
            await asyncio.sleep(random.uniform(0.25, 0.50))

        groups = self._model_groups.get(model)
        try:
            return await self._router.acompletion(
                model=groups[0] if groups else model,
                messages=messages,
                **kwargs,
            )
        except Exception as exc:
            logger.debug(
                "Model group {} failed with {} (HTTP {})",
                model, type(exc).__name__, getattr(exc, "status_code", None),
            )
            raise _translate_litellm_exc(exc) from exc

    def _strip_think_tags(self, text: str) -> str:
        """Remove <think>…</think> reasoning traces produced by some models."""
        import re
        if not text:
            return ""
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

    def _extract_json_block(self, text: str) -> str:
        """
        If the raw response is not parseable JSON, extract the first balanced
        JSON object using the deterministic scanner in app.llm.output_parser
        (handles markdown fences, nested braces, prose before/after, and
        truncated output). Falls back to the cleaned text itself.
        """
        cleaned = self._strip_think_tags(text)
        candidate = extract_json_block(cleaned)
        if candidate is None:
            candidate = cleaned.strip()
        return candidate

    # ── Context compression ──────────────────────────────────────────────────

    async def _maybe_compress_history(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Industry-standard sliding-window compression strategy:

        1. Always keep the FIRST message (system prompt — critical for KV caching).
        2. Identify non-system messages older than the recency window.
        3. Feed those older messages to the fast-router model and produce a
           single summary block.
        4. Return: [system_prompt] + [summary_block] + [recent_N_messages]

        This keeps the prompt size O(1) for long conversations while preserving
        full fidelity for the most recent turns.

        Recency window = last CONTEXT_COMPRESSION_THRESHOLD turns (20 messages
        by default), matching the production patterns used by LangGraph's
        trim_messages utility and Anthropic's context management guidelines.
        """
        # Count only non-system messages to determine conversation depth
        non_system = [m for m in messages if m.get("role") != "system"]
        if len(non_system) <= self._compression_threshold:
            return messages  # no compression needed

        # Separate system messages (always kept verbatim)
        system_msgs = [m for m in messages if m.get("role") == "system"]
        convo_msgs = [m for m in messages if m.get("role") != "system"]

        # Split into stale (to summarize) and recent (to keep verbatim)
        recent_window = self._compression_threshold
        stale_msgs = convo_msgs[:-recent_window]
        recent_msgs = convo_msgs[-recent_window:]

        # Build a summarisation prompt for the fast-router
        stale_text = "\n".join(
            f"[{m['role'].upper()}]: {m.get('content', '')}"
            for m in stale_msgs
        )
        compression_prompt = [
            {
                "role": "system",
                "content": (
                    "You are a concise conversation summariser. "
                    "Condense the following conversation history into a single, dense "
                    "paragraph that preserves all factual details, decisions made, "
                    "entities extracted, and the current state of any work-in-progress "
                    "log draft. Omit pleasantries and filler. Be factual and precise."
                ),
            },
            {"role": "user", "content": f"Conversation history to summarise:\n\n{stale_text}"},
        ]

        try:
            summary_response = await self._acompletion(
                model="fast-router",
                messages=compression_prompt,
                temperature=0.0,
                max_tokens=512,
            )
            summary_text = summary_response.choices[0].message.content or ""
            summary_text = self._strip_think_tags(summary_text)
            logger.info(
                f"[ResiliencyProvider] Context compressed: "
                f"{len(stale_msgs)} stale messages → 1 summary block "
                f"({len(recent_msgs)} recent messages kept verbatim)."
            )
            summary_block = {
                "role": "system",
                "content": f"[CONVERSATION SUMMARY — earlier turns condensed]\n{summary_text}",
            }
            return system_msgs + [summary_block] + recent_msgs

        except Exception as exc:
            # Compression failure is non-fatal — proceed with full history
            logger.warning(
                f"[ResiliencyProvider] Context compression failed ({exc}); "
                f"using full message history."
            )
            return messages

    # ── Public API — BaseLLMProvider interface ────────────────────────────────

    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a raw string response. Uses the agent-core failover pool.
        Automatically compresses conversation history if it exceeds the threshold.
        """
        compressed = await self._maybe_compress_history(messages)

        response = await self._acompletion(
            model="fast-router" if model == "fast-router" else "agent-core",
            messages=compressed,
            temperature=temperature if temperature is not None else settings.TEMPERATURE,
            max_tokens=max_tokens or settings.MAX_TOKENS,
        )
        raw = response.choices[0].message.content or ""
        return self._strip_think_tags(raw)

    async def generate_structured(
        self,
        messages: List[Dict[str, Any]],
        schema: Type[T],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        """
        Generate a structured Pydantic-validated response. Uses the agent-core
        failover pool with JSON mode. Compresses history automatically.
        """
        compressed = await self._maybe_compress_history(messages)

        role = "fast-router" if model == "fast-router" else "agent-core"
        group_timeout = min(settings.MODEL_TIMEOUT, 12 if role == "fast-router" else 18)
        last_error: Exception | None = None
        for group in self._model_groups[role]:
            try:
                # Bound retries as a group so a stalled model leaves time for backups.
                async with asyncio.timeout(group_timeout):
                    response = await self._acompletion(
                        model=group,
                        messages=compressed,
                        temperature=temperature if temperature is not None else 0.0,
                        response_format={"type": "json_object"},
                        disable_fallbacks=True,
                        num_retries=min(settings.ROUTER_NUM_RETRIES, self._group_sizes[group] - 1),
                    )
                raw = response.choices[0].message.content if response.choices else None
                output = schema.model_validate_json(self._extract_json_block(raw or ""))
                if schema.model_fields and not output.model_fields_set:
                    raise ProviderException("The provider returned none of the requested fields.")
                return output
            except (ProviderException, TimeoutError, ValidationError) as exc:
                last_error = exc
                logger.warning("Structured output from {} failed ({}); checking the next route", group, type(exc).__name__)
        raise AllProvidersExhaustedException("No configured provider returned valid structured output.") from last_error



# ---------------------------------------------------------------------------
# Shutdown — LiteLLM Router owns no long-lived httpx sessions we can close
# from here (it creates per-request clients internally), so this is a safe,
# idempotent no-op kept for a uniform shutdown interface across providers.
# ---------------------------------------------------------------------------

async def shutdown_llm_clients() -> None:
    """
    No-op for the LiteLLM Router-backed provider: litellm's Router exposes no
    aclose()/close() and manages its client lifecycle internally. Kept so
    app.llm.factory.shutdown_llm_clients() can call it uniformly, repeatedly,
    and safely.
    """
    return None
