from datetime import date, datetime
from typing import Optional
from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class DataIngestionJob(Base, TimestampMixin):
    """Tracks historical and batch market-data ingestion jobs."""
    __tablename__ = "data_ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(32), default="HISTORICAL_CANDLES", nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="5m", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    # PENDING, RUNNING, COMPLETED, FAILED, PARTIAL
    candles_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
