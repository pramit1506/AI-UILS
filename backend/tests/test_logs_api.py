import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies.db import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.log_record import LogRecord


@pytest.fixture
def authenticated_user():
    user = User(
        id=uuid.uuid4(),
        email="logowner@example.com",
        username="log_owner",
        hashed_password="hash",
        role="user",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_delete_log_success(authenticated_user):
    mock_log = MagicMock(spec=LogRecord)
    mock_log.log_reference = "LOG-TEST123"
    mock_log.schema_name = "Invoice"

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    with patch("app.api.v1.endpoints.logs.log_record_repository.delete_by_reference", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = mock_log

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/logs/LOG-TEST123")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "LOG-TEST123" in data["message"]
        assert data["data"]["log_reference"] == "LOG-TEST123"
        mock_delete.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_log_requires_authentication():
    """Log endpoints must reject anonymous callers — previously they fell back
    to an unfiltered query that returned/deleted every user's records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/v1/logs/LOG-TEST123")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_log_not_found(authenticated_user):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    with patch("app.api.v1.endpoints.logs.log_record_repository.delete_by_reference", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/logs/LOG-NONEXISTENT")

        assert response.status_code == 404
        mock_delete.assert_awaited_once()

    app.dependency_overrides.clear()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_edit_log_success(authenticated_user):
    """PATCH /logs/{ref} updates field values and returns the full record."""
    mock_log = MagicMock(spec=LogRecord)
    mock_log.log_reference = "LOG-EDIT123"
    mock_log.schema_name = "Invoice"
    mock_log.data = {"invoice_number": "INV-1", "total": "42"}
    updated = MagicMock(spec=LogRecord)
    updated.id = uuid.uuid4()
    updated.log_reference = "LOG-EDIT123"
    updated.schema_name = "Invoice"
    updated.domain = None
    updated.data = {"invoice_number": "INV-2", "total": "42"}
    updated.summary = None
    updated.source = None
    updated.source_filename = None
    updated.has_source_text = False
    updated.conversation_id = None
    updated.user_id = None
    updated.requires_review = False
    updated.overall_confidence = None
    updated.created_at = None
    updated.updated_at = None

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    with patch(
        "app.api.v1.endpoints.logs.log_record_repository.get_by_reference", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_log
        with patch(
            "app.api.v1.endpoints.logs.log_record_repository.update", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = updated

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    "/api/v1/logs/LOG-EDIT123",
                    json={"data": {"invoice_number": "INV-2", "total": "42"}},
                )

            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert body["data"]["data"]["invoice_number"] == "INV-2"
            mock_update.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_edit_log_empty_payload_rejected(authenticated_user):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch("/api/v1/logs/LOG-EDIT123", json={})

    assert response.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_edit_log_not_found(authenticated_user):
    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db

    with patch(
        "app.api.v1.endpoints.logs.log_record_repository.get_by_reference", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch("/api/v1/logs/LOG-MISSING", json={"summary": "x"})

        assert response.status_code == 404

    app.dependency_overrides.clear()
