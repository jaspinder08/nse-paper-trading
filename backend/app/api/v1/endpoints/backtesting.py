"""Historical Backtesting REST router."""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.backtest import BacktestRun, BacktestTrade
from backend.app.models.instrument import Instrument
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.trading import (
    BacktestRequest,
    BacktestRunDetailResponse,
    BacktestRunResponse,
    BacktestTradeResponse,
)
from trading_engine.backtesting.engine import BacktestEngine, BacktestResult

router = APIRouter(prefix="/backtest", tags=["Backtesting"])


@router.get(
    "/runs",
    response_model=ApiResponse[PaginatedResponse[BacktestRunResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Backtest Simulation Runs",
)
async def list_backtest_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[BacktestRunResponse]]:
    stmt = select(BacktestRun).order_by(desc(BacktestRun.created_at))
    count_stmt = select(func.count()).select_from(BacktestRun)
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    runs = (await db.execute(paginated_stmt)).scalars().all()

    items = [
        BacktestRunResponse(
            id=r.id,
            strategy_name=r.strategy_name,
            start_date=r.start_date,
            end_date=r.end_date,
            initial_capital=float(r.initial_capital),
            final_capital=float(r.final_capital),
            total_trades=r.total_trades,
            win_rate=float(r.win_rate),
            profit_factor=float(r.profit_factor) if r.profit_factor else None,
            max_drawdown_pct=float(r.max_drawdown_pct) if r.max_drawdown_pct else None,
            status=r.status,
            created_at=r.created_at,
        )
        for r in runs
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.post(
    "/run",
    response_model=ApiResponse[BacktestRunResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute Backtest Simulation",
)
async def run_backtest(
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BacktestRunResponse]:
    # 1. Initialize and execute backtesting engine
    engine = BacktestEngine(initial_capital=request.initial_capital)
    result: BacktestResult = await engine.run(
        strategy_name=request.strategy_name,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        timeframe=request.timeframe,
        db_session=db,
    )

    # 2. Persist BacktestRun entity
    run = BacktestRun(
        strategy_name=result.strategy_name,
        timeframe=result.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        total_trades=result.total_trades,
        win_rate=result.win_rate,
        max_drawdown=result.max_drawdown_pct,
        parameters_json=json.dumps(result.to_dict()),
        status="COMPLETED",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # 3. Persist individual BacktestTrade records
    instrument_map: dict[str, int] = {}
    for t in result.trades:
        sym = t.symbol.upper()
        if sym not in instrument_map:
            inst_stmt = select(Instrument).where(Instrument.symbol == sym)
            inst = (await db.execute(inst_stmt)).scalar_one_or_none()
            if not inst:
                inst = Instrument(symbol=sym, name=f"{sym} Equity", exchange="NSE")
                db.add(inst)
                await db.commit()
                await db.refresh(inst)
            instrument_map[sym] = inst.id

        b_trade = BacktestTrade(
            backtest_run_id=run.id,
            instrument_id=instrument_map[sym],
            entry_time=datetime.fromisoformat(t.entry_time) if isinstance(t.entry_time, str) else t.entry_time,
            exit_time=datetime.fromisoformat(t.exit_time) if isinstance(t.exit_time, str) else t.exit_time,
            side=t.side,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            quantity=t.quantity,
            pnl=t.net_pnl,
            return_pct=t.return_pct,
        )
        db.add(b_trade)

    if result.trades:
        await db.commit()

    return ApiResponse(
        success=True,
        message=f"Backtest simulation {run.id} completed with {result.total_trades} trades.",
        data=BacktestRunResponse(
            id=run.id,
            strategy_name=run.strategy_name,
            start_date=run.start_date,
            end_date=run.end_date,
            initial_capital=float(run.initial_capital),
            final_capital=float(run.final_capital),
            total_trades=run.total_trades,
            win_rate=float(run.win_rate),
            profit_factor=result.profit_factor,
            max_drawdown_pct=result.max_drawdown_pct,
            status=run.status,
            created_at=run.created_at,
        ),
    )


@router.get(
    "/runs/{run_id}",
    response_model=ApiResponse[BacktestRunDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Backtest Results",
)
async def get_backtest_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BacktestRunDetailResponse]:
    stmt = select(BacktestRun).where(BacktestRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest run {run_id} not found",
        )

    meta = {}
    if run.parameters_json:
        try:
            meta = json.loads(run.parameters_json)
        except Exception:
            pass

    trades_list = [
        BacktestTradeResponse(
            id=t.get("id"),
            symbol=t.get("symbol", ""),
            entry_time=t.get("entry_time", ""),
            exit_time=t.get("exit_time", ""),
            side=t.get("side", "LONG"),
            quantity=t.get("quantity", 0),
            entry_price=float(t.get("entry_price", 0.0)),
            exit_price=float(t.get("exit_price", 0.0)),
            gross_pnl=float(t.get("gross_pnl", 0.0)),
            total_charges=float(t.get("total_charges", 0.0)),
            slippage_cost=float(t.get("slippage_cost", 0.0)),
            net_pnl=float(t.get("net_pnl", 0.0)),
            return_pct=float(t.get("return_pct", 0.0)),
            exit_reason=t.get("exit_reason"),
        )
        for t in meta.get("trades", [])
    ]

    detail = BacktestRunDetailResponse(
        id=run.id,
        strategy_name=run.strategy_name,
        start_date=run.start_date,
        end_date=run.end_date,
        initial_capital=float(run.initial_capital),
        final_capital=float(run.final_capital),
        total_trades=run.total_trades,
        win_rate=float(run.win_rate),
        profit_factor=float(run.profit_factor) if run.profit_factor else None,
        max_drawdown_pct=float(run.max_drawdown_pct) if run.max_drawdown_pct else None,
        status=run.status,
        created_at=run.created_at,
        net_pnl=float(meta.get("net_pnl", round(float(run.final_capital) - float(run.initial_capital), 2))),
        return_pct=float(meta.get("return_pct", 0.0)),
        gross_profit=float(meta.get("gross_profit", 0.0)),
        gross_loss=float(meta.get("gross_loss", 0.0)),
        total_charges=float(meta.get("total_charges", 0.0)),
        total_slippage=float(meta.get("total_slippage", 0.0)),
        average_win=float(meta.get("average_win", 0.0)),
        average_loss=float(meta.get("average_loss", 0.0)),
        payoff_ratio=float(meta.get("payoff_ratio", 0.0)),
        expectancy=float(meta.get("expectancy", 0.0)),
        max_drawdown_amount=float(meta.get("max_drawdown_amount", 0.0)),
        largest_win=float(meta.get("largest_win", 0.0)),
        largest_loss=float(meta.get("largest_loss", 0.0)),
        max_consecutive_wins=int(meta.get("max_consecutive_wins", 0)),
        max_consecutive_losses=int(meta.get("max_consecutive_losses", 0)),
        trades=trades_list,
    )

    return ApiResponse(success=True, data=detail)


@router.get(
    "/runs/{run_id}/trades",
    response_model=ApiResponse[PaginatedResponse[BacktestTradeResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Trades for a Backtest Run",
)
async def list_backtest_trades(
    run_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[BacktestTradeResponse]]:
    stmt = (
        select(BacktestTrade, Instrument.symbol)
        .join(Instrument, BacktestTrade.instrument_id == Instrument.id)
        .where(BacktestTrade.backtest_run_id == run_id)
        .order_by(BacktestTrade.entry_time.asc())
    )
    count_stmt = select(func.count()).select_from(BacktestTrade).where(BacktestTrade.backtest_run_id == run_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(paginated)).all()

    items = [
        BacktestTradeResponse(
            id=t.id,
            symbol=sym,
            entry_time=t.entry_time.isoformat(),
            exit_time=t.exit_time.isoformat(),
            side=t.side,
            quantity=t.quantity,
            entry_price=float(t.entry_price),
            exit_price=float(t.exit_price),
            gross_pnl=float(t.pnl),
            total_charges=0.0,
            slippage_cost=0.0,
            net_pnl=float(t.pnl),
            return_pct=float(t.return_pct),
        )
        for t, sym in rows
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )

