import uuid
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Look up a user by UUID id."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Look up a user by email (case-insensitive)."""
        result = await db.execute(select(User).where(User.email.ilike(email.strip())))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Look up a user by username (case-insensitive)."""
        result = await db.execute(select(User).where(User.username.ilike(username.strip())))
        return result.scalar_one_or_none()

    async def get_by_login(self, db: AsyncSession, login: str) -> Optional[User]:
        """Look up a user by email OR username."""
        clean_login = login.strip()
        result = await db.execute(
            select(User).where(
                or_(
                    User.email.ilike(clean_login),
                    User.username.ilike(clean_login)
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        *,
        email: str,
        username: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        role: str = "user",
        avatar_url: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> User:
        """Create a new user with hashed password."""
        db_user = User(
            email=email.strip().lower(),
            username=username.strip(),
            hashed_password=hashed_password,
            full_name=full_name.strip() if full_name else None,
            role=role,
            avatar_url=avatar_url,
            bio=bio.strip() if bio else None,
            is_active=True,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def update_password(
        self,
        db: AsyncSession,
        *,
        user: User,
        hashed_password: str,
    ) -> User:
        """Update a user's hashed password."""
        user.hashed_password = hashed_password
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def delete_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Delete a user account by email address."""
        user = await self.get_by_email(db, email)
        if user:
            await db.delete(user)
            await db.commit()
        return user

    async def delete_user(self, db: AsyncSession, user: User) -> User:
        """Delete a user account."""
        await db.delete(user)
        await db.commit()
        return user


user_repository = UserRepository()
