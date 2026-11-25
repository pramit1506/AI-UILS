import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.builder import build_graph
from app.services.conversation_memory import conversation_memory_service
from app.tools.context import ToolExecutionContext


@pytest.mark.asyncio
@pytest.mark.parametrize("signed_in", [False, True])
async def test_new_chat_can_search_without_a_draft_or_model(signed_in):
    owner = SimpleNamespace(id=uuid.uuid4()) if signed_in else None
    context = ToolExecutionContext(
        request_id="test-search", conversation_id="search", current_user=owner,
        db=AsyncMock(spec=AsyncSession) if signed_in else None,
    )
    record = SimpleNamespace(
        id=uuid.uuid4(), log_reference="LOG-A1", schema_name="Note", domain=None,
        summary=None, source_filename="meeting.txt", data={"name": "Acme"}, created_at=None,
    )
    with (
        patch("app.graph.nodes.get_llm_provider", side_effect=AssertionError("Unexpected LLM call")),
        patch("app.services.conversation_memory.get_llm_provider", side_effect=AssertionError("Unexpected compression")),
        patch("app.tools.search_logs.log_record_repository.search", new_callable=AsyncMock) as search,
    ):
        search.return_value = [record]
        conversation = str(uuid.uuid4())
        metadata = await conversation_memory_service.get_metadata(conversation)
        metadata.message_count = 11
        await conversation_memory_service.save_metadata(conversation, metadata)
        result = await build_graph().ainvoke(
            {"user_message": "Search my documents for Acme", "conversation_id": conversation, "request_id": "test-search"},
            config={"configurable": {"thread_id": "test-search", "tool_context": context}},
        )
        if signed_in:
            search.assert_awaited_once_with(
                context.db, query="Acme", user_id=owner.id, schema_name=None, limit=5, references_only=True,
            )
            assert "LOG-A1" in result["llm_response"]
            assert "meeting.txt" in result["llm_response"]
            assert set(result["tool_result"]["results"][0]) == {"log_reference", "schema_name", "source_filename"}
        else:
            search.assert_not_awaited()
            assert "Sign in" in result["llm_response"]
