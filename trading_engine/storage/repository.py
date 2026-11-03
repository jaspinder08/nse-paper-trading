"""Async repository for trading worker persistence using SQLite (or PostgreSQL)."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import event, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.models.ingestion import DataIngestionJob
from backend.app.models.instrument import Instrument
from backend.app.models.logs import RiskLog, SystemLog, TradeLog
from backend.app.models.paper_order import PaperOrder
from backend.app.models.portfolio import PortfolioSnapshot
from backend.app.models.position import Position
from backend.app.models.signal import TradingSignal
from backend.app.models.trading_session import TradingSession
from shared.market_time import now_ist
from shared.runtime_config import sqlite_path_from_url
from trading_engine.config.settings import engine_settings


class EngineStorageRepository:
    """Async repository for trading worker persistence using SQLite (or PostgreSQL)."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self.db_url = db_url or engine_settings.DATABASE_ASYNC_URL
        self._ensure_dir()

        connect_args = {}
        if "sqlite" in self.db_url.lower():
            connect_args["check_same_thread"] = False

        self.engine = create_async_engine(
            self.db_url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )

        if "sqlite" in self.db_url.lower():
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_pragmas(dbapi_connection, _):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=10000")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def _ensure_dir(self) -> None:
        sqlite_path_from_url(self.db_url).parent.mkdir(parents=True, exist_ok=True)

    async def log_system_event(self, level: str, module: str, message: str, details: Optional[str] = None) -> None:
        """Write a system diagnostic event using a short transaction."""
        async with self.session_factory() as session:
            async with session.begin():
                log_entry = SystemLog(
                    level=level,
                    module=module,
                    message=message,
                    details=details,
                    logged_at=datetime.now(timezone.utc),
                )
                session.add(log_entry)

    async def get_or_create_today_session(self, initial_capital: float) -> int:
        """Get or initialize today's TradingSession in the database."""
        today = now_ist().date()
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(TradingSession).where(TradingSession.session_date == today)
                existing = (await session.execute(stmt)).scalar_one_or_none()
                if existing:
                    return existing.id

                new_session = TradingSession(
                    session_date=today,
                    status="ACTIVE",
                    is_paper=True,
                    initial_capital=initial_capital,
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    notes="Automated Intraday Paper Session",
                )
                session.add(new_session)
                await session.flush()
                return new_session.id

    async def get_instrument_by_symbol(self, symbol: str) -> Optional[Instrument]:
        """Fetch instrument record by trading symbol."""
        async with self.session_factory() as session:
            stmt = select(Instrument).where(Instrument.symbol == symbol.upper())
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def record_signal(
        self,
        session_id: Optional[int],
        instrument_id: int,
        strategy_name: str,
        signal_type: str,
        trigger_price: float,
        stop_loss: float,
        target_price: float,
        status: str = "GENERATED",
        rejection_reason: Optional[str] = None,
        generated_at: Optional[datetime] = None,
    ) -> int:
        """Persist a strategy trading signal."""
        async with self.session_factory() as session:
            async with session.begin():
                sig = TradingSignal(
                    session_id=session_id,
                    instrument_id=instrument_id,
                    strategy_name=strategy_name,
                    signal_type=signal_type,
                    trigger_price=trigger_price,
                    stop_loss=stop_loss,
                    target_price=target_price,
                    status=status,
                    rejection_reason=rejection_reason,
                    generated_at=generated_at or datetime.now(timezone.utc),
                )
                session.add(sig)
                await session.flush()
                return sig.id

    async def record_risk_log(
        self,
        session_id: Optional[int],
        signal_id: Optional[int],
        check_name: str,
        passed: bool,
        reason: Optional[str] = None,
    ) -> int:
        """Persist a risk gatekeeper audit log."""
        async with self.session_factory() as session:
            async with session.begin():
                entry = RiskLog(
                    session_id=session_id,
                    signal_id=signal_id,
                    check_name=check_name,
                    passed=passed,
                    reason=reason,
                )
                session.add(entry)
                await session.flush()
                return entry.id

    async def record_paper_order(
        self,
        session_id: Optional[int],
        instrument_id: int,
        signal_id: Optional[int],
        transaction_type: str,
        quantity: int,
        requested_price: float,
        executed_price: float,
        status: str = "FILLED",
        executed_at: Optional[datetime] = None,
    ) -> int:
        """Persist an executed simulated paper order."""
        async with self.session_factory() as session:
            async with session.begin():
                order = PaperOrder(
                    session_id=session_id,
                    instrument_id=instrument_id,
                    signal_id=signal_id,
                    order_type="MARKET",
                    transaction_type=transaction_type,
                    quantity=quantity,
                    requested_price=requested_price,
                    executed_price=executed_price,
                    status=status,
                    is_paper=True,
                    executed_at=executed_at or datetime.now(timezone.utc),
                )
                session.add(order)
                await session.flush()
                return order.id

    async def create_position(
        self,
        session_id: Optional[int],
        instrument_id: int,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
    ) -> int:
        """Open a new simulated paper position."""
        async with self.session_factory() as session:
            async with session.begin():
                pos = Position(
                    session_id=session_id,
                    instrument_id=instrument_id,
                    side=side,
                    quantity=quantity,
                    average_entry_price=entry_price,
                    current_price=entry_price,
                    stop_loss=stop_loss,
                    target=target,
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                    status="OPEN",
                    is_paper=True,
                    entry_time=datetime.now(timezone.utc),
                )
                session.add(pos)
                await session.flush()
                return pos.id

    async def get_open_positions_with_instruments(self) -> List[Dict[str, Any]]:
        """Retrieve all currently active OPEN positions with instrument details."""
        async with self.session_factory() as session:
            stmt = (
                select(Position, Instrument.symbol)
                .join(Instrument, Position.instrument_id == Instrument.id)
                .where(Position.status == "OPEN")
            )
            rows = (await session.execute(stmt)).all()
            return [
                {
                    "position": pos,
                    "symbol": sym,
                    "id": pos.id,
                    "instrument_id": pos.instrument_id,
                    "quantity": pos.quantity,
                    "entry_price": float(pos.average_entry_price),
                    "current_price": float(pos.current_price),
                    "stop_loss": float(pos.stop_loss),
                    "target": float(pos.target),
                    "realized_pnl": float(pos.realized_pnl),
                    "unrealized_pnl": float(pos.unrealized_pnl),
                }
                for pos, sym in rows
            ]

    async def update_position_price_and_pnl(self, position_id: int, current_price: float) -> None:
        """Update current mark-to-market price and unrealized P&L for an open position."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(Position).where(Position.id == position_id)
                pos = (await session.execute(stmt)).scalar_one_or_none()
                if pos and pos.status == "OPEN":
                    pos.current_price = current_price
                    pos.unrealized_pnl = round((current_price - float(pos.average_entry_price)) * pos.quantity, 2)

    async def close_position(
        self,
        position_id: int,
        exit_price: float,
        pnl: float,
        session_id: Optional[int] = None,
    ) -> None:
        """Close an active position and update trading session stats."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(Position).where(Position.id == position_id)
                pos = (await session.execute(stmt)).scalar_one_or_none()
                if pos:
                    pos.status = "CLOSED"
                    pos.current_price = exit_price
                    pos.realized_pnl = pnl
                    pos.unrealized_pnl = 0.0
                    pos.exit_time = datetime.now(timezone.utc)

                if session_id:
                    sess_stmt = select(TradingSession).where(TradingSession.id == session_id)
                    ts = (await session.execute(sess_stmt)).scalar_one_or_none()
                    if ts:
                        ts.realized_pnl = float(ts.realized_pnl) + pnl
                        ts.total_trades += 1
                        if pnl > 0:
                            ts.winning_trades += 1
                        elif pnl < 0:
                            ts.losing_trades += 1

    async def record_trade_log(
        self,
        order_id: Optional[int],
        position_id: Optional[int],
        instrument_id: int,
        action: str,  # ENTRY, EXIT, SL_HIT, TARGET_HIT, SQUARE_OFF
        quantity: int,
        price: float,
        pnl: Optional[float] = None,
    ) -> int:
        """Persist a trade lifecycle event."""
        async with self.session_factory() as session:
            async with session.begin():
                log = TradeLog(
                    order_id=order_id,
                    position_id=position_id,
                    instrument_id=instrument_id,
                    action=action,
                    quantity=quantity,
                    price=price,
                    pnl=pnl,
                    is_paper=True,
                    log_timestamp=datetime.now(timezone.utc),
                )
                session.add(log)
                await session.flush()
                return log.id

    async def recover_interrupted_jobs(self) -> int:
        """Recover any jobs left in 'RUNNING' status from previous worker crashes or restarts."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = (
                    update(DataIngestionJob)
                    .where(DataIngestionJob.status == "RUNNING")
                    .values(
                        status="PENDING",
                        error_message="Recovered from worker restart",
                    )
                )
                res = await session.execute(stmt)
                return res.rowcount or 0

    async def get_next_pending_job_id(self) -> Optional[int]:
        """Fetch the ID of the next pending ingestion job, if any."""
        async with self.session_factory() as session:
            stmt = (
                select(DataIngestionJob.id)
                .where(DataIngestionJob.status == "PENDING")
                .order_by(DataIngestionJob.id.asc())
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def dispose(self) -> None:
        await self.engine.dispose()
