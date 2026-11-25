# Dynamic Log Draft

The Dynamic Log Draft represents the AI's current, evolving understanding of the document or structured record throughout a conversational intake session in Nikarsh AI. It serves as the single source of truth for the session state and dynamically populates the React UI form on the frontend.

## Architecture & Lifecycle

1. **Initialization**: When a conversation starts or a new intent indicates document logging, a `DynamicLogDraft` is instantiated. It is added to the `GraphState`. The draft is a schema-agnostic Pydantic model (`app.schemas.draft.DynamicLogDraft`).
2. **Updates & Extraction**: As the conversation progresses, new information is extracted by the LLM or regex fallback. This information is merged into the draft using `app.services.draft_service.DraftService`.
3. **DraftService (Immutability)**: Every operation (`merge`, `update_field`, `remove_field`, `correct_field`) via the `DraftService` returns a `DraftUpdateResult` containing a fresh `DynamicLogDraft` copy, the list of `changed_fields`, and a `merge_summary`. This guarantees immutability, which is essential for deterministic LangGraph state transitions.
4. **Validation & Status**: `DraftService.validate(draft)` analyzes the draft against dynamic field requirements. It automatically derives a `DraftStatus` (`EMPTY`, `PARTIAL`, `READY`, `CONFIRMED`, `SAVED`).
5. **Completion**: Once the draft is `READY` (or manually marked as `CONFIRMED`) and the user saves or confirms, the log record is saved into PostgreSQL.

## GraphState Integration

The `GraphState` includes a `log_draft` field:
```python
class GraphState(TypedDict):
    log_draft: Optional[DynamicLogDraft]
    # ... other fields
```

## Immutable Draft Updates & Change Tracking

The `DraftService` provides the public API for all updates. Updates return a `DraftUpdateResult`:
- `updated_draft`: The new `DynamicLogDraft` instance.
- `changed_fields`: A list of strings identifying exactly which fields were modified. This enables granular frontend state updates.
- `merge_summary`: Human-readable summary of the operation.

## Field Metadata

The `DynamicLogDraft` includes `field_metadata: Dict[str, FieldMetadata]`.
`FieldMetadata` tracks:
- `value`: The extracted field value.
- `confidence`: AI confidence score for the extraction (0.0 to 1.0).
- `source`: The source of the value (e.g., "llm", "user_edit", "pdf", "email").
- `last_updated`: Timestamp of the change.

This structure allows rich metadata and confidence tracking across arbitrary domain schemas.
