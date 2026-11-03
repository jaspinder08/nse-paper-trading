"""Unit tests for NIFTY 50 Opening Range Breakout Scanner.

Validates:
- Symbol scan categorization (TRIGGERED, PENDING_BREAKOUT, RANGE_FORMING, REJECTED_VOLUME, NO_DATA)
- Proximity ranking for pending breakout candidates
- Batch scanning across Nifty 50 constituents
"""

from datetime import date, datetime, time
from decimal import Decimal
import pytest
from shared.market_time import IST_ZONE
from trading_engine.market_data.types import HistoricalCandle
from trading_engine.scanner.orb_scanner import ORBScanner
from trading_engine.strategy.orb import ORBStrategy


def make_candle(
    hour: int,
    minute: int,
    open_p: float,
    high_p: float,
    low_p: float,
    close_p: float,
    volume: int,
    session_date: date = date(2026, 11, 3),
) -> HistoricalCandle:
    dt = datetime(
        session_date.year, session_date.month, session_date.day, hour, minute, 0, tzinfo=IST_ZONE
    )
    return HistoricalCandle(
        timestamp=dt,
        open=Decimal(str(open_p)),
        high=Decimal(str(high_p)),
        low=Decimal(str(low_p)),
        close=Decimal(str(close_p)),
        volume=volume,
        complete=True,
    )


@pytest.fixture
def scanner():
    strategy = ORBStrategy(volume_multiplier=1.0, reward_risk_ratio=1.5)
    return ORBScanner(strategy=strategy)


def test_scan_symbol_triggered(scanner):
    """Stock with a valid breakout and volume confirmation must produce TRIGGERED status."""
    candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
        make_candle(9, 20, 102.0, 106.0, 101.0, 104.0, 6000),
        make_candle(9, 25, 104.0, 105.5, 102.0, 103.0, 4000),  # ORB: High 106.0, Low 98.0, Avg Vol 5000
        make_candle(9, 30, 103.0, 108.0, 102.5, 107.5, 8000),  # Breakout: Close 107.5 > 106.0, Vol 8000 > 5000
    ]

    candidate = scanner.scan_symbol("RELIANCE", candles)

    assert candidate.symbol == "RELIANCE"
    assert candidate.status == "TRIGGERED"
    assert candidate.current_price == 107.5
    assert candidate.orb_high == 106.0
    assert candidate.orb_low == 98.0
    assert candidate.signal is not None
    assert candidate.signal["entry_price"] == 107.5
    assert candidate.signal["stop_loss"] == 98.0


def test_scan_symbol_pending_breakout(scanner):
    """Stock within range without breakout must produce PENDING_BREAKOUT with distance."""
    candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
        make_candle(9, 20, 102.0, 106.0, 101.0, 104.0, 6000),
        make_candle(9, 25, 104.0, 105.5, 102.0, 103.0, 4000),  # ORB: High 106.0, Low 98.0
        make_candle(9, 30, 103.0, 105.0, 102.0, 104.5, 3000),  # Post-range: Close 104.5 (< 106.0)
    ]

    candidate = scanner.scan_symbol("TCS", candles)

    assert candidate.symbol == "TCS"
    assert candidate.status == "PENDING_BREAKOUT"
    assert candidate.current_price == 104.5
    assert candidate.orb_high == 106.0
    assert candidate.distance_to_high_pct == pytest.approx(-1.42, 0.05)
    assert candidate.signal is None


def test_scan_symbol_rejected_volume(scanner):
    """Stock breaking above high with insufficient volume must be flagged REJECTED_VOLUME."""
    candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
        make_candle(9, 20, 102.0, 106.0, 101.0, 104.0, 6000),
        make_candle(9, 25, 104.0, 105.5, 102.0, 103.0, 4000),  # Avg Vol = 5000
        make_candle(9, 30, 103.0, 108.0, 102.5, 107.0, 2000),  # Close 107.0 > 106.0, but Vol 2000 < 5000
    ]

    candidate = scanner.scan_symbol("INFY", candles)

    assert candidate.symbol == "INFY"
    assert candidate.status == "REJECTED_VOLUME"
    assert candidate.signal is None
    assert "failed volume filter" in candidate.reason


def test_scan_symbol_range_forming(scanner):
    """Before 09:30 with only 1 or 2 bars, status must be RANGE_FORMING."""
    candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
    ]

    candidate = scanner.scan_symbol("HDFCBANK", candles)

    assert candidate.symbol == "HDFCBANK"
    assert candidate.status == "RANGE_FORMING"
    assert candidate.signal is None
    assert "forming (1/3" in candidate.reason


def test_scan_symbol_no_data(scanner):
    """Empty candle list must return NO_DATA status."""
    candidate = scanner.scan_symbol("SBIN", [])

    assert candidate.symbol == "SBIN"
    assert candidate.status == "NO_DATA"


@pytest.mark.asyncio
async def test_batch_scan_prioritization(scanner):
    """Batch scan must order results by priority: TRIGGERED first, then closest PENDING_BREAKOUT."""
    # TCS: TRIGGERED
    tcs_candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
        make_candle(9, 20, 102.0, 106.0, 101.0, 104.0, 6000),
        make_candle(9, 25, 104.0, 105.5, 102.0, 103.0, 4000),
        make_candle(9, 30, 103.0, 108.0, 102.5, 107.5, 8000),
    ]

    # INFY: PENDING_BREAKOUT close to high (105.5 vs 106.0, -0.47%)
    infy_candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
        make_candle(9, 20, 102.0, 106.0, 101.0, 104.0, 6000),
        make_candle(9, 25, 104.0, 106.0, 102.0, 103.0, 4000),
        make_candle(9, 30, 103.0, 105.8, 102.5, 105.5, 3000),
    ]

    # RELIANCE: PENDING_BREAKOUT far from high (100.0 vs 106.0, -5.66%)
    rel_candles = [
        make_candle(9, 15, 100.0, 105.0, 98.0, 102.0, 5000),
        make_candle(9, 20, 102.0, 106.0, 101.0, 104.0, 6000),
        make_candle(9, 25, 104.0, 106.0, 102.0, 103.0, 4000),
        make_candle(9, 30, 101.0, 102.0, 99.0, 100.0, 3000),
    ]

    # SBIN: Empty
    candles_dict = {
        "RELIANCE": rel_candles,
        "INFY": infy_candles,
        "TCS": tcs_candles,
        "SBIN": [],
    }

    results = await scanner.scan(
        universe=["RELIANCE", "INFY", "TCS", "SBIN"],
        candles_by_symbol=candles_dict,
        as_of_date=date(2026, 11, 3),
    )

    # Ordering should be:
    # 1. TCS (TRIGGERED)
    # 2. INFY (PENDING_BREAKOUT, -0.47% from high)
    # 3. RELIANCE (PENDING_BREAKOUT, -5.66% from high)
    # 4. SBIN (NO_DATA)
    symbols_order = [r["symbol"] for r in results]
    assert symbols_order[0] == "TCS"
    assert symbols_order[1] == "INFY"
    assert symbols_order[2] == "RELIANCE"
    assert symbols_order[3] == "SBIN"
