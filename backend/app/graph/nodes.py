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
from app.exceptions.base import ProviderException, InvalidAPIKeyException, ModelUnavailableException, RateLimitException, AllProvidersExhaustedException
from app.shared.enums import AgentAction
from app.core.config import settings
from loguru import logger

SEARCH_COMMAND = re.compile(
    r"^\s*(?:(?:can|could) you\s+)?(?:please\s+)?(?:search|find|look up|retrieve|recall)\b"
    r"(?:\s+(?:(?:my|the|all)\s+)?(?:saved\s+)?(?:logs?|documents?|records?)\b)?"
    r"(?:\s+(?:for|containing|mentioning|matching)\b)?[\s:]*",
    re.IGNORECASE,
)

async def input_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Input Node: Received message for conversation {state.get('conversation_id')}")
    if state.get("conversation_id") and state.get("user_message"):
        await conversation_memory_service.append_message(
            state["conversation_id"],
            "user",
            state["user_message"],
            allow_compression=state.get("action") != "save_reviewed" and SEARCH_COMMAND.match(state["user_message"]) is None,
        )

    metadata = state.get("metadata", {}).copy()
    for key in ("all_providers_exhausted", "llm_unavailable", "extraction_error"):
        metadata.pop(key, None)
    return {
        "tool_result": None,
        "tool_status": None,
        "validation_errors": None,
        "metadata": metadata,
    }


async def intent_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Intent Node: Detecting intent")

    from app.shared.enums import ClarificationLifecycle

    message = state.get("user_message", "")
    if state.get("action") == "capture":
        return {"detected_intent": "capture", "log_draft": DynamicLogDraft(),
                "selected_tool": None, "pending_tool": None, "clarification_state": None}
    if state.get("action") == "save_reviewed":
        from app.schemas.decision import DecisionOutput
        from app.shared.enums import AgentState, ToolName, ToolReadiness

        draft = state["log_draft"]
        return {
            "detected_intent": "save_reviewed", "selected_tool": ToolName.SAVE_LOG,
            "log_draft": draft.model_copy(update={"schema_name": draft.schema_name or "Document"}),
            "tool_arguments": {}, "pending_tool": None, "clarification_state": None,
            "decision_output": DecisionOutput(action=AgentAction.EXECUTE_TOOL, selected_tool=ToolName.SAVE_LOG,
                tool_readiness=ToolReadiness.READY, decision_confidence=1.0, next_state=AgentState.READY_TO_EXECUTE),
        }
    command = SEARCH_COMMAND.match(message)
    if command:
        return _search_turn(message[command.end():].strip())

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
        # Break out of clarification if the user issues a new explicit command
        is_pivot = any(p in normalized_message for p in [
            "summar", "save the log", "save log", "save", "process this uploaded document", "upload", "create new"
        ])
        if not cancel_like and not is_pivot:
            tool_name = clarification.tool_name or state.get("pending_tool") or state.get("selected_tool")
            logger.info(
                f"[{state.get('request_id')}] Intent Node: Active clarification for {tool_name}; preserving workflow intent"
            )
            return {"detected_intent": tool_name}

    if settings.DEMO_OFFLINE_MODE:
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        return _fallback_intent_update(message, metadata)

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
        intent_output = await llm.generate_structured(
            messages=messages,
            schema=IntentOutput,
            model="fast-router" if settings.LLM_PROVIDER.lower().strip() == "multi" else None,
        )
        logger.info(f"[{state.get('request_id')}] Intent detected: {intent_output.intent}")
        metadata = state.get("metadata", {}).copy()
        metadata["intent_confidence"] = intent_output.confidence
        if intent_output.intent == "search_logs":
            return {**_search_turn(intent_output.search_query or message), "metadata": metadata}
        return {"detected_intent": intent_output.intent, "metadata": metadata}
    except AllProvidersExhaustedException as e:
        logger.critical(f"[{state.get('request_id')}] Intent Node: ALL providers exhausted — {e}")
        metadata = state.get("metadata", {}).copy()
        metadata["all_providers_exhausted"] = True
        return {
            "detected_intent": "conversation",
            "metadata": metadata,
            "llm_response": "The document assistant is temporarily unavailable. Please try again later.",
        }
    except (RateLimitException, InvalidAPIKeyException) as e:
        logger.error(f"[{state.get('request_id')}] API Limit/Key Error in Intent Node: {e}")
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        return _fallback_intent_update(message, metadata)
    except Exception as e:
        logger.error(f"[{state.get('request_id')}] Intent Node Error: {e}")
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        return _fallback_intent_update(message, metadata)



def _search_turn(query: str) -> dict:
    """Search is a read-only command independent of any document being drafted."""
    from app.schemas.decision import DecisionOutput
    from app.shared.enums import AgentState, ToolName, ToolReadiness

    return {
        "detected_intent": "search_logs",
        "selected_tool": ToolName.SEARCH_LOGS,
        "tool_arguments": {"query": query},
        "decision_output": DecisionOutput(
            action=AgentAction.EXECUTE_TOOL, selected_tool=ToolName.SEARCH_LOGS,
            tool_readiness=ToolReadiness.READY, decision_confidence=1.0,
            next_state=AgentState.READY_TO_EXECUTE,
        ),
    }


def _fallback_intent_update(message: str, metadata: dict) -> dict:
    intent = _fallback_intent(message)
    if intent == "search_logs":
        return {**_search_turn(message), "metadata": metadata}
    return {"detected_intent": intent, "metadata": metadata}


def _fallback_intent(message: str) -> str:
    import re
    text = (message or "").lower()
    # Explicit document ingestion is ALWAYS save_log
    if "process this uploaded document" in text or "uploaded document" in text:
        return "save_log"
    # Summarize triggers
    if any(term in text for term in ["summar", "what have", "overview", "brief", "show summary"]):
        return "summarize_log"
    # Explicit save triggers
    if any(term in text for term in ["save the log", "save log", "log it", "store", "record", "log this", "please save", "can you log"]):
        return "save_log"
    # Search / retrieval triggers (use regex word boundaries to avoid matching 'findings')
    if any(re.search(rf"\b{re.escape(term)}\b", text) for term in ["find", "search", "look up", "retrieve", "recall", "show me"]):
        return "search_logs"
    # Completeness check triggers
    if any(term in text for term in ["complete", "missing", "required fields", "check"]):
        return "completeness_check"
    # Long message with structured content → document to save
    if len(text) > 80:
        return "save_log"
    # Edit / correction triggers
    if any(term in text for term in ["edit", "update", "change", "correct", "actually", "sorry", "wait"]):
        return "save_log"
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


MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _parse_simple_date(value: str) -> str | None:
    """Parse a date string into ISO 8601 YYYY-MM-DD format."""
    text = (value or "").strip()
    today = date.today()
    lowered = text.lower()

    if "today" in lowered:
        return today.isoformat()
    if "yesterday" in lowered:
        return (today - timedelta(days=1)).isoformat()

    # ISO / numeric: 2026-11-03 or 3/11/2026
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
            return date(parts[2], parts[0], parts[1]).isoformat()
        except ValueError:
            return None

    # Named month: "November 3, 2026" / "3 November 2026" / "Aug 7th" / "Sept 14th"
    month_pattern = re.compile(
        r"""(?:(?P<day1>\d{1,2})\s*(?:st|nd|rd|th)?\s+(?P<month1>[A-Za-z]+)(?:\s*[,.]?\s*(?P<year1>\d{4}))?)|
           (?:(?P<month2>[A-Za-z]+)\s+(?P<day2>\d{1,2})(?:st|nd|rd|th)?(?:\s*[,.]?\s*(?P<year2>\d{4}))?)""",
        re.VERBOSE | re.IGNORECASE,
    )
    for m in month_pattern.finditer(text):
        if m.group("month1"):
            month_name = m.group("month1").lower()
            day_str = m.group("day1")
            year_str = m.group("year1")
        else:
            month_name = m.group("month2").lower()
            day_str = m.group("day2")
            year_str = m.group("year2")

        month_num = MONTH_MAP.get(month_name) or MONTH_MAP.get(month_name[:3])
        if not month_num:
            continue
        day = int(day_str)
        year = int(year_str) if year_str else today.year
        try:
            return date(year, month_num, day).isoformat()
        except ValueError:
            continue

    return None


def _normalize_amount(raw: str) -> str:
    """Ensure monetary values are consistently formatted."""
    cleaned = raw.strip().replace(",", "")
    match = re.search(r"[\$€£]?\s*(\d+(?:\.\d+)?)", cleaned)
    if match:
        amount = float(match.group(1))
        symbol = "$" if "$" in raw else ("€" if "€" in raw else ("£" if "£" in raw else "$"))
        return f"{symbol}{amount:,.2f}"
    return raw.strip()


def _is_correction_message(text: str) -> bool:
    """Detect if the message is EXPLICITLY correcting previously entered data."""
    lowered = (text or "").lower()
    if "process this uploaded document" in lowered:
        return False
    # Only explicit correction phrases — NOT general past-tense narrative
    markers = [
        "hold on", "oh, hold on", "oh hold on",
        "actually,", "wait,", "wait—", "hold on—",
        "correction:", "correct that", "not $", "not the ",
        "should be", "was actually", "it's actually",
        "rather than", "instead of",
    ]
    return any(m in lowered for m in markers)


def _fallback_extract_fields(
    message: str,
    existing_draft: DynamicLogDraft = None,
) -> tuple[dict, dict]:
    """
    Domain-agnostic offline extraction engine.

    Generic, deterministic parsing only — NO domain keyword tables. The document
    type (schema_name) is intentionally NOT inferred here: the LLM-driven
    extraction stage infers it from the draft schema, and when it cannot be
    determined the field stays empty and the pipeline relies on the standard
    clarification flow (decision_output.action == CLARIFY) instead of guessing.

    Returns (extracted_fields, corrections):
    - extracted_fields: new data to MERGE into the draft
    - corrections: values the user is CORRECTING (override existing fields)
    """
    text = message or ""
    lowered = text.lower()
    fields: Dict[str, Any] = {}
    corrections: Dict[str, Any] = {}
    is_correction = _is_correction_message(text)

    # ── 1. Source detection ──────────────────────────────────────────────────
    if "uploaded document" in lowered or ".pdf" in lowered:
        fields["_source"] = "pdf"
    elif "email" in lowered or ".eml" in lowered:
        fields["_source"] = "email"
    else:
        fields["_source"] = "text"

    # ── 2. Structured KV extraction (handles "Key: Value" documents) ─────────
    kv_pattern = re.compile(
        r"^[ \t]*([A-Za-z][A-Za-z0-9 \t_\-\.\(\)/]{1,35}?)[ \t]*:[ \t]*([^\n\r]{1,200})$",
        re.MULTILINE,
    )
    for match in kv_pattern.finditer(text):
        key_raw = match.group(1).strip().rstrip()
        value_raw = match.group(2).strip().rstrip(",;")
        if not value_raw or len(value_raw) > 300:
            continue
        # Skip instruction lines like "Process this uploaded document (sample.txt):"
        if "process this uploaded document" in key_raw.lower():
            continue
        # Skip keys that are just sentence starters, too short, or look like sentence fragments
        if len(key_raw) < 2 or key_raw.lower() in (
            "hi", "hey", "please", "note", "re", "from", "to", "subject", "dear",
            "ps", "etc", "i", "we", "they", "it",
        ):
            continue
        # Skip if key contains verb-like words (likely a sentence, not a field label)
        if re.search(r"\b(received|have|has|had|is|are|was|were|will|would|should|could|please|record|log)\b", key_raw, re.IGNORECASE):
            continue
        key = re.sub(r"[^a-z0-9]+", "_", key_raw.lower()).strip("_")
        # Normalize monetary values
        if any(money in key for money in ("amount", "total", "price", "cost", "fee")):
            value_raw = _normalize_amount(value_raw)
        # Normalize dates (but NOT for "due" alone - that matches due_date column)
        if any(dt in key for dt in ("date", "received", "issued", "billed")):
            parsed = _parse_simple_date(value_raw)
            if parsed:
                value_raw = parsed
        if key and value_raw:
            if is_correction:
                corrections[key] = value_raw
            else:
                fields[key] = value_raw

    # ── 3. Generic amount extraction (common total/amount labels, bare "$") ──
    # If a total-ish key was captured by KV extraction, expose the canonical
    # "total_amount" alias; otherwise look for an explicit total line.
    kv_total = fields.get("total_amount_due") or fields.get("total_due") or fields.get("total_amount") or fields.get("total")
    if kv_total and "total_amount" not in fields:
        fields["total_amount"] = _normalize_amount(str(kv_total))

    dest_key = corrections if is_correction else fields
    if "total_amount" not in fields and "total_amount" not in corrections:
        total_m = re.search(
            r"(?:total(?:\s+amount(?:\s+due)?)?|amount\s+due)\s*[:\s]?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)",
            text, re.IGNORECASE,
        )
        if total_m:
            dest_key["total_amount"] = _normalize_amount(f"${total_m.group(1)}")

    # ── 4. Generic date extraction ("due by ...", "received on ...", "dated ...") ──
    date_contexts = [
        (r"(?:due\s+(?:date|by|on))\s*[:\s]?\s*(.{5,25})", "due_date"),
        (r"(?:received|issued?)\s+(?:date|on)\s*[:\s]?\s*(.{5,25})", "received_date"),
        (r"(?:dated?)\s+(?:on\s+)?(.{5,25})", "date"),
        (r"(?:^|\n)\s*Date\s*:\s*(.{5,25})", "date"),
    ]
    for pattern, field_name in date_contexts:
        if field_name in fields or field_name in corrections:
            continue
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw_date = m.group(1).strip().rstrip(",;.")
            parsed = _parse_simple_date(raw_date)
            if parsed:
                (corrections if is_correction else fields)[field_name] = parsed

    # ── 5. Alias normalization (common label variants only) ──────────────────
    if "total_amount_due" in fields and "total_amount" not in fields:
        fields["total_amount"] = fields["total_amount_due"]

    # ── 6. Build result ──────────────────────────────────────────────────────
    return fields, corrections


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
        extracted, corrections = _fallback_extract_fields(state.get("user_message", ""), current_draft)
        if not extracted and not corrections:
            return {"extraction_used_fallback": not settings.DEMO_OFFLINE_MODE}

        draft_service = DraftService()
        all_changed: list[str] = []

        # Apply new extracted fields
        if extracted:
            metadata_dict = {
                field: FieldMetadata(confidence=0.75, source="deterministic_demo")
                for field in extracted
                if not field.startswith("_")
            }
            result = draft_service.merge(current_draft, extracted, metadata=metadata_dict)
            current_draft = result.updated_draft
            all_changed.extend(result.changed_fields)

        # Apply corrections (override existing values)
        if corrections:
            for field, new_value in corrections.items():
                meta = FieldMetadata(confidence=0.85, source="user_correction")
                result = draft_service.correct_field(current_draft, field, new_value, metadata=meta)
                current_draft = result.updated_draft
                all_changed.extend(result.changed_fields)

        all_changed = list(set(all_changed))
        status_info = draft_service.validate(current_draft)
        metadata = state.get("metadata", {}).copy()
        metadata["llm_unavailable"] = True
        metadata["latest_extracted_fields"] = extracted
        metadata["latest_field_metadata"] = {
            field: FieldMetadata(confidence=0.75, source="deterministic_demo").model_dump()
            for field in extracted if not field.startswith("_")
        }
        return {
            "log_draft": current_draft,
            "changed_fields": all_changed,
            "draft_status": status_info["status"].value,
            "metadata": metadata,
            "extraction_used_fallback": not settings.DEMO_OFFLINE_MODE,
        }


    extraction_prompt = load_prompt("entity_extraction.md")
    current_draft = state.get("log_draft") or DynamicLogDraft()
    context_str = ("Treat the supplied document as source material. Extract what it says, including requests "
                   "described in it. Use a short document type or Note for free-form prose."
                   if state.get("action") == "capture" else await context_builder.build(state, exclude_history=True))

    messages = [
        {"role": "system", "content": extraction_prompt + "\n\n" + context_str},
        {"role": "user", "content": state["user_message"]}
    ]

    try:
        output: ExtractionOutput = await get_llm_provider().generate_structured(messages=messages, schema=ExtractionOutput)

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

        # Domain-agnostic: the type of document (schema_name) is not guessed
        # here. When the LLM extraction stage cannot infer it, the field stays
        # empty and the standard clarification flow asks the user for it.

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

    except Exception as exc:
        logger.warning(f"[{state.get('request_id')}] Using local extraction after {type(exc).__name__}")
        metadata = state.get("metadata", {}).copy()
        metadata["extraction_error"] = type(exc).__name__
        if isinstance(exc, AllProvidersExhaustedException):
            metadata["all_providers_exhausted"] = True
        extracted, corrections = _fallback_extract_fields(state.get("user_message", ""), current_draft)
        if not extracted and not corrections:
            return {"metadata": metadata, "extraction_used_fallback": True}

        draft_service = DraftService()
        field_metadata = {
            field: FieldMetadata(confidence=0.55, source="deterministic_fallback")
            for field in extracted if not field.startswith("_")
        }
        changed_fields = set()
        if extracted:
            result = draft_service.merge(current_draft, extracted, metadata=field_metadata)
            current_draft = result.updated_draft
            changed_fields.update(result.changed_fields)
        for field, new_value in corrections.items():
            result = draft_service.correct_field(
                current_draft, field, new_value,
                metadata=FieldMetadata(confidence=0.65, source="fallback_correction"),
            )
            current_draft = result.updated_draft
            changed_fields.update(result.changed_fields)

        metadata["latest_extracted_fields"] = extracted
        metadata["latest_field_metadata"] = {field: value.model_dump() for field, value in field_metadata.items()}
        return {
            "log_draft": current_draft,
            "changed_fields": sorted(changed_fields),
            "draft_status": draft_service.validate(current_draft)["status"].value,
            "metadata": metadata,
            "extraction_used_fallback": True,
        }


async def decision_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Decision Node: Planning next step")
    if state.get("action") == "capture":
        from app.shared.enums import ConversationStatus, DraftStatus

        draft = state.get("log_draft") or DynamicLogDraft()
        text = re.sub(r"^Process this uploaded document \([^\n]*\):\n\n", "", state["user_message"]).strip()
        lines = text.splitlines()
        title = lines[0].strip("# ").strip() if lines else ""
        has_heading = len(lines) > 1 and 0 < len(title) <= 64 and ":" not in title
        requests = []
        if not draft.schema_name or not any(not key.startswith("_") for key in draft.fields):
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
                if re.search(r"^(?:please\s+)?(?:add|fix|improve|enable|update|allow)\b|\b(?:must|should)\b", sentence, re.I):
                    requests.append(sentence.strip())
        if not draft.schema_name:
            name = title if has_heading else "Change request" if requests else "Document note"
            draft = draft.model_copy(update={"schema_name": name})
        changes = list(state.get("changed_fields") or [])
        if text and not any(not k.startswith("_") for k in draft.fields):
            fields = {"requested_changes": requests} if requests else {"text": text}
            draft = draft.model_copy(update={"fields": fields})
            changes.extend(fields)
        return {"log_draft": draft, "changed_fields": changes, "draft_status": DraftStatus.PARTIAL.value,
                "decision_output": None, "clarification_state": None,
                "conversation_status": ConversationStatus.COLLECTING_INFORMATION}

    try:
        decision_output = await decision_service.determine_next_action(state)
    except AllProvidersExhaustedException as e:
        logger.critical(f"[{state.get('request_id')}] Decision Node: ALL providers exhausted — {e}")
        from app.shared.enums import AgentAction, ToolReadiness, AgentState, ConversationStatus
        from app.schemas.decision import DecisionOutput
        metadata = state.get("metadata", {}).copy()
        metadata["all_providers_exhausted"] = True
        return {
            "decision_output": DecisionOutput(
                action=AgentAction.RESPOND,
                tool_readiness=ToolReadiness.NOT_APPLICABLE,
                selected_tool=None,
                clarification_message=None,
                clarification_reason=None,
                required_missing_fields=[],
                optional_missing_fields=[],
                decision_confidence=0.0,
                next_state=AgentState.IDLE,
                reset_context=False
            ),
            "current_agent_state": AgentState.IDLE,
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
            "metadata": metadata,
            "llm_response": (
                "⚠️ All configured AI provider API keys have been exhausted. "
                "Please add new API keys to your .env file and restart the server."
            ),
        }
    except (RateLimitException, InvalidAPIKeyException) as e:
        logger.error(f"[{state.get('request_id')}] API Limit/Key Error in Decision Node: {e}")
        from app.shared.enums import AgentAction, ToolReadiness, AgentState, ConversationStatus
        from app.schemas.decision import DecisionOutput
        return {
            "decision_output": DecisionOutput(
                action=AgentAction.RESPOND,
                tool_readiness=ToolReadiness.NOT_APPLICABLE,
                selected_tool=None,
                clarification_message=None,
                clarification_reason=None,
                required_missing_fields=[],
                optional_missing_fields=[],
                decision_confidence=0.0,
                next_state=AgentState.IDLE,
                reset_context=False
            ),
            "current_agent_state": AgentState.IDLE,
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
            "llm_response": "The API limits are over or the API key is invalid. Please provide a new API key."
        }

    from app.shared.enums import ConversationStatus, ClarificationLifecycle, AgentAction, ToolReadiness

    # ── BUG-001 fix: prune required_missing_fields that are already satisfied ──
    # The entity_extraction_node runs before this node in the same turn.  If the
    # LLM's decision was computed against a *stale* draft snapshot it may still
    # list fields like schema_name as missing even though they were just set.
    # Re-validate against the *current* draft so the clarification is accurate.
    current_draft_now = state.get("log_draft")
    if current_draft_now and decision_output.required_missing_fields:
        pruned_missing: list[str] = []
        for field in decision_output.required_missing_fields:
            # Check top-level draft attributes first (schema_name, domain, source)
            if field in ("schema_name", "domain", "source"):
                val = getattr(current_draft_now, field, None)
            else:
                val = (current_draft_now.fields or {}).get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                pruned_missing.append(field)
        if pruned_missing != decision_output.required_missing_fields:
            logger.info(
                f"[{state.get('request_id')}] Decision Node (BUG-001 fix): "
                f"Pruned satisfied fields from missing list. "
                f"Before={decision_output.required_missing_fields}, After={pruned_missing}"
            )
            # DecisionOutput is a frozen Pydantic model — in-place attribute
            # assignment raises ValidationError. Rebuild via model_copy(update=…).
            upgraded = not pruned_missing and decision_output.action == AgentAction.CLARIFY and decision_output.selected_tool is not None
            updates_dict: dict = {"required_missing_fields": pruned_missing}
            if upgraded:
                from app.shared.enums import ToolReadiness as TR, AgentState
                updates_dict.update({
                    "action": AgentAction.EXECUTE_TOOL,
                    "tool_readiness": TR.READY,
                    "next_state": AgentState.READY_TO_EXECUTE,
                })
            decision_output = decision_output.model_copy(update=updates_dict)
            if upgraded:
                logger.info(
                    f"[{state.get('request_id')}] Decision Node (BUG-001 fix): "
                    f"Upgraded action from CLARIFY → EXECUTE_TOOL (all required fields satisfied)."
                )

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

    intent = state.get("detected_intent")

    # Registry validation: resolve the pending selection first, then fall back
    # to the pending tool / intent. An unresolvable (stale or invalid)
    # selection is cleared so the router sends the turn to response_node.
    pending_name = state.get("selected_tool") or state.get("pending_tool") or intent
    tool = tool_registry.get_tool(pending_name)

    if not tool:
        logger.warning(f"[{state.get('request_id')}] Tool Selection Node: no valid tool for '{pending_name}' — clearing stale selection")
        return {
            "selected_tool": None,
            "pending_tool": None,
            "tool_arguments": None,
        }

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

        # The tool-selection LLM's choice must be honored: if it names a
        # DIFFERENT, registry-validated tool than the pending selection, that
        # later selection wins for execution (tool_execution_node reads
        # `selected_tool`), and the stale pending_tool is cleared.
        selected = tool.name
        llm_tool = tool_registry.get_tool(output.tool_name) if output.tool_name else None
        if llm_tool and llm_tool.name != tool.name:
            selected = llm_tool.name
            logger.info(
                f"[{state.get('request_id')}] Tool Selection Node: tool-selection "
                f"override {tool.name} → {selected} (pending_tool cleared)."
            )

        updates: Dict[str, Any] = {
            "selected_tool": selected,
            "tool_arguments": output.tool_arguments,
        }
        if selected != tool.name:
            updates["pending_tool"] = None
        logger.info(f"[{state.get('request_id')}] Selected tool: {selected}")
        return updates
    except AllProvidersExhaustedException as e:
        logger.critical(f"[{state.get('request_id')}] Tool Selection Node: ALL providers exhausted — {e}")
        from app.shared.enums import ConversationStatus
        metadata = state.get("metadata", {}).copy()
        metadata["all_providers_exhausted"] = True
        return {
            "tool_arguments": {},
            "tool_status": "failed",
            "validation_errors": ["All LLM providers exhausted — cannot select tool arguments."],
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
            "metadata": metadata,
        }
    except (RateLimitException, InvalidAPIKeyException) as e:
        logger.error(f"[{state.get('request_id')}] API Limit/Key Error in Tool Selection Node: {e}")
        from app.shared.enums import ConversationStatus
        return {
            "tool_arguments": {},
            "tool_status": "failed",
            "validation_errors": [f"API Limit/Key Error: {str(e)}"],
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
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
    if not draft and state.get("selected_tool") != "search_logs":
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
    if tool_name_value == "search_logs":
        query = tool_args.get("query")
        if not isinstance(query, str) or len(query) > 256 or "\x00" in query or not any(c.isalnum() for c in query):
            message = "Enter search keywords or a document reference (up to 256 characters)."
            return {"tool_status": "failed", "tool_result": {"message": message}, "validation_errors": [message]}

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

    # Special handling: inject fields and metadata into save_log
    if tool_name_value == "save_log":
        if "fields" not in tool_args:
            tool_args["fields"] = draft.fields
        if "schema_name" not in tool_args and draft.schema_name:
            tool_args["schema_name"] = draft.schema_name
        if "domain" not in tool_args and draft.domain:
            tool_args["domain"] = draft.domain
        if "source" not in tool_args and draft.source:
            tool_args["source"] = draft.source
        if "field_metadata" not in tool_args:
            # Convert FieldMetadata pydantic models to dicts
            tool_args["field_metadata"] = {
                k: (v.model_dump() if hasattr(v, "model_dump") else v)
                for k, v in draft.field_metadata.items()
            }

    logger.info(f"[{state.get('request_id')}] Executing tool: {tool_name}")

    context: ToolExecutionContext = config["configurable"].get("tool_context")
    if not context:
        logger.error("ToolExecutionContext not found in config")
        return {"tool_status": "failed", "validation_errors": ["Execution context missing."]}

    if tool_name_value == "save_log" and decision.reset_context and not context.source_is_current_message:
        # A conversational pivot started a new record while the old file was still open.
        context = context.model_copy(update={"source_text": None, "source_filename": None, "excluded_fields": frozenset()})

    try:
        validated_args = tool.args_schema(**tool_args)

        result = await tool.execute(context, **validated_args.model_dump())

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
        if tool_name_value == "search_logs":
            logger.error(f"[{state.get('request_id')}] Search failed: {type(e).__name__}")
            message = "Document search is unavailable. Please try again."
            return {"tool_status": "failed", "tool_result": {"message": message}, "validation_errors": [message]}
        logger.error(f"[{state.get('request_id')}] Tool Execution Error: {e}")
        from app.shared.enums import ConversationStatus
        return {
            "tool_status": "failed",
            "validation_errors": [str(e)],
            "conversation_status": ConversationStatus.COLLECTING_INFORMATION,
        }


async def response_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Response Node: Generating response")
    if state.get("action") in ("save_reviewed", "capture"):
        if state["action"] == "capture":
            draft = state["log_draft"]
            response = ("Captured the original text as a note." if list(draft.fields) == ["text"]
                        else "Your extracted fields are ready for review.")
        else:
            result = state.get("tool_result") or {}
            response = result.get("message") or " ".join(state.get("validation_errors") or ["Could not save the record."])
        if state.get("conversation_id"):
            await conversation_memory_service.append_message(state["conversation_id"], "assistant", response, allow_compression=False)
        return {"llm_response": response}
    if state.get("detected_intent") == "search_logs":
        result = state.get("tool_result") or {}
        response = result.get("message") or "Enter search keywords or a document reference (up to 256 characters)."
        if result.get("results"):
            lines = [
                f"- {item['log_reference']} · {item.get('source_filename') or item['schema_name']}"
                for item in result["results"]
            ]
            response += "\n" + "\n".join(lines)
        if state.get("conversation_id"):
            await conversation_memory_service.append_message(
                state["conversation_id"], "assistant", response, allow_compression=False
            )
        return {"llm_response": response}
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
    except AllProvidersExhaustedException as e:
        logger.critical(f"[{state.get('request_id')}] Response Node: ALL providers exhausted — {e}")
        metadata = state.get("metadata", {}).copy()
        metadata["all_providers_exhausted"] = True
        response = "The document assistant is temporarily unavailable. Please try again later."
    except (RateLimitException, InvalidAPIKeyException) as e:
        logger.error(f"[{state.get('request_id')}] Response Node: API Limit/Key Error ({type(e).__name__}): {e}.")
        response = fallback_templates.generate_fallback_response(state)
    except ModelUnavailableException as e:
        logger.error(f"[{state.get('request_id')}] Response Node: Model Unavailable ({type(e).__name__}): {e}.")
        response = "I'm currently unable to process your request because the AI model is unavailable. Please try again later."
    except ProviderException as e:
        logger.warning(f"[{state.get('request_id')}] Response Node: Transient provider error ({type(e).__name__}): {e}. Using deterministic fallback.")
        response = fallback_templates.generate_fallback_response(state)

    if state.get("conversation_id"):
        await conversation_memory_service.append_message(state["conversation_id"], "assistant", response)

    return {"llm_response": response}


async def output_node(state: GraphState) -> Dict[str, Any]:
    logger.info(f"[{state.get('request_id')}] Output Node: Finalizing response")
    return {}

