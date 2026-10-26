from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class PaperOrder(Base, TimestampMixin):
    """Simulated paper order entity (strictly internal simulation)."""
    __tablename__ = "paper_orders"
    __table_args__ = (
        CheckConstraint("is_paper = 1", name="ck_paper_order_simulated"),
        CheckConstraint("quantity > 0", name="ck_paper_order_quantity_positive"),
        CheckConstraint("requested_price > 0", name="ck_paper_order_price_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("trading_signals.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    order_type: Mapped[str] = mapped_column(String(16), default="MARKET", nullable=False)  # MARKET, LIMIT, SL
    transaction_type: Mapped[str] = mapped_column(String(16), nullable=False)  # BUY, SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    executed_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
    )  # PENDING, FILLED, CANCELLED, REJECTED
    is_paper: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
