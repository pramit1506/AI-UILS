from enum import Enum


class DraftStatus(str, Enum):
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    READY = "READY"
    CONFIRMED = "CONFIRMED"
    SAVED = "SAVED"


class AgentAction(str, Enum):
    RESPOND = "RESPOND"
    CONTINUE = "CONTINUE"
    CLARIFY = "CLARIFY"
    EXECUTE_TOOL = "EXECUTE_TOOL"


class ToolReadiness(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_READY = "NOT_READY"
    READY = "READY"


class AgentState(str, Enum):
    IDLE = "IDLE"
    COLLECTING_INFORMATION = "COLLECTING_INFORMATION"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    COMPLETED = "COMPLETED"


class ToolName(str, Enum):
    SAVE_LOG = "save_log"
    EDIT_LOG = "edit_log"
    SUMMARIZE_LOG = "summarize_log"
    SEARCH_LOGS = "search_logs"
    COMPLETENESS_CHECKER = "completeness_check"


class ConversationStatus(str, Enum):
    COLLECTING_INFORMATION = "COLLECTING_INFORMATION"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
    EXECUTING_TOOL = "EXECUTING_TOOL"
    COMPLETED = "COMPLETED"


class ClarificationLifecycle(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    UPDATED = "UPDATED"
    RESOLVED = "RESOLVED"
    CLEARED = "CLEARED"


class LogSource(str, Enum):
    PDF = "PDF"
    EMAIL = "EMAIL"
    TEXT = "TEXT"
    PORTAL = "PORTAL"
    CALL = "CALL"
