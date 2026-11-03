"""NSE India Equity Intraday Transaction Cost and Slippage Models.

Implements official Indian exchange statutory levies and realistic fill slippage:
- STT (Securities Transaction Tax): 0.025% on intraday SELL turnover
- Exchange Transaction Charges: 0.00297% on total turnover (NSE)
- SEBI Turnover Charges: ₹10 per crore (0.0001%)
- GST: 18% on (Brokerage + Exchange Charges + SEBI Charges)
- Stamp Duty: 0.003% on BUY turnover
- Slippage: Configurable basis points / tick-size adverse execution
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Literal


@dataclass(frozen=True)
class TransactionCostBreakdown:
    """Detailed audit of all statutory levies and brokerage for an intraday trade."""
    turnover: float
    brokerage: float
    stt: float
    exchange_charges: float
    sebi_charges: float
    gst: float
    stamp_duty: float
    total_charges: float
    slippage_cost: float
    net_effective_price: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "turnover": self.turnover,
            "brokerage": self.brokerage,
            "stt": self.stt,
            "exchange_charges": self.exchange_charges,
            "sebi_charges": self.sebi_charges,
            "gst": self.gst,
            "stamp_duty": self.stamp_duty,
            "total_charges": self.total_charges,
            "slippage_cost": self.slippage_cost,
            "net_effective_price": self.net_effective_price,
        }


class NSECostModel:
    """Calculates official Indian regulatory levies and slippage for NSE cash equities."""

    # Official NSE Rates
    STT_SELL_RATE = 0.00025          # 0.025% on SELL
    EXCHANGE_RATE = 0.0000297        # 0.00297% on both BUY & SELL
    SEBI_RATE = 0.000001             # ₹10 / crore (0.0001%)
    GST_RATE = 0.18                  # 18% on (Brokerage + Exchange + SEBI)
    STAMP_DUTY_BUY_RATE = 0.00003    # 0.003% on BUY

    def __init__(
        self,
        brokerage_flat_per_order: float = 0.0,  # Zero for research or ₹20 discount
        brokerage_pct: float = 0.0,             # or 0.03%
        slippage_bps: float = 0.0,              # Default 0.0 bps (configurable for stress testing)
    ) -> None:
        self.brokerage_flat = brokerage_flat_per_order
        self.brokerage_pct = brokerage_pct
        self.slippage_bps = slippage_bps

    def calculate_fill_price(
        self,
        price: float,
        action: Literal["BUY", "SELL"],
        tick_size: float = 0.05,
    ) -> float:
        """Simulate realistic fill price with adverse slippage."""
        slippage = max(tick_size, price * (self.slippage_bps / 10000.0))
        if action == "BUY":
            fill = price + slippage
        else:
            fill = max(tick_size, price - slippage)

        # Round to nearest tick size
        ticks = round(fill / tick_size)
        return round(ticks * tick_size, 2)

    def calculate_costs(
        self,
        price: float,
        quantity: int,
        action: Literal["BUY", "SELL"],
        tick_size: float = 0.05,
    ) -> TransactionCostBreakdown:
        """Calculate exact statutory charges and net effective price for order execution."""
        fill_price = self.calculate_fill_price(price, action, tick_size)
        slippage_cost = abs(fill_price - price) * quantity
        turnover = fill_price * quantity

        # Brokerage calculation
        brokerage = min(self.brokerage_flat, turnover * (self.brokerage_pct / 100.0)) if self.brokerage_pct > 0 else self.brokerage_flat

        # STT (Intraday: 0.025% on sell side only)
        stt = turnover * self.STT_SELL_RATE if action == "SELL" else 0.0

        # Exchange Transaction Charges
        exchange_charges = turnover * self.EXCHANGE_RATE

        # SEBI Turnover Charges
        sebi_charges = turnover * self.SEBI_RATE

        # GST: 18% on (Brokerage + Exchange Charges + SEBI Charges)
        gst = (brokerage + exchange_charges + sebi_charges) * self.GST_RATE

        # Stamp Duty: 0.003% on buy side only
        stamp_duty = turnover * self.STAMP_DUTY_BUY_RATE if action == "BUY" else 0.0

        total_charges = round(brokerage + stt + exchange_charges + sebi_charges + gst + stamp_duty, 2)

        if action == "BUY":
            net_effective = (turnover + total_charges) / quantity if quantity > 0 else fill_price
        else:
            net_effective = (turnover - total_charges) / quantity if quantity > 0 else fill_price

        return TransactionCostBreakdown(
            turnover=round(turnover, 2),
            brokerage=round(brokerage, 2),
            stt=round(stt, 2),
            exchange_charges=round(exchange_charges, 2),
            sebi_charges=round(sebi_charges, 4),
            gst=round(gst, 2),
            stamp_duty=round(stamp_duty, 2),
            total_charges=total_charges,
            slippage_cost=round(slippage_cost, 2),
            net_effective_price=round(net_effective, 2),
        )


# Default singleton instance
cost_model = NSECostModel()
