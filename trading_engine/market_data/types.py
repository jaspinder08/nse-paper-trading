"""Provider-neutral, paper-trading-only market-data contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class InstrumentRecord:
    exchange: str
    symbol: str
    name: str
    token: str
    instrument_type: str = "EQUITY"
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")
    active: bool = True


@dataclass(frozen=True)
class HistoricalCandle:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    complete: bool = True
