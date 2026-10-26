from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health check response schema."""
    status: str = Field(default="healthy", description="System overall health status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current server timestamp in UTC"
    )
    environment: str = Field(..., description="Active environment name")
    version: str = Field(..., description="API Version")
    trading_mode: str = Field(default="PAPER", description="Current trading execution mode")
    database_status: str = Field(..., description="Database connection health")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health metrics")
