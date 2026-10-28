from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class MarketCalendar(Base, TimestampMixin):
    """NSE India market trading calendar and holiday schedule."""
    __tablename__ = "market_calendars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calendar_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    is_trading_day: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    session_type: Mapped[str] = mapped_column(String(32), default="REGULAR", nullable=False)
    # REGULAR, HOLIDAY, SPECIAL, MUHURAT
    market_open_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    market_close_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    holiday_reason: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    data_source: Mapped[str] = mapped_column(String(32), default="NSE", nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
