from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext
from app.repositories.log_record_repository import log_record_repository


class SearchLogsInput(BaseModel):
    query: str = Field(..., description="Natural language search query (e.g. 'invoice for vendor Acme', 'resume for John Doe').")
    schema_name: Optional[str] = Field(None, description="Optional: filter results by schema type (e.g. Invoice, Resume).")
    limit: int = Field(5, description="Maximum number of results to return.")


class SearchLogsOutput(BaseModel):
    results: List[Dict[str, Any]]
    count: int
    message: str


class SearchLogsTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_logs"

    @property
    def description(self) -> str:
        return (
            "Search the universal log ledger for previously saved records using natural language. "
            "Use this when the user asks to 'find', 'retrieve', 'look up', or 'recall' a past log. "
            "Can filter by document type (schema) and searches across all field values."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        return SearchLogsInput

    @property
    def return_schema(self) -> type[BaseModel]:
        return SearchLogsOutput

    def get_required_fields(self) -> list[str]:
        return ["query"]

    async def execute(self, context: ToolExecutionContext, **kwargs) -> dict:
        query = kwargs["query"]
        schema_name = kwargs.get("schema_name")
        limit = kwargs.get("limit", 5)

        context.logger.info(
            f"[{context.request_id}] SearchLogsTool: query='{query}', schema='{schema_name}'"
        )

        user_id = context.current_user.id if context.current_user else None
        records = await log_record_repository.search(
            context.db,
            query=query,
            user_id=user_id,
            schema_name=schema_name,
            limit=limit,
        )

        results = []
        for r in records:
            results.append({
                "id": str(r.id),
                "log_reference": r.log_reference,
                "schema_name": r.schema_name,
                "domain": r.domain,
                "summary": r.summary,
                "data": r.data,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

        return {
            "results": results,
            "count": len(results),
            "message": (
                f"Found {len(results)} log record(s) matching '{query}'."
                if results
                else f"No log records found matching '{query}'."
            ),
        }
