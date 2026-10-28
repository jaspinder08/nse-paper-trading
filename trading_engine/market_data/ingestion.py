"""Historical candlestick data ingestion engine.

Handles:
- Idempotent candle persistence
- Incremental historical fetching
- Rate-limited provider queries
- Validation and quality audit logging
- DataIngestionJob tracking
"""

from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.data_quality import DataQualityLog
from backend.app.models.ingestion import DataIngestionJob
from backend.app.models.instrument import Instrument
from backend.app.models.market_candle import MarketCandle
from trading_engine.market_data.base import AbstractMarketDataProvider
from trading_engine.market_data.calendar import MarketCalendarService
from trading_engine.market_data.validation import CandleValidationError, detect_missing_intervals, validate_candle
from trading_engine.universe.nifty50 import get_nifty50_constituents
from shared.market_time import IST_ZONE, to_ist, to_utc

logger = logging.getLogger("historical_ingestion")


class HistoricalCandleIngestionService:
    """Manages the end-to-end ingestion lifecycle of historical intraday bars."""

    def __init__(self, provider: AbstractMarketDataProvider) -> None:
        self.provider = provider

    async def get_latest_candle_timestamp(
        self,
        session: AsyncSession,
        instrument_id: int,
        timeframe: str = "5m",
    ) -> Optional[datetime]:
        """Query the most recent stored candle timestamp for an instrument."""
        stmt = (
            select(func.max(MarketCandle.candle_timestamp))
            .where(
                MarketCandle.instrument_id == instrument_id,
                MarketCandle.timeframe == timeframe,
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def ingest_instrument_candles(
        self,
        session: AsyncSession,
        instrument: Instrument,
        start_date: date,
        end_date: date,
        timeframe: str = "5m",
        incremental: bool = True,
    ) -> Dict[str, Any]:
        """Ingest candles for a single instrument between start_date and end_date."""
        if not instrument.token:
            raise ValueError(f"Instrument '{instrument.symbol}' has no exchange token.")

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=IST_ZONE)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=IST_ZONE)

        # If incremental, adjust start_dt if existing candles are present
        if incremental:
            latest_ts = await self.get_latest_candle_timestamp(session, instrument.id, timeframe)
            if latest_ts:
                latest_ist = to_ist(latest_ts)
                if latest_ist >= end_dt:
                    logger.info("Symbol %s is already up-to-date through %s.", instrument.symbol, latest_ist)
                    return {"symbol": instrument.symbol, "inserted": 0, "skipped": 0, "status": "UP_TO_DATE"}
                # Resume after latest candle (add 5 minutes)
                start_dt = max(start_dt, latest_ist + timedelta(minutes=5))

        logger.info(
            "Fetching historical candles for %s (token %s) from %s to %s...",
            instrument.symbol,
            instrument.token,
            start_dt.strftime("%Y-%m-%d %H:%M"),
            end_dt.strftime("%Y-%m-%d %H:%M"),
        )

        raw_candles = await self.provider.fetch_historical_candles(
            exchange=instrument.exchange,
            token=instrument.token,
            interval=timeframe,
            start=start_dt,
            end=end_dt,
        )

        inserted_count = 0
        skipped_count = 0

        def _normalize_dt(d: Any) -> datetime:
            if isinstance(d, datetime):
                if d.tzinfo is None:
                    return d.replace(tzinfo=timezone.utc)
                return d.astimezone(timezone.utc)
            return datetime.fromisoformat(str(d)).replace(tzinfo=timezone.utc)

        # Query existing timestamps for this instrument and timeframe to guarantee idempotency
        stmt_existing = select(MarketCandle.candle_timestamp).where(
            MarketCandle.instrument_id == instrument.id,
            MarketCandle.timeframe == timeframe,
        )
        res_existing = await session.execute(stmt_existing)
        existing_ts_set = {_normalize_dt(r[0]) for r in res_existing.fetchall()}

        for candle in raw_candles:
            # 1. Validate individual candle invariants
            try:
                validate_candle(candle, check_session=True)
            except CandleValidationError as val_err:
                logger.warning("Quality anomaly on %s candle %s: %s", instrument.symbol, candle.timestamp, val_err)
                quality_log = DataQualityLog(
                    instrument_id=instrument.id,
                    symbol=instrument.symbol,
                    check_type="INVALID_CANDLE",
                    severity="WARNING",
                    description=str(val_err),
                    candle_timestamp=to_utc(candle.timestamp),
                    detected_at=datetime.now(timezone.utc),
                )
                session.add(quality_log)
                skipped_count += 1
                continue

            # 2. Idempotent insertion check
            utc_ts = to_utc(candle.timestamp)
            if _normalize_dt(utc_ts) in existing_ts_set:
                skipped_count += 1
                continue

            # 3. Create persistent model
            db_candle = MarketCandle(
                instrument_id=instrument.id,
                timeframe=timeframe,
                candle_timestamp=utc_ts,
                open=float(candle.open),
                high=float(candle.high),
                low=float(candle.low),
                close=float(candle.close),
                volume=int(candle.volume),
            )
            session.add(db_candle)
            existing_ts_set.add(utc_ts)
            inserted_count += 1

        # 4. Check for missing intervals on active trading days in range
        curr_d = start_dt.date()
        while curr_d <= end_dt.date():
            sess = MarketCalendarService.get_session_info(curr_d)
            if sess["is_trading_day"] and sess["market_open_time"] and sess["market_close_time"]:
                missing = detect_missing_intervals(
                    candles=raw_candles,
                    timeframe_minutes=5,
                    session_start=sess["market_open_time"],
                    session_end=sess["market_close_time"],
                )
                if missing:
                    logger.debug("Symbol %s had %d missing intervals on %s.", instrument.symbol, len(missing), curr_d)
                    for m_ts in missing:
                        session.add(
                            DataQualityLog(
                                instrument_id=instrument.id,
                                symbol=instrument.symbol,
                                check_type="MISSING_INTERVAL",
                                severity="INFO",
                                description=f"Missing expected {timeframe} bar interval at {m_ts.strftime('%H:%M:%S')}",
                                candle_timestamp=to_utc(m_ts),
                                detected_at=datetime.now(timezone.utc),
                            )
                        )
            curr_d += timedelta(days=1)

        await session.commit()
        return {
            "symbol": instrument.symbol,
            "inserted": inserted_count,
            "skipped": skipped_count,
            "status": "COMPLETED",
        }

    async def execute_job(
        self,
        session: AsyncSession,
        job_id: int,
    ) -> DataIngestionJob:
        """Run an ingestion job asynchronously with state tracking."""
        stmt = select(DataIngestionJob).where(DataIngestionJob.id == job_id)
        res = await session.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            raise ValueError(f"Job #{job_id} not found.")

        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

        total_inserted = 0
        try:
            # Determine symbols to ingest
            if job.symbol:
                symbols = [job.symbol]
            else:
                symbols = get_nifty50_constituents(job.end_date)

            for sym in symbols:
                stmt_inst = select(Instrument).where(Instrument.symbol == sym, Instrument.exchange == "NSE")
                res_inst = await session.execute(stmt_inst)
                inst = res_inst.scalar_one_or_none()
                if not inst:
                    logger.warning("Instrument %s not found in database; skipping.", sym)
                    continue

                res_item = await self.ingest_instrument_candles(
                    session=session,
                    instrument=inst,
                    start_date=job.start_date,
                    end_date=job.end_date,
                    timeframe=job.timeframe,
                    incremental=True,
                )
                total_inserted += res_item.get("inserted", 0)

            job.status = "COMPLETED"
            job.candles_ingested = total_inserted
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return job

        except Exception as exc:
            logger.exception("Ingestion job #%d failed: %s", job_id, exc)
            job.status = "FAILED"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()
            raise
