from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


class PaperExecutionEngine:
    """Simulated paper order execution engine. Strictly internal simulation."""

    def __init__(self) -> None:
        self.is_simulation_only: bool = True
        self.max_price_age = timedelta(seconds=10)

    async def execute_paper_order(
        self,
        symbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        price_timestamp: Optional[datetime] = None,
        has_complete_candle: bool = False,
        risk_approved: bool = False,
        is_live: bool = False,
    ) -> Dict[str, Any]:
        """Simulate execution of a paper trade."""
        if is_live:
            raise PermissionError(
                "CRITICAL TRADING SAFETY VIOLATION: Live broker execution is strictly prohibited in this application."
            )

        if not self.is_simulation_only or is_live:
            raise PermissionError("Live broker execution is strictly prohibited in this application.")
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
        fill_price = price

        return {
            "symbol": symbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "requested_price": price,
            "executed_price": fill_price,
            "status": "FILLED",
            "is_paper": True,
            "executed_at": executed_at.isoformat(),
        }
