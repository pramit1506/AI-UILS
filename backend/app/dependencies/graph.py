from pathlib import Path

from langgraph.graph.state import CompiledStateGraph

from app.graph.builder import build_graph
from app.core.config import settings

# Persistent SQLite checkpointer (langgraph-checkpoint-sqlite). Import is
# guarded so the application still starts — degrading to the in-memory
# MemorySaver — in environments where the optional package is not installed
# (e.g. running with the wrong virtualenv).
try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    import aiosqlite
    _SQLITE_CHECKPOINTER_AVAILABLE = True
except ImportError:  # pragma: no cover — depends on environment
    AsyncSqliteSaver = None  # type: ignore[assignment]
    aiosqlite = None  # type: ignore[assignment]
    _SQLITE_CHECKPOINTER_AVAILABLE = False

from loguru import logger

# Cached (graph, saver, connection) singleton, created lazily on first
# request so the aiosqlite connection is opened inside the running event loop.
_graph_state: tuple[CompiledStateGraph, object, object] | None = None


async def get_graph() -> CompiledStateGraph:
    """Dependency to provide the compiled LangGraph instance backed by a
    persistent SQLite checkpointer (survives application restarts).

    Falls back to the in-memory checkpointer when langgraph-checkpoint-sqlite
    is not installed in the active environment."""
    global _graph_state
    if _graph_state is None:
        if _SQLITE_CHECKPOINTER_AVAILABLE:
            db_path = Path(settings.CHECKPOINTER_DB_PATH)
            # Ensure the parent directory exists before opening the connection.
            db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = await aiosqlite.connect(str(db_path))
            saver = AsyncSqliteSaver(connection)
            await saver.setup()
            graph = build_graph(checkpointer=saver)
            _graph_state = (graph, saver, connection)
        else:
            logger.warning(
                "langgraph-checkpoint-sqlite is not installed — falling back to the "
                "IN-MEMORY checkpointer (conversation state will be lost on restart). "
                "Install it with: pip install langgraph-checkpoint-sqlite aiosqlite"
            )
            graph = build_graph()  # MemorySaver fallback inside builder
            _graph_state = (graph, None, None)
    return _graph_state[0]


# Cached ephemeral graph for GUEST (unauthenticated) sessions. Guests may chat
# and draft freely, but everything must evaporate when they leave: this graph
# uses the in-process MemorySaver — thread state lives only in RAM, never on
# disk — while conversations/messages go through the LRU-limited in-memory
# conversation repository. Neither store survives a process restart, which is
# exactly the "guests lose all their logged info" behaviour.
_guest_graph: CompiledStateGraph | None = None


async def get_guest_graph() -> CompiledStateGraph:
    """Dependency providing the MemorySaver-backed (ephemeral) graph instance
    used for unauthenticated guest conversations."""
    global _guest_graph
    if _guest_graph is None:
        # build_graph() with no checkpointer falls back to MemorySaver inside
        # the builder — per-process RAM only, bounded and session-scoped.
        _guest_graph = build_graph()
    return _guest_graph


async def shutdown_graph() -> None:
    """Close the cached checkpointer connection and clear the cache.
    Intended to be called from the application lifespan on shutdown."""
    global _graph_state
    if _graph_state is not None:
        _, _, connection = _graph_state
        _graph_state = None
        if connection is not None:
            await connection.close()
