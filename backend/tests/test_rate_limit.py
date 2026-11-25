"""Tests for the in-process sliding-window rate limiter (app/core/rate_limit.py)."""
import pytest
from fastapi import Request
from unittest.mock import patch

from starlette.testclient import TestClient

from app.core import rate_limit
from app.core.rate_limit import check, client_ip, reset_all, rate_limit_dependency


def test_client_ip_uses_request_client_host():
    # Real starlette Request with a populated client
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("203.0.113.9", 5555),
    }
    req = Request(scope)
    assert client_ip(req) == "203.0.113.9"


def test_client_ip_falls_back_to_unknown(monkeypatch):
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "client": None}
    req = Request(scope)
    assert client_ip(req) == "unknown"


def test_check_allows_requests_under_limit_and_blocks_over():
    reset_all()
    key = ("1.2.3.4", "test_bucket")
    for _ in range(5):
        assert check(key, limit=5, window_seconds=60) is True
    # 6th hit inside the window is over the limit
    assert check(key, limit=5, window_seconds=60) is False
    reset_all()


def test_check_keys_are_isolated_per_ip_and_bucket():
    reset_all()
    for _ in range(3):
        assert check(("1.2.3.4", "login"), limit=3, window_seconds=60) is True
    assert check(("1.2.3.4", "login"), limit=3, window_seconds=60) is False
    # different IP / different bucket still allowed
    assert check(("5.6.7.8", "login"), limit=3, window_seconds=60) is True
    assert check(("1.2.3.4", "register"), limit=3, window_seconds=60) is True
    reset_all()


def test_check_window_slides():
    """Entries older than the window no longer count against the limit."""
    reset_all()
    key = ("1.2.3.4", "sliding")
    with patch.object(rate_limit.time, "monotonic", return_value=1000.0):
        for _ in range(3):
            assert check(key, limit=3, window_seconds=10) is True
    # 90 seconds later the window has entirely slid past those hits
    with patch.object(rate_limit.time, "monotonic", return_value=1090.0):
        assert check(key, limit=3, window_seconds=10) is True
    reset_all()


def test_reset_all_clears_state():
    reset_all()
    key = ("1.2.3.4", "resetme")
    assert check(key, limit=1, window_seconds=60) is True
    assert check(key, limit=1, window_seconds=60) is False
    reset_all()
    assert check(key, limit=1, window_seconds=60) is True
    reset_all()


def test_rate_limit_dependency_returns_429_with_retry_after():
    """
    Wire the real dependency factory into a throwaway FastAPI app with a low
    limit so the HTTP layer (status code, detail, Retry-After header) is
    exercised without depending on module-level endpoint constants.
    """
    from fastapi import Depends, FastAPI

    reset_all()
    app = FastAPI()
    dependency = rate_limit_dependency(limit=3, window_seconds=60, bucket="test_http")

    @app.get("/ping", dependencies=[Depends(dependency)])
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    for _ in range(3):
        assert client.get("/ping", headers={"x-test-ip": "1"}).status_code == 200
    response = client.get("/ping")
    assert response.status_code == 429
    assert response.json()["detail"] == rate_limit.TOO_MANY_REQUESTS_DETAIL
    assert response.headers["Retry-After"] == "60"
    reset_all()
