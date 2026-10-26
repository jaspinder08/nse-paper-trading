from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.health import HealthResponse
from backend.app.services.base import BaseService


class HealthService(BaseService):
    """Service to evaluate system and database connectivity health."""

    @staticmethod
    async def check_health(session: AsyncSession) -> HealthResponse:
        db_status = "disconnected"
        db_latency_ms = None
        try:
            start_t = datetime.now(timezone.utc)
            await session.execute(text("SELECT 1"))
            db_latency_ms = round((datetime.now(timezone.utc) - start_t).total_seconds() * 1000, 2)
            db_status = "connected"
        except Exception as e:
            logger.error("Database health check failed: %s", str(e))
            db_status = "unhealthy"

        overall_status = "healthy" if db_status == "connected" else "degraded"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            environment=settings.ENVIRONMENT,
            version="0.1.0",
            trading_mode=settings.TRADING_MODE,
            database_status=db_status,
            details={
                "project_name": settings.PROJECT_NAME,
                "db_latency_ms": db_latency_ms,
                "is_paper_trading_only": settings.is_paper_trading_only,
            },
        )
