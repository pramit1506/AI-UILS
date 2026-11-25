"""
Tests for ResiliencyProvider — multi-provider LiteLLM Router failover.

Covers:
  - Failover chain: first slot 429 → second slot succeeds
  - Key pool construction from numbered env vars
  - AllProvidersExhaustedException when the entire pool fails
  - Context compression (history trimming + fast-router summarisation)
  - Jitter injection heuristic
"""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Any, Dict, List, Type

# ---------------------------------------------------------------------------
# Helpers to build fake litellm router responses
# ---------------------------------------------------------------------------

def _make_choice(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    return choice


def _make_response(content: str = "OK") -> MagicMock:
    resp = MagicMock()
    resp.choices = [_make_choice(content)]
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Patch settings so we don't need a real .env during testing."""
    from app.llm.providers import resiliency_provider as module
    from app.core.config import Settings

    for prefix in ("GEMINI", "GROQ", "OPENROUTER"):
        for suffix in ("", *(f"_{i}" for i in range(1, 11))):
            monkeypatch.delenv(f"{prefix}_API_KEY{suffix}", raising=False)
    config = Settings(
        _env_file=None,
        GEMINI_FREE_TIER_CONFIRMED=True,
        GROQ_FREE_TIER_CONFIRMED=True,
        GROQ_API_KEY="gsk_test_key_1",
        GROQ_API_KEY_1="gsk_test_key_1",
        GROQ_API_KEY_2="gsk_test_key_2",
        GEMINI_API_KEY_1="AIza_test_key_1",
        GEMINI_API_KEY_2="AIza_test_key_2",
        OPENROUTER_API_KEY_1="sk-or-test_key_1",
        CONTEXT_COMPRESSION_THRESHOLD=3,
    )
    monkeypatch.setattr(module, "settings", config)
    return config


# ---------------------------------------------------------------------------
# 1. Key pool construction
# ---------------------------------------------------------------------------

class TestKeyPoolConstruction:
    def test_collects_numbered_groq_keys(self):
        from app.llm.providers.resiliency_provider import _collect_keys
        keys = _collect_keys("GROQ_API_KEY")
        # Should include legacy GROQ_API_KEY (if set) + numbered keys
        assert "gsk_test_key_1" in keys
        assert "gsk_test_key_2" in keys

    def test_skips_empty_keys(self, monkeypatch):
        from app.llm.providers.resiliency_provider import _collect_keys
        # If GROQ_API_KEY_3 is empty it should not appear
        monkeypatch.setenv("GROQ_API_KEY_3", "")
        keys = _collect_keys("GROQ_API_KEY")
        assert "" not in keys

    def test_model_list_contains_agent_core_slots(self):
        from app.llm.providers.resiliency_provider import _build_model_list
        model_list = _build_model_list()
        agent_core = [m for m in model_list if m["model_name"] == "agent-core"]
        fast_router = [m for m in model_list if m["model_name"] == "fast-router"]
        assert len(agent_core) >= 1
        assert len(fast_router) >= 1

    @pytest.mark.parametrize("role", ["agent-core", "fast-router"])
    def test_priority_and_distinct_keys(self, role):
        from app.llm.providers.resiliency_provider import _build_model_list
        slots = [m["litellm_params"] for m in _build_model_list() if m["model_name"] == role]
        expected = [("gemini", 0)] * 2
        if role == "agent-core":
            expected += [("gemini", 1)] * 2
        expected += [("groq", 2), ("groq", 2), ("openrouter", 3), ("openrouter", 4)]
        assert [(p["model"].split("/")[0], p["order"]) for p in slots] == expected
        assert len({(p["model"], p["api_key"]) for p in slots}) == len(slots)
        assert slots[-1]["model"].endswith(":free")
        assert slots[-1]["extra_body"]["provider"]["max_price"] == {"request": 0, "prompt": 0, "completion": 0}

    def test_unconfirmed_plans_use_only_free_openrouter(self, patch_settings):
        from app.llm.providers.resiliency_provider import _build_model_list
        patch_settings.GEMINI_FREE_TIER_CONFIRMED = False
        patch_settings.GROQ_FREE_TIER_CONFIRMED = False
        assert all(d["litellm_params"]["model"].endswith(":free") for d in _build_model_list())

    def test_paid_openrouter_model_rejected(self, patch_settings):
        from app.llm.providers.resiliency_provider import _build_model_list
        patch_settings.OPENROUTER_MODEL = "google/gemma-4-31b-it"
        with pytest.raises(ValueError, match=":free"):
            _build_model_list()

    def test_raises_when_no_eligible_keys(self, patch_settings):
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        from app.exceptions.base import AllProvidersExhaustedException
        patch_settings.GEMINI_FREE_TIER_CONFIRMED = False
        patch_settings.GROQ_FREE_TIER_CONFIRMED = False
        patch_settings.OPENROUTER_API_KEY_1 = ""
        with pytest.raises(AllProvidersExhaustedException):
            ResiliencyProvider()


# ---------------------------------------------------------------------------
# 2. generate_response — successful path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGenerateResponse:
    async def test_returns_stripped_response(self):
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        provider = ResiliencyProvider.__new__(ResiliencyProvider)
        provider._compression_threshold = 6

        async def fake_acompletion(**kwargs):
            return _make_response("<think>internal</think>Hello!")

        provider._acompletion = fake_acompletion

        result = await provider.generate_response(
            messages=[{"role": "user", "content": "Hi"}]
        )
        assert result == "Hello!"

    async def test_calls_agent_core_pool(self):
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        provider = ResiliencyProvider.__new__(ResiliencyProvider)
        provider._compression_threshold = 6
        called_model = []

        async def fake_acompletion(model, messages, **kwargs):
            called_model.append(model)
            return _make_response("OK")

        provider._acompletion = fake_acompletion
        await provider.generate_response(messages=[{"role": "user", "content": "test"}])
        assert called_model[0] == "agent-core"


# ---------------------------------------------------------------------------
# 3. Failover — AllProvidersExhaustedException
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFailover:
    @pytest.mark.parametrize("role", ["agent-core", "fast-router"])
    async def test_router_uses_priority_for_each_role(self, role, patch_settings, monkeypatch):
        import litellm
        from app.llm.providers.resiliency_provider import ResiliencyProvider

        patch_settings.ROUTER_NUM_RETRIES = 0
        attempted = []

        async def complete(**kwargs):
            provider = kwargs["model"].split("/")[0]
            attempted.append(provider)
            if provider != "openrouter":
                raise litellm.ServiceUnavailableError("simulated outage", provider, kwargs["model"])
            assert kwargs["extra_body"]["provider"]["max_price"]["request"] == 0
            return litellm.ModelResponse(choices=[{"message": {"role": "assistant", "content": "OK"}}])

        monkeypatch.setattr(litellm, "acompletion", complete)
        router = ResiliencyProvider()
        result = await router.generate_response([{"role": "user", "content": "ping"}], model=role)
        assert result == "OK"
        gemini_attempts = 2 if role == "agent-core" else 1
        assert attempted == ["gemini"] * gemini_attempts + ["groq", "openrouter"]

    async def test_raises_all_providers_exhausted_on_pool_failure(self):
        from app.llm.providers.resiliency_provider import ResiliencyProvider, _translate_litellm_exc
        from app.exceptions.base import AllProvidersExhaustedException

        provider = ResiliencyProvider.__new__(ResiliencyProvider)
        provider._compression_threshold = 6

        async def always_fail(model, messages, **kwargs):
            # Simulate what _acompletion does: translate and raise
            raw_exc = Exception("all retries failed — no healthy deployment")
            raise _translate_litellm_exc(raw_exc)

        provider._acompletion = always_fail

        with pytest.raises(AllProvidersExhaustedException):
            await provider.generate_response(messages=[{"role": "user", "content": "test"}])

    async def test_translate_exhaustion_signal(self):
        from app.llm.providers.resiliency_provider import _translate_litellm_exc
        from app.exceptions.base import AllProvidersExhaustedException

        exc = Exception("no healthy deployment available after all retries")
        result = _translate_litellm_exc(exc)
        assert isinstance(result, AllProvidersExhaustedException)

    async def test_translate_rate_limit_signal(self):
        from app.llm.providers.resiliency_provider import _translate_litellm_exc
        from app.exceptions.base import RateLimitException

        exc = Exception("429 rate limit exceeded")
        result = _translate_litellm_exc(exc)
        assert isinstance(result, RateLimitException)



# ---------------------------------------------------------------------------
# 4. Context compression
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestContextCompression:
    def _make_convo(self, n_turns: int) -> List[Dict]:
        msgs = [{"role": "system", "content": "You are a helpful assistant."}]
        for i in range(n_turns):
            msgs.append({"role": "user", "content": f"User message {i}"})
            msgs.append({"role": "assistant", "content": f"Assistant response {i}"})
        return msgs

    async def test_no_compression_below_threshold(self):
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        provider = ResiliencyProvider.__new__(ResiliencyProvider)
        provider._compression_threshold = 6  # 3 turns × 2 = 6 messages

        messages = self._make_convo(n_turns=2)  # 4 non-system messages < 6
        compressed = await provider._maybe_compress_history(messages)
        assert compressed == messages  # unchanged

    async def test_compression_fires_above_threshold(self):
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        provider = ResiliencyProvider.__new__(ResiliencyProvider)
        provider._compression_threshold = 4  # 2 turns × 2 = 4 messages

        summary_called = []

        async def fake_acompletion(model, messages, **kwargs):
            summary_called.append(model)
            return _make_response("This is a summary of earlier conversation.")

        provider._acompletion = fake_acompletion
        messages = self._make_convo(n_turns=4)  # 8 non-system > 4
        compressed = await provider._maybe_compress_history(messages)

        assert "fast-router" in summary_called
        # Should have system + summary_block + recent_N
        system_msgs = [m for m in compressed if m["role"] == "system"]
        assert len(system_msgs) >= 2  # original system + summary block

    async def test_compression_failure_returns_full_history(self):
        from app.llm.providers.resiliency_provider import ResiliencyProvider
        provider = ResiliencyProvider.__new__(ResiliencyProvider)
        provider._compression_threshold = 4

        async def always_fail(model, messages, **kwargs):
            raise Exception("fast-router also failed")

        provider._acompletion = always_fail
        messages = self._make_convo(n_turns=4)
        compressed = await provider._maybe_compress_history(messages)
        # Must return original messages if compression fails (non-fatal)
        assert compressed == messages


# ---------------------------------------------------------------------------
# 5. Jitter heuristic
# ---------------------------------------------------------------------------

class TestJitterHeuristic:
    def test_no_jitter_with_assistant_in_recent_messages(self):
        from app.llm.providers.resiliency_provider import _should_add_jitter
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        assert _should_add_jitter(messages) is False

    def test_jitter_without_recent_assistant(self):
        from app.llm.providers.resiliency_provider import _should_add_jitter
        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ]
        assert _should_add_jitter(messages) is True

    def test_no_jitter_on_single_message(self):
        from app.llm.providers.resiliency_provider import _should_add_jitter
        assert _should_add_jitter([{"role": "user", "content": "hi"}]) is False
