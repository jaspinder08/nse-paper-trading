"""Simulated paper order execution engine.

Strict Safety Mandate:
- Strictly Internal Paper Simulation
- Live broker execution interfaces are permanently rejected
- Realistic fill modeling with adverse slippage and exchange statutory costs
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional
from shared.costs import NSECostModel, cost_model


class PaperExecutionEngine:
    """Simulated paper order execution engine with statutory charges and slippage."""

    def __init__(self, cost_calculator: Optional[NSECostModel] = None) -> None:
        self.is_simulation_only: bool = True
        self.max_price_age = timedelta(seconds=10)
        self.costs = cost_calculator or cost_model

    async def execute_paper_order(
        self,
        symbol: str,
        transaction_type: str,  # "BUY" or "SELL"
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        price_timestamp: Optional[datetime] = None,
        has_complete_candle: bool = False,
        risk_approved: bool = False,
        is_live: bool = False,
        tick_size: float = 0.05,
    ) -> Dict[str, Any]:
        """Simulate execution of a paper trade with slippage and statutory cost accounting."""
        if is_live or not self.is_simulation_only:
            raise PermissionError(
                "CRITICAL TRADING SAFETY VIOLATION: Live broker execution is strictly prohibited in this application."
            )

        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Paper order quantity must be a positive integer.")
        if price is None or price <= 0:
            raise ValueError("A valid positive market price is required for paper execution.")
        if price_timestamp is None:
            raise ValueError("A timestamped market price is required for paper execution.")
        if price_timestamp.tzinfo is None:
            raise ValueError("Market price timestamp must be timezone-aware.")

        executed_at = datetime.now(timezone.utc)
        if executed_at - price_timestamp.astimezone(timezone.utc) > self.max_price_age:
            raise ValueError("Stale market price blocks paper execution.")
        if not has_complete_candle:
            raise ValueError("A complete valid candle is required for paper execution.")
        if not risk_approved:
            raise PermissionError("Risk approval is required before paper execution.")

        action: Literal["BUY", "SELL"] = "BUY" if transaction_type.upper() in ("BUY", "LONG") else "SELL"
        cost_breakdown = self.costs.calculate_costs(
            price=price,
            quantity=quantity,
            action=action,
            tick_size=tick_size,
        )

        return {
            "symbol": symbol.upper(),
            "transaction_type": action,
            "quantity": quantity,
            "order_type": order_type,
            "requested_price": round(price, 2),
            "executed_price": round(cost_breakdown.turnover / quantity, 2) if quantity > 0 else price,
            "net_effective_price": round(cost_breakdown.net_effective_price, 2),
            "raw_fill_price": round(cost_breakdown.turnover / quantity, 2) if quantity > 0 else price,
            "turnover": cost_breakdown.turnover,
            "total_charges": cost_breakdown.total_charges,
            "slippage_cost": cost_breakdown.slippage_cost,
            "status": "FILLED",
            "is_paper": True,
            "executed_at": executed_at.isoformat(),
            "cost_breakdown": cost_breakdown.to_dict(),
        }
