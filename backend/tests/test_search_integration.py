"""Run with SEARCH_TEST_DATABASE_URL pointing at a migrated PostgreSQL test database."""
import os
import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.security import create_access_token
from app.core.config import settings
from app.dependencies.db import get_db_session
from app.dependencies.graph import get_graph
from app.graph.builder import build_graph
from app.main import app
from app.models.log_record import LogRecord
from app.models.user import User


@pytest.mark.skipif(not os.getenv("SEARCH_TEST_DATABASE_URL"), reason="needs migrated PostgreSQL")
async def test_search_and_saved_source_lifecycle(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_OFFLINE_MODE", True)
    engine = create_async_engine(os.environ["SEARCH_TEST_DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            async with AsyncSession(connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                owners = [User(username=uuid.uuid4().hex, email=f"{uuid.uuid4()}@example.org",
                               hashed_password="unused") for _ in range(2)]
                db.add_all(owners)
                await db.flush()
                prefix = uuid.uuid4().hex
                timestamp = datetime.now(timezone.utc)
                refs = [f"LOG-{prefix}-{i}" for i in range(4)]
                for index, ref in enumerate(refs):
                    db.add(LogRecord(user_id=owners[int(index == 3)].id, log_reference=ref,
                                     schema_name="Inspection", data={"asset": {"serial_code": ["ZX", 321]},
                                                                     "notes": "Line 1\nरसीद café"},
                                     summary="Routine visit", source="txt", created_at=timestamp,
                                     source_filename="report-Q4.txt" if index else None,
                                     source_text="Approved exception for ultramarine fittings." if index else None,
                                     requires_review=index == 2))
                await db.flush()

                async def use_test_db():
                    yield db

                app.dependency_overrides[get_db_session] = use_test_db
                test_graph = build_graph()
                app.dependency_overrides[get_graph] = lambda: test_graph
                headers = {"Authorization": "Bearer " + create_access_token(subject=str(owners[0].id))}
                base = "/api/v1/logs"
                try:
                    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as client:
                        async def search(query, **filters):
                            response = await client.get(base + "/search", params={"q": query, **filters})
                            assert response.status_code == 200, response.text
                            return response.json()

                        page = await search("Inspection ZX 321", limit=2)
                        assert len(page["data"]) == 2 and page["next_cursor"]
                        last = await search("Inspection ZX 321", cursor=page["next_cursor"], limit=2)
                        assert last["next_cursor"] is None
                        assert {row["log_reference"] for row in page["data"] + last["data"]} == set(refs[:3])
                        match = await search("Q4 ultramarine", needs_review=True, schema_name="Inspection")
                        assert [row["log_reference"] for row in match["data"]] == [refs[2]]
                        assert "source_text" not in match["data"][0]
                        assert (await search(refs[2]))["data"][0]["log_reference"] == refs[2]
                        source = await client.get(f"{base}/{refs[2]}/source")
                        assert source.json()["data"]["text"].endswith("ultramarine fittings.")
                        international = await search("रसीद café")
                        assert {r["log_reference"] for r in international["data"]} == set(refs[:3])
                        for ref in (refs[0], refs[3]):
                            assert (await client.get(f"{base}/{ref}/source")).status_code == 404
                        assert (await client.get(base + "/search", params={"q": "ZX", "cursor": "invalid"})).status_code == 422
                        assert (await client.get(base + "/search", params={"q": "   "})).status_code == 422
                        edited = await client.patch(f"{base}/{refs[0]}", json={"data": {"replacement_part": "mauve"}})
                        assert edited.status_code == 200, edited.text
                        assert [r["log_reference"] for r in (await search("mauve"))["data"]] == [refs[0]]
                        assert refs[0] not in {r["log_reference"] for r in (await search("321"))["data"]}
                        assert (await client.delete(f"{base}/{refs[2]}")).status_code == 200
                        assert (await client.get(f"{base}/{refs[2]}/source")).status_code == 404
                        assert [r["log_reference"] for r in (await search("ultramarine"))["data"]] == [refs[1]]

                        # Save the reviewed draft via the same chat command used by the editor.
                        chat_url = "/api/v1/chat/"
                        capture = await client.post(chat_url, json={"action": "capture",
                            "user_message": "Please improve the software so that users can recover access using their account email."})
                        assert capture.status_code == 200, capture.text
                        captured = capture.json()["data"]["log_draft"]
                        assert captured["schema_name"] == "Change request"
                        assert captured["fields"]["requested_changes"][0].startswith("Please improve")
                        assert not capture.json()["data"]["clarification_state"]
                        saved = await client.post(chat_url, json={
                            "action": "save_reviewed",
                            "user_message": "Save the log", "expected_user_id": str(owners[0].id),
                            "log_draft": {"schema_name": "Visit", "fields": {"result": "Pass"}},
                            "source_document": {"filename": "visit.txt", "text": "Copper gasket supplied. Medical cardiology automobile bioluminescence."},
                        })
                        assert saved.status_code == 200, saved.text
                        assert saved.json()["data"]["tool_execution_result"]["status"] == "success"
                        hit = (await search("gasket"))["data"]
                        assert len(hit) == 1 and hit[0]["data"] == {"result": "Pass"}
                        for phrase in ("medicine", "cardio", "automob", "car", "bioluminescen"):
                            assert hit[0]["log_reference"] in {r["log_reference"] for r in (await search(phrase))["data"]}
                        assert not (await search("medicine", related="false"))["data"]
                        recalled = await client.post(chat_url, json={"user_message": "find gasket"})
                        assert recalled.status_code == 200, recalled.text
                        assert hit[0]["log_reference"] in recalled.json()["data"]["assistant_message"]
                finally:
                    app.dependency_overrides.pop(get_db_session, None)
                    app.dependency_overrides.pop(get_graph, None)
            await transaction.rollback()
    finally:
        await engine.dispose()
