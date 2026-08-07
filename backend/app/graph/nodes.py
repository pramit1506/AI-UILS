import json
import re
from typing import Dict, Any
from datetime import date, timedelta
from langchain_core.runnables import RunnableConfig
from app.graph.state import GraphState, IntentOutput, ToolSelectionOutput
from app.llm.factory import get_llm_provider
from app.prompts.loader import load_prompt
from app.tools.registry import tool_registry
from app.tools.context import ToolExecutionContext
from app.schemas.extraction import ExtractionOutput
from app.services.draft_service import DraftService
from app.schemas.draft import FieldMetadata, DynamicLogDraft
from app.services.decision_service import decision_service
from app.services.context_builder import context_builder
from app.services.conversation_memory import conversation_memory_service
from app.services.fallback_templates import fallback_templates
from app.exceptions.base import ProviderException, InvalidAPIKeyException, ModelUnavailableException
from app.shared.enums import AgentAction
from app.core.config import settings
from loguru import logger


async def input_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Input Node: Received message for conversation {state.get('conversation_id')}")
    if state.get("conversation_id") and state.get("user_message"):
        await conversation_memory_service.append_message(
            state["conversation_id"],
            "user",
            state["user_message"]
        )

    return {
        "tool_result": None,
        "tool_status": None,
        "validation_errors": None,
    }


async def intent_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Intent Node: Detecting intent")

    from app.shared.enums import ClarificationLifecycle

    clarification = state.get("clarification_state")
    if clarification and clarification.status in [
        ClarificationLifecycle.CREATED,
        ClarificationLifecycle.ACTIVE,
        ClarificationLifecycle.UPDATED,
    ]:
        normalized_message = state.get("user_message", "").strip().lower().rstrip(".!?")
        cancel_like = normalized_message in {
            "cancel", "cancel that", "cancel it", "stop", "nevermind", "never mind",
        }
        if not cancel_like:
            tool_name = clarification.tool_name or state.get("pending_tool") or state.get("selected_tool")
            logger.info(
                f"[{state.get('request_id')}] Intent Node: Active clarification for {tool_name}; preserving workflow intent"
            )
            return {"detected_intent": tool_name}

    if settings.DEMO_OFFLINE_MODE:
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        return {"detected_intent": _fallback_intent(state.get("user_message", "")), "metadata": metadata}

    llm = get_llm_provider()
    system_prompt = load_prompt("system.md")
    intent_prompt = load_prompt("intent.md")
    context_str = await context_builder.build(state)

    messages = [
        {"role": "system", "content": system_prompt + "\n\n" + context_str},
        {"role": "system", "content": intent_prompt},
        {"role": "user", "content": state["user_message"]}
    ]

    try:
        intent_output = await llm.generate_structured(messages=messages, schema=IntentOutput)
        logger.info(f"[{state.get('request_id')}] Intent detected: {intent_output.intent}")
        metadata = state.get("metadata", {}).copy()
        metadata["intent_confidence"] = intent_output.confidence
        return {"detected_intent": intent_output.intent, "metadata": metadata}
    except Exception as e:
        logger.error(f"[{state.get('request_id')}] Intent Node Error: {e}")
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        return {"detected_intent": _fallback_intent(state.get("user_message", "")), "metadata": metadata}


def _fallback_intent(message: str) -> str:
    text = (message or "").lower()
    if len(text) > 100:
        return "save_log"
    if any(term in text for term in ["save", "log it", "store", "record", "process this uploaded document"]):
        return "save_log"
    if any(term in text for term in ["edit", "update", "change", "correct"]):
        return "edit_log"
    if any(term in text for term in ["find", "search", "look up", "retrieve", "recall"]):
        return "search_logs"
    if "summar" in text:
        return "summarize_log"
    if any(term in text for term in ["complete", "missing", "required fields", "check"]):
        return "completeness_check"
    return "conversation"


def _is_update_message(text: str) -> bool:
    lowered = (text or "").lower()
    if "process this uploaded document" in lowered:
        return False
    update_markers = [
        "sorry", "actually", "correct", "correction", "change",
        "update", "replace", "should be",
    ]
    return any(marker in lowered for marker in update_markers)


def _parse_simple_date(value: str) -> str | None:
    text = (value or "").strip()
    today = date.today()
    lowered = text.lower()
    if "today" in lowered:
        return today.isoformat()
    if "yesterday" in lowered:
        return (today - timedelta(days=1)).isoformat()
    patterns = [
        r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",
        r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",
    ]
    for idx, pattern in enumerate(patterns):
        match = re.search(pattern, text)
        if not match:
            continue
        parts = [int(p) for p in match.groups()]
        try:
            if idx == 0:
                return date(parts[0], parts[1], parts[2]).isoformat()
            return date(parts[2], parts[1], parts[0]).isoformat()
        except ValueError:
            return None
    return None


def _fallback_extract_fields(message: str, existing_draft: DynamicLogDraft = None) -> Dict[str, Any]:
    """
    Domain-agnostic fallback extraction when LLM is unavailable.
    Attempts to detect document type and extract common key-value patterns.
    """
    text = message or ""
    fields: Dict[str, Any] = {}
    schema_name = None
    domain = None

    # Detect document type
    lowered = text.lower()
    if any(t in lowered for t in ["invoice", "vendor", "bill", "amount due", "payment"]):
        schema_name = "Invoice"
        domain = "Finance"
    elif any(t in lowered for t in ["resume", "curriculum vitae", "work experience", "education", "skills"]):
        schema_name = "Resume"
        domain = "HR"
    elif any(t in lowered for t in ["contract", "agreement", "parties", "clause", "whereas"]):
        schema_name = "Contract"
        domain = "Legal"
    elif any(t in lowered for t in ["patient", "diagnosis", "prescription", "medical", "doctor"]):
        schema_name = "Medical Record"
        domain = "Healthcare"
    elif any(t in lowered for t in ["receipt", "total", "subtotal", "tax", "purchase"]):
        schema_name = "Receipt"
        domain = "Finance"
    elif any(t in lowered for t in ["complaint", "issue", "defect", "problem", "quality"]):
        schema_name = "Complaint"
        domain = "Quality Management"
    else:
        schema_name = "General Document"
        domain = "General"

    # Source detection
    if "uploaded document" in lowered or ".pdf" in lowered:
        fields["_source"] = "pdf"
    elif "email" in lowered or ".eml" in lowered:
        fields["_source"] = "email"

    # Generic key: value extraction from text (handles both multiline and single-line pasted text)
    kv_pattern = re.compile(r"([A-Za-z0-9\s_\-\.\(\)/]{2,30}?)\s*:\s*([^:]+?)(?=\s+[A-Za-z0-9\s_\-\.\(\)/]{2,30}?\s*:|$)", re.IGNORECASE)
    for match in kv_pattern.finditer(text):
        key_raw = match.group(1).strip()
        value_raw = match.group(2).strip()
        if not value_raw or len(value_raw) > 500:
            continue
        # Normalize key to snake_case
        key = re.sub(r"[^a-z0-9]+", "_", key_raw.lower()).strip("_")
        if key and value_raw:
            fields[key] = value_raw

    result = {}
    if schema_name:
        result["schema_name"] = schema_name
    if domain:
        result["domain"] = domain
    result.update(fields)
    return result


async def entity_extraction_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Entity Extraction Node: Extracting entities")

    intent = state.get("detected_intent")
    if intent == "conversation":
        logger.info(f"[{state.get('request_id')}] Skipping extraction for conversation intent")
        return {}

    normalized_message = (state.get("user_message") or "").strip().lower().rstrip(".!?")
    confirmation_messages = {
        "ok", "okay", "yes", "y", "confirm", "confirmed", "go ahead",
        "execute", "save", "save log", "log it",
    }
    if normalized_message in confirmation_messages and state.get("log_draft"):
        draft_service = DraftService()
        status_info = draft_service.validate(state["log_draft"])
        logger.info(f"[{state.get('request_id')}] Skipping extraction for confirmation-only message")
        return {
            "draft_status": status_info["status"].value,
            "changed_fields": [],
        }

    if settings.DEMO_OFFLINE_MODE or (state.get("metadata") or {}).get("llm_unavailable"):
        current_draft = state.get("log_draft") or DynamicLogDraft()
        extracted = _fallback_extract_fields(state.get("user_message", ""), current_draft)
        if not extracted:
            return {}

        draft_service = DraftService()
        metadata_dict = {
            field: FieldMetadata(confidence=0.7, source="deterministic_demo")
            for field in extracted
            if not field.startswith("_")
        }
        result = draft_service.merge(current_draft, extracted, metadata=metadata_dict)
        status_info = draft_service.validate(result.updated_draft)
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        metadata["latest_extracted_fields"] = extracted
        metadata["latest_field_metadata"] = {
            field: meta.model_dump() for field, meta in metadata_dict.items()
        }
        return {
            "log_draft": result.updated_draft,
            "changed_fields": result.changed_fields,
            "draft_status": status_info["status"].value,
            "metadata": metadata,
        }

    llm = get_llm_provider()
    extraction_prompt = load_prompt("entity_extraction.md")
    current_draft = state.get("log_draft") or DynamicLogDraft()
    context_str = await context_builder.build(state, exclude_history=True)

    messages = [
        {"role": "system", "content": extraction_prompt + "\n\n" + context_str},
        {"role": "user", "content": state["user_message"]}
    ]

    try:
        output: ExtractionOutput = await llm.generate_structured(messages=messages, schema=ExtractionOutput)
        logger.info(f"[{state.get('request_id')}] Extraction output: {output.model_dump()}")

        draft_service = DraftService()
        draft = current_draft
        all_changed_fields = []

        if output.extracted_fields:
            metadata_dict = {}
            for field, meta in output.field_metadata.items():
                if field in output.extracted_fields:
                    metadata_dict[field] = FieldMetadata(**meta)
            result = draft_service.merge(draft, output.extracted_fields, metadata=metadata_dict)
            draft = result.updated_draft
            all_changed_fields.extend(result.changed_fields)

        if output.corrections:
            for field, new_value in output.corrections.items():
                meta = output.field_metadata.get(field)
                meta_obj = FieldMetadata(**meta) if meta else None
                result = draft_service.correct_field(draft, field, new_value, metadata=meta_obj)
                draft = result.updated_draft
                all_changed_fields.extend(result.changed_fields)

        if output.removed_fields:
            for field in output.removed_fields:
                result = draft_service.remove_field(draft, field)
                draft = result.updated_draft
                all_changed_fields.extend(result.changed_fields)

        all_changed_fields = list(set(all_changed_fields))
        status_info = draft_service.validate(draft)
        draft_status = status_info["status"].value

        metadata = state.get("metadata", {}).copy()
        metadata["latest_extracted_fields"] = output.extracted_fields
        metadata["latest_field_metadata"] = output.field_metadata

        return {
            "log_draft": draft,
            "changed_fields": all_changed_fields,
            "draft_status": draft_status,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"[{state.get('request_id')}] Entity Extraction Error: {e}")
        extracted = _fallback_extract_fields(
            state.get("user_message", ""),
            current_draft,
        )
        if not extracted:
            return {}

        draft_service = DraftService()
        metadata_dict = {
            field: FieldMetadata(confidence=0.55, source="deterministic_fallback")
            for field in extracted
            if not field.startswith("_")
        }
        result = draft_service.merge(current_draft, extracted, metadata=metadata_dict)
        status_info = draft_service.validate(result.updated_draft)
        metadata = state.get("metadata", {}).copy()
        metadata["latest_extracted_fields"] = extracted
        metadata["latest_field_metadata"] = {
            field: meta.model_dump() for field, meta in metadata_dict.items()
        }
        return {
            "log_draft": result.updated_draft,
            "changed_fields": result.changed_fields,
            "draft_status": status_info["status"].value,
            "metadata": metadata,
        }


async def decision_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Decision Node: Planning next step")

    decision_output = await decision_service.determine_next_action(state)

    from app.shared.enums import ConversationStatus, ClarificationLifecycle, AgentAction, ToolReadiness
    conversation_status = ConversationStatus.COLLECTING_INFORMATION
    if decision_output.action == AgentAction.CLARIFY:
        conversation_status = ConversationStatus.AWAITING_CLARIFICATION
    elif decision_output.action == AgentAction.EXECUTE_TOOL:
        conversation_status = ConversationStatus.READY_FOR_EXECUTION

    updates = {
        "decision_output": decision_output,
        "current_agent_state": decision_output.next_state,
        "clarification_reason": decision_output.clarification_reason,
        "required_missing_fields": decision_output.required_missing_fields,
        "optional_missing_fields": decision_output.optional_missing_fields,
        "conversation_status": conversation_status,
    }

    metadata = state.get("metadata", {}).copy()
    normalized_message = state.get("user_message", "").strip().lower().rstrip(".!?")
    if metadata.get("awaiting_new_log_decision") and normalized_message in {
        "no", "n", "nope", "no thanks", "not now",
    }:
        metadata["awaiting_new_log_decision"] = False

    if hasattr(decision_output, "reset_context") and decision_output.reset_context:
        logger.info(f"[{state.get('request_id')}] Decision Node: Executing state reset for new workflow/pivot.")
        metadata["current_log_start_idx"] = metadata.get("message_count", 0)
        metadata["awaiting_new_log_decision"] = False

        updates["log_draft"] = None
        updates["clarification_state"] = None
        updates["selected_tool"] = None
        updates["pending_tool"] = None
        updates["tool_arguments"] = None

        latest_extracted = metadata.get("latest_extracted_fields")
        if latest_extracted:
            from app.services.draft_service import DraftService
            draft_service = DraftService()
            fresh_draft = DynamicLogDraft()

            latest_meta = metadata.get("latest_field_metadata", {})
            meta_dict = {}
            for field, m in latest_meta.items():
                if field in latest_extracted:
                    meta_dict[field] = FieldMetadata(**m)

            fresh_draft = draft_service.merge(fresh_draft, latest_extracted, metadata=meta_dict).updated_draft
            updates["log_draft"] = fresh_draft

    updates["metadata"] = metadata

    if decision_output.selected_tool:
        updates["selected_tool"] = decision_output.selected_tool
        updates["pending_tool"] = decision_output.selected_tool

    clarification = state.get("clarification_state")
    if decision_output.action == AgentAction.CLARIFY:
        from app.schemas.memory import ClarificationState
        if not clarification:
            clarification = ClarificationState(
                tool_name=decision_output.selected_tool or "unknown",
                required_fields=decision_output.required_missing_fields,
                missing_fields=decision_output.required_missing_fields,
                original_request=state.get("user_message", ""),
                status=ClarificationLifecycle.CREATED,
            )
        else:
            clarification.missing_fields = decision_output.required_missing_fields
            clarification.status = ClarificationLifecycle.UPDATED
        updates["clarification_state"] = clarification
    else:
        if clarification and decision_output.tool_readiness == ToolReadiness.READY:
            clarification.status = ClarificationLifecycle.CLEARED
            updates["clarification_state"] = None

    return updates


async def tool_selection_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Tool Selection Node: Selecting tool")

    tool_name = state.get("selected_tool")
    intent = state.get("detected_intent")

    if tool_name:
        tool = tool_registry.get_tool(tool_name)
    else:
        tool = tool_registry.get_tool(intent)

    if not tool:
        logger.warning(f"[{state.get('request_id')}] No tool found for intent {intent}")
        return {}

    decision = state.get("decision_output")
    from app.shared.enums import AgentAction

    if decision and decision.action == AgentAction.EXECUTE_TOOL:
        draft = state.get("log_draft")
        if draft:
            # Map DynamicLogDraft to the tool's argument schema
            tool_schema_fields = set(tool.args_schema.model_fields.keys())
            tool_args = {}

            # Top-level draft fields
            if "schema_name" in tool_schema_fields and draft.schema_name:
                tool_args["schema_name"] = draft.schema_name
            if "domain" in tool_schema_fields and draft.domain:
                tool_args["domain"] = draft.domain
            if "source" in tool_schema_fields and draft.source:
                tool_args["source"] = draft.source

            # Pass the whole fields dict if the tool accepts it
            if "fields" in tool_schema_fields:
                tool_args["fields"] = draft.fields or {}

            # Also try individual field keys for tools like edit_log
            for k, v in (draft.fields or {}).items():
                if k in tool_schema_fields:
                    tool_args[k] = v
        else:
            tool_args = {}

        logger.info(f"[{state.get('request_id')}] Selected tool: {tool.name}, args from DynamicLogDraft")
        return {
            "selected_tool": tool.name,
            "tool_arguments": tool_args,
        }

    llm = get_llm_provider()
    tool_selection_prompt = load_prompt("tool_selection.md").format(
        tool_name=tool.name,
        tool_description=tool.description
    )
    schema_json = json.dumps(tool.args_schema.model_json_schema())
    tool_selection_prompt += f"\n\nArguments Schema: {schema_json}"
    tool_selection_prompt += "\n\nIMPORTANT: Place the extracted arguments directly into the `tool_arguments` field of your JSON response."

    context_str = await context_builder.build(state)

    messages = [
        {"role": "system", "content": tool_selection_prompt + "\n\n" + context_str},
        {"role": "user", "content": state["user_message"]}
    ]

    try:
        output = await llm.generate_structured(messages=messages, schema=ToolSelectionOutput)
        logger.info(f"[{state.get('request_id')}] Selected tool: {tool.name}")
        return {
            "selected_tool": tool.name,
            "tool_arguments": output.tool_arguments,
        }
    except Exception as e:
        logger.error(f"[{state.get('request_id')}] Tool Selection Error: {e}")
        from app.shared.enums import ConversationStatus
        return {
            "tool_arguments": {},
            "tool_status": "failed",
            "validation_errors": [f"Tool selection failed: {str(e)}"],
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
        }


async def tool_execution_node(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Tool Execution Node: Executing {state.get('selected_tool')}")

    decision = state.get("decision_output")
    from app.shared.enums import ToolReadiness, ConversationStatus, DraftStatus
    if not decision or decision.tool_readiness != ToolReadiness.READY:
        logger.error(f"[{state.get('request_id')}] Workflow Invariant Violation: Tool execution attempted while NOT_READY")
        raise RuntimeError("Workflow Invariant Violation: Tool execution attempted while NOT_READY")

    draft = state.get("log_draft")
    if not draft:
        logger.error(f"[{state.get('request_id')}] Workflow Invariant Violation: Tool execution attempted with no DynamicLogDraft")
        return {"tool_status": "failed", "validation_errors": ["No log draft found."]}

    tool_name = state.get("selected_tool")
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        return {"tool_status": "failed", "validation_errors": ["Tool not found."]}
    tool_name_value = tool_name.value if hasattr(tool_name, "value") else str(tool_name)

    # For tools that require schema_name + fields, validate those exist
    if tool_name_value in ("save_log", "summarize_log", "completeness_check"):
        if not draft.schema_name:
            return {
                "tool_status": "failed",
                "validation_errors": ["Cannot save log: document type (schema_name) has not been determined yet."],
            }

    tool_args = state.get("tool_arguments") or {}

    # Special handling: inject active log reference for edit_log
    if tool_name_value == "edit_log" and not tool_args.get("log_reference"):
        active_log_ref = (state.get("metadata") or {}).get("active_log_reference")
        if not active_log_ref:
            return {
                "tool_status": "failed",
                "validation_errors": ["No active log record to edit. Please save a log first."],
                "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
            }
        tool_args = {**tool_args, "log_reference": active_log_ref}

    logger.info(f"[{state.get('request_id')}] Executing tool: {tool_name}")

    context: ToolExecutionContext = config["configurable"].get("tool_context")
    if not context:
        logger.error("ToolExecutionContext not found in config")
        return {"tool_status": "failed", "validation_errors": ["Execution context missing."]}

    try:
        validated_args = tool.args_schema(**tool_args)
        logger.info(f"[{state.get('request_id')}] Validated arguments: {validated_args.model_dump()}")

        result = await tool.execute(context, **validated_args.model_dump())
        logger.info(f"[{state.get('request_id')}] Tool execution result: {result}")

        result_status = None
        if isinstance(result, dict):
            result_status = str(result.get("status", "")).lower()

        if result_status in {"failed", "failure", "error"}:
            message = result.get("message") or "Tool execution failed."
            return {
                "tool_result": result,
                "tool_status": "failed",
                "validation_errors": [message],
                "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
            }

        metadata = state.get("metadata", {}).copy()
        if isinstance(result, dict):
            if result.get("id"):
                metadata["active_log_id"] = str(result.get("id"))
            if result.get("log_reference"):
                metadata["active_log_reference"] = result.get("log_reference")
            metadata["last_tool"] = tool_name_value
            if tool_name_value == "save_log":
                metadata["awaiting_new_log_decision"] = True

        return {
            "tool_result": result,
            "tool_status": "success",
            "validation_errors": [],
            "conversation_status": ConversationStatus.COMPLETED,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"[{state.get('request_id')}] Tool Execution Error: {e}")
        from app.shared.enums import ConversationStatus
        return {
            "tool_status": "failed",
            "validation_errors": [str(e)],
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
        }


async def response_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Response Node: Generating response")
    llm = get_llm_provider()

    decision = state.get("decision_output")
    context_str = await context_builder.build(state)

    if settings.DEMO_OFFLINE_MODE or (state.get("metadata") or {}).get("llm_unavailable"):
        response = fallback_templates.generate_fallback_response(state)
        if state.get("conversation_id"):
            await conversation_memory_service.append_message(state["conversation_id"], "assistant", response)
        return {"llm_response": response}

    messages = []

    if decision and decision.action == AgentAction.CLARIFY:
        clarification_message = decision.clarification_message or "I need more information to proceed."
        clarification_prompt = load_prompt("clarification.md").format(
            tool_name=state.get("selected_tool"),
            clarification_message=clarification_message,
        )
        messages = [
            {"role": "system", "content": clarification_prompt + "\n\n" + context_str},
            {"role": "user", "content": state["user_message"]}
        ]
    else:
        tool_result = state.get("tool_result")
        tool_status = state.get("tool_status")
        validation_errors = state.get("validation_errors")

        system_prompt = load_prompt("system.md")
        response_prompt = load_prompt("response.md").format(user_message=state["user_message"])

        if tool_result:
            response_prompt += f"\n\nTool Result ({tool_status}):\n{json.dumps(tool_result, indent=2, default=str)}"
        elif validation_errors:
            response_prompt += f"\n\nTool Execution Failed with validation errors:\n{json.dumps(validation_errors)}"

        messages = [
            {"role": "system", "content": system_prompt + "\n\n" + context_str},
            {"role": "user", "content": response_prompt}
        ]

    try:
        response = await llm.generate_response(messages=messages)
    except ProviderException as e:
        logger.warning(f"[{state.get('request_id')}] Response Node: Transient provider error ({type(e).__name__}): {e}. Using deterministic fallback.")
        response = fallback_templates.generate_fallback_response(state)
    except (InvalidAPIKeyException, ModelUnavailableException) as e:
        logger.error(f"[{state.get('request_id')}] Response Node: Permanent provider configuration error ({type(e).__name__}): {e}.")
        response = "I'm currently unable to process your request because the AI service is unavailable or incorrectly configured. Please contact support."

    if state.get("conversation_id"):
        await conversation_memory_service.append_message(state["conversation_id"], "assistant", response)

    return {"llm_response": response}


async def output_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Output Node: Finalizing response")
    return {}
