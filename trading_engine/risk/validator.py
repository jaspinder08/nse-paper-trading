from typing import Any, Dict, Tuple
from trading_engine.config.settings import engine_settings


class RiskValidator:
    """Validates generated signals against account and risk limits before paper execution."""

    def __init__(
        self,
        max_daily_loss: float = engine_settings.MAX_LOSS_PER_DAY,
        max_open_positions: int = engine_settings.MAX_OPEN_POSITIONS,
        max_capital_per_day: float = engine_settings.MAX_CAPITAL_PER_DAY,
    ) -> None:
        self.max_daily_loss = max_daily_loss
        self.max_open_positions = max_open_positions
        self.max_capital_per_day = max_capital_per_day

    def validate_signal(
        self,
        signal: Dict[str, Any],
        current_daily_pnl: float,
        open_positions_count: int,
        utilized_capital: float,
    ) -> Tuple[bool, str]:
        """Check if a signal satisfies risk parameters. Returns (passed, reason)."""
        # Critical safety check
        if current_daily_pnl <= -abs(self.max_daily_loss):
            return False, f"Max daily loss threshold (₹{self.max_daily_loss}) breached."

        if open_positions_count >= self.max_open_positions:
            return False, f"Max open positions count ({self.max_open_positions}) reached."

        estimated_cost = signal.get("trigger_price", 0.0) * signal.get("quantity", 1)
        if utilized_capital + estimated_cost > self.max_capital_per_day:
            return False, f"Max intraday capital (₹{self.max_capital_per_day}) exceeded."

        return True, "Risk validation approved."
