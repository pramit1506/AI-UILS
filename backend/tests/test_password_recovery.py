import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.dependencies.db import get_db_session
from app.main import app
from app.models.user import User
from app.services import password_recovery


@pytest.mark.skipif(not os.getenv("SEARCH_TEST_DATABASE_URL"), reason="needs migrated PostgreSQL")
async def test_email_code_recovery(monkeypatch):
    mail = Mock()
    monkeypatch.setattr(password_recovery, "send_code", mail)
    monkeypatch.setattr(settings, "SMTP_HOST", "mail.example.org")
    monkeypatch.setattr(settings, "SMTP_FROM", "recovery@example.org")
    engine = create_async_engine(os.environ["SEARCH_TEST_DATABASE_URL"])
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            async with AsyncSession(conn, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                email = f"{uuid.uuid4().hex}@example.org"
                user = User(email=email, username=uuid.uuid4().hex, hashed_password=get_password_hash("previous-pass"))
                db.add(user)
                await db.commit()
                headers = {"Authorization": "Bearer " + create_access_token(subject=str(user.id))}

                async def session():
                    yield db

                app.dependency_overrides[get_db_session] = session
                try:
                    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1/auth/") as client:
                        unknown = await client.post("recovery/request", json={"email": "unknown@example.org"})
                        known = await client.post("recovery/request", json={"email": email})
                        assert known.status_code == unknown.status_code == 202
                        assert known.json() == unknown.json()
                        mail.assert_called_once()
                        address, code = mail.call_args.args
                        assert address == email and len(code) == 6 and code.isdigit()
                        assert user.recovery_digest != code
                        await client.post("recovery/request", json={"email": email})
                        mail.assert_called_once()
                        payload = {"email": email, "code": code, "new_password": "updated-pass"}
                        invalid = {**payload, "code": "000000" if code != "000000" else "000001"}
                        for _ in range(5):
                            assert (await client.post("recovery/confirm", json=invalid)).status_code == 400
                        assert (await client.post("recovery/confirm", json=payload)).status_code == 400
                        user.recovery_expires = datetime.now(timezone.utc) - timedelta(seconds=1)
                        await db.commit()
                        await client.post("recovery/request", json={"email": email})
                        payload["code"] = mail.call_args.args[1]
                        user.recovery_expires = datetime.now(timezone.utc) - timedelta(seconds=1)
                        await db.commit()
                        assert (await client.post("recovery/confirm", json=payload)).status_code == 400
                        await client.post("recovery/request", json={"email": email})
                        payload["code"] = mail.call_args.args[1]
                        assert (await client.post("recovery/confirm", json=payload)).status_code == 200
                        assert (await client.post("recovery/confirm", json=payload)).status_code == 400
                        assert (await client.get("me", headers=headers)).status_code == 401
                        assert (await client.post("login", json={"login": email, "password": "previous-pass"})).status_code == 401
                        assert (await client.post("login", json={"login": email, "password": "updated-pass"})).status_code == 200
                finally:
                    app.dependency_overrides.pop(get_db_session, None)
            await transaction.rollback()
    finally:
        await engine.dispose()
