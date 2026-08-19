from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables.

    Multi-provider failover is enabled by setting LLM_PROVIDER=multi.
    Each provider supports up to 3 numbered API keys (e.g. GROQ_API_KEY_1,
    GROQ_API_KEY_2, GROQ_API_KEY_3). The LiteLLM Router cycles through all
    configured keys automatically on 429/5xx errors — no manual intervention needed.
    """
    PROJECT_NAME: str = "AI-Powered Universal Logging System"
    API_VERSION: str = "v1"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "uils_jwt_default_secret_key_change_in_production_min32bytes"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"

    # ── Core LLM Settings ──────────────────────────────────────────────────────
    DEFAULT_MODEL: str = "qwen/qwen3.6-27b"
    LANGGRAPH_ENABLED: bool = True
    MODEL_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 4096
    DEMO_OFFLINE_MODE: bool = False

    # ── LLM Provider Routing ───────────────────────────────────────────────────
    # Options: "groq" (single key, default), "multi" (failover pool), "ollama" (local)
    LLM_PROVIDER: str = "groq"

    # Ollama (local/private inference — no API key required)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = ""  # Falls back to DEFAULT_MODEL when empty

    # ── Groq API Keys (multi — numbered keys auto-cycled on 429) ──────────────
    # Groq keys
    GROQ_API_KEY: str = ""
    GROQ_API_KEY_1: str = ""
    GROQ_API_KEY_2: str = ""
    GROQ_API_KEY_3: str = ""
    GROQ_API_KEY_4: str = ""
    GROQ_API_KEY_5: str = ""
    GROQ_API_KEY_6: str = ""

    # ── Cerebras API Keys ──────────────────────────────────────────────────────
    CEREBRAS_API_KEY_1: str = ""
    CEREBRAS_API_KEY_2: str = ""
    CEREBRAS_API_KEY_3: str = ""

    # ── Google AI Studio (Gemini) API Keys ────────────────────────────────────
    GEMINI_API_KEY_1: str = ""
    GEMINI_API_KEY_2: str = ""
    GEMINI_API_KEY_3: str = ""

    # ── OpenRouter API Keys ────────────────────────────────────────────────────
    OPENROUTER_API_KEY_1: str = ""
    OPENROUTER_API_KEY_2: str = ""
    OPENROUTER_API_KEY_3: str = ""

    # ── LiteLLM Router Settings (used when LLM_PROVIDER=multi) ────────────────
    # Number of retries across the failover pool before raising an exception
    ROUTER_NUM_RETRIES: int = 3
    # Base delay (seconds) between retries; Router applies jittered exponential backoff
    ROUTER_RETRY_AFTER: float = 1.5
    # Routing strategy: "simple-shuffle" distributes load across healthy endpoints
    ROUTER_STRATEGY: str = "simple-shuffle"

    # ── Context Compression Settings ──────────────────────────────────────────
    CONTEXT_COMPRESSION_THRESHOLD: int = 10  # turns (= 20 messages)
    FAST_ROUTER_MODEL: str = "groq/openai/gpt-oss-20b"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )



settings = Settings()
