from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

router = APIRouter()

class SystemLogCreate(BaseModel):
    level: str
    message: str
    source: str = "frontend"
    url: Optional[str] = None
    stack_trace: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None

@router.post("/")
async def create_system_log(log_data: SystemLogCreate):
    """Receive logs from the frontend or other external sources and write them to the system log."""
    
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
