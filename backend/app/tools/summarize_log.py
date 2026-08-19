from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext
from app.llm.factory import get_llm_provider


class SummarizeLogInput(BaseModel):
    schema_name: str = Field(..., description="The type/schema of the document being summarized.")
    fields: Dict[str, Any] = Field(..., description="The key-value fields extracted from the document.")


class SummarizeLogOutput(BaseModel):
    summary: str
    message: str


class SummarizeLogTool(BaseTool):
    @property
    def name(self) -> str:
        return "summarize_log"

    @property
    def description(self) -> str:
        return (
            "Generate a concise one-sentence summary of any log record's content. "
            "Works for any document type or schema."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        return SummarizeLogInput

    @property
    def return_schema(self) -> type[BaseModel]:
        return SummarizeLogOutput

    def get_required_fields(self) -> list[str]:
        return ["schema_name", "fields"]

    async def execute(self, context: ToolExecutionContext, **kwargs) -> dict:
        schema_name = kwargs["schema_name"]
        fields = kwargs.get("fields") or {}
        fields_text = "\n".join(f"- {k}: {v}" for k, v in fields.items() if v)

        llm = get_llm_provider()
        prompt = (
            f"You are summarizing a {schema_name} record. "
            f"Produce a single clear sentence that captures the essential information.\n\n"
            f"Fields:\n{fields_text}"
        )
        try:
            response = await llm.generate_response([{"role": "user", "content": prompt}])
        except Exception as e:
            from app.exceptions.base import RateLimitException, InvalidAPIKeyException
            if isinstance(e, (RateLimitException, InvalidAPIKeyException)):
                raise e
            # Fallback: build a mechanical summary from the first few non-empty fields
            top_fields = [(k, v) for k, v in fields.items() if v][:4]
            response = f"{schema_name}: " + "; ".join(f"{k}={v}" for k, v in top_fields)

        return {
            "summary": response,
            "message": "Summarization complete.",
        }
