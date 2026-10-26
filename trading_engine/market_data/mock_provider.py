import asyncio
import random
from typing import Any, Callable, Dict, List, Optional
from trading_engine.market_data.base import AbstractMarketDataProvider


class MockMarketDataProvider(AbstractMarketDataProvider):
    """Simulated market data provider for paper-trading development without broker dependency."""

    def __init__(self) -> None:
        self._connected: bool = False
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        self._subscribers.clear()

    def is_connected(self) -> bool:
        return self._connected

    async def subscribe_ticks(self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]) -> None:
        for sym in symbols:
            if sym not in self._subscribers:
                self._subscribers[sym] = []
            self._subscribers[sym].append(callback)

    async def unsubscribe_ticks(self, symbols: List[str]) -> None:
        for sym in symbols:
            self._subscribers.pop(sym, None)

    async def simulate_tick(self, symbol: str, base_price: float = 2500.0) -> Dict[str, Any]:
        """Generate a simulated tick variation."""
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
