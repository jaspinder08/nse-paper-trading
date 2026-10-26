import pytest
from trading_engine.config.settings import engine_settings
from trading_engine.risk.validator import RiskValidator
from trading_engine.risk.sizing import PositionSizer
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.portfolio.manager import PortfolioManager


def test_trading_engine_settings_invariants():
    """Verify that paper trading mode is strictly invariant."""
    assert engine_settings.TRADING_MODE == "PAPER"
    assert engine_settings.is_paper_mode is True


def test_position_sizer():
    """Verify position sizing calculation."""
    sizer = PositionSizer(risk_pct_per_trade=1.0)
    # Capital = 100,000, 1% risk = 1,000. Entry = 200, SL = 190 (risk per share = 10). Quantity should be 100 shares.
    qty = sizer.calculate_quantity(capital=100000.0, entry_price=200.0, stop_loss_price=190.0, lot_size=1)
    assert qty == 100


def test_risk_validator_daily_loss_limit():
    """Verify that breach of daily loss stops new signals."""
    validator = RiskValidator(max_daily_loss=2000.0, max_open_positions=3)
    passed, reason = validator.validate_signal(
        signal={"trigger_price": 500.0, "quantity": 10},
        current_daily_pnl=-2500.0,  # Breached max loss of 2000
        open_positions_count=1,
        utilized_capital=5000.0,
    )
    assert passed is False
    assert "daily loss" in reason.lower()


@pytest.mark.asyncio
async def test_paper_execution_safety_guard():
    """Verify that paper execution rejects live trading orders."""
    executor = PaperExecutionEngine()
    with pytest.raises(PermissionError) as exc_info:
        await executor.execute_paper_order(
            symbol="INFY",
            transaction_type="BUY",
            quantity=10,
            is_live=True,  # Attempt live execution
        )
    assert "Live broker execution is strictly prohibited" in str(exc_info.value)


@pytest.mark.asyncio
async def test_paper_execution_simulated_order():
    """Verify paper order simulation returns a valid filled paper order."""
    executor = PaperExecutionEngine()
    order = await executor.execute_paper_order(
        symbol="RELIANCE",
        transaction_type="BUY",
        quantity=5,
        price=2900.0,
        is_live=False,
    )
    assert order["is_paper"] is True
    assert order["status"] == "FILLED"
    assert order["executed_price"] == 2900.0
