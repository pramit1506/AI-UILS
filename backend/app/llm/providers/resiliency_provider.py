"""
ResiliencyProvider — Drop-in multi-provider LLM failover backed by LiteLLM Router.

Architecture:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Tier 1 — fast-router pool (light, high-RPM)                   │
  │    • Groq llama-3.1-8b-instant  (all configured keys)          │
  │    • Cerebras llama3.1-8b        (fallback if Groq keys fail)  │
  │  Used for: intent classification, context compression          │
  ├─────────────────────────────────────────────────────────────────┤
  │  Tier 2 — agent-core pool (reasoning, multi-step synthesis)    │
  │    • Groq  openai/gpt-oss-120b   (all configured keys)         │
  │    • Cerebras llama-3.3-70b       (all configured keys)        │
  │    • Gemini gemini-2.5-flash-lite (all configured keys)        │
  │    • OpenRouter llama-3.3-70b     (all configured keys)        │
  │  Used for: entity extraction, decision, response generation    │
  └─────────────────────────────────────────────────────────────────┘

Key Cycling:
  Each provider slot in the router is a separate entry identified by its
  API key. The router's "simple-shuffle" strategy distributes load randomly
  across healthy slots and transparently fails over to the next slot on
  429 / 5xx — no external intervention needed.

Context Compression:
  When conversation history exceeds CONTEXT_COMPRESSION_THRESHOLD turns
  (default 10 = 20 messages) the fast-router summarises older turns into a
  single [system] block before the agent-core call. This keeps prompt size
  stable and maximises KV-cache reuse on the provider side.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional, Type

from loguru import logger

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
        "Install it with: pip install litellm>=1.40.0"
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
    """
    Construct the LiteLLM Router model list from all configured API keys.

    Verified working model IDs:
    ┌──────────────────┬───────────────────────────────────────────────────────┐
    │ Tier 2 agent-core│                                                       │
    ├──────────────────┼───────────────────────────────────────────────────────┤
    │ Groq             │ groq/openai/gpt-oss-120b, groq/qwen/qwen3.6-27b      │
    │ Gemini           │ gemini/gemini-3.5-flash                               │
    │ OpenRouter       │ openrouter/openai/gpt-oss-20b:free                    │
    │ Cerebras         │ cerebras/gpt-oss-120b                                 │
    ├──────────────────┼───────────────────────────────────────────────────────┤
    │ Tier 1 fast-router│                                                      │
    ├──────────────────┼───────────────────────────────────────────────────────┤
    │ Groq             │ groq/openai/gpt-oss-20b, groq/qwen/qwen3.6-27b       │
    │ Gemini           │ gemini/gemini-3.5-flash-lite                          │
    │ OpenRouter       │ openrouter/nvidia/nemotron-3.5-lightning:free         │
    │ Cerebras         │ cerebras/gemma-4-31b                                  │
    └──────────────────┴───────────────────────────────────────────────────────┘
    """
    model_list: List[Dict[str, Any]] = []

    groq_keys = _collect_keys("GROQ_API_KEY")
    cerebras_keys = _collect_keys("CEREBRAS_API_KEY")
    gemini_keys = _collect_keys("GEMINI_API_KEY")
    openrouter_keys = _collect_keys("OPENROUTER_API_KEY")

    # ── Tier 2 — agent-core (reasoning / synthesis / extraction) ─────────────
    # Primary: Groq gpt-oss-120b + qwen3.6-27b
    for key in groq_keys:
        model_list.append({
            "model_name": "agent-core",
            "litellm_params": {
                "model": "groq/openai/gpt-oss-120b",
                "api_key": key,
                "rpm": 30,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })
        model_list.append({
            "model_name": "agent-core",
            "litellm_params": {
                "model": "groq/qwen/qwen3.6-27b",
                "api_key": key,
                "rpm": 30,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    # Failover: Google Gemini 3.5 Flash
    for key in gemini_keys:
        model_list.append({
            "model_name": "agent-core",
            "litellm_params": {
                "model": "gemini/gemini-3.5-flash",
                "api_key": key,
                "rpm": 15,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    # Failover: OpenRouter Free Models
    for key in openrouter_keys:
        model_list.append({
            "model_name": "agent-core",
            "litellm_params": {
                "model": "openrouter/openai/gpt-oss-20b:free",
                "api_key": key,
                "rpm": 20,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    # Failover: Cerebras gpt-oss-120b
    for key in cerebras_keys:
        model_list.append({
            "model_name": "agent-core",
            "litellm_params": {
                "model": "cerebras/gpt-oss-120b",
                "api_key": key,
                "rpm": 30,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    # ── Tier 1 — fast-router (intent classification / context compression) ────
    for key in groq_keys:
        model_list.append({
            "model_name": "fast-router",
            "litellm_params": {
                "model": "groq/openai/gpt-oss-20b",
                "api_key": key,
                "rpm": 30,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    for key in gemini_keys:
        model_list.append({
            "model_name": "fast-router",
            "litellm_params": {
                "model": "gemini/gemini-3.5-flash-lite",
                "api_key": key,
                "rpm": 15,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    for key in openrouter_keys:
        model_list.append({
            "model_name": "fast-router",
            "litellm_params": {
                "model": "openrouter/nvidia/nemotron-3.5-lightning:free",
                "api_key": key,
                "rpm": 20,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    for key in cerebras_keys:
        model_list.append({
            "model_name": "fast-router",
            "litellm_params": {
                "model": "cerebras/gemma-4-31b",
                "api_key": key,
                "rpm": 30,
                "timeout": settings.MODEL_TIMEOUT,
            },
        })

    return model_list





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
        return AllProvidersExhaustedException(
            f"Every configured API key across all providers has been exhausted. "
            f"Add new keys to your .env file (GROQ_API_KEY_1, CEREBRAS_API_KEY_1, etc.). "
            f"Original error: {msg}"
        )
    if "429" in msg or "rate limit" in msg_lower:
        return RateLimitException(f"Rate limit hit across providers: {msg}")
    if "401" in msg or "authentication" in msg_lower or "invalid api key" in msg_lower:
        return InvalidAPIKeyException(f"API key rejected by provider: {msg}")
    if "timeout" in msg_lower:
        return TimeoutException(f"Provider timed out: {msg}")
    if "model" in msg_lower and ("not found" in msg_lower or "unavailable" in msg_lower):
        return ModelUnavailableException(f"Model unavailable: {msg}")
    return ProviderException(f"LiteLLM Router error: {msg}", status_code=502)


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

    Additional public method:
        fast_classify(messages) → str   — Tier-1 fast-router call
    """

    def __init__(self) -> None:
        model_list = _build_model_list()

        if not model_list:
            raise AllProvidersExhaustedException(
                "No API keys are configured for any provider. "
                "Set at least one key in backend/.env "
                "(e.g. GROQ_API_KEY_1=gsk_...) before using LLM_PROVIDER=multi."
            )

        agent_core_slots = [m for m in model_list if m["model_name"] == "agent-core"]
        fast_router_slots = [m for m in model_list if m["model_name"] == "fast-router"]

        logger.info(
            f"[ResiliencyProvider] Initialised with "
            f"{len(agent_core_slots)} agent-core slots and "
            f"{len(fast_router_slots)} fast-router slots across all configured keys."
        )

        self._router = Router(
            model_list=model_list,
            num_retries=max(settings.ROUTER_NUM_RETRIES, len(agent_core_slots)),
            retry_after=settings.ROUTER_RETRY_AFTER,
            routing_strategy=settings.ROUTER_STRATEGY,
            allowed_fails=len(agent_core_slots) + len(fast_router_slots),
            cooldown_time=60,
            fallbacks=[{"agent-core": ["fast-router"]}],
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

        try:
            return await self._router.acompletion(
                model=model,
                messages=messages,
                **kwargs,
            )
        except Exception as exc:
            raise _translate_litellm_exc(exc) from exc

    def _strip_think_tags(self, text: str) -> str:
        """Remove <think>…</think> reasoning traces produced by some models."""
        import re
        if not text:
            return ""
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

    def _extract_json_block(self, text: str) -> str:
        """
        If the raw response is not a bare JSON object, attempt to extract the
        outermost { … } block (handles markdown code-fenced responses).
        """
        import re
        cleaned = self._strip_think_tags(text)
        if cleaned.strip().startswith("{"):
            return cleaned
        match = re.search(r"\{[\s\S]*\}", cleaned)
        return match.group(0) if match else cleaned

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
            model="agent-core",
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

        response = await self._acompletion(
            model="agent-core",
            messages=compressed,
            temperature=temperature if temperature is not None else 0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        cleaned = self._extract_json_block(raw)
        return schema.model_validate_json(cleaned)

    async def fast_classify(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> str:
        """
        Tier-1 fast-router call. Use for intent classification, guardrails,
        and any lightweight inference where speed matters over reasoning depth.
        Does NOT apply context compression (fast calls are always short).
        """
        response = await self._acompletion(
            model="fast-router",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw = response.choices[0].message.content or ""
        return self._strip_think_tags(raw)
