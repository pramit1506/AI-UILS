import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies.db import get_db_session
from app.models.user import User
from app.models.log_record import LogRecord
from app.core.security import get_password_hash, create_access_token
from app.core.config import settings


@pytest.mark.asyncio
async def test_auth_lookup_reads_only_user_table():
    from sqlalchemy import event, inspect
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from app.repositories.user_repository import user_repository

    engine = create_async_engine("sqlite+aiosqlite://")
    user_id = uuid.uuid4()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(User.__table__.create)
            await connection.execute(User.__table__.insert().values(
                id=user_id, email="owner@example.com", username="owner", hashed_password="unused"
            ))

        statements = []

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def capture_query(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        async with AsyncSession(engine) as session:
            user = await user_repository.get_by_id(session, user_id)
            assert user.username == "owner"
            assert "logs" in inspect(user).unloaded
        assert len(statements) == 1
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
def patch_test_settings(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "test_secret_key_minimum_32_bytes_long_for_jwt_test")


@pytest.mark.asyncio
async def test_register_user_success():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    mock_created_user = User(
        id=uuid.uuid4(),
        email="doctor@hospital.org",
        username="dr_smith",
        full_name="Dr. Jane Smith",
        hashed_password=get_password_hash("securepass123"),
        role="user",
        bio="Cardiologist",
        is_active=True,
    )

    with patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.get_by_username", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.auth_service.user_repository.create_user", new_callable=AsyncMock) as mock_create:
        
        mock_get_email.return_value = None
        mock_get_user.return_value = None
        mock_create.return_value = mock_created_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/register", json={
                "email": "doctor@hospital.org",
                "username": "dr_smith",
                "password": "securepass123",
                "full_name": "Dr. Jane Smith",
                "bio": "Cardiologist"
            })

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None
        assert data["data"]["user"]["username"] == "dr_smith"
        assert data["data"]["user"]["email"] == "doctor@hospital.org"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_duplicate_email():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    with patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email:
        mock_get_email.return_value = MagicMock(spec=User)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/register", json={
                "email": "existing@hospital.org",
                "username": "new_user",
                "password": "securepass123"
            })

        assert response.status_code == 400
        res_json = response.json()
        detail_msg = res_json.get("detail", "") or res_json.get("message", "")
        assert "already exists" in detail_msg

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_success():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    stored_user = User(
        id=uuid.uuid4(),
        email="doctor@hospital.org",
        username="dr_smith",
        full_name="Dr. Jane Smith",
        hashed_password=get_password_hash("securepass123"),
        role="user",
        is_active=True,
    )

    with patch("app.services.auth_service.user_repository.get_by_login", new_callable=AsyncMock) as mock_get_login:
        mock_get_login.return_value = stored_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/login", json={
                "login": "dr_smith",
                "password": "securepass123"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None
        assert data["data"]["user"]["username"] == "dr_smith"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_invalid_password():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    stored_user = User(
        id=uuid.uuid4(),
        email="doctor@hospital.org",
        username="dr_smith",
        hashed_password=get_password_hash("correct_password"),
        role="user",
        is_active=True,
    )

    with patch("app.services.auth_service.user_repository.get_by_login", new_callable=AsyncMock) as mock_get_login:
        mock_get_login.return_value = stored_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/login", json={
                "login": "dr_smith",
                "password": "wrong_password"
            })

        assert response.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_current_user_profile_me():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="alice@company.com",
        username="alice_w",
        full_name="Alice Walker",
        hashed_password="hash",
        role="admin",
        bio="Lead Auditor",
        is_active=True,
    )
    token = create_access_token(subject=str(user_id))

    with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_by_id:
        mock_get_by_id.return_value = mock_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["username"] == "alice_w"
        assert data["data"]["role"] == "admin"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_profile():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="alice@company.com",
        username="alice_w",
        full_name="Alice Walker",
        hashed_password="hash",
        role="user",
        bio="Junior Auditor",
        is_active=True,
    )
    updated_user = User(
        id=user_id,
        email="alice@company.com",
        username="alice_w",
        full_name="Alice Walker-Smith",
        hashed_password="hash",
        role="user",
        bio="Senior Lead Auditor",
        is_active=True,
    )
    token = create_access_token(subject=str(user_id))

    with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_by_id, \
         patch("app.services.auth_service.user_repository.update", new_callable=AsyncMock) as mock_update:
        
        mock_get_by_id.return_value = mock_user
        mock_update.return_value = updated_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/auth/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"full_name": "Alice Walker-Smith", "bio": "Senior Lead Auditor"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["full_name"] == "Alice Walker-Smith"
        assert data["data"]["bio"] == "Senior Lead Auditor"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_logs_isolation():
    """Verify that when User A requests logs, User A's user_id is used for filtering."""
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_a_id = uuid.uuid4()
    user_a = User(
        id=user_a_id,
        email="usera@corp.com",
        username="user_a",
        hashed_password="hash",
        role="user",
        is_active=True,
    )
    token_a = create_access_token(subject=str(user_a_id))

    mock_log = MagicMock(spec=LogRecord)
    mock_log.id = uuid.uuid4()
    mock_log.log_reference = "LOG-USERA12"
    mock_log.schema_name = "Invoice"
    mock_log.domain = "Finance"
    mock_log.data = {"amount": 1000}
    mock_log.summary = "Invoice for Vendor"
    mock_log.source = "pdf"
    mock_log.source_filename = None
    mock_log.has_source_text = False
    mock_log.conversation_id = "conv-1"
    mock_log.user_id = user_a_id
    mock_log.requires_review = False
    mock_log.overall_confidence = 0.95
    mock_log.created_at = None
    mock_log.updated_at = None

    with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_user, \
         patch("app.api.v1.endpoints.logs.log_record_repository.get_all", new_callable=AsyncMock) as mock_get_all:
        
        mock_get_user.return_value = user_a
        mock_get_all.return_value = [mock_log]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/logs/",
                headers={"Authorization": f"Bearer {token_a}"}
            )

        assert response.status_code == 200
        mock_get_all.assert_awaited_once()
        call_kwargs = mock_get_all.call_args.kwargs
        assert call_kwargs.get("user_id") == user_a_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_success():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_id = uuid.uuid4()
    current_password = "old_password"
    stored_user = User(
        id=user_id,
        email="jane.smith@pharma-qms.io",
        username="dr_smith",
        full_name="Dr. Jane Smith",
        hashed_password=get_password_hash(current_password),
        role="user",
        is_active=True,
    )
    updated_user = User(
        id=user_id,
        email="jane.smith@pharma-qms.io",
        username="dr_smith",
        full_name="Dr. Jane Smith",
        hashed_password=get_password_hash("new_secure_pass123"),
        role="user",
        is_active=True,
    )
    token = create_access_token(subject=str(user_id))

    with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_by_id, \
         patch("app.services.auth_service.user_repository.update_password", new_callable=AsyncMock) as mock_update_pw:

        mock_get_by_id.return_value = stored_user
        mock_update_pw.return_value = updated_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/reset-password", headers={
                "Authorization": f"Bearer {token}"
            }, json={
                "current_password": current_password,
                "new_password": "new_secure_pass123"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None
        assert data["data"]["user"]["email"] == "jane.smith@pharma-qms.io"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_requires_authentication():
    """The old unauthenticated flow (login identifier + new password) was an
    account-takeover vector — without a token the request must be rejected."""
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/reset-password", json={
            "current_password": "whatever",
            "new_password": "new_secure_pass123"
        })

    assert response.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_rejects_wrong_current_password():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_id = uuid.uuid4()
    stored_user = User(
        id=user_id,
        email="jane.smith@pharma-qms.io",
        username="dr_smith",
        hashed_password=get_password_hash("actual_current_password"),
        role="user",
        is_active=True,
    )
    token = create_access_token(subject=str(user_id))

    with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_by_id, \
         patch("app.services.auth_service.user_repository.update_password", new_callable=AsyncMock) as mock_update_pw:

        mock_get_by_id.return_value = stored_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/reset-password", headers={
                "Authorization": f"Bearer {token}"
            }, json={
                "current_password": "wrong_current_password",
                "new_password": "new_secure_pass123"
            })

        assert response.status_code == 401
        mock_update_pw.assert_not_awaited()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_account_authenticated():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_id = uuid.uuid4()
    current_user = User(
        id=user_id,
        email="user_to_delete@example.com",
        username="user_delete",
        role="user",
        is_active=True,
    )
    token = create_access_token(subject=str(user_id))

    with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_by_id, \
         patch("app.services.auth_service.user_repository.delete_user", new_callable=AsyncMock) as mock_delete:
        
        mock_get_by_id.return_value = current_user
        mock_delete.return_value = current_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                "/api/v1/auth/account",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True
        mock_delete.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_account_by_email_removed():
    """The unauthenticated delete-by-email recovery endpoint was removed — it
    allowed anyone to destroy any account (and all its logs) with one request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/delete-account", json={
            "email": "victim@example.com",
        })

    assert response.status_code in (404, 405)


@pytest.mark.asyncio
async def test_register_role_escalation_ignored():
    """Client-supplied roles must not be persisted — nobody can register as admin."""
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    created_kwargs: dict = {}

    async def fake_create_user(db, **kwargs):
        created_kwargs.update(kwargs)
        return User(
            id=uuid.uuid4(),
            email="attacker@corp.com",
            username="attacker",
            hashed_password=get_password_hash("securepass123"),
            role=kwargs.get("role", "user"),
            is_active=True,
        )

    with patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.get_by_username", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.auth_service.user_repository.create_user", side_effect=fake_create_user):

        mock_get_email.return_value = None
        mock_get_user.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/register", json={
                "email": "attacker@corp.com",
                "username": "attacker",
                "password": "securepass123",
                "role": "admin",
            })

        assert response.status_code == 201
        assert created_kwargs.get("role") == "user"
        data = response.json()
        assert data["data"]["user"]["role"] == "user"

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Cookie transport (httpOnly uils_access) + CSRF double-submit (new)
# ═══════════════════════════════════════════════════════════════════════════

from app.core import rate_limit  # noqa: E402


@pytest.fixture
def cookie_env(monkeypatch):
    """
    Isolated environment for cookie tests:
    - DEBUG=True → Secure flag off so httpx (base_url http://test) stores
      and re-sends the cookies on subsequent requests.
    - Rate-limit counters cleared so cookie tests start from a clean window.
    """
    monkeypatch.setattr(settings, "DEBUG", True)
    rate_limit.reset_all()
    yield


async def _register_browser_logged_in(client):
    """
    Mock-backed register (same pattern as the tests above) that yields the
    built user + access token; the real endpoint also sets the auth cookies
    into the client's cookie jar.
    """
    mock_created_user = User(
        id=uuid.uuid4(),
        email="cookie@hospital.org",
        username="cookie_user",
        full_name="Cookie User",
        hashed_password=get_password_hash("securepass123"),
        role="user",
        is_active=True,
    )
    with patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.get_by_username", new_callable=AsyncMock) as mock_get_user, \
         patch("app.services.auth_service.user_repository.create_user", new_callable=AsyncMock) as mock_create:

        mock_get_email.return_value = None
        mock_get_user.return_value = None
        mock_create.return_value = mock_created_user

        response = await client.post("/api/v1/auth/register", json={
            "email": "cookie@hospital.org",
            "username": "cookie_user",
            "password": "securepass123",
            "full_name": "Cookie User",
        })

    assert response.status_code == 201, response.json()
    data = response.json()
    return mock_created_user, data["data"]["access_token"]


@pytest.mark.asyncio
async def test_login_sets_httponly_access_cookie_and_readable_csrf_cookie(cookie_env):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    stored_user = User(
        id=uuid.uuid4(),
        email="doctor@hospital.org",
        username="dr_smith",
        hashed_password=get_password_hash("securepass123"),
        role="user",
        is_active=True,
    )

    with patch("app.services.auth_service.user_repository.get_by_login", new_callable=AsyncMock) as mock_get_login:
        mock_get_login.return_value = stored_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/login", json={
                "login": "dr_smith",
                "password": "securepass123"
            })

        assert response.status_code == 200
        token = response.json()["data"]["access_token"]

        set_cookies = response.headers.get_list("set-cookie")
        access_line = next(h for h in set_cookies if h.startswith("uils_access="))
        csrf_line = next(h for h in set_cookies if h.startswith("uils_csrf="))
        lower_access = access_line.lower()
        lower_csrf = csrf_line.lower()

        assert "httponly" in lower_access          # access cookie is httpOnly
        assert "httponly" not in lower_csrf        # CSRF cookie must be JS-readable
        assert "samesite=lax" in lower_access
        assert "samesite=lax" in lower_csrf
        assert "max-age=86400" in lower_access
        assert "max-age=86400" in lower_csrf

        # Cookie jar holds both, and the access cookie carries the real JWT
        assert client.cookies["uils_access"] == token
        assert client.cookies["uils_csrf"]  # non-empty random value

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cookie_auth_with_correct_csrf_header_succeeds(cookie_env):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, _token = await _register_browser_logged_in(client)
        csrf_token = client.cookies["uils_csrf"]
        assert csrf_token

        mock_user = User(
            id=uuid.uuid4(),
            email="cookie@hospital.org",
            username="cookie_user",
            hashed_password="hash",
            role="user",
            is_active=True,
        )
        mock_updated = User(
            id=mock_user.id,
            email="cookie@hospital.org",
            username="cookie_user",
            full_name="Cookie Renamed",
            hashed_password="hash",
            role="user",
            is_active=True,
        )
        with patch("app.dependencies.auth.user_repository.get_by_id", new_callable=AsyncMock) as mock_get_by_id, \
             patch("app.services.auth_service.user_repository.update", new_callable=AsyncMock) as mock_update:
            mock_get_by_id.return_value = mock_user
            mock_update.return_value = mock_updated

            response = await client.put(
                "/api/v1/auth/profile",
                # NOTE: no Authorization header — authenticated purely via cookie
                headers={"x-csrf-token": csrf_token},
                json={"full_name": "Cookie Renamed"},
            )

        assert response.status_code == 200, response.json()
        assert response.json()["data"]["full_name"] == "Cookie Renamed"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cookie_auth_without_csrf_header_gets_403(cookie_env):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register_browser_logged_in(client)

        response = await client.put(
            "/api/v1/auth/profile",
            headers={},  # NO x-csrf-token header
            json={"full_name": "Attacker Rename"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "CSRF check failed"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cookie_auth_with_wrong_csrf_header_gets_403(cookie_env):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register_browser_logged_in(client)

        response = await client.put(
            "/api/v1/auth/profile",
            headers={"x-csrf-token": "forged-or-mismatched-token"},
            json={"full_name": "Attacker Rename"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "CSRF check failed"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_logout_clears_both_cookies(cookie_env):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    stored_user = User(
        id=uuid.uuid4(),
        email="doctor@hospital.org",
        username="dr_smith",
        hashed_password=get_password_hash("securepass123"),
        role="user",
        is_active=True,
    )

    with patch("app.services.auth_service.user_repository.get_by_login", new_callable=AsyncMock) as mock_get_login:
        mock_get_login.return_value = stored_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_response = await client.post("/api/v1/auth/login", json={
                "login": "dr_smith",
                "password": "securepass123"
            })
            assert login_response.status_code == 200
            assert "uils_access" in client.cookies
            assert "uils_csrf" in client.cookies

            response = await client.post(
                "/api/v1/auth/logout",
                headers={"x-csrf-token": client.cookies["uils_csrf"]},
            )

        assert response.status_code == 200

        set_cookies = response.headers.get_list("set-cookie")
        access_line = next(h for h in set_cookies if h.startswith("uils_access="))
        csrf_line = next(h for h in set_cookies if h.startswith("uils_csrf="))
        # Both cookies must be expired/blanked by the server
        assert "max-age=0" in access_line.lower()
        assert "max-age=0" in csrf_line.lower()

    app.dependency_overrides.clear()
