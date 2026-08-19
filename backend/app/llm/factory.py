from app.llm.base import BaseLLMProvider
from app.core.config import settings


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to get the configured LLM provider.

    Controlled by the LLM_PROVIDER environment variable:
      - "multi"  (recommended) — LiteLLM Router with automatic failover across
                                  Groq, Cerebras, Gemini, and OpenRouter. Cycles
                                  through all configured numbered API keys on
                                  429/5xx before surfacing an error. Set at least
                                  one key per provider in .env:
                                    GROQ_API_KEY_1, CEREBRAS_API_KEY_1, etc.
      - "groq"   (default)     — Single-provider cloud inference via Groq API.
                                  Requires GROQ_API_KEY.
      - "ollama"               — Fully local inference via Ollama. Requires Ollama
                                  to be running locally (`ollama serve`). Set
                                  OLLAMA_BASE_URL and OLLAMA_MODEL in .env.

    Example .env entries for multi-provider failover mode:
        LLM_PROVIDER=multi
        GROQ_API_KEY_1=gsk_...
        GROQ_API_KEY_2=gsk_...
        CEREBRAS_API_KEY_1=csk-...
        GEMINI_API_KEY_1=AIza...
        OPENROUTER_API_KEY_1=sk-or-...

    Example .env entries for local/private mode:
        LLM_PROVIDER=ollama
        OLLAMA_BASE_URL=http://localhost:11434
        OLLAMA_MODEL=llama3
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
