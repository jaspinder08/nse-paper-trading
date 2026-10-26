from datetime import datetime, timezone
from typing import Any, Dict, Optional


class PaperExecutionEngine:
    """Simulated paper order execution engine. Strictly internal simulation."""

    def __init__(self) -> None:
        self.is_simulation_only: bool = True

    async def execute_paper_order(
        self,
        symbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        is_live: bool = False,
    ) -> Dict[str, Any]:
        """Simulate execution of a paper trade."""
        if is_live:
            raise PermissionError(
                "CRITICAL TRADING SAFETY VIOLATION: Live broker execution is strictly prohibited in this application."
            )

        executed_at = datetime.now(timezone.utc)
        fill_price = price if price is not None else 100.0

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
