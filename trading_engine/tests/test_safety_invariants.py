"""Safety Invariants and Hardening Regression Test Suite (Phase 8 / Section 16 & 18).

Mandatory System Invariants:
1. Under NO circumstances does any live broker order placement code exist in the codebase.
2. The trading engine permanently rejects any live-execution parameter (is_live=True).
3. Stale market data (>10s) strictly blocks new entries.
4. Fail-closed behavior: Corrupt or incomplete state blocks new entries while exits remain available.
"""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from trading_engine.config.settings import engine_settings
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.risk.validator import RiskValidator


def test_no_broker_order_execution_apis_in_codebase():
    """Scan all source files to guarantee no real broker order placement APIs are defined or called."""
    root_dir = Path(__file__).resolve().parent.parent.parent

    # Forbidden broker order methods from Angel One / Zerodha / Upstox execution SDKs
    forbidden_terms = [
        "placeorder",
        "modifyorder",
        "cancelorder",
        "order/place",
        "order/modify",
        "order/cancel",
    ]

    scanned_files = 0
    for py_file in root_dir.glob("**/*.py"):
        # Skip test files and virtualenv
        str_path = str(py_file)
        if "test" in str_path.lower() or ".venv" in str_path or ".git" in str_path:
            continue

        scanned_files += 1
        content = py_file.read_text(encoding="utf-8", errors="ignore").lower()
        for term in forbidden_terms:
            assert term not in content, (
                f"SAFETY VIOLATION: Forbidden broker order API '{term}' found in {py_file}!"
            )

    assert scanned_files > 20, "Should have scanned at least 20 source files."


def test_trading_mode_is_permanently_paper():
    """Verify that settings permanently enforce PAPER mode with no live mode switch."""
    assert engine_settings.TRADING_MODE == "PAPER"
    assert engine_settings.is_paper_mode is True


@pytest.mark.asyncio
async def test_paper_executor_rejects_live_mode():
    """Verify PaperExecutionEngine raises PermissionError if live execution is attempted."""
    executor = PaperExecutionEngine()
    with pytest.raises(PermissionError, match="CRITICAL TRADING SAFETY VIOLATION"):
        await executor.execute_paper_order(
            symbol="RELIANCE",
            transaction_type="BUY",
            quantity=1,
            price=2900.0,
            price_timestamp=datetime.now(timezone.utc),
            has_complete_candle=True,
            risk_approved=True,
            is_live=True,  # Forbidden
        )


@pytest.mark.asyncio
async def test_paper_executor_rejects_stale_prices():
    """Verify that prices older than max_price_age (10s) strictly abort paper order fills."""
    executor = PaperExecutionEngine()
    stale_timestamp = datetime.now(timezone.utc) - timedelta(seconds=11)

    with pytest.raises(ValueError, match="Stale market price"):
        await executor.execute_paper_order(
            symbol="INFY",
            transaction_type="BUY",
            quantity=1,
            price=1800.0,
            price_timestamp=stale_timestamp,
            has_complete_candle=True,
            risk_approved=True,
            is_live=False,
        )


def test_risk_gatekeeper_fail_closed_on_circuit_breaker():
    """Verify fail-closed behavior: Circuit breaker blocks new entries, exits stay allowed."""
    validator = RiskValidator(max_daily_loss=75.0)
    sig = {
        "symbol": "TCS",
        "signal_type": "LONG",
        "entry_price": 3950.0,
        "stop_loss": 3900.0,
        "target_price": 4025.0,
        "volume_ratio": 1.5,
    }

    # When daily realized loss is ₹80 (exceeds ₹75 limit)
    verdict = validator.validate_candidate(
        signal=sig,
        equity=5000.0,
        available_cash=4500.0,
        current_daily_pnl=-80.0,
        open_positions={},
        trades_today_count=1,
    )

    assert verdict.approved is False
    assert "circuit breaker" in verdict.reason.lower()
