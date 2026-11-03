"""Unit and integration tests for the Historical Backtesting Engine (Phase 3 / FR-10)."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo
import pytest

from backend.app.database.session import async_engine
from backend.app.database.base import Base
from trading_engine.backtesting.engine import BacktestEngine, BacktestResult

IST = ZoneInfo("Asia/Kolkata")


def make_candle(day: date, hour: int, minute: int, o: float, h: float, l: float, c: float, v: int) -> dict:
    dt = datetime.combine(day, time(hour, minute)).replace(tzinfo=IST)
    return {
        "candle_timestamp": dt,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
    }


@pytest.fixture
def test_day():
    return date(2026, 11, 2)


@pytest.mark.asyncio
async def test_empty_backtest(test_day):
    """Verify empty candle dataset produces a clean zero-trade BacktestResult."""
    engine = BacktestEngine(initial_capital=5000.0)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=["TCS"],
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol={"TCS": []},
    )

    assert result.total_trades == 0
    assert result.initial_capital == 5000.0
    assert result.final_capital == 5000.0
    assert result.win_rate == 0.0
    assert result.net_pnl == 0.0


@pytest.mark.asyncio
async def test_backtest_orb_target_hit(test_day):
    """Test ORB breakout triggers, calculates fees/slippage, and exits on target hit."""
    candles = [
        # 09:15 - 09:30 range: High = 105.0, Low = 95.0, Avg Vol = 1000
        make_candle(test_day, 9, 15, 100.0, 105.0, 98.0, 102.0, 1000),
        make_candle(test_day, 9, 20, 102.0, 104.0, 95.0, 99.0, 1000),
        make_candle(test_day, 9, 25, 99.0, 103.0, 97.0, 101.0, 1000),
        # 09:30: Breakout candle! Close = 108.0 > 105.0, Vol = 2000 >= 1.2 * 1000
        # Entry fill: 108.0 + 0.05 = 108.05. SL = 95.0. Risk = 13.05. Target = 108.05 + 1.5 * 13.05 = 127.625 -> ~127.63
        make_candle(test_day, 9, 30, 101.0, 109.0, 100.0, 108.0, 2000),
        # 09:35: High reaches 130.0 -> Target Hit!
        make_candle(test_day, 9, 35, 108.0, 130.0, 107.0, 128.0, 1500),
    ]

    engine = BacktestEngine(initial_capital=5000.0, max_risk_per_trade=25.0)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=["TCS"],
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol={"TCS": candles},
    )

    assert result.total_trades == 1
    assert result.winning_trades == 1
    assert result.losing_trades == 0
    assert result.win_rate == 100.0
    assert result.net_pnl > 0.0
    assert result.profit_factor > 0.0
    assert result.total_charges > 0.0
    assert result.total_slippage > 0.0

    trade = result.trades[0]
    assert trade.symbol == "TCS"
    assert trade.exit_reason == "TARGET_HIT"
    assert trade.net_pnl > 0.0
    assert trade.exit_price > trade.entry_price


@pytest.mark.asyncio
async def test_backtest_orb_stop_loss_hit(test_day):
    """Test ORB breakout triggers and exits on stop-loss hit."""
    candles = [
        # 09:15 - 09:30 range: High = 105.0, Low = 95.0, Avg Vol = 1000
        make_candle(test_day, 9, 15, 100.0, 105.0, 98.0, 102.0, 1000),
        make_candle(test_day, 9, 20, 102.0, 104.0, 95.0, 99.0, 1000),
        make_candle(test_day, 9, 25, 99.0, 103.0, 97.0, 101.0, 1000),
        # 09:30: Breakout candle
        make_candle(test_day, 9, 30, 101.0, 108.0, 100.0, 107.0, 2000),
        # 09:35: Price drops to 92.0 <= Stop Loss (95.0)
        make_candle(test_day, 9, 35, 106.0, 106.0, 92.0, 93.0, 1200),
    ]

    engine = BacktestEngine(initial_capital=5000.0, max_risk_per_trade=25.0)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=["INFY"],
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol={"INFY": candles},
    )

    assert result.total_trades == 1
    assert result.losing_trades == 1
    assert result.winning_trades == 0
    assert result.win_rate == 0.0
    assert result.net_pnl < 0.0

    trade = result.trades[0]
    assert trade.symbol == "INFY"
    assert trade.exit_reason == "STOP_LOSS_HIT"
    assert trade.net_pnl < 0.0


@pytest.mark.asyncio
async def test_backtest_same_bar_conflict_sl_priority(test_day):
    """Test conservative invariant: If target and stop-loss are both reached in same bar, SL takes priority."""
    candles = [
        # 09:15 - 09:30 range: High = 105.0, Low = 95.0
        make_candle(test_day, 9, 15, 100.0, 105.0, 98.0, 102.0, 1000),
        make_candle(test_day, 9, 20, 102.0, 104.0, 95.0, 99.0, 1000),
        make_candle(test_day, 9, 25, 99.0, 103.0, 97.0, 101.0, 1000),
        # 09:30: Breakout candle -> target is ~127.5, SL is 95.0
        make_candle(test_day, 9, 30, 101.0, 108.0, 100.0, 107.0, 2000),
        # 09:35: Extreme volatility bar touching BOTH high (135) and low (90)
        make_candle(test_day, 9, 35, 107.0, 135.0, 90.0, 110.0, 3000),
    ]

    engine = BacktestEngine(initial_capital=5000.0)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=["RELIANCE"],
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol={"RELIANCE": candles},
    )

    assert result.total_trades == 1
    trade = result.trades[0]
    # Conservative priority: MUST be STOP_LOSS_HIT
    assert trade.exit_reason == "STOP_LOSS_HIT"


@pytest.mark.asyncio
async def test_backtest_eod_square_off(test_day):
    """Test that a trade still open at 15:15 IST squares off at market close."""
    candles = [
        make_candle(test_day, 9, 15, 100.0, 105.0, 98.0, 102.0, 1000),
        make_candle(test_day, 9, 20, 102.0, 104.0, 95.0, 99.0, 1000),
        make_candle(test_day, 9, 25, 99.0, 103.0, 97.0, 101.0, 1000),
        make_candle(test_day, 9, 30, 101.0, 108.0, 100.0, 107.0, 2000),
        # Bar at 15:15 IST
        make_candle(test_day, 15, 15, 107.0, 109.0, 106.0, 108.5, 800),
    ]

    engine = BacktestEngine(initial_capital=5000.0)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=["TCS"],
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol={"TCS": candles},
    )

    assert result.total_trades == 1
    trade = result.trades[0]
    assert trade.exit_reason == "EOD_SQUARE_OFF"


@pytest.mark.asyncio
async def test_backtest_max_trades_per_day(test_day):
    """Test max 3 trades per day constraint."""
    # Create 4 symbols all triggering breakouts
    symbols = ["SYM1", "SYM2", "SYM3", "SYM4"]
    candles_dict = {}
    for s in symbols:
        candles_dict[s] = [
            make_candle(test_day, 9, 15, 100.0, 105.0, 98.0, 102.0, 1000),
            make_candle(test_day, 9, 20, 102.0, 104.0, 95.0, 99.0, 1000),
            make_candle(test_day, 9, 25, 99.0, 103.0, 97.0, 101.0, 1000),
            # Breakout at 09:30
            make_candle(test_day, 9, 30, 101.0, 108.0, 100.0, 107.0, 2000),
            # Target hit at 09:35
            make_candle(test_day, 9, 35, 107.0, 130.0, 106.0, 128.0, 1500),
        ]

    engine = BacktestEngine(initial_capital=100000.0, max_trades_per_day=3)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=symbols,
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol=candles_dict,
    )

    # Exactly 3 trades should be executed despite 4 candidates
    assert result.total_trades == 3


@pytest.mark.asyncio
async def test_backtest_daily_circuit_breaker(test_day):
    """Test that tripping the daily loss circuit breaker (₹75) blocks subsequent trades."""
    # Sym 1 has a large loss that trips the circuit breaker
    # Sym 2 has a breakout later in the day that should be blocked
    candles_sym1 = [
        make_candle(test_day, 9, 15, 100.0, 105.0, 95.0, 102.0, 1000),
        make_candle(test_day, 9, 20, 102.0, 104.0, 95.0, 99.0, 1000),
        make_candle(test_day, 9, 25, 99.0, 103.0, 95.0, 101.0, 1000),
        # 09:30 Breakout
        make_candle(test_day, 9, 30, 101.0, 108.0, 100.0, 107.0, 2000),
        # 09:35 SL Hit
        make_candle(test_day, 9, 35, 106.0, 106.0, 90.0, 92.0, 1500),
    ]

    candles_sym2 = [
        make_candle(test_day, 9, 15, 200.0, 205.0, 195.0, 202.0, 1000),
        make_candle(test_day, 9, 20, 202.0, 204.0, 195.0, 199.0, 1000),
        make_candle(test_day, 9, 25, 199.0, 203.0, 195.0, 201.0, 1000),
        # 10:00 Breakout (should be blocked if circuit breaker tripped)
        make_candle(test_day, 10, 0, 201.0, 210.0, 200.0, 208.0, 2000),
        make_candle(test_day, 10, 5, 208.0, 220.0, 207.0, 218.0, 1500),
    ]

    # Set tight daily loss limit of ₹10 to ensure 1 trade trips it
    engine = BacktestEngine(initial_capital=5000.0, max_daily_loss=10.0)
    result = await engine.run(
        strategy_name="ORB_STRATEGY",
        symbols=["SYM1", "SYM2"],
        start_date=test_day,
        end_date=test_day,
        candles_by_symbol={"SYM1": candles_sym1, "SYM2": candles_sym2},
    )

    # Only 1 trade should be taken because circuit breaker blocked SYM2
    assert result.total_trades == 1
    assert result.trades[0].symbol == "SYM1"


@pytest.mark.asyncio
async def test_backtest_rest_api_flow():
    """Test full REST API lifecycle: run backtest, query runs, query detail, and export CSV."""
    from httpx import ASGITransport, AsyncClient
    import backend.app.models  # noqa: F401
    from backend.app.main import app

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Trigger backtest run
        payload = {
            "strategy_name": "ORB_STRATEGY",
            "symbols": ["RELIANCE", "TCS"],
            "start_date": "2026-11-01",
            "end_date": "2026-11-02",
            "initial_capital": 5000.0,
            "timeframe": "5m",
        }
        resp = await client.post("/v1/backtest/run", json=payload)
        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        run_id = data["data"]["id"]
        assert run_id > 0

        # 2. Query backtest runs
        runs_resp = await client.get("/v1/backtest/runs")
        assert runs_resp.status_code == 200
        runs_data = runs_resp.json()
        assert runs_data["success"] is True
        assert any(r["id"] == run_id for r in runs_data["data"]["items"])

        # 3. Query backtest run detail
        detail_resp = await client.get(f"/v1/backtest/runs/{run_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["success"] is True
        assert detail_data["data"]["id"] == run_id

        # 4. Query backtest run trades
        trades_resp = await client.get(f"/v1/backtest/runs/{run_id}/trades")
        assert trades_resp.status_code == 200

        # 5. Export backtest trades to CSV
        export_resp = await client.get(f"/v1/export/backtest/{run_id}")
        assert export_resp.status_code == 200
        assert "text/csv" in export_resp.headers["content-type"]

