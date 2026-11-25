import datetime
from datetime import timezone
from typing import Any, Optional, Union
import jwt
import bcrypt
import hashlib
import hmac
import os
import secrets

from fastapi import Response

from app.core.config import settings

ALGORITHM = "HS256"
# Access token lifetime. 7 days was far too long for a token that cannot be
# revoked; 24 hours is a sane default for this app's session model.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ── Cookie transport constants (browser clients send the JWT as an
#    httpOnly cookie; API clients keep using the Authorization header) ──
AUTH_COOKIE_NAME = "uils_access"
CSRF_COOKIE_NAME = "uils_csrf"
CSRF_HEADER_NAME = "x-csrf-token"
COOKIE_MAX_AGE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 86400


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain text password against hashed password using bcrypt or pbkdf2.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        if hashed_password.startswith("pbkdf2:"):
            # Format: pbkdf2:salt:hash
            parts = hashed_password.split(":")
            if len(parts) == 3:
                salt = bytes.fromhex(parts[1])
                expected_hash = parts[2]
                computed_hash = hashlib.pbkdf2_hmac(
                    "sha256", plain_password.encode("utf-8"), salt, 100000
                ).hex()
                return hmac.compare_digest(computed_hash, expected_hash)

        # Standard bcrypt check
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Generate secure hash of a plain text password using bcrypt.
    """
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except Exception:
        # Fallback to PBKDF2-HMAC-SHA256
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return f"pbkdf2:{salt.hex()}:{key.hex()}"


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[datetime.timedelta] = None,
    extra_claims: Optional[dict] = None
) -> str:
    """
    Create a signed JWT access token.
    """
    now = datetime.datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
    }
    if extra_claims:
        to_encode.update(extra_claims)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Returns the decoded payload if valid, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        # Expired, malformed, bad signature, etc. Only catch PyJWT's own error
        # hierarchy — a bare `except Exception` hid cryptography/programming bugs.
        return None


def _fresh_csrf_token() -> str:
    """Unique per-login CSRF token for the double-submit pattern."""
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    token: str,
    csrf_token: Optional[str] = None,
    secure: Optional[bool] = None,
) -> str:
    """
    Attach the httpOnly access-token cookie and the readable CSRF cookie.

    Used on successful login / register / password change. The token is ALSO
    still returned in the JSON body for backward compatibility with API
    clients that use the Authorization header.
    Returns the CSRF token value (useful when it was auto-generated).
    """
    if csrf_token is None:
        csrf_token = _fresh_csrf_token()
    # Reflect the issued token's real lifetime; tests may pass secure=False
    # explicitly, otherwise honor the deployment mode (HTTPS in production).
    if secure is None:
        secure = settings.AUTH_COOKIE_SECURE
    if secure is None:
        secure = not settings.DEBUG

    # Access token: httpOnly so JavaScript can never exfiltrate it.
    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
        secure=secure,
    )
    # CSRF token: readable by JS so the SPA can echo it back in x-csrf-token.
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=COOKIE_MAX_AGE_SECONDS,
        httponly=False,
        samesite="lax",
        path="/",
        secure=secure,
    )
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Delete both auth cookies (called by the logout endpoint)."""
    response.delete_cookie(AUTH_COOKIE_NAME, path="/", samesite="lax")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", samesite="lax")
