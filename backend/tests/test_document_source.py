import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import chat
from app.schemas.chat import ChatRequest, DocumentSource
from app.tools.save_log import SaveLogTool


@pytest.mark.parametrize(("message", "inline"), [
    ("Process this uploaded document (report.txt):\n\nUnextracted clause", None),
    ("Unextracted clause", None),
    ("Save the log", "Unextracted clause"),
])
async def test_chat_preserves_source_supplied_by_editor(monkeypatch, message, inline):
    owner = SimpleNamespace(id=uuid.uuid4())
    created = AsyncMock(return_value=SimpleNamespace(
        id=uuid.uuid4(), log_reference="LOG-TEST", schema_name="Report",
    ))
    monkeypatch.setattr("app.tools.save_log.log_record_repository.create", created)
    graph = AsyncMock()

    async def invoke(state, config):
        assert "source_document" not in state
        result = await SaveLogTool().execute(
            config["configurable"]["tool_context"], schema_name="Report", fields={"kind": "inspection", "guess": "incorrect"}, field_metadata={"guess": {"confidence": 0.2}},
        )
        return {**state, "tool_result": result, "selected_tool": "save_log", "llm_response": "Saved"}

    graph.ainvoke.side_effect = invoke
    await chat.chat_endpoint(
        ChatRequest(user_message=message, expected_user_id=owner.id, excluded_fields={"guess"},
                    source_document=DocumentSource(filename="report.txt", text=inline)),
        graph=graph, guest_graph=AsyncMock(), db=None, current_user=owner,
    )
    saved = created.await_args.kwargs["obj_in"]
    assert saved.source_text == "Unextracted clause"
    assert saved.source_filename == "report.txt"
    assert saved.user_id == owner.id
    assert saved.field_metadata == {}
    assert saved.data == {"kind": "inspection"}


async def test_account_change_stops_chat_before_processing():
    graph = AsyncMock()
    with pytest.raises(HTTPException) as error:
        await chat.chat_endpoint(
            ChatRequest(user_message="Save", expected_user_id=uuid.uuid4()),
            graph=graph, guest_graph=graph, db=None,
            current_user=SimpleNamespace(id=uuid.uuid4()),
        )
    assert error.value.status_code == 409
    graph.ainvoke.assert_not_awaited()
