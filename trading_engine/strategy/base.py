from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseStrategy(ABC):
    """Abstract interface for trading strategies."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def evaluate(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate market data and return trading signal dict or None."""
        pass
