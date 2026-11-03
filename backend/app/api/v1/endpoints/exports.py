"""CSV and JSON Data Export endpoints (FR-14)."""

import csv
import io
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.logs import TradeLog
from backend.app.models.position import Position
from backend.app.models.signal import TradingSignal

router = APIRouter(prefix="/export", tags=["Exports (CSV / JSON)"])


@router.get(
    "/signals",
    status_code=status.HTTP_200_OK,
    summary="Export Trading Signals to CSV",
)
async def export_signals_csv(db: AsyncSession = Depends(get_db)) -> Response:
    stmt = (
        select(TradingSignal, Instrument.symbol)
        .join(Instrument, TradingSignal.instrument_id == Instrument.id)
        .order_by(desc(TradingSignal.generated_at))
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "symbol", "strategy_name", "signal_type", "trigger_price",
        "stop_loss", "target_price", "status", "rejection_reason", "generated_at"
    ])
    for sig, sym in rows:
        writer.writerow([
            sig.id, sym, sig.strategy_name, sig.signal_type, float(sig.trigger_price),
            float(sig.stop_loss), float(sig.target_price), sig.status,
            sig.rejection_reason or "", sig.generated_at.isoformat()
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=signals.csv"},
    )


@router.get(
    "/trades",
    status_code=status.HTTP_200_OK,
    summary="Export Trade Journal to CSV",
)
async def export_trades_csv(db: AsyncSession = Depends(get_db)) -> Response:
    stmt = (
        select(TradeLog, Instrument.symbol)
        .join(Instrument, TradeLog.instrument_id == Instrument.id)
        .order_by(desc(TradeLog.log_timestamp))
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "symbol", "action", "quantity", "price", "pnl", "is_paper", "timestamp"])
    for t, sym in rows:
        writer.writerow([
            t.id, sym, t.action, t.quantity, float(t.price),
            float(t.pnl) if t.pnl is not None else "", t.is_paper, t.log_timestamp.isoformat()
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trade_journal.csv"},
    )


@router.get(
    "/positions",
    status_code=status.HTTP_200_OK,
    summary="Export Positions to CSV",
)
async def export_positions_csv(db: AsyncSession = Depends(get_db)) -> Response:
    stmt = (
        select(Position, Instrument.symbol)
        .join(Instrument, Position.instrument_id == Instrument.id)
        .order_by(desc(Position.entry_time))
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "symbol", "side", "quantity", "entry_price", "current_price",
        "stop_loss", "target", "realized_pnl", "unrealized_pnl", "status", "entry_time", "exit_time"
    ])
    for p, sym in rows:
        writer.writerow([
            p.id, sym, p.side, p.quantity, float(p.average_entry_price), float(p.current_price),
            float(p.stop_loss), float(p.target), float(p.realized_pnl), float(p.unrealized_pnl),
            p.status, p.entry_time.isoformat(), p.exit_time.isoformat() if p.exit_time else ""
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=positions.csv"},
    )


@router.get(
    "/backtest/{run_id}",
    status_code=status.HTTP_200_OK,
    summary="Export Backtest Run Trades to CSV",
)
async def export_backtest_csv(run_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    from backend.app.models.backtest import BacktestTrade

    stmt = (
        select(BacktestTrade, Instrument.symbol)
        .join(Instrument, BacktestTrade.instrument_id == Instrument.id)
        .where(BacktestTrade.backtest_run_id == run_id)
        .order_by(BacktestTrade.entry_time.asc())
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "symbol", "side", "quantity", "entry_price", "exit_price",
        "pnl", "return_pct", "entry_time", "exit_time"
    ])
    for t, sym in rows:
        writer.writerow([
            t.id, sym, t.side, t.quantity, float(t.entry_price), float(t.exit_price),
            float(t.pnl), float(t.return_pct), t.entry_time.isoformat(), t.exit_time.isoformat()
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=backtest_run_{run_id}_trades.csv"},
    )

