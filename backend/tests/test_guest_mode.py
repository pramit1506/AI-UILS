"""Guest-mode tests: unauthenticated chat must be allowed, ephemeral, and
log saving must be refused with a login wall."""
import sys
import os
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.rate_limit import reset_all
from app.tools.save_log import SaveLogTool
from app.tools.context import ToolExecutionContext
from loguru import logger
from app.core.config import settings


@pytest.mark.asyncio
async def test_signed_in_chat_scopes_prompt_memory_and_preserves_log_conversation_id(monkeypatch):
    from unittest.mock import AsyncMock
    from app.api.v1.endpoints import chat
    from app.models.user import User
    from app.schemas.chat import ChatRequest
    from app.schemas.memory import ConversationMetadata

    owner = User(id=uuid.uuid4())
    conversation_id = str(uuid.uuid4())
    memory_key = f"user:{owner.id}:{conversation_id}"
    graph = AsyncMock()
    graph.ainvoke.return_value = {"llm_response": "Accepted"}
    read_metadata = AsyncMock(return_value=ConversationMetadata())
    monkeypatch.setattr(chat.conversation_memory_service, "get_metadata", read_metadata)

    response = await chat.chat_endpoint(
        ChatRequest(user_message="Keep this note", conversation_id=conversation_id),
        graph=graph, guest_graph=AsyncMock(), db=None, current_user=owner,
    )

    state = graph.ainvoke.await_args.args[0]
    config = graph.ainvoke.await_args.kwargs["config"]["configurable"]
    assert state["conversation_id"] == config["thread_id"] == memory_key
    read_metadata.assert_awaited_once_with(memory_key)
    assert config["tool_context"].conversation_id == conversation_id
    assert response.data.conversation_id == conversation_id


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_all()
    yield
    reset_all()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.asyncio
async def test_save_log_tool_refuses_guest_with_login_wall():
    """A guest with real extracted data must get the login wall — not a silent
    failure — describing that drafts are discarded without an account."""
    tool = SaveLogTool()
    context = ToolExecutionContext(
        db=None,
        request_id="guest-req",
        conversation_id="guest-conv",
        logger=logger,
        settings=settings,
        current_user=None,
        llm_provider=None,
    )

    result = await tool.execute(
        context,
        schema_name="Invoice",
        domain="Finance",
        fields={"invoice_number": "INV-1", "total_amount": "$10.00"},
        field_metadata={},
    )

    assert result["status"] == "error"
    assert result.get("login_required") is True
    assert "Login required" in result["message"]
    assert "discarded" in result["message"]


def test_guest_chat_no_auth_required(client):
    """The chat endpoint is now reachable WITHOUT credentials (guest mode);
    a signed-out client must not get 401/403."""
    cid = str(uuid.uuid4())
    response = client.post(
        "/api/v1/chat/",
        json={
            "user_message": "Hello, testing guest access.",
            "conversation_id": cid,
            "message_history": [],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True

    # The response must carry the client's unprefixed conversation id back —
    # the server-side guest namespace ("guest:<id>") never leaks.
    assert body["data"]["conversation_id"] == cid


@pytest.mark.asyncio
async def test_guest_conversation_memory_is_namespaced(client):
    """Guest conversation memory is keyed under a 'guest:'-prefixed work id,
    so it can never collide with (or leak into) a signed-in user's memory."""
    from app.repositories.conversation_repository import conversation_repository

    cid = str(uuid.uuid4())
    client.post(
        "/api/v1/chat/",
        json={
            "user_message": "Store the passcode Kestrel-9.",
            "conversation_id": cid,
            "message_history": [],
        },
    )

    guest_messages = await conversation_repository.get_messages(f"guest:{cid}")
    assert any("Kestrel-9" in m.content for m in guest_messages), (
        "Guest messages should be stored under the 'guest:'-prefixed key"
    )

    # The unprefixed id must NOT contain anything — a signed-in user holding
    # the same unprefixed conversation id would otherwise see this guest chat.
    user_messages = await conversation_repository.get_messages(cid)
    assert all("Kestrel-9" not in m.content for m in user_messages)
