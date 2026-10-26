from typing import Optional
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class Instrument(Base, TimestampMixin):
    """NSE/NIFTY tradable instrument definition."""
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), default="NSE", nullable=False, index=True)
    token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    segment: Mapped[str] = mapped_column(String(16), default="EQUITY", nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tick_size: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    is_tradable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
