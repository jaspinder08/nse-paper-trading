"""Comprehensive unit tests for Opening Range Breakout (ORB) strategy.

Validates:
- 09:15-09:30 IST 3-bar range calculation
- Incomplete and malformed range bar rejection
- Long breakout trigger condition (close > orb_high)
- Volume filter threshold verification
- Entry cutoff time enforcement
- Incomplete candle rejection
- Exact Decimal financial math for Entry, Stop-Loss, and Target
"""

from datetime import date, datetime, time
from decimal import Decimal
import pytest
from shared.market_time import IST_ZONE
from trading_engine.market_data.types import HistoricalCandle
from trading_engine.strategy.orb import ORBStrategy, OpeningRange, ORBSignal


def make_5m_candle(
    hour: int,
    minute: int,
    open_p: float,
    high_p: float,
    low_p: float,
    close_p: float,
    volume: int,
    complete: bool = True,
    session_date: date = date(2026, 11, 3),
) -> HistoricalCandle:
    """Helper to generate standardized 5m candles in Asia/Kolkata timezone."""
    dt = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        hour,
        minute,
        0,
        tzinfo=IST_ZONE,
    )
    return HistoricalCandle(
        timestamp=dt,
        open=Decimal(str(open_p)),
        high=Decimal(str(high_p)),
        low=Decimal(str(low_p)),
        close=Decimal(str(close_p)),
        volume=volume,
        complete=complete,
    )


@pytest.fixture
def strategy():
    return ORBStrategy(
        range_minutes=15,
        timeframe_minutes=5,
        volume_multiplier=1.0,
        reward_risk_ratio=1.5,
        entry_cutoff_time=time(14, 30, 0),
    )


@pytest.fixture
def valid_opening_candles():
    """Three valid 5m candles forming the 09:15-09:30 opening range."""
    return [
        make_5m_candle(9, 15, 2500.0, 2515.0, 2495.0, 2510.0, 10000),  # Bar 1
        make_5m_candle(9, 20, 2510.0, 2520.0, 2505.0, 2512.0, 12000),  # Bar 2
        make_5m_candle(9, 25, 2512.0, 2518.0, 2500.0, 2508.0, 8000),   # Bar 3
    ]


def test_calculate_valid_opening_range(strategy, valid_opening_candles):
    """Verify that 3 completed bars correctly determine ORB high, low, and average volume."""
    rng = strategy.calculate_opening_range(valid_opening_candles)

    assert rng.is_valid is True
    assert rng.invalid_reason is None
    assert rng.high == Decimal("2520.0")
    assert rng.low == Decimal("2495.0")
    assert rng.bar_count == 3
    assert rng.avg_volume == (10000 + 12000 + 8000) / 3.0  # 10,000


def test_reject_insufficient_opening_bars(strategy):
    """Opening range must be rejected if fewer than 3 bars exist in 09:15-09:30."""
    bars = [
        make_5m_candle(9, 15, 2500.0, 2515.0, 2495.0, 2510.0, 10000),
        make_5m_candle(9, 20, 2510.0, 2520.0, 2505.0, 2512.0, 12000),
    ]
    rng = strategy.calculate_opening_range(bars)

    assert rng.is_valid is False
    assert "Insufficient opening range bars" in rng.invalid_reason
    assert rng.bar_count == 2


def test_reject_incomplete_opening_bar(strategy, valid_opening_candles):
    """If any opening range bar is incomplete, opening range must be marked invalid."""
    incomplete_bars = [
        valid_opening_candles[0],
        make_5m_candle(9, 20, 2510.0, 2520.0, 2505.0, 2512.0, 12000, complete=False),
        valid_opening_candles[2],
    ]
    rng = strategy.calculate_opening_range(incomplete_bars)

    assert rng.is_valid is False
    assert "marked incomplete" in rng.invalid_reason


def test_reject_malformed_ohlc(strategy):
    """Bars with invalid OHLC relationships (e.g. high < low) must invalidate range."""
    malformed_bars = [
        make_5m_candle(9, 15, 2500.0, 2490.0, 2515.0, 2510.0, 10000),  # High < Low!
        make_5m_candle(9, 20, 2510.0, 2520.0, 2505.0, 2512.0, 12000),
        make_5m_candle(9, 25, 2512.0, 2518.0, 2500.0, 2508.0, 8000),
    ]
    rng = strategy.calculate_opening_range(malformed_bars)

    assert rng.is_valid is False
    assert "invalid OHLC" in rng.invalid_reason


def test_reject_pre_open_bars(strategy):
    """Pre-market candles (< 09:15) must not be counted in the opening range."""
    bars_with_premarket = [
        make_5m_candle(9, 5, 2490.0, 2495.0, 2485.0, 2490.0, 5000),   # 09:05 Pre-market
        make_5m_candle(9, 15, 2500.0, 2515.0, 2495.0, 2510.0, 10000),  # Bar 1
        make_5m_candle(9, 20, 2510.0, 2520.0, 2505.0, 2512.0, 12000),  # Bar 2
    ]
    rng = strategy.calculate_opening_range(bars_with_premarket)

    # Only 2 regular bars exist, pre-market excluded -> should fail
    assert rng.is_valid is False
    assert rng.bar_count == 2


def test_valid_long_breakout_signal(strategy, valid_opening_candles):
    """A 5m candle closing above ORB high with sufficient volume triggers a valid signal."""
    rng = strategy.calculate_opening_range(valid_opening_candles)

    # Breakout bar at 09:30: High 2528, Close 2525 (> ORB high 2520), Volume 15000 (> avg 10000)
    breakout_candle = make_5m_candle(9, 30, 2515.0, 2528.0, 2514.0, 2525.0, 15000)
    signal = strategy.evaluate_candle(breakout_candle, rng, "RELIANCE")

    assert signal is not None
    assert isinstance(signal, ORBSignal)
    assert signal.symbol == "RELIANCE"
    assert signal.signal_type == "LONG"
    assert signal.entry_price == Decimal("2525.0")
    assert signal.stop_loss == Decimal("2495.0")  # ORB Low
    assert signal.initial_risk == Decimal("30.0")  # 2525 - 2495 = 30.0
    # Target = 2525 + 1.5 * 30 = 2525 + 45 = 2570.0
    assert signal.target_price == Decimal("2570.0")
    assert signal.reward_risk_ratio == 1.5
    assert signal.volume_ratio == 1.5  # 15000 / 10000
    assert "broke above ORB high" in signal.reason


def test_breakout_rejected_when_close_below_high(strategy, valid_opening_candles):
    """If candle wicks above high but closes below high, no breakout should trigger."""
    rng = strategy.calculate_opening_range(valid_opening_candles)

    # High is 2522 (above 2520), but close is 2518 (below 2520)
    candle = make_5m_candle(9, 30, 2515.0, 2522.0, 2510.0, 2518.0, 15000)
    signal = strategy.evaluate_candle(candle, rng, "INFY")

    assert signal is None


def test_breakout_rejected_by_volume_filter(strategy, valid_opening_candles):
    """Breakout candle must be rejected if volume is below opening range average."""
    rng = strategy.calculate_opening_range(valid_opening_candles)

    # Close is 2525 (> 2520), but volume is only 6000 (< avg 10000)
    low_vol_candle = make_5m_candle(9, 30, 2515.0, 2528.0, 2514.0, 2525.0, 6000)
    signal = strategy.evaluate_candle(low_vol_candle, rng, "TCS")

    assert signal is None


def test_breakout_rejected_after_entry_cutoff(strategy, valid_opening_candles):
    """Breakouts occurring after entry cutoff time (14:30) must be rejected."""
    rng = strategy.calculate_opening_range(valid_opening_candles)

    # 14:35 IST candle is after cutoff 14:30
    late_candle = make_5m_candle(14, 35, 2515.0, 2530.0, 2514.0, 2526.0, 20000)
    signal = strategy.evaluate_candle(late_candle, rng, "HDFCBANK")

    assert signal is None


def test_breakout_rejected_if_incomplete(strategy, valid_opening_candles):
    """Incomplete candidate bars must never trigger simulated orders."""
    rng = strategy.calculate_opening_range(valid_opening_candles)

    incomplete_candle = make_5m_candle(9, 30, 2515.0, 2528.0, 2514.0, 2525.0, 15000, complete=False)
    signal = strategy.evaluate_candle(incomplete_candle, rng, "SBIN")

    assert signal is None
