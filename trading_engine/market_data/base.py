from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from trading_engine.market_data.types import HistoricalCandle, InstrumentRecord


class AbstractMarketDataProvider(ABC):
    """Abstract interface for market data streaming and historical data fetching."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection with the data provider."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data provider."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connection is active."""
        pass

    @abstractmethod
    async def subscribe_ticks(self, symbols: List[str], callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to live market price ticks for a list of symbols."""
        pass

    @abstractmethod
    async def unsubscribe_ticks(self, symbols: List[str]) -> None:
        """Unsubscribe from live tick stream."""
        pass

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate only for market-data retrieval; never for order APIs."""
        pass

    @abstractmethod
    async def health(self) -> bool:
        """Return provider availability without exposing credentials."""
        pass

    @abstractmethod
    async def fetch_instruments(self) -> List[InstrumentRecord]:
        """Return verified provider instrument mappings."""
        pass

    @abstractmethod
    async def fetch_historical_candles(self, *, exchange: str, token: str, interval: str, start: datetime, end: datetime) -> List[HistoricalCandle]:
        """Return provider candles for a bounded interval."""
        pass
