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
    stored_user = User(
        id=user_id,
        email="jane.smith@pharma-qms.io",
        username="dr_smith",
        full_name="Dr. Jane Smith",
        hashed_password=get_password_hash("old_password"),
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

    with patch("app.services.auth_service.user_repository.get_by_login", new_callable=AsyncMock) as mock_get_login, \
         patch("app.services.auth_service.user_repository.update_password", new_callable=AsyncMock) as mock_update_pw:
        
        mock_get_login.return_value = stored_user
        mock_update_pw.return_value = updated_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/reset-password", json={
                "login": "jane.smith@pharma-qms.io",
                "new_password": "new_secure_pass123"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["access_token"] is not None
        assert data["data"]["user"]["email"] == "jane.smith@pharma-qms.io"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reset_password_user_not_found():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    with patch("app.services.auth_service.user_repository.get_by_login", new_callable=AsyncMock) as mock_get_login:
        mock_get_login.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/reset-password", json={
                "login": "nonexistent@user.com",
                "new_password": "new_secure_pass123"
            })

        assert response.status_code == 404

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
async def test_delete_account_by_email_recovery():
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    user_id = uuid.uuid4()
    target_user = User(
        id=user_id,
        email="jane.smith@pharma-qms.io",
        username="dr_smith",
        role="user",
        is_active=True,
    )

    with patch("app.services.auth_service.user_repository.get_by_email", new_callable=AsyncMock) as mock_get_email, \
         patch("app.services.auth_service.user_repository.delete_user", new_callable=AsyncMock) as mock_delete:
        
        mock_get_email.return_value = target_user
        mock_delete.return_value = target_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/auth/delete-account", json={
                "email": "jane.smith@pharma-qms.io",
                "confirm_text": "DELETE"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True
        mock_delete.assert_awaited_once()

    app.dependency_overrides.clear()
