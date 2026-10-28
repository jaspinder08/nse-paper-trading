from datetime import date
from typing import Optional
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class InstrumentConstituentHistory(Base, TimestampMixin):
    """Index constituent membership history for survivorship-bias free backtesting & filtering."""
    __tablename__ = "instrument_constituent_history"
    __table_args__ = (
        UniqueConstraint("index_name", "symbol", "effective_from", name="uq_constituent_idx_sym_from"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_name: Mapped[str] = mapped_column(String(32), default="NIFTY 50", nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    instrument_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
