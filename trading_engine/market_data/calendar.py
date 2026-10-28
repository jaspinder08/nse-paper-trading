"""NSE India market calendar, session timing, and holiday schedule service.

Strictly manages:
- Regular trading sessions: 09:15 to 15:30 IST
- Weekends (Saturday & Sunday closed unless special disaster-recovery session)
- Declared NSE trading holidays
- Muhurat trading sessions (Diwali evening special session)
- Special Saturday disaster recovery live trading sessions
"""

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.market_calendar import MarketCalendar
from shared.market_time import (
    IST_ZONE,
    MARKET_CLOSE_TIME,
    MARKET_OPEN_TIME,
    now_ist,
    to_ist,
    to_utc,
)

# Reference timestamp for calendar data verification
CALENDAR_DATA_SOURCE = "NSE_OFFICIAL_CIRCULARS"
CALENDAR_LAST_UPDATED = datetime(2026, 1, 15, 0, 0, 0, tzinfo=IST_ZONE)

# Standard Trading Holidays (Date -> Reason)
NSE_HOLIDAYS: Dict[date, str] = {
    # 2024
    date(2024, 1, 22): "Special Holiday (Ram Mandir Pran Pratishtha)",
    date(2024, 1, 26): "Republic Day",
    date(2024, 3, 8): "Mahashivratri",
    date(2024, 3, 25): "Holi",
    date(2024, 3, 29): "Good Friday",
    date(2024, 4, 11): "Id-Ul-Fitr",
    date(2024, 4, 17): "Ram Navami",
    date(2024, 5, 1): "Maharashtra Day",
    date(2024, 5, 20): "General Elections (Mumbai Constituency)",
    date(2024, 6, 17): "Bakri Id",
    date(2024, 7, 17): "Muharram",
    date(2024, 8, 15): "Independence Day",
    date(2024, 10, 2): "Mahatma Gandhi Jayanti",
    date(2024, 11, 15): "Guru Nanak Jayanti",
    date(2024, 11, 20): "Maharashtra Assembly Elections",
    date(2024, 12, 25): "Christmas",

    # 2025
    date(2025, 2, 26): "Mahashivratri",
    date(2025, 3, 14): "Holi",
    date(2025, 3, 31): "Id-Ul-Fitr",
    date(2025, 4, 10): "Mahavir Jayanti",
    date(2025, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
    date(2025, 4, 18): "Good Friday",
    date(2025, 5, 1): "Maharashtra Day",
    date(2025, 8, 15): "Independence Day",
    date(2025, 8, 27): "Ganesh Chaturthi",
    date(2025, 10, 2): "Mahatma Gandhi Jayanti",
    date(2025, 10, 22): "Diwali Balipratipada",
    date(2025, 11, 5): "Prakash Gurpurb Sri Guru Nanak Dev",
    date(2025, 12, 25): "Christmas",

    # 2026
    date(2026, 1, 26): "Republic Day",
    date(2026, 2, 16): "Mahashivratri",
    date(2026, 3, 4): "Holi",
    date(2026, 3, 20): "Id-Ul-Fitr",
    date(2026, 4, 3): "Good Friday",
    date(2026, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
    date(2026, 5, 1): "Maharashtra Day",
    date(2026, 5, 27): "Bakri Id",
    date(2026, 9, 15): "Ganesh Chaturthi",
    date(2026, 10, 2): "Mahatma Gandhi Jayanti",
    date(2026, 10, 20): "Dussehra",
    date(2026, 11, 24): "Guru Nanak Jayanti",
    date(2026, 12, 25): "Christmas",
}

# Special Trading Sessions (Muhurat Trading & Saturday DR Sessions)
# Date -> (session_type, open_time, close_time, description)
SPECIAL_SESSIONS: Dict[date, Tuple[str, time, time, str]] = {
    # 2024 Special Saturday DR Sessions
    date(2024, 3, 2): ("SPECIAL", time(9, 15), time(12, 30), "Disaster Recovery Site Live Trading"),
    date(2024, 5, 18): ("SPECIAL", time(9, 15), time(12, 30), "Disaster Recovery Site Live Trading"),
    # 2024 Diwali Muhurat Trading
    date(2024, 11, 1): ("MUHURAT", time(18, 0), time(19, 15), "Diwali Laxmi Pujan Muhurat Trading"),

    # 2025 Diwali Muhurat Trading
    date(2025, 10, 21): ("MUHURAT", time(18, 15), time(19, 15), "Diwali Laxmi Pujan Muhurat Trading"),

    # 2026 Diwali Muhurat Trading
    date(2026, 11, 8): ("MUHURAT", time(18, 0), time(19, 0), "Diwali Laxmi Pujan Muhurat Trading"),
}


class MarketCalendarService:
    """Provides market hours, calendar verification, and status evaluation."""

    @staticmethod
    def get_session_info(check_date: date) -> Dict[str, Any]:
        """Return full session specification for any given date."""
        # 1. Check special sessions (Muhurat or DR Saturday)
        if check_date in SPECIAL_SESSIONS:
            sess_type, o_time, c_time, desc = SPECIAL_SESSIONS[check_date]
            open_dt = datetime.combine(check_date, o_time, tzinfo=IST_ZONE)
            close_dt = datetime.combine(check_date, c_time, tzinfo=IST_ZONE)
            return {
                "date": check_date,
                "is_trading_day": True,
                "session_type": sess_type,
                "market_open_time": open_dt,
                "market_close_time": close_dt,
                "description": desc,
                "holiday_reason": None,
            }

        # 2. Check declared holidays
        if check_date in NSE_HOLIDAYS:
            reason = NSE_HOLIDAYS[check_date]
            return {
                "date": check_date,
                "is_trading_day": False,
                "session_type": "HOLIDAY",
                "market_open_time": None,
                "market_close_time": None,
                "description": f"NSE Trading Holiday: {reason}",
                "holiday_reason": reason,
            }

        # 3. Check weekends (Saturday = 5, Sunday = 6)
        weekday = check_date.weekday()
        if weekday in (5, 6):
            day_name = "Saturday" if weekday == 5 else "Sunday"
            return {
                "date": check_date,
                "is_trading_day": False,
                "session_type": "WEEKEND",
                "market_open_time": None,
                "market_close_time": None,
                "description": f"Weekend: {day_name}",
                "holiday_reason": day_name,
            }

        # 4. Regular weekday trading session
        open_dt = datetime.combine(check_date, MARKET_OPEN_TIME, tzinfo=IST_ZONE)
        close_dt = datetime.combine(check_date, MARKET_CLOSE_TIME, tzinfo=IST_ZONE)
        return {
            "date": check_date,
            "is_trading_day": True,
            "session_type": "REGULAR",
            "market_open_time": open_dt,
            "market_close_time": close_dt,
            "description": "NSE Regular Trading Session",
            "holiday_reason": None,
        }

    @classmethod
    def is_trading_day(cls, check_date: date) -> bool:
        """Return True if the date has an active trading session."""
        return cls.get_session_info(check_date)["is_trading_day"]

    @classmethod
    def is_market_open(cls, dt: Optional[datetime] = None) -> bool:
        """Determine whether the market is open at the specified datetime (or current IST)."""
        eval_dt = to_ist(dt or now_ist())
        session = cls.get_session_info(eval_dt.date())
        if not session["is_trading_day"]:
            return False
        return session["market_open_time"] <= eval_dt <= session["market_close_time"]

    @classmethod
    def get_market_status(cls, dt: Optional[datetime] = None) -> Dict[str, Any]:
        """Provide detailed current market operational status and next open/close times."""
        eval_dt = to_ist(dt or now_ist())
        current_date = eval_dt.date()
        current_session = cls.get_session_info(current_date)

        is_open = False
        if current_session["is_trading_day"]:
            if current_session["market_open_time"] <= eval_dt <= current_session["market_close_time"]:
                is_open = True

        # Find next open and close
        if is_open:
            next_close = current_session["market_close_time"]
            next_open = cls._find_next_session_open(current_date + timedelta(days=1))
        else:
            # Check if today hasn't opened yet
            if current_session["is_trading_day"] and eval_dt < current_session["market_open_time"]:
                next_open = current_session["market_open_time"]
                next_close = current_session["market_close_time"]
            else:
                next_open = cls._find_next_session_open(current_date + timedelta(days=1))
                next_sess = cls.get_session_info(next_open.date())
                next_close = next_sess["market_close_time"]

        return {
            "current_time_ist": eval_dt.isoformat(),
            "is_market_open": is_open,
            "session_type": current_session["session_type"],
            "session_description": current_session["description"],
            "current_date": current_date.isoformat(),
            "next_open": next_open.isoformat() if next_open else None,
            "next_close": next_close.isoformat() if next_close else None,
            "data_source": CALENDAR_DATA_SOURCE,
            "last_verified_at": CALENDAR_LAST_UPDATED.isoformat(),
        }

    @classmethod
    def _find_next_session_open(cls, search_start: date, max_days_ahead: int = 30) -> datetime:
        """Scan forward to find the next trading day open datetime."""
        for i in range(max_days_ahead):
            d = search_start + timedelta(days=i)
            sess = cls.get_session_info(d)
            if sess["is_trading_day"]:
                return sess["market_open_time"]
        # Fallback
        return datetime.combine(search_start, MARKET_OPEN_TIME, tzinfo=IST_ZONE)

    @classmethod
    def get_calendar_range(cls, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Return day-by-day session definitions for a requested date range."""
        results = []
        curr = start_date
        while curr <= end_date:
            results.append(cls.get_session_info(curr))
            curr += timedelta(days=1)
        return results

    @classmethod
    async def seed_market_calendar(cls, session: AsyncSession, start_year: int = 2024, end_year: int = 2026) -> int:
        """Seed or update database MarketCalendar records for specified years."""
        start_d = date(start_year, 1, 1)
        end_d = date(end_year, 12, 31)
        entries = cls.get_calendar_range(start_d, end_d)

        count = 0
        for item in entries:
            cal_date = item["date"]
            stmt = select(MarketCalendar).where(MarketCalendar.calendar_date == cal_date)
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            # Convert to UTC for DB persistence
            open_utc = to_utc(item["market_open_time"]) if item["market_open_time"] else None
            close_utc = to_utc(item["market_close_time"]) if item["market_close_time"] else None

            if existing is None:
                record = MarketCalendar(
                    calendar_date=cal_date,
                    is_trading_day=item["is_trading_day"],
                    session_type=item["session_type"],
                    market_open_time=open_utc,
                    market_close_time=close_utc,
                    holiday_reason=item["holiday_reason"],
                    data_source=CALENDAR_DATA_SOURCE,
                    last_updated_at=datetime.now(IST_ZONE),
                )
                session.add(record)
                count += 1
            else:
                existing.is_trading_day = item["is_trading_day"]
                existing.session_type = item["session_type"]
                existing.market_open_time = open_utc
                existing.market_close_time = close_utc
                existing.holiday_reason = item["holiday_reason"]
                existing.last_updated_at = datetime.now(IST_ZONE)

        await session.commit()
        return count
