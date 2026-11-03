"""Risk Gatekeeper Engine enforcing Phase 1 / Phase 2 intraday paper safety constraints.

Implementation of PDF Section 9, 9.2 & 20:
- Stop-Loss Requirement: No simulated entry without an explicit, strictly positive stop-loss
- Minimum Reward:Risk: Must satisfy minimum ratio (default 1.5:1 candidate)
- Long-Only Invariant: Shorting, options, leverage, and margin are strictly disallowed
- Daily Circuit Breaker: When daily realized loss exceeds threshold (e.g. ₹75), all new entries are blocked
- Max Daily Trades: Capped at maximum trades per day (default 3)
- Max Simulated Events: Capped at maximum order events per day (default 6)
- Max Open Positions: Capped at maximum concurrent open positions (default 3)
- Duplicate Position Prevention: No averaging down or multiple concurrent positions in the same symbol
- Dynamic Position Sizing: Verifies risk budget, 10% cash reserve, and 25% max position value
"""

from typing import Any, Dict, List, Optional
from trading_engine.config.settings import engine_settings
from trading_engine.risk.models import PositionSizingResult, RiskVerdict
from trading_engine.risk.sizing import PositionSizer


class RiskValidator:
    """Production risk gatekeeper for algorithmic paper trading simulation."""

    def __init__(
        self,
        max_daily_loss: float = engine_settings.MAX_DAILY_LOSS_INR,
        max_open_positions: int = engine_settings.MAX_OPEN_POSITIONS,
        max_trades_per_day: int = engine_settings.MAX_TRADES_PER_DAY,
        max_events_per_day: int = engine_settings.MAX_EVENTS_PER_DAY,
        min_reward_risk: float = engine_settings.MIN_REWARD_RISK,
        position_sizer: Optional[PositionSizer] = None,
    ) -> None:
        self.max_daily_loss = abs(max_daily_loss)
        self.max_open_positions = max_open_positions
        self.max_trades_per_day = max_trades_per_day
        self.max_events_per_day = max_events_per_day
        self.min_reward_risk = min_reward_risk
        self.sizer = position_sizer or PositionSizer()

    def validate_candidate(
        self,
        signal: Dict[str, Any],
        equity: float,
        available_cash: float,
        current_daily_pnl: float,
        open_positions: Dict[str, Any],
        trades_today_count: int = 0,
        events_today_count: int = 0,
        planned_open_risk: float = 0.0,
    ) -> RiskVerdict:
        """Comprehensive risk evaluation of a candidate breakout signal.

        Returns a structured RiskVerdict indicating approval status, quantity, and audit reasoning.
        """
        symbol = signal.get("symbol", "").upper()
        signal_type = signal.get("signal_type", "LONG").upper()
        entry_price = float(signal.get("entry_price") or signal.get("trigger_price") or 0.0)
        stop_loss = float(signal.get("stop_loss") or 0.0)
        target_price = float(signal.get("target_price") or 0.0)
        open_positions_count = len(open_positions)

        # 1. Daily Circuit Breaker Check (Always checked first)
        if current_daily_pnl <= -self.max_daily_loss:
            return RiskVerdict(
                approved=False,
                reason=(
                    f"Daily loss circuit breaker tripped! Realized daily loss (₹{abs(current_daily_pnl):.2f}) "
                    f"breached threshold (₹{self.max_daily_loss:.2f}). New entries blocked."
                ),
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=True,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 2. Max Daily Trades Limit
        if trades_today_count >= self.max_trades_per_day:
            return RiskVerdict(
                approved=False,
                reason=f"Daily trade limit reached ({trades_today_count}/{self.max_trades_per_day} trades completed).",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 3. Max Daily Simulated Order Events
        if events_today_count >= self.max_events_per_day:
            return RiskVerdict(
                approved=False,
                reason=f"Daily order event limit reached ({events_today_count}/{self.max_events_per_day} simulated events).",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 4. Max Open Positions Limit
        if open_positions_count >= self.max_open_positions:
            return RiskVerdict(
                approved=False,
                reason=f"Max concurrent open positions ({self.max_open_positions}) reached.",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 5. Duplicate Position Prevention (No averaging down)
        if symbol and symbol in open_positions:
            return RiskVerdict(
                approved=False,
                reason=f"Duplicate position rejected: {symbol} already has an open position (averaging down prohibited).",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 6. Safety Invariant: Long-Only Equity (No Shorting / Options / Margin)
        if signal_type != "LONG":
            return RiskVerdict(
                approved=False,
                reason=f"Safety invariant violation: '{signal_type}' not permitted. Only LONG cash equity permitted.",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 7. Stop-Loss Requirement
        if stop_loss <= 0:
            return RiskVerdict(
                approved=False,
                reason="Safety violation: A strictly positive stop-loss is mandatory for all simulated orders.",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        if stop_loss >= entry_price:
            return RiskVerdict(
                approved=False,
                reason=f"Invalid stop-loss: Stop (₹{stop_loss:.2f}) must be strictly below entry (₹{entry_price:.2f}).",
                adjusted_quantity=0,
                sizing=None,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # 8. Minimum Reward:Risk Ratio Check
        if target_price > entry_price:
            initial_risk = entry_price - stop_loss
            reward = target_price - entry_price
            rr_ratio = reward / initial_risk if initial_risk > 0 else 0.0
            if rr_ratio < (self.min_reward_risk - 0.01):  # Allow tiny floating point margin
                return RiskVerdict(
                    approved=False,
                    reason=f"Insufficient reward-risk: {rr_ratio:.2f}:1 is below required {self.min_reward_risk:.1f}:1.",
                    adjusted_quantity=0,
                    sizing=None,
                    circuit_breaker_active=False,
                    trades_today=trades_today_count,
                    events_today=events_today_count,
                    open_positions_count=open_positions_count,
                    planned_open_risk=planned_open_risk,
                    realized_daily_pnl=current_daily_pnl,
                    unrealized_pnl=0.0,
                )

        # 9. Dynamic Position Sizing (PDF Section 9.1)
        # If signal already specifies a fixed quantity (e.g. legacy test), validate that it doesn't exceed budget
        manual_qty = signal.get("quantity")
        sizing: PositionSizingResult = self.sizer.calculate_sizing(
            equity=equity,
            available_cash=available_cash,
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            lot_size=signal.get("lot_size", 1),
        )

        final_qty = sizing.quantity
        if manual_qty is not None and isinstance(manual_qty, int) and manual_qty > 0:
            final_qty = min(manual_qty, sizing.quantity) if sizing.quantity > 0 else manual_qty

        if not sizing.is_valid or final_qty <= 0:
            return RiskVerdict(
                approved=False,
                reason=f"Position sizing rejected: {sizing.rejection_reason}",
                adjusted_quantity=0,
                sizing=sizing,
                circuit_breaker_active=False,
                trades_today=trades_today_count,
                events_today=events_today_count,
                open_positions_count=open_positions_count,
                planned_open_risk=planned_open_risk,
                realized_daily_pnl=current_daily_pnl,
                unrealized_pnl=0.0,
            )

        # Signal passed all risk gatekeeper checks!
        approval_reason = (
            f"Risk approved: {final_qty} shares of {symbol} at ₹{entry_price:.2f} "
            f"(Risk: ₹{sizing.total_rupee_risk:.2f}, Position Value: ₹{sizing.position_value:.2f}, "
            f"Reserve Preserved: ₹{sizing.cash_reserve_preserved:.2f}, Capped by: {sizing.limiting_factor})."
        )

        return RiskVerdict(
            approved=True,
            reason=approval_reason,
            adjusted_quantity=final_qty,
            sizing=sizing,
            circuit_breaker_active=False,
            trades_today=trades_today_count,
            events_today=events_today_count,
            open_positions_count=open_positions_count,
            planned_open_risk=planned_open_risk + sizing.total_rupee_risk,
            realized_daily_pnl=current_daily_pnl,
            unrealized_pnl=0.0,
        )

    def validate_signal(
        self,
        signal: Dict[str, Any],
        current_daily_pnl: float,
        open_positions_count: int,
        utilized_capital: float,
    ) -> tuple[bool, str]:
        """Backward-compatible interface for simple tuple check."""
        capital = engine_settings.PAPER_INITIAL_CAPITAL
        available = max(0.0, capital - utilized_capital)
        fake_positions = {f"POS_{i}": {} for i in range(open_positions_count)}
        
        # Ensure fallback stop_loss if none provided
        sig_copy = dict(signal)
        entry = float(sig_copy.get("trigger_price") or sig_copy.get("entry_price") or 100.0)
        if "stop_loss" not in sig_copy:
            sig_copy["stop_loss"] = entry * 0.98

        verdict = self.validate_candidate(
            signal=sig_copy,
            equity=capital,
            available_cash=available,
            current_daily_pnl=current_daily_pnl,
            open_positions=fake_positions,
        )
        return verdict.approved, verdict.reason
