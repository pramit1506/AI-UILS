import uuid
from typing import List, Optional
from sqlalchemy import select, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log_record import LogRecord
from app.repositories.base_repository import BaseRepository
from app.schemas.log_record import LogRecordCreate, LogRecordUpdate


class LogRecordRepository(BaseRepository[LogRecord, LogRecordCreate, LogRecordUpdate]):
    def __init__(self):
        super().__init__(LogRecord)

    async def get_by_reference(
        self, db: AsyncSession, log_reference: str, user_id: Optional[uuid.UUID] = None
    ) -> Optional[LogRecord]:
        """Look up a log record by its human-readable reference ID, optionally scoped to a user."""
        stmt = select(LogRecord).where(LogRecord.log_reference == log_reference)
        if user_id is not None:
            stmt = stmt.where(LogRecord.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
        *,
        user_id: Optional[uuid.UUID] = None,
        needs_review: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[LogRecord]:
        """Retrieve all records, optionally filtered by owner user_id and needs_review."""
        stmt = select(LogRecord)
        if user_id is not None:
            stmt = stmt.where(LogRecord.user_id == user_id)
        if needs_review is not None:
            stmt = stmt.where(LogRecord.requires_review == needs_review)
        stmt = stmt.offset(skip).limit(limit).order_by(LogRecord.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_schema(
        self,
        db: AsyncSession,
        schema_name: str,
        *,
        user_id: Optional[uuid.UUID] = None,
        needs_review: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[LogRecord]:
        """Retrieve all records of a particular schema type for a user."""
        stmt = select(LogRecord).where(LogRecord.schema_name == schema_name)
        if user_id is not None:
            stmt = stmt.where(LogRecord.user_id == user_id)
        if needs_review is not None:
            stmt = stmt.where(LogRecord.requires_review == needs_review)
        stmt = stmt.offset(skip).limit(limit).order_by(LogRecord.created_at.desc())
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        db: AsyncSession,
        query: str,
        *,
        user_id: Optional[uuid.UUID] = None,
        schema_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[LogRecord]:
        """
        Full-text ILIKE search across schema_name, domain, summary, and the JSONB data cast to text.
        Optionally scoped to a specific user.
        """
        pattern = f"%{query}%"
        data_text = cast(LogRecord.data, String)

        conditions = or_(
            LogRecord.schema_name.ilike(pattern),
            LogRecord.domain.ilike(pattern),
            LogRecord.summary.ilike(pattern),
            LogRecord.log_reference.ilike(pattern),
            data_text.ilike(pattern),
        )

        stmt = select(LogRecord).where(conditions)
        if user_id is not None:
            stmt = stmt.where(LogRecord.user_id == user_id)
        if schema_name:
            stmt = stmt.where(LogRecord.schema_name == schema_name)
        stmt = stmt.order_by(LogRecord.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_conversation(
        self, db: AsyncSession, conversation_id: str, *, user_id: Optional[uuid.UUID] = None, limit: int = 20
    ) -> List[LogRecord]:
        """Get all log records created during a specific conversation."""
        stmt = select(LogRecord).where(LogRecord.conversation_id == conversation_id)
        if user_id is not None:
            stmt = stmt.where(LogRecord.user_id == user_id)
        stmt = stmt.order_by(LogRecord.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_reference(
        self, db: AsyncSession, log_reference: str, user_id: Optional[uuid.UUID] = None
    ) -> Optional[LogRecord]:
        """Delete a log record by its human-readable reference ID."""
        record = await self.get_by_reference(db, log_reference, user_id=user_id)
        if record:
            await db.delete(record)
            await db.commit()
        return record


log_record_repository = LogRecordRepository()
