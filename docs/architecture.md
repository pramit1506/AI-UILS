# Architecture

The React frontend uses a same-origin API proxy through Vite in development or Nginx in Docker Compose. FastAPI handles authentication, document intake, conversation, and owner-scoped record access.

LangGraph runs capture and editing turns. Cloud inference tries OpenRouter, Gemini and Groq Cloud in that order. The application can also use Ollama for local inference. Saved-record search runs in PostgreSQL without making model calls.

PostgreSQL stores users and structured log records. SQLite stores signed-in graph checkpoints. Recovery email uses the SMTP server configured by the operator.

See the [workflow](langgraph.md), [API](api.md), and [database notes](database.md) for details.
