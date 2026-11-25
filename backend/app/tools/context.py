from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.core.config import settings

class ToolExecutionContext(BaseModel):
    """
    Context injected into tools during execution.
    Provides necessary resources without tightly coupling to GraphState.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    db: Optional[AsyncSession] = None
    request_id: str
    conversation_id: str
    logger: Any = logger
    settings: Any = settings
    current_user: Optional[Any] = None
    source_text: Optional[str] = None
    source_filename: Optional[str] = None
    source_is_current_message: bool = False
    excluded_fields: frozenset[str] = frozenset()
    llm_provider: Optional[Any] = None
