from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db_session
from app.models.user import User
from app.repositories.log_record_repository import log_record_repository
from app.schemas.log_record import LogRecordRead, LogRecordUpdate
from app.shared.responses import APIResponse

router = APIRouter()


class SearchPage(APIResponse[List[LogRecordRead]]):
    next_cursor: str | None = None


class SavedSource(BaseModel):
    filename: str | None
    text: str


@router.get("/", response_model=APIResponse[List[LogRecordRead]])
async def list_logs(
    schema_name: Optional[str] = Query(None, description="Filter by schema type (e.g. Invoice, Resume)"),
    needs_review: Optional[bool] = Query(None, description="Filter records needing review"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all log records for the authenticated user, optionally filtered by schema type and review status."""
    user_id = current_user.id

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


@router.get("/search", response_model=SearchPage)
async def search_logs(
    q: str = Query(..., min_length=1, max_length=256, description="Words to find in a saved document"),
    schema_name: Optional[str] = Query(None, max_length=100),
    needs_review: Optional[bool] = Query(None),
    cursor: Optional[str] = Query(None, max_length=100),
    related: bool = Query(True),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Full-text search across log records for the authenticated user."""
    if not any(char.isalnum() for char in q):
        raise HTTPException(status_code=422, detail="Enter a word, number or document reference.")
    before = None
    if cursor is not None:
        try:
            stamp, record_id = cursor.split("|")
            timestamp = datetime.fromisoformat(stamp)
            if timestamp.tzinfo is None:
                raise ValueError("Cursor timestamp requires a timezone")
            before = (timestamp, UUID(record_id))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid search cursor.") from None
    records = await log_record_repository.search(
        db, query=q.strip(), user_id=current_user.id, schema_name=schema_name,
        needs_review=needs_review, before=before, limit=limit + 1, related=related,
    )
    page = records[:limit]
    next_cursor = None
    if len(records) > limit:
        last = page[-1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"
    return SearchPage(
        success=True,
        message=f"Retrieved {len(page)} matching records.",
        data=[LogRecordRead.model_validate(r) for r in page],
        next_cursor=next_cursor,
    )


@router.get("/{log_reference}/source", response_model=APIResponse[SavedSource])
async def get_saved_source(
    log_reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    source = await log_record_repository.get_source(db, log_reference, user_id=current_user.id)
    if source is None:
        raise HTTPException(status_code=404, detail="Saved source text was not found.")
    filename, body = source
    return APIResponse(success=True, message="Retrieved saved source.", data=SavedSource(filename=filename, text=body))


@router.get("/{log_reference}", response_model=APIResponse[LogRecordRead])
async def get_log(
    log_reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve a specific log record by its reference ID."""
    user_id = current_user.id
    record = await log_record_repository.get_by_reference(db, log_reference=log_reference, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")
    return APIResponse(
        success=True,
        message="Log record retrieved.",
        data=LogRecordRead.model_validate(record),
    )


@router.patch("/{log_reference}", response_model=APIResponse[LogRecordRead])
async def edit_log(
    log_reference: str,
    update: LogRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Edit a log record: replace field values (`data`), field metadata, the
    summary, and/or the review flag. Partial — only supplied keys change.

    When `data` is provided it replaces the stored field dict entirely; send
    the full set of fields you want to keep."""
    user_id = current_user.id
    record = await log_record_repository.get_by_reference(db, log_reference=log_reference, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")

    updates = update.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields supplied to update.")

    updated_record = await log_record_repository.update(db, db_obj=record, obj_in=updates)

    return APIResponse(
        success=True,
        message=f"Log record '{log_reference}' updated.",
        data=LogRecordRead.model_validate(updated_record),
    )


@router.patch("/{log_reference}/review", response_model=APIResponse[LogRecordRead])
async def mark_log_reviewed(
    log_reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Mark a log record as reviewed, removing it from the review queue."""
    user_id = current_user.id
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a specific log record by its reference ID."""
    user_id = current_user.id
    deleted_record = await log_record_repository.delete_by_reference(db, log_reference=log_reference, user_id=user_id)
    if not deleted_record:
        raise HTTPException(status_code=404, detail=f"Log record '{log_reference}' not found.")
    
    return APIResponse(
        success=True,
        message=f"Log record '{log_reference}' deleted successfully.",
        data={"log_reference": log_reference},
    )
