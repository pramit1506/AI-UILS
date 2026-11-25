from typing import List, Dict, Optional, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.draft import DynamicLogDraft
from app.schemas.memory import ClarificationState, ConversationMetadata
from app.schemas.decision import DecisionOutput
from app.shared.enums import DraftStatus, ConversationStatus


MAX_SOURCE_CHARACTERS = 10 * 1024 * 1024


class DocumentSource(BaseModel):
    """The document open in the editor. On its intake turn the message carries the text."""
    filename: str = Field(min_length=1, max_length=255, pattern=r"^[^\x00]+$")
    text: Optional[str] = Field(default=None, max_length=MAX_SOURCE_CHARACTERS)

    def body_for(self, message: str) -> str:
        if self.text is not None:
            return self.text
        return message.removeprefix(f"Process this uploaded document ({self.filename}):\n\n")


class ChatRequest(BaseModel):
    action: Literal["chat", "capture", "save_reviewed"] = "chat"
    user_message: str
    excluded_fields: set[str] = Field(default_factory=set)
    expected_user_id: Optional[UUID] = None
    conversation_id: Optional[str] = None
    message_history: List[Dict[str, str]] = Field(default_factory=list)
    log_draft: Optional[DynamicLogDraft] = None
    source_document: Optional[DocumentSource] = None


class FieldChange(BaseModel):
    field_name: str
    previous_value: Optional[Any] = None
    current_value: Optional[Any] = None
    change_type: str  # "added", "updated", "removed"


class ToolExecutionResult(BaseModel):
    status: str
    created_resource_id: Optional[str] = None
    success_message: Optional[str] = None
    validation_warnings: List[str] = Field(default_factory=list)
    # Name of the executed tool (e.g. "save_log"); lets the frontend react to
    # specific tool failures — like raising the guest "login to save" wall —
    # without parsing the assistant message text.
    tool_name: Optional[str] = None


class ConversationResponse(BaseModel):
    assistant_message: str
    conversation_id: str
    log_draft: Optional[DynamicLogDraft] = None
    extraction_used_fallback: bool = False
    draft_status: Optional[DraftStatus] = None
    draft_changes: List[FieldChange] = Field(default_factory=list)
    clarification_state: Optional[ClarificationState] = None
    decision_output: Optional[DecisionOutput] = None
    tool_execution_result: Optional[ToolExecutionResult] = None
    conversation_status: ConversationStatus
    conversation_metadata: Optional[ConversationMetadata] = None
