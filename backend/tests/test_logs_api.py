import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies.db import get_db_session
from app.models.log_record import LogRecord


@pytest.mark.asyncio
async def test_delete_log_success():
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
async def test_delete_log_not_found():
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
