from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class DataQualityLog(Base, TimestampMixin):
    """Logs data anomalies, invalid OHLC relationships, and missing intervals."""
    __tablename__ = "data_quality_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # INVALID_OHLC, NEGATIVE_PRICE, NEGATIVE_VOLUME, MISSING_INTERVAL, DUPLICATE_CANDLE, OUT_OF_SESSION
    severity: Mapped[str] = mapped_column(String(16), default="WARNING", nullable=False)
    # INFO, WARNING, ERROR
    description: Mapped[str] = mapped_column(Text, nullable=False)
    candle_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
