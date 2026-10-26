import asyncio
import logging
import signal
import sys
from typing import Optional

from trading_engine.config.settings import engine_settings
from trading_engine.market_data.mock_provider import MockMarketDataProvider
from trading_engine.scanner.orb_scanner import ORBScanner
from trading_engine.strategy.orb import ORBStrategy
from trading_engine.risk.validator import RiskValidator
from trading_engine.risk.sizing import PositionSizer
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.portfolio.manager import PortfolioManager
from trading_engine.storage.repository import EngineStorageRepository

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

    async def start(self) -> None:
        """Start the trading worker event loop."""
        self.is_running = True
        logger.info("==================================================================")
        logger.info("  NSE INTRADAY TRADING ENGINE WORKER - STARTED")
        logger.info("  EXECUTION MODE: %s (Simulated orders only)", engine_settings.TRADING_MODE)
        logger.info("  INITIAL CAPITAL: ₹%.2f", engine_settings.PAPER_INITIAL_CAPITAL)
        logger.info("  DATABASE TARGET: %s", engine_settings.DATABASE_ASYNC_URL)
        logger.info("==================================================================")

        await self.market_data.connect()
        logger.info("Market data provider initialized (Mock Provider).")

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

                # Periodic heartbeat log
                if iteration % 10 == 0:
                    summary = self.portfolio.get_summary()
                    logger.info(
                        "Heartbeat cycle #%d | Positions: %d | Available Margin: ₹%.2f | Realized PnL: ₹%.2f",
                        iteration,
                        summary["open_positions_count"],
                        summary["available_margin"],
                        summary["realized_pnl"],
                    )

                await asyncio.sleep(engine_settings.ENGINE_SCAN_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Worker loop received cancellation signal.")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Perform graceful shutdown."""
        if not self.is_running:
            return
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
