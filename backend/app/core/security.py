import datetime
from datetime import timezone
from typing import Any, Optional, Union
import jwt
import bcrypt
import hashlib
import os

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days expiration


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
                return computed_hash == expected_hash

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
    except (jwt.PyJWTError, Exception):
        return None
