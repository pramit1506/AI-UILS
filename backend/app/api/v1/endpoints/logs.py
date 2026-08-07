from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db_session
from app.repositories.log_record_repository import log_record_repository
from app.shared.responses import APIResponse
from app.schemas.log_record import LogRecordRead

router = APIRouter()


@router.get("/", response_model=APIResponse[List[LogRecordRead]])
async def list_logs(
    schema_name: Optional[str] = Query(None, description="Filter by schema type (e.g. Invoice, Resume)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    """List all log records, optionally filtered by schema type."""
    if schema_name:
        records = await log_record_repository.get_by_schema(db, schema_name=schema_name, skip=skip, limit=limit)
    else:
        records = await log_record_repository.get_all(db, skip=skip, limit=limit)

    return APIResponse(
        success=True,
        message=f"Retrieved {len(records)} log record(s).",
        data=[LogRecordRead.model_validate(r) for r in records],
    )


@router.get("/search", response_model=APIResponse[List[LogRecordRead]])
async def search_logs(
    q: str = Query(..., description="Search query across all fields"),
    schema_name: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
):
    """Full-text search across all log records using ILIKE queries."""
    records = await log_record_repository.search(db, query=q, schema_name=schema_name, limit=limit)
    return APIResponse(
        success=True,
        message=f"Found {len(records)} result(s) for '{q}'.",
        data=[LogRecordRead.model_validate(r) for r in records],
    )


@router.get("/{log_reference}", response_model=APIResponse[LogRecordRead])
async def get_log(
    log_reference: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve a specific log record by its reference ID."""
    record = await log_record_repository.get_by_reference(db, log_reference=log_reference)
    if not record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")
    return APIResponse(
        success=True,
        message="Log record retrieved.",
        data=LogRecordRead.model_validate(record),
    )
