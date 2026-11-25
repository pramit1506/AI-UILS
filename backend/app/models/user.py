import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.database.mixins import UUIDMixin, TimestampMixin


class User(UUIDMixin, TimestampMixin, Base):
    """
    SQLAlchemy User model for authentication and multi-user profile management.
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    session_version: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    recovery_digest: Mapped[str | None] = mapped_column(String(64))
    recovery_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_attempts: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    # Authentication reads the user on every private request. Load records
    # explicitly only when needed so a lookup does not fetch the entire ledger.
    logs = relationship("LogRecord", back_populates="user", cascade="all, delete-orphan", lazy="raise")
