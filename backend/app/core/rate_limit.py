"""
In-process, sliding-window rate limiting for auth endpoints.

No external dependency (no Redis): each (client_ip, bucket) pair keeps a
deque of recent hit timestamps guarded by a threading.Lock — safe for
Starlette's thread-pooled sync paths and the asyncio event loop alike.

State is per-process and best-effort: a restart resets the counters and a
multi-worker deployment (uvicorn --workers N) enforces N independent windows.
That trade-off is acceptable for this single-process deployment.

Limits below are intentionally GENEROUS — chosen well above what a
legitimate user (and the automated test suite, which replays these
endpoints many times) needs — while still blunting credential stuffing.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

# ── Auth endpoint limits (per client IP; sliding window in seconds) ──────
LOGIN_RATE_LIMIT = 30           # POST /auth/login          → 30 per minute
REGISTER_RATE_LIMIT = 10        # POST /auth/register       → 10 per minute
RESET_PASSWORD_RATE_LIMIT = 10  # POST /auth/reset-password → 10 per minute
RATE_LIMIT_WINDOW_SECONDS = 60

TOO_MANY_REQUESTS_DETAIL = "Too many requests. Please try again shortly."

TOO_MANY_REQUESTS_STATUS = status.HTTP_429_TOO_MANY_REQUESTS

_lock = threading.Lock()

# (client_ip, bucket) -> deque[monotonic timestamps of allowed hits]
_hits: defaultdict = defaultdict(deque)


def client_ip(request: Request) -> str:
    """Best-effort client IP; ASGI TestClients / proxies may not set client."""
    if request.client is None or not request.client.host:
        return "unknown"
    return request.client.host


def check(key: tuple, limit: int, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS) -> bool:
    """
    Register a hit for `key` under a sliding window of `window_seconds`.
    Returns True (allowed) or False (over the limit — hit NOT consumed).
    """
    now = time.monotonic()
    with _lock:
        hits = _hits[key]
        cutoff = now - window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


def reset_all() -> None:
    """Clear all rate-limit state (used by tests to isolate scenarios)."""
    with _lock:
        _hits.clear()


def rate_limit_dependency(limit: int, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS, bucket: str = "auth"):
    """
    FastAPI dependency factory: raises HTTP 429 with a Retry-After header
    when the calling client IP exceeds `limit` hits per sliding window.
    Endpoint-scoped only (applied via route dependencies) — deliberately
    NOT a global middleware so chat/log endpoints stay unaffected.
    """

    async def _enforce(request: Request) -> None:
        allowed = check((client_ip(request), bucket), limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=TOO_MANY_REQUESTS_STATUS,
                detail=TOO_MANY_REQUESTS_DETAIL,
                headers={"Retry-After": str(window_seconds)},
            )

    return _enforce
