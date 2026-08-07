from typing import List, Optional
from sqlalchemy import select, or_, cast, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log_record import LogRecord
from app.repositories.base_repository import BaseRepository
from app.schemas.log_record import LogRecordCreate, LogRecordUpdate


class LogRecordRepository(BaseRepository[LogRecord, LogRecordCreate, LogRecordUpdate]):
    def __init__(self):
        super().__init__(LogRecord)

    async def get_by_reference(self, db: AsyncSession, log_reference: str) -> Optional[LogRecord]:
        """Look up a log record by its human-readable reference ID."""
        result = await db.execute(
            select(LogRecord).where(LogRecord.log_reference == log_reference)
        )
        return result.scalar_one_or_none()

    async def get_by_schema(
        self, db: AsyncSession, schema_name: str, *, skip: int = 0, limit: int = 50
    ) -> List[LogRecord]:
        """Retrieve all records of a particular schema type."""
        result = await db.execute(
            select(LogRecord)
            .where(LogRecord.schema_name == schema_name)
            .offset(skip)
            .limit(limit)
            .order_by(LogRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def search(
        self,
        db: AsyncSession,
        query: str,
        *,
        schema_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[LogRecord]:
        """
        Full-text ILIKE search across schema_name, domain, summary, and the JSONB data cast to text.
        Used by the search_logs tool for AI-driven memory retrieval.
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
        if schema_name:
            stmt = stmt.where(LogRecord.schema_name == schema_name)
        stmt = stmt.order_by(LogRecord.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_conversation(
        self, db: AsyncSession, conversation_id: str, *, limit: int = 20
    ) -> List[LogRecord]:
        """Get all log records created during a specific conversation."""
        result = await db.execute(
            select(LogRecord)
            .where(LogRecord.conversation_id == conversation_id)
            .order_by(LogRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


log_record_repository = LogRecordRepository()
