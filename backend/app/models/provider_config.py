from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class ProviderConfiguration(Base, TimestampMixin):
    """Runtime configuration and health metrics for market data providers."""
    __tablename__ = "provider_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    # ANGEL_ONE, MOCK
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rate_limit_rps: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False)
