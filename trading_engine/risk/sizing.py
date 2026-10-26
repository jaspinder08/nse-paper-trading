import math
from typing import Any, Dict


class PositionSizer:
    """Calculates appropriate order quantity based on account risk per trade."""

    def __init__(self, risk_pct_per_trade: float = 1.0) -> None:
        self.risk_pct_per_trade = risk_pct_per_trade

    def calculate_quantity(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        lot_size: int = 1,
    ) -> int:
        """Calculate position sizing ensuring risk does not exceed specified percent."""
        risk_amount = capital * (self.risk_pct_per_trade / 100.0)
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            return lot_size

        raw_qty = risk_amount / risk_per_share
        lots = max(1, math.floor(raw_qty / lot_size))
        return lots * lot_size
