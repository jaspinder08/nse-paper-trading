from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, Numeric, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class TradingSession(Base, TimestampMixin):
    """Represents an intraday paper-trading session."""
    __tablename__ = "trading_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED", nullable=False)
    market_open_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    market_close_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Numeric(18, 2), default=100000.0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
