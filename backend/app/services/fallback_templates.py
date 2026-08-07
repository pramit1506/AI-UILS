from typing import List, Dict, Any
from app.graph.state import GraphState
from app.shared.enums import AgentAction
import logging

logger = logging.getLogger(__name__)


class FallbackTemplateService:
    """Generates deterministic natural language responses from application state."""

    @classmethod
    def generate_clarification_response(cls, state: GraphState) -> str:
        """Generates a clarification response based on missing fields."""
        decision = state.get("decision_output")
        missing_fields = []

        if decision and hasattr(decision, "required_missing_fields") and decision.required_missing_fields:
            missing_fields = decision.required_missing_fields
        else:
            clarification = state.get("clarification_state")
            if clarification and hasattr(clarification, "missing_fields") and clarification.missing_fields:
                missing_fields = clarification.missing_fields

        if not missing_fields:
            return "I've updated the log draft. What else would you like to add or change?"

        target_field = missing_fields[0]
        question = f"Could you provide the {target_field.replace('_', ' ')}?"
        return question

    @classmethod
    def generate_fallback_response(cls, state: GraphState) -> str:
        """Generates a contextual fallback response when the LLM is unavailable."""
        decision = state.get("decision_output")
        action = decision.action if decision and hasattr(decision, "action") else None

        if action == AgentAction.CLARIFY:
            return cls.generate_clarification_response(state)

        elif action == AgentAction.CONTINUE:
            changed_fields = state.get("changed_fields") or []
            if changed_fields:
                pretty_fields = ", ".join(field.replace("_", " ") for field in changed_fields)
                return f"Updated {pretty_fields}. Please review the log form, then say 'save the log' when ready."
            draft_status = state.get("draft_status")
            if str(draft_status) == "READY" or (hasattr(draft_status, "value") and draft_status.value == "READY"):
                return "I've extracted the information from your document. Please review the log form on the left, then say 'save the log' when ready."
            return "I've updated the log draft. Please provide any additional details so I can complete the form."

        elif action == AgentAction.EXECUTE_TOOL:
            validation_errors = state.get("validation_errors") or []
            if validation_errors:
                return f"I could not complete the action: {', '.join(str(error) for error in validation_errors)}"
            tool_result = state.get("tool_result") or {}
            if isinstance(tool_result, dict):
                message = tool_result.get("message")
                log_reference = tool_result.get("log_reference")
                if message:
                    return str(message)
                if log_reference:
                    return f"Log saved successfully. Reference: {log_reference}."
            return "Action completed successfully."

        elif action == AgentAction.RESPOND:
            draft = state.get("log_draft")
            if draft and draft.schema_name:
                return f"I'm ready to help you log your {draft.schema_name}. What would you like to do next?"
            return "I'm ready to help you log and organize information from any document. Upload a file or paste text to get started."

        # Generic fallback
        return "I'm ready to help. Upload a document or paste text, and I'll extract and log the information for you."


fallback_templates = FallbackTemplateService()
