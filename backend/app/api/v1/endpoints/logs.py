from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_optional_current_user
from app.dependencies.db import get_db_session
from app.models.user import User
from app.repositories.log_record_repository import log_record_repository
from app.schemas.log_record import LogRecordRead
from app.shared.responses import APIResponse

router = APIRouter()


@router.get("/", response_model=APIResponse[List[LogRecordRead]])
async def list_logs(
    schema_name: Optional[str] = Query(None, description="Filter by schema type (e.g. Invoice, Resume)"),
    needs_review: Optional[bool] = Query(None, description="Filter records needing review"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all log records for the current user, optionally filtered by schema type and review status."""
    user_id = current_user.id if current_user else None

    if schema_name:
        records = await log_record_repository.get_by_schema(
            db, schema_name=schema_name, user_id=user_id, needs_review=needs_review, skip=skip, limit=limit
        )
    else:
        records = await log_record_repository.get_all(
            db, user_id=user_id, needs_review=needs_review, skip=skip, limit=limit
        )

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
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Full-text search across log records for the current user."""
    user_id = current_user.id if current_user else None
    records = await log_record_repository.search(
        db, query=q, user_id=user_id, schema_name=schema_name, limit=limit
    )
    return APIResponse(
        success=True,
        message=f"Found {len(records)} result(s) for '{q}'.",
        data=[LogRecordRead.model_validate(r) for r in records],
    )


@router.get("/{log_reference}", response_model=APIResponse[LogRecordRead])
async def get_log(
    log_reference: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve a specific log record by its reference ID."""
    user_id = current_user.id if current_user else None
    record = await log_record_repository.get_by_reference(db, log_reference=log_reference, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")
    return APIResponse(
        success=True,
        message="Log record retrieved.",
        data=LogRecordRead.model_validate(record),
    )


@router.patch("/{log_reference}/review", response_model=APIResponse[LogRecordRead])
async def mark_log_reviewed(
    log_reference: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Mark a log record as reviewed, removing it from the review queue."""
    user_id = current_user.id if current_user else None
    record = await log_record_repository.get_by_reference(db, log_reference=log_reference, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")
    
    updated_record = await log_record_repository.update(db, db_obj=record, obj_in={"requires_review": False})
    
    return APIResponse(
        success=True,
        message="Log record marked as reviewed.",
        data=LogRecordRead.model_validate(updated_record),
    )


@router.delete("/{log_reference}", response_model=APIResponse[dict])
async def delete_log(
    log_reference: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a specific log record by its reference ID."""
    user_id = current_user.id if current_user else None
    deleted_record = await log_record_repository.delete_by_reference(db, log_reference=log_reference, user_id=user_id)
    if not deleted_record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")
    
    return APIResponse(
        success=True,
        message=f"Log record '{log_reference}' deleted successfully.",
        data={"log_reference": log_reference},
    )
