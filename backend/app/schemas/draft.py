from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def get_utc_now():
    return datetime.now(timezone.utc)


class FieldMetadata(BaseModel):
    """Tracks AI confidence and provenance for each extracted field."""
    value: Any = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    last_updated: Optional[datetime] = Field(default_factory=get_utc_now)


class DynamicLogDraft(BaseModel):
    """
    A flexible, domain-agnostic log draft.
    The AI infers the schema from document content and fills `fields` accordingly.
    No hardcoded domain-specific attributes — works for invoices, resumes, medical forms, etc.
    """
    # Schema / domain inferred by AI from the document
    schema_name: Optional[str] = None       # e.g. "Invoice", "Medical Intake Form", "Resume"
    domain: Optional[str] = None            # e.g. "Finance", "Healthcare", "HR"
    source: Optional[str] = None            # e.g. "pdf", "text", "email"

    # All extracted key-value pairs live here — completely dynamic
    fields: Dict[str, Any] = Field(default_factory=dict)

    # Per-field AI confidence metadata
    field_metadata: Dict[str, FieldMetadata] = Field(default_factory=dict)


class DraftUpdateResult(BaseModel):
    updated_draft: DynamicLogDraft
    changed_fields: List[str]
    merge_summary: str
