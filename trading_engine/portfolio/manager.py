from typing import Any, Dict, List


class PortfolioManager:
    """Manages open simulated positions, margin, and P&L tracking."""

    def __init__(self, initial_capital: float = 100000.0) -> None:
        self.initial_capital = initial_capital
        self.available_margin = initial_capital
        self.realized_pnl: float = 0.0
        self.open_positions: Dict[str, Dict[str, Any]] = {}

    def get_summary(self) -> Dict[str, Any]:
        unrealized = sum(p.get("unrealized_pnl", 0.0) for p in self.open_positions.values())
        return {
            "initial_capital": self.initial_capital,
            "available_margin": self.available_margin,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized,
            "net_equity": self.available_margin + unrealized,
            "open_positions_count": len(self.open_positions),
            "is_paper": True,
        }
