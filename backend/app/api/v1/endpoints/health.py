from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.schemas.health import HealthResponse
from backend.app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the health status of the API server and SQLite database connection.",
)
async def get_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Check backend operational status and database connection."""
    return await HealthService.check_health(db)
