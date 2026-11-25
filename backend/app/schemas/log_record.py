import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LogRecordCreate(BaseModel):
    schema_name: str
    domain: Optional[str] = None
    log_reference: str
    data: Dict[str, Any] = Field(default_factory=dict)
    field_metadata: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    source: Optional[str] = None
    source_filename: Optional[str] = None
    source_text: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    requires_review: bool = False
    overall_confidence: Optional[float] = None


class LogRecordUpdate(BaseModel):
    data: Optional[Dict[str, Any]] = None
    field_metadata: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    requires_review: Optional[bool] = None
    overall_confidence: Optional[float] = None


class LogRecordRead(BaseModel):
    id: uuid.UUID
    schema_name: str
    domain: Optional[str] = None
    log_reference: str
    data: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    source: Optional[str] = None
    source_filename: Optional[str] = None
    has_source_text: bool = False
    conversation_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    requires_review: bool = False
    overall_confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
