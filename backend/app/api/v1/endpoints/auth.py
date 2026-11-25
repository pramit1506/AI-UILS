from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from app.services import password_recovery
from app.schemas.user import RecoveryEmail, RecoveryConfirmation
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import (
    LOGIN_RATE_LIMIT,
    RATE_LIMIT_WINDOW_SECONDS,
    REGISTER_RATE_LIMIT,
    RESET_PASSWORD_RATE_LIMIT,
    rate_limit_dependency,
)
from app.core.security import set_auth_cookies, clear_auth_cookies
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db_session
from app.models.user import User
from app.schemas.user import (
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


@router.get("/recovery/status")
def recovery_status():
    return {"email_recovery_configured": password_recovery.is_configured()}


@router.post("/recovery/request", status_code=202, dependencies=[
    Depends(rate_limit_dependency(5, RATE_LIMIT_WINDOW_SECONDS, "recovery_request"))])
async def request_recovery(payload: RecoveryEmail, tasks: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):
    await password_recovery.request_code(db, payload.email, tasks)
    return {"message": "If that address has an active account, a code will arrive by email."}


@router.post("/recovery/confirm", dependencies=[
    Depends(rate_limit_dependency(10, RATE_LIMIT_WINDOW_SECONDS, "recovery_confirm"))])
async def confirm_recovery(payload: RecoveryConfirmation, db: AsyncSession = Depends(get_db_session)):
    await password_recovery.confirm_code(db, payload.email, payload.code, payload.new_password)
    return {"message": "Password updated. Sign in with your new password."}


@router.post("/register", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit_dependency(REGISTER_RATE_LIMIT, RATE_LIMIT_WINDOW_SECONDS, "register"))])
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    response: Response = None,
) -> APIResponse[TokenResponse]:
    """
    Register a new user profile with email, username, and password.
    Returns the created user details along with a JWT access token.
    Cookies: also issues the httpOnly uils_access + uils_csrf cookie pair.
    """
    user, access_token = await auth_service.register(db, user_in)
    set_auth_cookies(response, access_token)
    return APIResponse(
        success=True,
        message=f"Welcome {user.full_name or user.username}! Account created successfully.",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        ),
    )


@router.post("/login", response_model=APIResponse[TokenResponse],
             dependencies=[Depends(rate_limit_dependency(LOGIN_RATE_LIMIT, RATE_LIMIT_WINDOW_SECONDS, "login"))])
async def login(
    login_in: UserLogin,
    db: AsyncSession = Depends(get_db_session),
    response: Response = None,
) -> APIResponse[TokenResponse]:
    """
    Sign in to an existing account with username or email.
    Cookies: also issues the httpOnly uils_access + uils_csrf cookie pair.
    """
    user, access_token = await auth_service.login(db, login_in)
    set_auth_cookies(response, access_token)
    return APIResponse(
        success=True,
        message=f"Welcome back, {user.full_name or user.username}!",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        ),
    )


@router.post("/reset-password", response_model=APIResponse[TokenResponse],
             dependencies=[Depends(rate_limit_dependency(RESET_PASSWORD_RATE_LIMIT, RATE_LIMIT_WINDOW_SECONDS, "reset_password"))])
async def reset_password(
    reset_in: PasswordResetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    response: Response = None,
) -> APIResponse[TokenResponse]:
    """
    Change the authenticated user's password.

    Requires a valid Bearer token and the current password. (Previously this
    endpoint was unauthenticated — anyone who knew a user's email could take
    over the account.)
    """
    user, access_token = await auth_service.reset_password(db, current_user, reset_in)
    set_auth_cookies(response, access_token)
    return APIResponse(
        success=True,
        message="Password has been changed successfully.",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserRead.model_validate(user),
        ),
    )


@router.post("/logout", response_model=APIResponse[dict])
async def logout(
    response: Response = None,
) -> APIResponse[dict]:
    """
    Log out the browser session by clearing the uils_access / uils_csrf cookies.

    JWTs are stateless — there is no server-side session to invalidate — so
    clearing the cookies *is* the logout for browser clients (additive; the
    previous in-memory-only flow simply had no browser logout story).
    Bearer-header clients just stop sending the token.
    """
    clear_auth_cookies(response)
    return APIResponse(
        success=True,
        message="Logged out successfully.",
        data={"logout": True},
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

    NOTE: The former unauthenticated `POST /delete-account` (delete any account
    by email address) was removed — it was a critical vulnerability allowing
    anyone to destroy accounts and all their data with a single request.
    """
    username = current_user.username
    await auth_service.delete_account(db, current_user)
    return APIResponse(
        success=True,
        message=f"Account @{username} has been permanently deleted.",
        data={"deleted": True, "username": username},
    )
