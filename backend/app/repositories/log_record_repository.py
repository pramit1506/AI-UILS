import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import func, select, text, tuple_, or_, and_
from app.database.identifier_prefixes import INDEXED_PREFIX_LENGTH
from app.services.search_vocabulary import related_terms
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
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
        user_id: uuid.UUID,
        schema_name: Optional[str] = None,
        needs_review: Optional[bool] = None,
        before: tuple[datetime, uuid.UUID] | None = None,
        references_only: bool = False,
        related: bool = True,
        limit: int = 10,
    ) -> List[LogRecord]:
        """Find records containing every query keyword with an owner-scoped keyset."""
        if user_id is None:
            raise ValueError("Search requires an authenticated owner")
        if not 1 <= len(query.strip()) <= 256 or not 1 <= limit <= 51:
            raise ValueError("Invalid search query length or result limit")

        stmt = select(LogRecord).where(LogRecord.user_id == user_id)
        if related:
            keywords = await db.scalar(select(func.uils_search_terms_v1(query)))
            if not keywords:
                return []
            prefixes = LogRecord.search_prefixes
            for word in keywords:
                match = LogRecord.search_terms.overlap(related_terms(word))
                if len(word) >= 3 and word.isalnum():
                    prefix_match = prefixes.contains([word[:INDEXED_PREFIX_LENGTH]])
                    if len(word) > INDEXED_PREFIX_LENGTH:
                        # Confirm long prefixes on documents passing the indexed prefix.
                        term = func.unnest(LogRecord.search_terms).column_valued("term")
                        longer_match = select(1).where(func.starts_with(term, word)).correlate(LogRecord).exists()
                        prefix_match = and_(prefix_match, longer_match)
                    match = or_(match, prefix_match)
                stmt = stmt.where(match)
        else:
            stmt = stmt.where(LogRecord.search_terms.contains(func.uils_search_terms_v1(query)))
        if references_only:
            stmt = stmt.options(load_only(LogRecord.log_reference, LogRecord.schema_name, LogRecord.source_filename))
        if schema_name:
            stmt = stmt.where(LogRecord.schema_name == schema_name)
        if needs_review is not None:
            stmt = stmt.where(LogRecord.requires_review == needs_review)
        if before:
            stmt = stmt.where(tuple_(LogRecord.created_at, LogRecord.id) < before)
        # A frequent term benefits from walking the owner's newest records and
        # stopping at the limit. A rare term benefits from the inverted index.
        # A generic prepared plan cannot see the supplied terms or their frequency.
        await db.execute(text("SET LOCAL plan_cache_mode = force_custom_plan"))
        if related and any(len(word) >= 3 and word.isalnum() for word in keywords):
            # An ordered LIMIT can make the planner walk the entire owner's date
            # index and recompute prefixes on every row when a typed word misses.
            # Plan the keyword lookup without the ordering or limit. PostgreSQL
            # streams this CTE and the consumer stops once the match is common.
            candidates = stmt.with_only_columns(LogRecord.id).cte("keyword_hits").prefix_with("MATERIALIZED")
            probe_size = limit * 2 + 1
            ids = (await db.scalars(select(candidates.c.id).limit(probe_size))).all()
            if not ids:
                return []
            if len(ids) < probe_size:
                stmt = stmt.where(LogRecord.id.in_(ids))
        stmt = stmt.order_by(LogRecord.created_at.desc(), LogRecord.id.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_source(
        self, db: AsyncSession, log_reference: str, *, user_id: uuid.UUID
    ) -> tuple[str | None, str] | None:
        if user_id is None:
            raise ValueError("Reading a source requires an authenticated owner")
        result = await db.execute(
            select(LogRecord.source_filename, LogRecord.source_text).where(
                LogRecord.user_id == user_id,
                LogRecord.log_reference == log_reference,
                LogRecord.source_text.is_not(None),
            )
        )
        return result.tuples().one_or_none()

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
