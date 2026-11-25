import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.dependencies.graph import get_graph, get_guest_graph
from app.dependencies.db import get_db_session
from app.shared.responses import APIResponse
from app.core.config import settings
from app.core.rate_limit import RATE_LIMIT_WINDOW_SECONDS, rate_limit_dependency
from app.tools.context import ToolExecutionContext
from app.schemas.chat import ChatRequest, ConversationResponse, MAX_SOURCE_CHARACTERS
from app.utils.response_mapper import ConversationResponseMapper
from app.services.conversation_memory import conversation_memory_service

from app.dependencies.auth import get_optional_current_user
from app.models.user import User

router = APIRouter()

# Guests can now chat without an account, so the endpoint needs its own IP
# bucket — previously "chat was auth-protected" made dedicated limiting moot.
CHAT_RATE_LIMIT = 60  # POST /chat → 60 per minute per IP (guests included)
CHAT_PROCESSING_SECONDS = 105

@router.post(
    "/",
    response_model=APIResponse[ConversationResponse],
    dependencies=[Depends(rate_limit_dependency(CHAT_RATE_LIMIT, RATE_LIMIT_WINDOW_SECONDS, "chat"))],
)
async def chat_endpoint(
    request: ChatRequest,
    graph: CompiledStateGraph = Depends(get_graph),
    guest_graph: CompiledStateGraph = Depends(get_guest_graph),
    db: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> APIResponse[ConversationResponse]:
    if request.expected_user_id is not None and (
        current_user is None or current_user.id != request.expected_user_id
    ):
        raise HTTPException(status_code=409, detail="Your signed-in account changed. Reload before continuing.")
    request_id = str(uuid.uuid4())
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Guest mode: unauthenticated visitors can chat and build drafts, but
    # nothing may reach persistence. They run on a MemorySaver-backed graph
    # and a "guest:"-prefixed conversation namespace so their ephemeral
    # state can never collide with (or read into) a signed-in user's
    # conversation memory.
    if current_user is not None:
        # Security: namespace the checkpointer thread by user id so one user can
        # never read or continue another user's conversation by passing its id.
        # Client-side conversation ids remain intact for the frontend, while
        # server-side storage is always scoped per user.
        thread_scope = f"user:{current_user.id}"
        work_conversation_id = f"{thread_scope}:{conversation_id}"
        graph_to_use = graph
    else:
        thread_scope = f"guest:{conversation_id}"
        work_conversation_id = f"guest:{conversation_id}"
        graph_to_use = guest_graph

    input_state = {
        "action": request.action,
        "conversation_id": work_conversation_id,
        "request_id": request_id,
        "user_message": request.user_message,
        "message_history": request.message_history,
        # Ephemeral fields are cleared on every turn
        "tool_status": None,
        "tool_result": None,
        "validation_errors": None,
        "llm_response": None,
        "extraction_used_fallback": False,
        # Note: We omit selected_tool, tool_arguments, and metadata
        # so they are preserved by the MemorySaver checkpointer.
        "model_name": "agent-core" if settings.LLM_PROVIDER.lower().strip() == "multi" else settings.DEFAULT_MODEL
    }
    if request.log_draft:
        input_state["log_draft"] = request.log_draft
    if request.action == "save_reviewed" and not request.log_draft:
        raise HTTPException(status_code=422, detail="Add fields before saving the record.")

    # Only the persistence tool needs a separate copy of the open document.
    # Keeping it out of graph state avoids adding it to every prompt/checkpoint.
    source = request.source_document if current_user is not None else None
    source_text = source.body_for(request.user_message) if source else None
    if source_text is not None and (len(source_text) > MAX_SOURCE_CHARACTERS or "\x00" in source_text):
        raise HTTPException(status_code=422, detail="Use document text without null characters, up to 10,485,760 characters.")
    tool_context = ToolExecutionContext(
        db=db if current_user is not None else None,
        request_id=request_id,
        conversation_id=conversation_id if current_user is not None else work_conversation_id,
        logger=logger,
        settings=settings,
        current_user=current_user,
        source_filename=source.filename if source else None,
        source_text=source_text,
        excluded_fields=frozenset(request.excluded_fields),
        source_is_current_message=source is not None and source.text is None,
    )

    config = {"configurable": {"tool_context": tool_context, "thread_id": f"{thread_scope}:{conversation_id}"}}

    try:
        # Bound the whole turn because retries and multiple graph steps share the request.
        async with asyncio.timeout(CHAT_PROCESSING_SECONDS):
            final_state = await graph_to_use.ainvoke(input_state, config=config)

        # Atomic metadata sync
        from datetime import datetime, timezone
        metadata = final_state.get("metadata", {})
        # The repo-side ConversationMetadata.message_count is the ONE canonical
        # counter (user + assistant messages, incremented via
        # conversation_memory.append_message during the graph run). The
        # graph-state value here is only a derived mirror of that counter —
        # do not increment it independently.
        repo_metadata = await conversation_memory_service.get_metadata(work_conversation_id)
        metadata["message_count"] = repo_metadata.message_count
        metadata["last_activity"] = datetime.now(timezone.utc).isoformat()

        draft = final_state.get("log_draft")
        if draft:
            metadata["active_schema"] = draft.schema_name

        tool_result = final_state.get("tool_result")
        if tool_result and isinstance(tool_result, dict) and "log_reference" in tool_result:
            metadata["active_log_reference"] = tool_result.get("log_reference")
            if tool_result.get("id"):
                metadata["active_log_id"] = str(tool_result.get("id"))
            selected_tool = final_state.get("selected_tool")
            metadata["last_tool"] = selected_tool.value if hasattr(selected_tool, "value") else selected_tool

        if final_state.get("clarification_state"):
            metadata["clarification_state_status"] = final_state.get("clarification_state").status.value
        else:
            metadata["clarification_state_status"] = None

        await graph_to_use.aupdate_state(config, {"metadata": metadata})
        final_state["metadata"] = metadata

        # The graph works on the scoped conversation id (user- or guest-
        # prefixed); the client keeps talking in its own unprefixed id.
        final_state["conversation_id"] = conversation_id

        # Map state to unified response model
        chat_response = ConversationResponseMapper.map_to_response(final_state)

        return APIResponse(
            success=True,
            message="Chat processed successfully",
            data=chat_response
        )
    except TimeoutError:
        logger.warning(f"[{request_id}] Chat workflow exceeded its deadline")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="This turn took too long. Check your draft and try again.",
        ) from None
    except Exception:
        logger.exception(f"[{request_id}] Error executing chat workflow")
        # Do not echo internal exception text to clients (information disclosure).
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during conversation processing."
        )
