from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db_session
from app.models.user import User
from app.schemas.user import (
    AccountDeleteRequest,
    PasswordResetRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)
from app.services.auth_service import auth_service
from app.shared.responses import APIResponse

router = APIRouter()


@router.post("/register", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[TokenResponse]:
    """
    Register a new user profile with email, username, and password.
    Returns the created user details along with a JWT access token.
    """
    user, access_token = await auth_service.register(db, user_in)
    return APIResponse(
        success=True,
        message=f"Welcome {user.full_name or user.username}! Account created successfully.",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        ),
    )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    login_in: UserLogin,
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[TokenResponse]:
    """
    Sign in to an existing account with username or email.
    """
    user, access_token = await auth_service.login(db, login_in)
    return APIResponse(
        success=True,
        message=f"Welcome back, {user.full_name or user.username}!",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        ),
    )


@router.post("/reset-password", response_model=APIResponse[TokenResponse])
async def reset_password(
    reset_in: PasswordResetRequest,
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[TokenResponse]:
    """
    Reset password for an existing user account and issue a fresh access token.
    """
    user, access_token = await auth_service.reset_password(db, reset_in)
    return APIResponse(
        success=True,
        message="Password has been reset successfully. You are now logged in.",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        ),
    )


@router.get("/me", response_model=APIResponse[UserRead])
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> APIResponse[UserRead]:
    """
    Retrieve the profile details of the currently authenticated user.
    """
    return APIResponse(
        success=True,
        message="Profile retrieved successfully.",
        data=UserRead.model_validate(current_user),
    )


@router.put("/profile", response_model=APIResponse[UserRead])
async def update_profile(
    update_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[UserRead]:
    """
    Update the authenticated user's profile details (full name, username, bio, avatar).
    """
    updated_user = await auth_service.update_profile(db, current_user, update_in)
    return APIResponse(
        success=True,
        message="Profile updated successfully.",
        data=UserRead.model_validate(updated_user),
    )


@router.delete("/account", response_model=APIResponse[dict])
async def delete_current_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[dict]:
    """
    Permanently delete the authenticated user's account and associated logs.
    """
    username = current_user.username
    await auth_service.delete_account(db, current_user)
    return APIResponse(
        success=True,
        message=f"Account @{username} has been permanently deleted.",
        data={"deleted": True, "username": username},
    )


@router.post("/delete-account", response_model=APIResponse[dict])
async def delete_account_by_email(
    delete_in: AccountDeleteRequest,
    db: AsyncSession = Depends(get_db_session),
) -> APIResponse[dict]:
    """
    Unauthenticated recovery endpoint to purge an orphaned or stuck account by email.
    """
    await auth_service.delete_account_by_email(db, delete_in)
    return APIResponse(
        success=True,
        message=f"Account associated with {delete_in.email} has been permanently removed.",
        data={"deleted": True, "email": delete_in.email},
    )
