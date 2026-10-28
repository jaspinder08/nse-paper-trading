"""Market time and timezone utilities for NSE India paper trading.

All exchange-local operations strictly reference the Asia/Kolkata timezone.
Standard trading hours: 09:15:00 to 15:30:00 IST.
"""

from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

# Standard Indian Standard Time Zone
IST_ZONE = ZoneInfo("Asia/Kolkata")
UTC_ZONE = ZoneInfo("UTC")

# Standard Regular Session Times
MARKET_OPEN_TIME = time(9, 15, 0)
MARKET_CLOSE_TIME = time(15, 30, 0)


def now_ist() -> datetime:
    """Return the current datetime localized to Asia/Kolkata."""
    return datetime.now(IST_ZONE)


def now_utc() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(UTC_ZONE)


def to_ist(dt: datetime) -> datetime:
    """Convert any timezone-aware datetime to Asia/Kolkata."""
    if dt.tzinfo is None:
        # If naive, assume UTC as standard storage representation
        dt = dt.replace(tzinfo=UTC_ZONE)
    return dt.astimezone(IST_ZONE)


def to_utc(dt: datetime) -> datetime:
    """Convert any datetime to UTC for storage."""
    if dt.tzinfo is None:
        # If naive, assume IST
        dt = dt.replace(tzinfo=IST_ZONE)
    return dt.astimezone(UTC_ZONE)


def is_regular_trading_hours(dt: Optional[datetime] = None) -> bool:
    """Check if the provided datetime falls within standard 09:15 to 15:30 IST window."""
    t = to_ist(dt or now_ist()).time()
    return MARKET_OPEN_TIME <= t <= MARKET_CLOSE_TIME


def get_market_session_bounds(calendar_date: date) -> tuple[datetime, datetime]:
    """Return the regular session start and end datetimes localized to Asia/Kolkata."""
    session_start = datetime.combine(calendar_date, MARKET_OPEN_TIME, tzinfo=IST_ZONE)
    session_end = datetime.combine(calendar_date, MARKET_CLOSE_TIME, tzinfo=IST_ZONE)
    return session_start, session_end
