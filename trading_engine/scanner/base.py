from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseScanner(ABC):
    """Abstract interface for scanning stock universes (e.g. Nifty 50)."""

    @abstractmethod
    async def scan(self, universe: List[str]) -> List[Dict[str, Any]]:
        """Scan given universe of stocks and return filtered breakout candidates."""
        pass
