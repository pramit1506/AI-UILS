import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LogRecordCreate(BaseModel):
    schema_name: str
    domain: Optional[str] = None
    log_reference: str
    data: Dict[str, Any] = Field(default_factory=dict)
    field_metadata: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    source: Optional[str] = None
    conversation_id: Optional[str] = None


class LogRecordUpdate(BaseModel):
    data: Optional[Dict[str, Any]] = None
    field_metadata: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None


class LogRecordRead(BaseModel):
    id: uuid.UUID
    schema_name: str
    domain: Optional[str]
    log_reference: str
    data: Dict[str, Any]
    summary: Optional[str]
    source: Optional[str]
    conversation_id: Optional[str]

    class Config:
        from_attributes = True
