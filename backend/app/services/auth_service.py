import uuid
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import (
    AccountDeleteRequest,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
    UserUpdate,
)


class AuthService:
    """
    Business logic for user authentication, registration, password reset, account deletion, and profile management.
    """

    async def register(self, db: AsyncSession, user_in: UserCreate) -> Tuple[User, str]:
        """
        Register a new user account, returning the created user and their access token.
        """
        # Check if email is already taken
        existing_email = await user_repository.get_by_email(db, user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

        # Check if username is already taken
        existing_username = await user_repository.get_by_username(db, user_in.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This username is already taken. Please choose another one.",
            )

        hashed_password = get_password_hash(user_in.password)
        user = await user_repository.create_user(
            db,
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=user_in.role or "user",
            avatar_url=user_in.avatar_url,
            bio=user_in.bio,
        )

        token = create_access_token(
            subject=str(user.id),
            extra_claims={"username": user.username, "email": user.email, "role": user.role}
        )
        logger.info(f"User registered successfully: {user.username} ({user.id})")
        return user, token

    async def login(self, db: AsyncSession, login_in: UserLogin) -> Tuple[User, str]:
        """
        Authenticate a user by email/username and password.
        """
        user = await user_repository.get_by_login(db, login_in.login)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(login_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username/email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been disabled.",
            )

        token = create_access_token(
            subject=str(user.id),
            extra_claims={"username": user.username, "email": user.email, "role": user.role}
        )
        logger.info(f"User logged in: {user.username} ({user.id})")
        return user, token

    async def reset_password(
        self, db: AsyncSession, reset_in: PasswordResetRequest
    ) -> Tuple[User, str]:
        """
        Reset a user's password using their email or username and immediately issue a new access token.
        """
        user = await user_repository.get_by_login(db, reset_in.login)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found matching this email or username.",
            )

        if len(reset_in.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters long.",
            )

        new_hashed = get_password_hash(reset_in.new_password)
        updated_user = await user_repository.update_password(
            db, user=user, hashed_password=new_hashed
        )

        token = create_access_token(
            subject=str(updated_user.id),
            extra_claims={
                "username": updated_user.username,
                "email": updated_user.email,
                "role": updated_user.role,
            },
        )
        logger.info(f"Password reset successfully for user: {updated_user.username} ({updated_user.id})")
        return updated_user, token

    async def delete_account(self, db: AsyncSession, user: User) -> None:
        """
        Permanently delete an authenticated user account and all associated log records.
        """
        logger.info(f"Deleting user account: {user.username} ({user.id})")
        await user_repository.delete_user(db, user)

    async def delete_account_by_email(
        self, db: AsyncSession, delete_in: AccountDeleteRequest
    ) -> None:
        """
        Delete an account by email for account recovery / purging orphaned accounts.
        """
        user = await user_repository.get_by_email(db, delete_in.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address.",
            )

        logger.info(f"Account deleted via recovery request: {user.email} ({user.id})")
        await user_repository.delete_user(db, user)

    async def update_profile(self, db: AsyncSession, user: User, update_in: UserUpdate) -> User:
        """
        Update a user's editable profile information.
        """
        updates = {}
        if update_in.full_name is not None:
            updates["full_name"] = update_in.full_name.strip() if update_in.full_name else None
        if update_in.bio is not None:
            updates["bio"] = update_in.bio.strip() if update_in.bio else None
        if update_in.avatar_url is not None:
            updates["avatar_url"] = update_in.avatar_url
        if update_in.username is not None and update_in.username.strip() != user.username:
            existing = await user_repository.get_by_username(db, update_in.username.strip())
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This username is already taken.",
                )
            updates["username"] = update_in.username.strip()

        if updates:
            updated_user = await user_repository.update(db, db_obj=user, obj_in=updates)
            return updated_user
        return user


auth_service = AuthService()
