"""Strict validation and anomaly detection for market candles before persistence.

Guarantees data integrity, OHLC sanity, market session compliance,
and non-fabrication of missing intervals.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Set
from trading_engine.market_data.calendar import MarketCalendarService
from trading_engine.market_data.types import HistoricalCandle
from shared.market_time import to_ist


class CandleValidationError(ValueError):
    """Raised when a candle violates market data structural or business rules."""
    pass


def validate_candle(
    candle: HistoricalCandle,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    check_session: bool = True,
) -> None:
    """Validate all invariants of an individual candlestick.

    Raises:
        CandleValidationError: If any rule is violated.
    """
    if candle.timestamp.tzinfo is None:
        raise CandleValidationError("Candle timestamp must be timezone-aware.")

    ts_ist = to_ist(candle.timestamp)

    if start is not None and ts_ist < to_ist(start):
        raise CandleValidationError(f"Candle timestamp {ts_ist} precedes start boundary {start}.")

    if end is not None and ts_ist > to_ist(end):
        raise CandleValidationError(f"Candle timestamp {ts_ist} exceeds end boundary {end}.")

    if not candle.complete:
        raise CandleValidationError("Incomplete candle cannot be recorded as completed.")

    if min(candle.open, candle.high, candle.low, candle.close) <= 0:
        raise CandleValidationError(
            f"Candle prices must be strictly positive: O={candle.open}, H={candle.high}, L={candle.low}, C={candle.close}."
        )

    if candle.high < max(candle.open, candle.close, candle.low):
        raise CandleValidationError(
            f"Invalid OHLC relationship: High ({candle.high}) is less than max(O, C, L) ({max(candle.open, candle.close, candle.low)})."
        )

    if candle.low > min(candle.open, candle.close, candle.high):
        raise CandleValidationError(
            f"Invalid OHLC relationship: Low ({candle.low}) is greater than min(O, C, L) ({min(candle.open, candle.close, candle.high)})."
        )

    if candle.volume < 0:
        raise CandleValidationError(f"Candle volume cannot be negative: {candle.volume}.")

    if check_session:
        session = MarketCalendarService.get_session_info(ts_ist.date())
        if not session["is_trading_day"]:
            raise CandleValidationError(
                f"Candle timestamp {ts_ist} falls on non-trading day ({session['description']})."
            )

        sess_open = session["market_open_time"]
        sess_close = session["market_close_time"]
        if not (sess_open <= ts_ist <= sess_close):
            raise CandleValidationError(
                f"Candle timestamp {ts_ist} falls outside active session hours [{sess_open} - {sess_close}]."
            )


def detect_missing_intervals(
    candles: List[HistoricalCandle],
    timeframe_minutes: int,
    session_start: datetime,
    session_end: datetime,
) -> List[datetime]:
    """Detect expected session candlestick intervals that are missing from the provider feed.

    NEVER fabricate fake OHLCV data to fill intervals. Returns the list of missing datetimes
    for data quality auditing and logging.
    """
    start_ist = to_ist(session_start)
    end_ist = to_ist(session_end)
    step = timedelta(minutes=timeframe_minutes)

    present_timestamps: Set[datetime] = {to_ist(c.timestamp) for c in candles}
    missing: List[datetime] = []

    current = start_ist
    while current < end_ist:
        if current not in present_timestamps:
            missing.append(current)
        current += step

    return missing
