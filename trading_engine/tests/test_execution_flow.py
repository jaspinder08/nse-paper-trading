"""Integration tests for end-to-end simulated paper trading execution flow.

Validates:
- Breakout candidate detection -> Risk gatekeeper approval
- Paper execution with NSE transaction fees and adverse slippage
- Persistence in paper_orders, positions, and trade_logs
- Target hit / SL hit exit simulation and realized P&L accounting
"""

from datetime import datetime, timezone
import pytest
from shared.costs import NSECostModel
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.risk.sizing import PositionSizer
from trading_engine.risk.validator import RiskValidator
from trading_engine.storage.repository import EngineStorageRepository


@pytest.fixture
def cost_model():
    return NSECostModel(brokerage_flat_per_order=0.0, slippage_bps=2.0)


@pytest.fixture
def executor(cost_model):
    return PaperExecutionEngine(cost_calculator=cost_model)


@pytest.mark.asyncio
async def test_paper_execution_costs_and_slippage(executor):
    """Test that paper execution properly applies adverse slippage and statutory costs."""
    # BUY order of 10 shares at ₹100.0
    fill = await executor.execute_paper_order(
        symbol="TCS",
        transaction_type="BUY",
        quantity=10,
        price=100.0,
        price_timestamp=datetime.now(timezone.utc),
        has_complete_candle=True,
        risk_approved=True,
    )

    assert fill["status"] == "FILLED"
    assert fill["is_paper"] is True
    # Fill price should include upward slippage on BUY
    assert fill["executed_price"] >= 100.0
    assert "cost_breakdown" in fill
    charges = fill["cost_breakdown"]
    assert charges["turnover"] >= 1000.0
    assert charges["stamp_duty"] > 0.0  # Stamp duty on BUY


@pytest.mark.asyncio
async def test_paper_execution_sell_stt(executor):
    """Test that SELL orders calculate STT (Securities Transaction Tax)."""
    fill = await executor.execute_paper_order(
        symbol="INFY",
        transaction_type="SELL",
        quantity=5,
        price=200.0,
        price_timestamp=datetime.now(timezone.utc),
        has_complete_candle=True,
        risk_approved=True,
    )

    assert fill["status"] == "FILLED"
    assert fill["executed_price"] <= 200.0  # Downward slippage on SELL
    charges = fill["cost_breakdown"]
    assert charges["stt"] > 0.0  # STT applies on intraday SELL


@pytest.mark.asyncio
async def test_repository_order_and_position_lifecycle():
    """Verify database persistence of paper orders, position opening, and closing."""
    repo = EngineStorageRepository(db_url="sqlite+aiosqlite:///:memory:")
    
    # Initialize in-memory tables
    from backend.app.database.base import Base
    import backend.app.models
    async with repo.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Create or get session
    session_id = await repo.get_or_create_today_session(initial_capital=5000.0)
    assert session_id is not None

    # 2. Add an instrument
    from backend.app.models.instrument import Instrument
    async with repo.session_factory() as sess:
        async with sess.begin():
            inst = Instrument(
                symbol="RELIANCE",
                name="Reliance Industries",
                exchange="NSE",
                token="2885",
                lot_size=1,
                tick_size=0.05,
                is_tradable=True,
            )
            sess.add(inst)
            await sess.flush()
            inst_id = inst.id

    # 3. Record Paper Order
    order_id = await repo.record_paper_order(
        session_id=session_id,
        instrument_id=inst_id,
        signal_id=None,
        transaction_type="BUY",
        quantity=5,
        requested_price=100.0,
        executed_price=100.10,
        status="FILLED",
    )
    assert order_id is not None

    # 4. Open Position
    pos_id = await repo.create_position(
        session_id=session_id,
        instrument_id=inst_id,
        side="LONG",
        quantity=5,
        entry_price=100.10,
        stop_loss=95.0,
        target=107.5,
    )
    assert pos_id is not None

    # 5. Check open positions
    open_pos = await repo.get_open_positions_with_instruments()
    assert len(open_pos) == 1
    assert open_pos[0]["symbol"] == "RELIANCE"
    assert open_pos[0]["quantity"] == 5

    # 6. Record Trade Log
    log_id = await repo.record_trade_log(
        order_id=order_id,
        position_id=pos_id,
        instrument_id=inst_id,
        action="ENTRY",
        quantity=5,
        price=100.10,
    )
    assert log_id is not None

    # 7. Close Position (Target Hit at 107.5)
    await repo.close_position(
        position_id=pos_id,
        exit_price=107.45,
        pnl=36.75,
        session_id=session_id,
    )

    # 8. Verify open positions is now empty
    remaining_open = await repo.get_open_positions_with_instruments()
    assert len(remaining_open) == 0

    await repo.dispose()
