"""Position sizing engine enforcing strict mathematical risk parameters.

Implementation of PDF Section 9 & 9.1:
- Virtual starting capital / current total equity
- 10% Cash Reserve: Preserved strictly, never allocated to new position entries
- 25% Maximum Position Value: Position cost capped at 25% of net equity
- Maximum Planned Risk per Trade: e.g. ₹25 (or configurable rupee amount)
- Whole-share rounding: Rounded down to nearest lot size
- Zero-quantity rejection: If calculated shares < lot size, reject with explicit bottleneck reason
"""

import math
from typing import Optional
from trading_engine.config.settings import engine_settings
from trading_engine.risk.models import PositionSizingResult


class PositionSizer:
    """Calculates order quantity based on exact financial risk and allocation caps."""

    def __init__(
        self,
        max_risk_per_trade_inr: float = engine_settings.MAX_RISK_PER_TRADE_INR,
        cash_reserve_pct: float = engine_settings.CASH_RESERVE_PCT,
        max_position_pct: float = engine_settings.MAX_POSITION_PCT,
        risk_pct_per_trade: Optional[float] = None,
    ) -> None:
        self.max_risk_per_trade_inr = max_risk_per_trade_inr
        self.cash_reserve_pct = cash_reserve_pct
        self.max_position_pct = max_position_pct
        self.risk_pct_per_trade = risk_pct_per_trade

    def calculate_sizing(
        self,
        equity: float,
        available_cash: float,
        entry_price: float,
        stop_loss_price: float,
        lot_size: int = 1,
    ) -> PositionSizingResult:
        """Calculate exact share quantity capped by risk budget, position cap, and cash reserve."""
        if entry_price <= 0:
            return PositionSizingResult(
                quantity=0,
                risk_per_share=0.0,
                total_rupee_risk=0.0,
                position_value=0.0,
                cash_reserve_preserved=0.0,
                limiting_factor="ZERO_QUANTITY",
                is_valid=False,
                rejection_reason="Entry price must be positive.",
            )

        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            return PositionSizingResult(
                quantity=0,
                risk_per_share=0.0,
                total_rupee_risk=0.0,
                position_value=0.0,
                cash_reserve_preserved=0.0,
                limiting_factor="ZERO_QUANTITY",
                is_valid=False,
                rejection_reason="Stop loss must not equal entry price (zero risk per share).",
            )

        # 1. Determine maximum rupee risk budget
        if self.risk_pct_per_trade is not None:
            max_risk = equity * (self.risk_pct_per_trade / 100.0)
        else:
            # If capital is scaled above ₹5000, allow risk to scale proportionally up to max_risk_per_trade_inr
            base_risk = self.max_risk_per_trade_inr
            if equity > 5000.0:
                # E.g. for ₹100,000 capital, scale risk proportionally (0.5% risk = ₹500)
                scaled_risk = equity * 0.005
                max_risk = max(base_risk, scaled_risk)
            else:
                max_risk = base_risk

        # Quantity permitted by risk budget
        risk_qty = math.floor(max_risk / risk_per_share)

        # 2. Maximum position value cap (25% of net equity)
        max_pos_value = equity * self.max_position_pct
        pos_cap_qty = math.floor(max_pos_value / entry_price)

        # 3. Available cash after preserving 10% cash reserve
        cash_reserve = equity * self.cash_reserve_pct
        usable_cash = max(0.0, available_cash - cash_reserve)
        cash_cap_qty = math.floor(usable_cash / entry_price)

        # 4. Find the bottleneck constraint
        raw_qty = min(risk_qty, pos_cap_qty, cash_cap_qty)

        # Determine limiting factor
        if raw_qty <= 0:
            if risk_qty <= 0:
                limiting = "RISK_BUDGET"
                reason = f"Per-share risk (₹{risk_per_share:.2f}) exceeds trade risk budget (₹{max_risk:.2f})."
            elif cash_cap_qty <= 0:
                limiting = "AVAILABLE_CASH"
                reason = (
                    f"Available cash after {int(self.cash_reserve_pct * 100)}% reserve "
                    f"(₹{usable_cash:.2f}) is insufficient for 1 share at ₹{entry_price:.2f}."
                )
            elif pos_cap_qty <= 0:
                limiting = "POSITION_CAP"
                reason = (
                    f"Max {int(self.max_position_pct * 100)}% position limit (₹{max_pos_value:.2f}) "
                    f"is less than single share price ₹{entry_price:.2f}."
                )
            else:
                limiting = "ZERO_QUANTITY"
                reason = "Calculated quantity is zero."

            return PositionSizingResult(
                quantity=0,
                risk_per_share=round(risk_per_share, 4),
                total_rupee_risk=0.0,
                position_value=0.0,
                cash_reserve_preserved=round(cash_reserve, 2),
                limiting_factor=limiting,
                is_valid=False,
                rejection_reason=reason,
            )

        if raw_qty == risk_qty:
            limiting = "RISK_BUDGET"
        elif raw_qty == pos_cap_qty:
            limiting = "POSITION_CAP"
        else:
            limiting = "AVAILABLE_CASH"

        # Apply whole-share lot size constraint
        final_qty = (raw_qty // lot_size) * lot_size
        if final_qty <= 0:
            return PositionSizingResult(
                quantity=0,
                risk_per_share=round(risk_per_share, 4),
                total_rupee_risk=0.0,
                position_value=0.0,
                cash_reserve_preserved=round(cash_reserve, 2),
                limiting_factor="ZERO_QUANTITY",
                is_valid=False,
                rejection_reason=f"Calculated quantity ({raw_qty}) does not satisfy minimum lot size ({lot_size}).",
            )

        position_value = final_qty * entry_price
        total_risk = final_qty * risk_per_share

        return PositionSizingResult(
            quantity=final_qty,
            risk_per_share=round(risk_per_share, 4),
            total_rupee_risk=round(total_risk, 2),
            position_value=round(position_value, 2),
            cash_reserve_preserved=round(cash_reserve, 2),
            limiting_factor=limiting,
            is_valid=True,
            rejection_reason=None,
        )

    def calculate_quantity(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        lot_size: int = 1,
    ) -> int:
        """Backward-compatible helper returning simple integer quantity."""
        sizing = self.calculate_sizing(
            equity=capital,
            available_cash=capital,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            lot_size=lot_size,
        )
        return sizing.quantity
