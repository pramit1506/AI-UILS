from fastapi import APIRouter
from app.api.v1.endpoints import health, chat, upload, logs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
