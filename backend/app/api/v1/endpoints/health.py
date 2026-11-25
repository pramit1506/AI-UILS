from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from app.shared.responses import APIResponse
from app.core.config import settings
from app.core.constants import STATUS_OK
from app.dependencies.db import get_db_session

router = APIRouter()

@router.get("/", response_model=APIResponse[dict])
def read_root():
    return APIResponse(
        success=True,
        message=f"Welcome to the {settings.PROJECT_NAME} API",
        data={
            "project_name": settings.PROJECT_NAME,
            "version": settings.API_VERSION
        }
    )

@router.get("/health", response_model=APIResponse[dict])
def check_health():
    return APIResponse(
        success=True,
        message="Health check passed",
        data={"status": STATUS_OK}
    )

@router.get("/ready", response_model=APIResponse[dict])
async def check_ready(response: Response, db=Depends(get_db_session)):
    """Readiness probe — verifies the application can actually reach the database."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return APIResponse(
            success=False,
            message="Service is not ready: database unreachable",
            data={"status": "degraded", "database": "unreachable"},
        )
    return APIResponse(
        success=True,
        message="Service is ready",
        data={"status": STATUS_OK, "database": "reachable"}
    )
