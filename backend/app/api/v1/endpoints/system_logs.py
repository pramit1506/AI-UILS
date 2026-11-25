from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from loguru import logger
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter()

MAX_LOG_FIELD_LENGTH = 8000

class SystemLogCreate(BaseModel):
    level: str
    message: str
    source: str = "frontend"
    url: Optional[str] = None
    stack_trace: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

    @field_validator("level", "source", "url")
    @classmethod
    def _clean_short_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Strip control characters to prevent log-forging via injected newlines
        # and cap length to bound log-file abuse.
        return "".join(ch for ch in v if ch.isprintable())[:500]

    @field_validator("message", "stack_trace")
    @classmethod
    def _clean_long_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return "".join(ch for ch in v if ch.isprintable())[:MAX_LOG_FIELD_LENGTH]

@router.post("/")
async def create_system_log(
    log_data: SystemLogCreate,
    current_user: User = Depends(get_current_user),
):
    """Receive logs from the authenticated frontend and write them to the system log."""

    log_msg = f"[{log_data.source.upper()}] {log_data.message}"
    if log_data.url:
        log_msg += f" | URL: {log_data.url}"
    if log_data.stack_trace:
        log_msg += f" | Stack: {log_data.stack_trace}"
    if log_data.additional_info:
        log_msg += f" | Extra: {log_data.additional_info}"

    level = log_data.level.upper()
    
    # Map console levels to loguru levels
    if level in ("ERROR", "FATAL"):
        logger.error(log_msg)
    elif level == "WARN" or level == "WARNING":
        logger.warning(log_msg)
    elif level == "INFO":
        logger.info(log_msg)
    elif level == "DEBUG":
        logger.debug(log_msg)
    else:
        logger.info(log_msg)
        
    return {"success": True, "message": "Log recorded"}
