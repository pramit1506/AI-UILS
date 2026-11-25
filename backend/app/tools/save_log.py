from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext
from app.repositories.log_record_repository import log_record_repository
from app.schemas.log_record import LogRecordCreate
from fastapi.encoders import jsonable_encoder
import uuid


class SaveLogInput(BaseModel):
    schema_name: str = Field(..., description="The inferred schema/type of the document (e.g. Invoice, Resume, Medical Intake Form).")
    domain: Optional[str] = Field(None, description="The business domain (e.g. Finance, HR, Healthcare).")
    source: Optional[str] = Field(None, description="How the information arrived (e.g. pdf, email, text).")
    fields: Dict[str, Any] = Field(..., description="All extracted key-value pairs from the document.")
    summary: Optional[str] = Field(None, description="A one-sentence AI-generated summary of the log content.")
    field_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata for fields including confidence scores.")


class SaveLogOutput(BaseModel):
    id: str
    log_reference: str
    schema_name: str
    status: str
    message: str


class SaveLogTool(BaseTool):
    @property
    def name(self) -> str:
        return "save_log"

    @property
    def description(self) -> str:
        return (
            "Save the extracted fields as a record in Nikarsh AI. "
            "Use this when the user wants to save, log, record, or store the current document data. "
            "Works for any document type: invoices, resumes, contracts, medical forms, receipts, etc."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        return SaveLogInput

    @property
    def return_schema(self) -> type[BaseModel]:
        return SaveLogOutput

    # Schema-specific minimum required fields for a meaningful log.
    # These are the fields we will CLARIFY if missing.
    SCHEMA_REQUIRED_FIELDS: dict[str, list[str]] = {
        "Invoice": ["invoice_number", "invoice_date", "vendor", "total_amount"],
        "Resume": ["candidate_name"],
        "Contract": ["parties", "effective_date"],
        "Medical Record": ["patient_name", "diagnosis"],
        "Receipt": ["total_amount"],
        "Complaint": ["description", "customer_name"],
    }

    def get_required_fields(self) -> list[str]:
        """Minimum required: just schema_name (before we know the type)."""
        return ["schema_name"]

    def get_required_fields_for_schema(self, schema_name: str | None) -> list[str]:
        """Return the schema-specific required fields for a known document type."""
        if not schema_name:
            return ["schema_name"]
        return self.SCHEMA_REQUIRED_FIELDS.get(schema_name, [])


    async def execute(self, context: ToolExecutionContext, **kwargs) -> dict:
        context.logger.info(
            f"[{context.request_id}] Executing SaveLogTool for schema '{kwargs.get('schema_name')}'"
        )

        log_reference = f"LOG-{uuid.uuid4().hex[:8].upper()}"
        schema_name = kwargs["schema_name"]
        fields = kwargs.get("fields") or {}
        field_metadata = {k: v for k, v in (kwargs.get("field_metadata") or {}).items()
                          if k not in context.excluded_fields}

        non_empty_fields = {
            k: v for k, v in fields.items()
            if k not in context.excluded_fields and not k.startswith("_") and v is not None and v != "" and v != []
        }
        if not non_empty_fields:
            return {
                "status": "error",
                "message": "Cannot save log: No extracted data fields found. Please provide document content first.",
            }

        # Guest wall: unauthenticated visitors can chat and draft freely, but
        # records may only be written to a signed-in account (user-scoped DB
        # rows). Returning a structured error here makes the AI explain the
        # wall in chat, and the frontend raises its own "login to save"
        # modal so the guest is never left with a silent failure. (Checked
        # AFTER the empty-fields case: an empty draft is a drafting problem,
        # not an auth problem.)
        if not context.current_user:
            return {
                "status": "error",
                "login_required": True,
                "message": (
                    "Login required to save. As a guest you can draft and verify "
                    "information, but records can only be stored to a signed-in "
                    "account. Sign in to keep this log — otherwise everything you "
                    "captured will be discarded when you leave the page."
                ),
            }

        overall_confidence = None
        requires_review = False
        
        confidences = []
        for field, meta in field_metadata.items():
            conf = meta.get("confidence")
            if isinstance(conf, (int, float)):
                confidences.append(conf)
                # BUG-002 fix: threshold aligned to frontend "High" boundary (≥ 0.75)
                if conf < 0.75:
                    requires_review = True
                    
        if confidences:
            overall_confidence = sum(confidences) / len(confidences)
            # Flag for review if average confidence is below the High threshold
            if overall_confidence < 0.75:
                requires_review = True

        record = await log_record_repository.create(
            context.db,
            obj_in=LogRecordCreate(
                schema_name=schema_name,
                domain=kwargs.get("domain"),
                log_reference=log_reference,
                # Persist only the cleaned public fields — internal keys
                # (`_source`, `_raw_text`, …) previously leaked into the
                # stored JSONB and crossed the API boundary via LogRecordRead.
                data=jsonable_encoder(non_empty_fields),
                field_metadata=jsonable_encoder(field_metadata),
                summary=kwargs.get("summary"),
                source=kwargs.get("source"),
                source_filename=context.source_filename,
                source_text=context.source_text,
                conversation_id=context.conversation_id,
                user_id=context.current_user.id,
                requires_review=requires_review,
                overall_confidence=overall_confidence,
            ),
        )

        return {
            "id": str(record.id),
            "log_reference": record.log_reference,
            "schema_name": record.schema_name,
            "status": "success",
            "message": f"Record saved in Nikarsh AI. Reference: {log_reference}",
        }
