from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext


class CompletenessInput(BaseModel):
    schema_name: str = Field(..., description="The inferred schema/type of the document.")
    fields: Dict[str, Any] = Field(..., description="All extracted fields so far.")


class CompletenessOutput(BaseModel):
    is_complete: bool
    missing_critical_fields: List[str]
    message: str


class CompletenessCheckerTool(BaseTool):
    @property
    def name(self) -> str:
        return "completeness_check"

    @property
    def description(self) -> str:
        return (
            "Check whether the current log draft has a sufficient number of fields to be saved. "
            "Works for any document type. At minimum, schema_name and at least one data field must be present."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        return CompletenessInput

    @property
    def return_schema(self) -> type[BaseModel]:
        return CompletenessOutput

    def get_required_fields(self) -> list[str]:
        return ["schema_name", "fields"]

    async def execute(self, context: ToolExecutionContext, **kwargs) -> dict:
        schema_name = kwargs.get("schema_name", "")
        fields = kwargs.get("fields") or {}

        missing = []
        if not schema_name:
            missing.append("schema_name (document type could not be inferred)")
        if not any(v for v in fields.values() if v is not None):
            missing.append("At least one data field must be extracted before saving.")

        return {
            "is_complete": len(missing) == 0,
            "missing_critical_fields": missing,
            "message": (
                "Log draft has sufficient data to save."
                if len(missing) == 0
                else "Log draft is incomplete and cannot be saved yet."
            ),
        }
