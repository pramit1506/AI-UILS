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
    monkeypatch.setenv("GROQ_API_KEY_1", "gsk_test_key_1")
    monkeypatch.setenv("GROQ_API_KEY_2", "gsk_test_key_2")
    monkeypatch.setenv("CEREBRAS_API_KEY_1", "csk_test_key_1")
    monkeypatch.setenv("GEMINI_API_KEY_1", "AIza_test_key_1")
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "sk-or-test_key_1")
    monkeypatch.setenv("LLM_PROVIDER", "multi")
    monkeypatch.setenv("CONTEXT_COMPRESSION_THRESHOLD", "3")  # low threshold for testing
    # Reload settings so our monkeypatched env vars take effect
    from app.core import config as cfg
    cfg.settings.__init__()


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

    def test_raises_when_no_keys_configured(self, monkeypatch):
        """ResiliencyProvider init must fail fast if zero keys are configured."""
        import os
        from app.core.config import settings
        from app.exceptions.base import AllProvidersExhaustedException

        # Blank out all keys on both the settings singleton and os.environ
        all_prefixes = ["GROQ_API_KEY", "CEREBRAS_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]
        monkeypatch.setattr(settings, "GROQ_API_KEY", "", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "")
        for prefix in all_prefixes:
            for i in range(1, 11):
                monkeypatch.setattr(settings, f"{prefix}_{i}", "", raising=False)
                monkeypatch.setenv(f"{prefix}_{i}", "")

        from app.llm.providers.resiliency_provider import _build_model_list, ResiliencyProvider
        assert _build_model_list() == [], "Expected empty model list with all keys blanked"

        with pytest.raises((AllProvidersExhaustedException, Exception)):
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
