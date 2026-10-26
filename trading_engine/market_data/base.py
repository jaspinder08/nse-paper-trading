from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional


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
