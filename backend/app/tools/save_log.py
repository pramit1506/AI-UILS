from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext
from app.repositories.log_record_repository import log_record_repository
from app.schemas.log_record import LogRecordCreate
import uuid


class SaveLogInput(BaseModel):
    schema_name: str = Field(..., description="The inferred schema/type of the document (e.g. Invoice, Resume, Medical Intake Form).")
    domain: Optional[str] = Field(None, description="The business domain (e.g. Finance, HR, Healthcare).")
    source: Optional[str] = Field(None, description="How the information arrived (e.g. pdf, email, text).")
    fields: Dict[str, Any] = Field(..., description="All extracted key-value pairs from the document.")
    summary: Optional[str] = Field(None, description="A one-sentence AI-generated summary of the log content.")


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

    def get_required_fields(self) -> list[str]:
        return ["schema_name"]

    async def execute(self, context: ToolExecutionContext, **kwargs) -> dict:
        context.logger.info(
            f"[{context.request_id}] Executing SaveLogTool for schema '{kwargs.get('schema_name')}'"
        )

        log_reference = f"LOG-{uuid.uuid4().hex[:8].upper()}"
        schema_name = kwargs["schema_name"]
        fields = kwargs.get("fields") or {}

        record = await log_record_repository.create(
            context.db,
            obj_in=LogRecordCreate(
                schema_name=schema_name,
                domain=kwargs.get("domain"),
                log_reference=log_reference,
                data=fields,
                field_metadata={},
                summary=kwargs.get("summary"),
                source=kwargs.get("source"),
                conversation_id=context.conversation_id,
            ),
        )

        return {
            "id": str(record.id),
            "log_reference": record.log_reference,
            "schema_name": record.schema_name,
            "status": "success",
            "message": f"Log saved successfully to the universal ledger. Reference: {log_reference}",
        }
