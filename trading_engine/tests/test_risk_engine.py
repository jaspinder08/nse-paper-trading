"""Comprehensive unit tests for Risk Validator and Position Sizer.

Enforces PDF Section 9, 9.1, 9.2 & 20 requirements:
- Virtual starting capital ₹5,000
- 10% cash reserve strictly preserved
- 25% max position value cap
- ₹25 max planned risk per trade
- ₹75 daily loss circuit breaker
- Max 3 trades per day
- Max 6 simulated events per day
- Whole-share rounding down
- Explainable rejection reasons
"""

import pytest
from trading_engine.risk.models import PositionSizingResult, RiskVerdict
from trading_engine.risk.sizing import PositionSizer
from trading_engine.risk.validator import RiskValidator


@pytest.fixture
def sizer():
    return PositionSizer(
        max_risk_per_trade_inr=25.0,
        cash_reserve_pct=0.10,
        max_position_pct=0.25,
    )


@pytest.fixture
def validator(sizer):
    return RiskValidator(
        max_daily_loss=75.0,
        max_open_positions=3,
        max_trades_per_day=3,
        max_events_per_day=6,
        min_reward_risk=1.5,
        position_sizer=sizer,
    )


# -------------------------------------------------------------------------
# Position Sizer Tests (Section 9.1)
# -------------------------------------------------------------------------

def test_position_sizing_limited_by_risk_budget(sizer):
    """₹5,000 capital, ₹100 stock, SL ₹95 (risk ₹5/share) -> limited by ₹25 risk budget to 5 shares."""
    res: PositionSizingResult = sizer.calculate_sizing(
        equity=5000.0,
        available_cash=5000.0,
        entry_price=100.0,
        stop_loss_price=95.0,
        lot_size=1,
    )

    assert res.is_valid is True
    assert res.quantity == 5  # 25 / 5 = 5
    assert res.total_rupee_risk == 25.0
    assert res.position_value == 500.0  # 5 * 100 <= 1250 cap
    assert res.cash_reserve_preserved == 500.0  # 10% of 5000
    assert res.limiting_factor == "RISK_BUDGET"


def test_position_sizing_limited_by_position_cap(sizer):
    """₹5,000 capital, ₹500 stock, SL ₹498 (risk ₹2/share) -> risk allows 12, but 25% cap (₹1250) limits to 2 shares."""
    res = sizer.calculate_sizing(
        equity=5000.0,
        available_cash=5000.0,
        entry_price=500.0,
        stop_loss_price=498.0,
        lot_size=1,
    )

    assert res.is_valid is True
    assert res.quantity == 2  # floor(1250 / 500) = 2
    assert res.position_value == 1000.0  # <= 1250 max position cap
    assert res.total_rupee_risk == 4.0  # 2 * 2
    assert res.limiting_factor == "POSITION_CAP"


def test_position_sizing_limited_by_available_cash_reserve(sizer):
    """When available cash is ₹700, 10% reserve (₹500) leaves only ₹200 usable cash -> limits to 2 shares."""
    res = sizer.calculate_sizing(
        equity=5000.0,
        available_cash=700.0,  # Only 700 cash left in account
        entry_price=100.0,
        stop_loss_price=98.0,
        lot_size=1,
    )

    assert res.is_valid is True
    # Usable cash = 700 - 500 = 200. floor(200 / 100) = 2 shares
    assert res.quantity == 2
    assert res.position_value == 200.0
    assert res.limiting_factor == "AVAILABLE_CASH"


def test_position_sizing_rejects_single_share_exceeding_position_cap(sizer):
    """Stock price ₹1,500 exceeds the 25% max position cap (₹1,250) -> must reject with 0 shares."""
    res = sizer.calculate_sizing(
        equity=5000.0,
        available_cash=5000.0,
        entry_price=1500.0,
        stop_loss_price=1490.0,
        lot_size=1,
    )

    assert res.is_valid is False
    assert res.quantity == 0
    assert "position limit" in res.rejection_reason.lower()


def test_position_sizing_rejects_risk_per_share_exceeding_budget(sizer):
    """Per-share risk ₹30 exceeds the ₹25 trade risk budget -> must reject with 0 shares."""
    res = sizer.calculate_sizing(
        equity=5000.0,
        available_cash=5000.0,
        entry_price=100.0,
        stop_loss_price=70.0,  # Risk = 30 > 25
        lot_size=1,
    )

    assert res.is_valid is False
    assert res.quantity == 0
    assert "exceeds trade risk budget" in res.rejection_reason


# -------------------------------------------------------------------------
# Risk Gatekeeper Tests (Section 9 & 9.2)
# -------------------------------------------------------------------------

def test_daily_circuit_breaker_trips(validator):
    """Realized loss of ₹75 (or more) must activate circuit breaker and block new entries."""
    verdict: RiskVerdict = validator.validate_candidate(
        signal={
            "symbol": "RELIANCE",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 107.5,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=-75.50,  # Loss exceeds ₹75 threshold
        open_positions={},
    )

    assert verdict.approved is False
    assert verdict.circuit_breaker_active is True
    assert "circuit breaker tripped" in verdict.reason.lower()


def test_daily_trades_limit_reached(validator):
    """Max 3 trades per day constraint."""
    verdict = validator.validate_candidate(
        signal={
            "symbol": "TCS",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 107.5,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
        trades_today_count=3,  # Already executed 3 trades
    )

    assert verdict.approved is False
    assert "daily trade limit reached" in verdict.reason.lower()


def test_daily_simulated_order_events_limit(validator):
    """Max 6 simulated order events per day constraint."""
    verdict = validator.validate_candidate(
        signal={
            "symbol": "INFY",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 107.5,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
        events_today_count=6,  # 6 events reached
    )

    assert verdict.approved is False
    assert "order event limit reached" in verdict.reason.lower()


def test_max_open_positions_limit(validator):
    """Max concurrent open positions (3) reached."""
    verdict = validator.validate_candidate(
        signal={
            "symbol": "SBIN",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 107.5,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={"POS_1": {}, "POS_2": {}, "POS_3": {}},  # 3 open
    )

    assert verdict.approved is False
    assert "open positions" in verdict.reason.lower()


def test_duplicate_position_rejected(validator):
    """Cannot open a second position in the same symbol (no averaging down)."""
    verdict = validator.validate_candidate(
        signal={
            "symbol": "TCS",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "target_price": 107.5,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={"TCS": {"quantity": 5}},
    )

    assert verdict.approved is False
    assert "duplicate position rejected" in verdict.reason.lower()


def test_reject_short_positions(validator):
    """Short selling is strictly disallowed in v1."""
    verdict = validator.validate_candidate(
        signal={
            "symbol": "ITC",
            "signal_type": "SHORT",  # Disallowed
            "entry_price": 100.0,
            "stop_loss": 105.0,
            "target_price": 92.5,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
    )

    assert verdict.approved is False
    assert "only long cash equity permitted" in verdict.reason.lower()


def test_reject_missing_or_invalid_stop_loss(validator):
    """A valid stop loss below entry price is mandatory."""
    # Missing stop loss
    v1 = validator.validate_candidate(
        signal={"symbol": "ITC", "signal_type": "LONG", "entry_price": 100.0, "stop_loss": 0.0},
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
    )
    assert v1.approved is False
    assert "positive stop-loss is mandatory" in v1.reason.lower()

    # Stop loss >= entry price
    v2 = validator.validate_candidate(
        signal={"symbol": "ITC", "signal_type": "LONG", "entry_price": 100.0, "stop_loss": 105.0},
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
    )
    assert v2.approved is False
    assert "must be strictly below entry" in v2.reason.lower()


def test_reject_insufficient_reward_risk(validator):
    """Signals with reward:risk < 1.5 must be rejected."""
    # Entry 100, Stop 90 (risk 10). Target 110 (reward 10) -> RR = 1.0 < 1.5
    verdict = validator.validate_candidate(
        signal={
            "symbol": "HDFCBANK",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 90.0,
            "target_price": 110.0,
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
    )

    assert verdict.approved is False
    assert "insufficient reward-risk" in verdict.reason.lower()


def test_valid_signal_approved_with_exact_quantity(validator):
    """A fully compliant signal passes all gatekeeper checks and returns sized quantity."""
    verdict = validator.validate_candidate(
        signal={
            "symbol": "RELIANCE",
            "signal_type": "LONG",
            "entry_price": 100.0,
            "stop_loss": 95.0,  # Risk = 5. Risk budget = 25 -> 5 shares
            "target_price": 107.5,  # Reward = 7.5 -> 7.5/5 = 1.5:1
        },
        equity=5000.0,
        available_cash=5000.0,
        current_daily_pnl=0.0,
        open_positions={},
    )

    assert verdict.approved is True
    assert verdict.adjusted_quantity == 5
    assert verdict.circuit_breaker_active is False
    assert "risk approved" in verdict.reason.lower()
    assert verdict.sizing is not None
    assert verdict.sizing.total_rupee_risk == 25.0
