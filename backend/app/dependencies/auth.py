import uuid
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.dependencies.db import get_db_session
from app.models.user import User
from app.repositories.user_repository import user_repository


async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> User:
    """
    FastAPI dependency to extract and validate Bearer token from the Authorization header.
    Returns the authenticated User or raises 401 Unauthorized.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def get_optional_current_user(
    db: AsyncSession = Depends(get_db_session),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[User]:
    """
    FastAPI dependency that returns the authenticated User if valid Bearer token is present,
    or None if no token or invalid token is supplied (without throwing 401).
    """
    if not authorization:
        return None

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            return None

        user_id = uuid.UUID(payload["sub"])
        user = await user_repository.get_by_id(db, user_id)
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None
