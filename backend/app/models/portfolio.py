from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class PortfolioSnapshot(Base, TimestampMixin):
    """Periodic snapshot of paper-trading account equity and margin."""
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trading_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    total_capital: Mapped[float] = mapped_column(Float, nullable=False)
    available_margin: Mapped[float] = mapped_column(Float, nullable=False)
    utilized_margin: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    open_positions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
