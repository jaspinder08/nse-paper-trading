"""Independent paper trading worker process.

Strict safety invariants:
- Strictly Paper Trading mode
- All orders simulated with statutory cost and adverse slippage modeling
- Live broker execution interfaces rejected across all layers
- Automatic risk gatekeeping, position sizing, and EOD square-off
"""

import asyncio
from datetime import datetime, time, timezone
import logging
import signal
import sys
from typing import Any, Dict, List, Optional

from shared.market_time import IST_ZONE, now_ist
from trading_engine.config.settings import engine_settings
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.market_data.calendar import MarketCalendarService
from trading_engine.market_data.ingestion import HistoricalCandleIngestionService
from trading_engine.market_data.mock_provider import MockMarketDataProvider
from trading_engine.portfolio.manager import PortfolioManager
from trading_engine.risk.models import RiskVerdict
from trading_engine.risk.sizing import PositionSizer
from trading_engine.risk.validator import RiskValidator
from trading_engine.scanner.orb_scanner import ORBScanner
from trading_engine.storage.repository import EngineStorageRepository
from trading_engine.strategy.orb import ORBStrategy
from trading_engine.universe.nifty50 import get_nifty50_constituents, seed_nifty50_universe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | [TradingWorker] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trading_worker")


class TradingWorker:
    """Independent paper trading worker process."""

    def __init__(self) -> None:
        if engine_settings.MARKET_DATA_PROVIDER.lower() == "angel_one" and engine_settings.SMARTAPI_API_KEY:
            from trading_engine.market_data.angel_one import AngelOneMarketDataProvider
            self.market_data = AngelOneMarketDataProvider(
                api_key=engine_settings.SMARTAPI_API_KEY,
                client_code=engine_settings.SMARTAPI_CLIENT_CODE,
                password=engine_settings.SMARTAPI_PASSWORD,
                totp_key=engine_settings.SMARTAPI_TOTP_KEY,
            )
        else:
            self.market_data = MockMarketDataProvider()

        self.strategy = ORBStrategy()
        self.scanner = ORBScanner(strategy=self.strategy, market_data_provider=self.market_data)
        self.position_sizer = PositionSizer(
            max_risk_per_trade_inr=engine_settings.MAX_RISK_PER_TRADE_INR,
            cash_reserve_pct=engine_settings.CASH_RESERVE_PCT,
            max_position_pct=engine_settings.MAX_POSITION_PCT,
        )
        self.risk_validator = RiskValidator(
            max_daily_loss=engine_settings.MAX_DAILY_LOSS_INR,
            max_open_positions=engine_settings.MAX_OPEN_POSITIONS,
            max_trades_per_day=engine_settings.MAX_TRADES_PER_DAY,
            max_events_per_day=engine_settings.MAX_EVENTS_PER_DAY,
            min_reward_risk=engine_settings.MIN_REWARD_RISK,
            position_sizer=self.position_sizer,
        )
        self.execution = PaperExecutionEngine()
        self.portfolio = PortfolioManager(initial_capital=engine_settings.PAPER_INITIAL_CAPITAL)
        self.storage = EngineStorageRepository()
        self.ingestion_service = HistoricalCandleIngestionService(self.market_data)
        self.session_id: Optional[int] = None
        self.is_running: bool = False

    async def start(self) -> None:
        """Start the trading worker event loop."""
        self.is_running = True
        logger.info("==================================================================")
        logger.info("  NSE INTRADAY TRADING ENGINE WORKER - STARTED")
        logger.info("  EXECUTION MODE: %s (Simulated orders only)", engine_settings.TRADING_MODE)
        logger.info("  INITIAL CAPITAL: ₹%.2f", engine_settings.PAPER_INITIAL_CAPITAL)
        logger.info("  DATABASE TARGET: local SQLite database")
        logger.info("==================================================================")

        await self.market_data.connect()
        provider_name = "Angel One SmartAPI" if engine_settings.MARKET_DATA_PROVIDER.lower() == "angel_one" else "Mock Provider"
        logger.info("Market data provider initialized (%s).", provider_name)

        # Seed instruments master if needed
        try:
            async with self.storage.session_factory() as session:
                synced = await seed_nifty50_universe(session)
                if synced > 0:
                    logger.info("Synchronized %d NIFTY 50 instrument constituent records.", synced)
        except Exception as seed_err:
            logger.warning("Could not verify instrument constituent seeding: %s", seed_err)

        # Initialize today's trading session
        try:
            self.session_id = await self.storage.get_or_create_today_session(engine_settings.PAPER_INITIAL_CAPITAL)
            logger.info("Active Trading Session ID: #%d", self.session_id)
        except Exception as sess_err:
            logger.warning("Could not initialize session record: %s", sess_err)

        # Recover any interrupted jobs from previous worker crash
        try:
            recovered_count = await self.storage.recover_interrupted_jobs()
            if recovered_count > 0:
                logger.info("Worker recovery: Reset %d interrupted ingestion job(s) to PENDING.", recovered_count)
        except Exception as exc:
            logger.warning("Could not execute job recovery: %s", exc)

        try:
            await self.storage.log_system_event(
                level="INFO",
                module="TradingWorker",
                message="Trading engine worker initialized successfully.",
                details="Paper-trading simulation engine started.",
            )
        except Exception as e:
            logger.warning("Could not log startup event to storage: %s", str(e))

        iteration = 0
        try:
            while self.is_running:
                iteration += 1

                # 1. Process pending historical candle ingestion jobs if any
                try:
                    job_id = await self.storage.get_next_pending_job_id()
                    if job_id:
                        logger.info("Found pending ingestion job #%d; executing...", job_id)
                        async with self.storage.session_factory() as session:
                            await self.ingestion_service.execute_job(session, job_id)
                        logger.info("Completed ingestion job #%d.", job_id)
                except Exception as job_err:
                    logger.exception("Ingestion job execution encountered error: %s", job_err)

                # 2. Manage Active Open Positions (Check SL, Target, EOD Square-Off)
                try:
                    await self._manage_open_positions()
                except Exception as pos_err:
                    logger.exception("Error managing open positions: %s", pos_err)

                # 3. Scan Nifty 50 and Execute Breakout Paper Orders
                try:
                    await self._scan_and_execute_breakouts()
                except Exception as scan_err:
                    logger.exception("Error in scanner execution: %s", scan_err)

                # 4. Periodic heartbeat log
                if iteration % 15 == 0:
                    summary = self.portfolio.get_summary()
                    market_stat = MarketCalendarService.get_market_status()
                    logger.info(
                        "Heartbeat #%d | Market: %s (%s) | Open Positions: %d | Realized P&L: ₹%.2f",
                        iteration,
                        "OPEN" if market_stat["is_market_open"] else "CLOSED",
                        market_stat["session_type"],
                        summary["open_positions_count"],
                        summary["realized_pnl"],
                    )

                try:
                    await asyncio.sleep(engine_settings.ENGINE_SCAN_INTERVAL_SECONDS)
                except Exception:
                    await asyncio.sleep(min(engine_settings.ENGINE_SCAN_INTERVAL_SECONDS, 1.0))

        except asyncio.CancelledError:
            logger.info("Worker loop received cancellation signal.")
        finally:
            await self.stop()

    async def _manage_open_positions(self) -> None:
        """Monitor open positions against current market price for target, stop-loss, or EOD exit."""
        open_positions = await self.storage.get_open_positions_with_instruments()
        if not open_positions:
            return

        current_time = now_ist().time()
        is_eod_square_off = current_time >= time(15, 15, 0)  # Standard NSE square-off at 15:15 IST

        for pos_data in open_positions:
            pos_id = pos_data["id"]
            symbol = pos_data["symbol"]
            inst_id = pos_data["instrument_id"]
            entry_price = pos_data["entry_price"]
            stop_loss = pos_data["stop_loss"]
            target = pos_data["target"]
            qty = pos_data["quantity"]

            # Fetch latest price
            try:
                # Query recent candle for symbol
                candles = await self.market_data.fetch_candles(
                    symbol=symbol,
                    timeframe="5m",
                    from_dt=datetime.combine(now_ist().date(), datetime.min.time()),
                    to_dt=datetime.combine(now_ist().date(), datetime.max.time()),
                )
                if not candles:
                    continue
                current_price = float(candles[-1].close)
            except Exception:
                current_price = pos_data["current_price"]

            # Update mark-to-market unrealized P&L
            await self.storage.update_position_price_and_pnl(pos_id, current_price)

            # Check exit conditions
            exit_reason: Optional[str] = None
            if current_price >= target:
                exit_reason = "TARGET_HIT"
            elif current_price <= stop_loss:
                exit_reason = "SL_HIT"
            elif is_eod_square_off:
                exit_reason = "SQUARE_OFF"

            if exit_reason:
                logger.info("Position #%d (%s) exit triggered: %s at ₹%.2f (Entry: ₹%.2f)", pos_id, symbol, exit_reason, current_price, entry_price)
                fill = await self.execution.execute_paper_order(
                    symbol=symbol,
                    transaction_type="SELL",
                    quantity=qty,
                    order_type="MARKET",
                    price=current_price,
                    price_timestamp=datetime.now(timezone.utc),
                    has_complete_candle=True,
                    risk_approved=True,
                )

                executed_price = fill["executed_price"]
                pnl = round((executed_price - entry_price) * qty, 2)

                order_id = await self.storage.record_paper_order(
                    session_id=self.session_id,
                    instrument_id=inst_id,
                    signal_id=None,
                    transaction_type="SELL",
                    quantity=qty,
                    requested_price=current_price,
                    executed_price=executed_price,
                    status="FILLED",
                )

                await self.storage.close_position(
                    position_id=pos_id,
                    exit_price=executed_price,
                    pnl=pnl,
                    session_id=self.session_id,
                )

                await self.storage.record_trade_log(
                    order_id=order_id,
                    position_id=pos_id,
                    instrument_id=inst_id,
                    action=exit_reason,
                    quantity=qty,
                    price=executed_price,
                    pnl=pnl,
                )

                self.portfolio.realized_pnl += pnl
                if symbol in self.portfolio.open_positions:
                    del self.portfolio.open_positions[symbol]

                logger.info(
                    "CLOSED Position #%d (%s) via %s | PnL: ₹%+.2f (Fees/Slippage deducted)",
                    pos_id, symbol, exit_reason, pnl
                )

    async def _scan_and_execute_breakouts(self) -> None:
        """Scan Nifty 50 constituents and execute simulated orders for validated breakout candidates."""
        current_time = now_ist().time()
        # Only evaluate breakout entries between 09:30 and 14:30 IST
        if current_time < time(9, 30, 0) or current_time > time(14, 30, 0):
            return

        constituents = get_nifty50_constituents(now_ist().date())
        # Fetch existing open positions to prevent duplicate entries
        open_positions = await self.storage.get_open_positions_with_instruments()
        pos_by_symbol = {p["symbol"]: p for p in open_positions}

        # Scan universe
        scan_results = await self.scanner.scan(universe=constituents)
        triggered_candidates = [c for c in scan_results if c["status"] == "TRIGGERED"]

        for cand in triggered_candidates:
            symbol = cand["symbol"]
            signal_data = cand.get("signal")
            if not signal_data:
                continue

            # Skip if already holding an open position
            if symbol in pos_by_symbol:
                continue

            inst = await self.storage.get_instrument_by_symbol(symbol)
            if not inst:
                continue

            # Risk gatekeeper validation
            summary = self.portfolio.get_summary()
            verdict: RiskVerdict = self.risk_validator.validate_candidate(
                signal=signal_data,
                equity=summary["net_equity"],
                available_cash=summary["available_margin"],
                current_daily_pnl=summary["realized_pnl"],
                open_positions=pos_by_symbol,
                trades_today_count=len(open_positions),
            )

            # Record signal in database
            sig_id = await self.storage.record_signal(
                session_id=self.session_id,
                instrument_id=inst.id,
                strategy_name="ORB_STRATEGY",
                signal_type="BUY",
                trigger_price=signal_data["entry_price"],
                stop_loss=signal_data["stop_loss"],
                target_price=signal_data["target_price"],
                status="RISK_APPROVED" if verdict.approved else "RISK_REJECTED",
                rejection_reason=None if verdict.approved else verdict.reason,
            )

            # Record risk audit log
            await self.storage.record_risk_log(
                session_id=self.session_id,
                signal_id=sig_id,
                check_name="ORB_RISK_GATEKEEPER",
                passed=verdict.approved,
                reason=verdict.reason,
            )

            if not verdict.approved:
                logger.debug("Signal for %s rejected by risk: %s", symbol, verdict.reason)
                continue

            # Execute Paper Order!
            qty = verdict.adjusted_quantity
            entry_price = signal_data["entry_price"]

            logger.info("EXECUTING Paper BUY Order: %d shares of %s at ₹%.2f...", qty, symbol, entry_price)
            fill = await self.execution.execute_paper_order(
                symbol=symbol,
                transaction_type="BUY",
                quantity=qty,
                order_type="MARKET",
                price=entry_price,
                price_timestamp=datetime.now(timezone.utc),
                has_complete_candle=True,
                risk_approved=True,
            )

            executed_price = fill["executed_price"]

            # Record Order in DB
            order_id = await self.storage.record_paper_order(
                session_id=self.session_id,
                instrument_id=inst.id,
                signal_id=sig_id,
                transaction_type="BUY",
                quantity=qty,
                requested_price=entry_price,
                executed_price=executed_price,
                status="FILLED",
            )

            # Open Position in DB
            pos_id = await self.storage.create_position(
                session_id=self.session_id,
                instrument_id=inst.id,
                side="LONG",
                quantity=qty,
                entry_price=executed_price,
                stop_loss=signal_data["stop_loss"],
                target=signal_data["target_price"],
            )

            # Record Trade Log
            await self.storage.record_trade_log(
                order_id=order_id,
                position_id=pos_id,
                instrument_id=inst.id,
                action="ENTRY",
                quantity=qty,
                price=executed_price,
            )

            # Update In-Memory Portfolio
            self.portfolio.open_positions[symbol] = {
                "id": pos_id,
                "quantity": qty,
                "entry_price": executed_price,
                "current_price": executed_price,
                "stop_loss": signal_data["stop_loss"],
                "target": signal_data["target_price"],
            }
            pos_by_symbol[symbol] = self.portfolio.open_positions[symbol]

            logger.info(
                "FILLED Paper BUY Order #%d | %s | %d shares @ ₹%.2f (Target: ₹%.2f, SL: ₹%.2f)",
                order_id, symbol, qty, executed_price, signal_data["target_price"], signal_data["stop_loss"]
            )

    async def stop(self) -> None:
        """Perform graceful shutdown."""
        self.is_running = False
        logger.info("Stopping trading worker and releasing resources...")
        await self.market_data.disconnect()
        await self.storage.dispose()
        logger.info("Trading worker shutdown complete.")


async def main() -> None:
    worker = TradingWorker()
    loop = asyncio.get_running_loop()

    # Graceful shutdown handler
    def handle_signal(sig, frame):
        logger.info("Received termination signal (%s). Initiating graceful shutdown...", sig)
        worker.is_running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(worker.stop()))
        except NotImplementedError:
            signal.signal(sig, handle_signal)

    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process exited.")
