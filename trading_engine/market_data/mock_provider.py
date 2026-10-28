"""Simulated market data provider for paper-trading development and automated testing."""

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import random
from typing import Any, Callable, Dict, List, Optional
from trading_engine.market_data.base import AbstractMarketDataProvider
from trading_engine.market_data.calendar import MarketCalendarService
from trading_engine.market_data.types import HistoricalCandle, InstrumentRecord
from trading_engine.universe.nifty50 import HISTORICAL_NIFTY50_DATA
from shared.market_time import IST_ZONE, to_ist


class MockMarketDataProvider(AbstractMarketDataProvider):
    """Simulated market data provider without any external broker dependency."""

    def __init__(self) -> None:
        self._connected: bool = False
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._custom_candles: Optional[List[HistoricalCandle]] = None
        self._injected_failure: Optional[str] = None
        self._failure_count: int = 0

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        self._subscribers.clear()

    def is_connected(self) -> bool:
        return self._connected

    async def authenticate(self) -> None:
        if not self._connected:
            await self.connect()

    async def health(self) -> bool:
        return self._connected

    def inject_failure(self, error_type: str = "RATE_LIMIT_429", count: int = 1) -> None:
        """Inject a simulated network/provider failure for testing retry behavior."""
        self._injected_failure = error_type
        self._failure_count = count

    def set_custom_candles(self, candles: List[HistoricalCandle]) -> None:
        """Set explicit candles to be returned on the next historical candle fetch."""
        self._custom_candles = candles

    async def fetch_instruments(self) -> List[InstrumentRecord]:
        """Return instrument records derived from authoritative Nifty 50 data."""
        records = []
        for d in HISTORICAL_NIFTY50_DATA:
            records.append(
                InstrumentRecord(
                    exchange="NSE",
                    symbol=d["symbol"],
                    name=d["name"],
                    token=d["token"],
                    instrument_type="EQUITY",
                    lot_size=1,
                    tick_size=Decimal("0.05"),
                    active=d["to"] is None,
                )
            )
        return records

    async def fetch_historical_candles(
        self,
        *,
        exchange: str,
        token: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> List[HistoricalCandle]:
        """Generate realistic simulated 5-minute candles between start and end."""
        # Check injected failures
        if self._failure_count > 0:
            self._failure_count -= 1
            if self._injected_failure == "RATE_LIMIT_429":
                raise RuntimeError("HTTP 429 Too Many Requests - Provider rate limit exceeded")
            elif self._injected_failure == "SERVER_ERROR_500":
                raise RuntimeError("HTTP 500 Internal Server Error - Market data provider unavailable")
            elif self._injected_failure == "TIMEOUT":
                raise asyncio.TimeoutError("Connection timed out waiting for provider response")
            else:
                raise RuntimeError(f"Simulated error: {self._injected_failure}")

        # If custom candles were injected, return them
        if self._custom_candles is not None:
            c = self._custom_candles
            self._custom_candles = None
            return c

        candles: List[HistoricalCandle] = []
        start_ist = to_ist(start)
        end_ist = to_ist(end)

        # Parse interval minutes (e.g. "5m" -> 5)
        step_minutes = 5
        if interval.endswith("m"):
            try:
                step_minutes = int(interval[:-1])
            except ValueError:
                step_minutes = 5

        current_date = start_ist.date()
        base_price = Decimal("2500.00")

        # Deterministic seed based on token for reproducible tests
        rnd = random.Random(int(token) if token.isdigit() else 42)

        while current_date <= end_ist.date():
            session = MarketCalendarService.get_session_info(current_date)
            if session["is_trading_day"]:
                sess_open = session["market_open_time"]
                sess_close = session["market_close_time"]

                current_time = sess_open
                while current_time < sess_close:
                    if start_ist <= current_time <= end_ist:
                        change = Decimal(str(round(rnd.uniform(-2.5, 2.5), 2)))
                        open_p = (base_price + change).quantize(Decimal("0.05"))
                        high_delta = Decimal(str(round(rnd.uniform(0.1, 4.0), 2)))
                        low_delta = Decimal(str(round(rnd.uniform(0.1, 4.0), 2)))
                        high_p = (open_p + high_delta).quantize(Decimal("0.05"))
                        low_p = max(Decimal("1.00"), (open_p - low_delta).quantize(Decimal("0.05")))
                        close_p = (low_p + Decimal(str(round(rnd.uniform(0.0, float(high_p - low_p)), 2)))).quantize(Decimal("0.05"))
                        vol = rnd.randint(500, 25000)

                        candles.append(
                            HistoricalCandle(
                                timestamp=current_time,
                                open=open_p,
                                high=high_p,
                                low=low_p,
                                close=close_p,
                                volume=vol,
                                complete=True,
                            )
                        )
                        base_price = close_p
                    current_time += timedelta(minutes=step_minutes)

            current_date += timedelta(days=1)

        return candles

    async def subscribe_ticks(self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]) -> None:
        for sym in symbols:
            self._subscribers.setdefault(sym, []).append(callback)

    async def unsubscribe_ticks(self, symbols: List[str]) -> None:
        for sym in symbols:
            self._subscribers.pop(sym, None)

    async def simulate_tick(self, symbol: str, base_price: float = 2500.0) -> Dict[str, Any]:
        variation = round(random.uniform(-1.5, 1.5), 2)
        tick = {
            "symbol": symbol,
            "ltp": round(base_price + variation, 2),
            "volume": random.randint(100, 2500),
            "timestamp": asyncio.get_event_loop().time(),
        }
        if symbol in self._subscribers:
            for cb in self._subscribers[symbol]:
                cb(tick)
        return tick
