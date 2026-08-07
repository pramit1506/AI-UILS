from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext
from app.repositories.log_record_repository import log_record_repository
import uuid


class EditLogInput(BaseModel):
    log_reference: str = Field(..., description="The log reference ID of the record to edit (e.g. LOG-ABC12345).")
    field_updates: Dict[str, Any] = Field(..., description="Key-value pairs of fields to update in the log record.")


class EditLogOutput(BaseModel):
    log_reference: str
    updated_fields: list
    message: str


class EditLogTool(BaseTool):
    @property
    def name(self) -> str:
        return "edit_log"

    @property
    def description(self) -> str:
        return (
            "Edit or update specific fields in a saved log record. "
            "Use this when the user wants to correct or change data in a previously saved log."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        return EditLogInput

    @property
    def return_schema(self) -> type[BaseModel]:
        return EditLogOutput

    def get_required_fields(self) -> list[str]:
        return ["log_reference", "field_updates"]

    async def execute(self, context: ToolExecutionContext, **kwargs) -> dict:
        log_reference = kwargs["log_reference"]
        field_updates = kwargs.get("field_updates") or {}
        context.logger.info(
            f"[{context.request_id}] EditLogTool: Updating {log_reference} with {list(field_updates.keys())}"
        )

        record = await log_record_repository.get_by_reference(context.db, log_reference=log_reference)
        if not record:
            return {
                "log_reference": log_reference,
                "updated_fields": [],
                "message": f"Log record '{log_reference}' not found.",
            }

        # Merge field_updates into existing data
        merged_data = {**(record.data or {}), **field_updates}
        await log_record_repository.update(context.db, db_obj=record, obj_in={"data": merged_data})

        return {
            "log_reference": log_reference,
            "updated_fields": list(field_updates.keys()),
            "message": f"Log record '{log_reference}' updated successfully.",
        }
