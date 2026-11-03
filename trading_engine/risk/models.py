"""Risk contracts and verdicts for NSE paper trading simulation."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PositionSizingResult:
    """Exact position sizing metrics calculated according to PDF Section 9.1."""
    quantity: int
    risk_per_share: float
    total_rupee_risk: float
    position_value: float
    cash_reserve_preserved: float
    limiting_factor: str  # "RISK_BUDGET", "POSITION_CAP", "AVAILABLE_CASH", "ZERO_QUANTITY"
    is_valid: bool
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskVerdict:
    """Structured, explainable risk gatekeeper decision."""
    approved: bool
    reason: str
    adjusted_quantity: int
    sizing: Optional[PositionSizingResult]
    circuit_breaker_active: bool
    trades_today: int
    events_today: int
    open_positions_count: int
    planned_open_risk: float
    realized_daily_pnl: float
    unrealized_pnl: float

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.sizing:
            data["sizing"] = self.sizing.to_dict()
        return data
