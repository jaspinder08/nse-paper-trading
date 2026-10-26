from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.base import Base, TimestampMixin


class MarketCandle(Base, TimestampMixin):
    """OHLCV candlestick data for intraday timeframe bars."""
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "timeframe",
            "candle_timestamp",
            name="uq_candle_instrument_timeframe_timestamp",
        ),
        Index("ix_candle_inst_tf_ts", "instrument_id", "timeframe", "candle_timestamp"),
        CheckConstraint("open > 0 AND high >= low AND high >= open AND high >= close AND low <= open AND low <= close", name="ck_candle_ohlc_valid"),
        CheckConstraint("volume >= 0", name="ck_candle_volume_nonnegative"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # e.g., "1m", "5m", "15m", "1d"
    candle_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    open_interest: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
