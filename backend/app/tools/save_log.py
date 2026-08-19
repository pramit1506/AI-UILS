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
            "Save the extracted log data into the universal ledger. "
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
        field_metadata = kwargs.get("field_metadata") or {}

        non_empty_fields = {
            k: v for k, v in fields.items()
            if not k.startswith("_") and v is not None and v != "" and v != []
        }
        if not non_empty_fields:
            return {
                "status": "error",
                "message": "Cannot save log: No extracted data fields found. Please provide document content first.",
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
                data=jsonable_encoder(fields),
                field_metadata=jsonable_encoder(field_metadata),
                summary=kwargs.get("summary"),
                source=kwargs.get("source"),
                conversation_id=context.conversation_id,
                user_id=context.current_user.id if context.current_user else None,
                requires_review=requires_review,
                overall_confidence=overall_confidence,
            ),
        )

        return {
            "id": str(record.id),
            "log_reference": record.log_reference,
            "schema_name": record.schema_name,
            "status": "success",
            "message": f"Log saved successfully to the universal ledger. Reference: {log_reference}",
        }
