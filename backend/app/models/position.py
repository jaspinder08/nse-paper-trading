from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class Position(Base, TimestampMixin):
    """Simulated open or closed position during a paper trading session."""
    __tablename__ = "positions"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_position_quantity_positive"), CheckConstraint("is_paper = 1", name="ck_position_simulated"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trading_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    side: Mapped[str] = mapped_column(String(16), nullable=False)  # LONG, SHORT
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_entry_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    target: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(18, 2), default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False, index=True)  # OPEN, CLOSED
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
