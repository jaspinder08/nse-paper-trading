"""Independent paper trading worker process.

Strict safety invariants:
- Strictly Paper Trading mode
- All orders simulated
- Live broker execution interfaces rejected
- Rate-limited historical candle ingestion
- Graceful recovery on restart
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from trading_engine.config.settings import engine_settings
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.market_data.calendar import MarketCalendarService
from trading_engine.market_data.ingestion import HistoricalCandleIngestionService
from trading_engine.market_data.mock_provider import MockMarketDataProvider
from trading_engine.portfolio.manager import PortfolioManager
from trading_engine.risk.sizing import PositionSizer
from trading_engine.risk.validator import RiskValidator
from trading_engine.scanner.orb_scanner import ORBScanner
from trading_engine.storage.repository import EngineStorageRepository
from trading_engine.strategy.orb import ORBStrategy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | [TradingWorker] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("trading_worker")


class TradingWorker:
    """Independent paper trading worker process."""

    def __init__(self) -> None:
        self.is_running: bool = False
        self.market_data = MockMarketDataProvider()
        self.scanner = ORBScanner()
        self.strategy = ORBStrategy()
        self.risk_validator = RiskValidator()
        self.position_sizer = PositionSizer()
        self.execution = PaperExecutionEngine()
        self.portfolio = PortfolioManager(initial_capital=engine_settings.PAPER_INITIAL_CAPITAL)
        self.storage = EngineStorageRepository()
        self.ingestion_service = HistoricalCandleIngestionService(self.market_data)

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
        logger.info("Market data provider initialized (Mock Provider).")

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
                logger.debug("Worker cycle #%d executing scan...", iteration)

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

                # 2. Periodic heartbeat log
                if iteration % 10 == 0:
                    summary = self.portfolio.get_summary()
                    market_stat = MarketCalendarService.get_market_status()
                    logger.info(
                        "Heartbeat cycle #%d | Market Open: %s (%s) | Positions: %d | Realized PnL: ₹%.2f",
                        iteration,
                        market_stat["is_market_open"],
                        market_stat["session_type"],
                        summary["open_positions_count"],
                        summary["realized_pnl"],
                    )

                try:
                    await asyncio.sleep(engine_settings.ENGINE_SCAN_INTERVAL_SECONDS)
                except Exception:
                    logger.exception("Worker cycle pause failed; continuing.")
                    await asyncio.sleep(min(engine_settings.ENGINE_SCAN_INTERVAL_SECONDS, 1.0))

        except asyncio.CancelledError:
            logger.info("Worker loop received cancellation signal.")
        finally:
            await self.stop()

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
            # Fallback for Windows
            signal.signal(sig, handle_signal)

    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process exited.")
