from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import hmac
import secrets
import smtplib
import ssl

from fastapi import BackgroundTasks, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user_repository import user_repository


def is_configured() -> bool:
    return bool(settings.SMTP_HOST.strip() and settings.SMTP_FROM.strip())


def send_code(recipient: str, code: str) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message["Subject"] = "Your Universal Log password reset code"
    message.set_content(f"Enter {code} in Universal Log to reset your password. "
                        "This code expires in 10 minutes. If you did not request it, ignore this email.")
    tls = ssl.create_default_context()
    try:
        if settings.SMTP_IMPLICIT_TLS:
            client = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=tls, timeout=10)
        else:
            client = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        with client:
            if not settings.SMTP_IMPLICIT_TLS:
                client.starttls(context=tls)
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.error("Recovery email delivery failed. Check SMTP configuration and availability.")


def digest(user: User, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"recovery:{user.id}:{code}".encode(), hashlib.sha256).hexdigest()


async def locked_account(db: AsyncSession, email: str):
    return await db.scalar(select(User).where(User.email == email.strip().lower(), User.is_active.is_(True))
                           .with_for_update().execution_options(populate_existing=True))


async def request_code(db: AsyncSession, email: str, tasks: BackgroundTasks):
    if not is_configured():
        raise HTTPException(503, "Recovery email is unavailable. Please contact your administrator.")
    user = await locked_account(db, email)
    now = datetime.now(timezone.utc)
    if not user or (user.recovery_expires and user.recovery_expires > now + timedelta(minutes=9)):
        return
    code = f"{secrets.randbelow(1_000_000):06d}"
    user.recovery_digest = digest(user, code)
    user.recovery_expires = now + timedelta(minutes=10)
    user.recovery_attempts = 0
    recipient = user.email
    await db.commit()
    tasks.add_task(send_code, recipient, code)


async def confirm_code(db: AsyncSession, email: str, code: str, password: str):
    user = await locked_account(db, email)
    invalid = HTTPException(400, "That code is invalid or expired. Request a new code and try again.")
    if not user or not user.recovery_digest or not user.recovery_expires or user.recovery_expires <= datetime.now(timezone.utc):
        raise invalid
    if not hmac.compare_digest(user.recovery_digest, digest(user, code)):
        user.recovery_attempts += 1
        if user.recovery_attempts >= 5:
            user.recovery_digest = None
        await db.commit()
        raise invalid
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(422, "Use a password of at most 72 UTF-8 bytes.")
    await user_repository.update_password(db, user=user, hashed_password=get_password_hash(password))
