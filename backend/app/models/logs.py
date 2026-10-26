from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class TradeLog(Base, TimestampMixin):
    """Detailed audit trail for trade lifecycle events."""
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("paper_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    position_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # ENTRY, EXIT, SL_HIT, TARGET_HIT, SQUARE_OFF
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    log_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskLog(Base, TimestampMixin):
    """Audit log of risk validation checks performed on signals and positions."""
    __tablename__ = "risk_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trading_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    signal_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trading_signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    check_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SystemLog(Base, TimestampMixin):
    """System-wide operational and diagnostic logs."""
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # INFO, WARNING, ERROR, CRITICAL
    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
