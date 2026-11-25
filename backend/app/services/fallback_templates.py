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

        # Use the AI-written clarification message if available
        if decision and getattr(decision, "clarification_message", None):
            return decision.clarification_message

        if not missing_fields:
            return "I've updated the log draft. What else would you like to add or change?"

        # Build a friendly message mentioning a couple of details we already
        # captured (schema-driven: any populated draft field, generic naming).
        draft = state.get("log_draft")
        have_parts = []
        if draft:
            for key, value in (draft.fields or {}).items():
                if key.startswith("_") or value is None or (isinstance(value, str) and not value.strip()):
                    continue
                have_parts.append(f"{key.replace('_', ' ')} ({value})")
                if len(have_parts) >= 2:
                    break

        target_field = missing_fields[0].replace("_", " ")
        if have_parts and len(have_parts) <= 2:
            have_str = " and ".join(have_parts)
            return f"I have the {have_str}. Could you also provide the {target_field}?"
        return f"Could you please provide the {target_field}?"

    @classmethod
    def generate_fallback_response(cls, state: GraphState) -> str:
        """Generates a contextual fallback response when the LLM is unavailable."""
        decision = state.get("decision_output")
        action = decision.action if decision and hasattr(decision, "action") else None

        if action == AgentAction.CLARIFY:
            return cls.generate_clarification_response(state)

        elif action == AgentAction.CONTINUE:
            changed_fields = state.get("changed_fields") or []
            draft = state.get("log_draft")
            if changed_fields:
                pretty_fields = ", ".join(field.replace("_", " ") for field in changed_fields[:4])
                schema = draft.schema_name if draft and draft.schema_name else "document"
                return f"Got it — I've captured the {pretty_fields} for your {schema}. Review the log form on the left, and say 'save the log' when you're ready."
            draft_status = state.get("draft_status")
            if str(draft_status) == "READY" or (hasattr(draft_status, "value") and draft_status.value == "READY"):
                schema = draft.schema_name if draft and draft.schema_name else "document"
                return f"Looks good! Your {schema} draft is ready. Review the fields on the left and say 'save the log' when you're happy with it."
            return "I've updated the log draft. What other details can I add for you?"

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
