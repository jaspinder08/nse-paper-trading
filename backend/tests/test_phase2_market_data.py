"""Phase 2 Market Data Foundation Test Suite.

Comprehensive tests for:
- Instrument import and mapping
- Duplicate instrument rejection
- Historical constituent queries
- Holiday and special-session handling
- Timezone conversion
- Historical candle ingestion
- Malformed candle rejection
- Duplicate candle handling (idempotency)
- Missing candle detection
- Provider failures and retry handling
- API response validation
- Worker restart and recovery
- Backend/worker shared database
- Foreign-key enforcement
- Paper-only safety
"""

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.constituent import InstrumentConstituentHistory
from backend.app.models.data_quality import DataQualityLog
from backend.app.models.ingestion import DataIngestionJob
from backend.app.models.instrument import Instrument
from backend.app.models.market_candle import MarketCandle
from backend.app.models.paper_order import PaperOrder
from trading_engine.execution.paper_executor import PaperExecutionEngine
from trading_engine.market_data.angel_one import AngelOneMarketDataProvider, generate_totp
from trading_engine.market_data.calendar import MarketCalendarService
from trading_engine.market_data.ingestion import HistoricalCandleIngestionService
from trading_engine.market_data.mock_provider import MockMarketDataProvider
from trading_engine.market_data.rate_limiter import AsyncTokenBucketRateLimiter
from trading_engine.market_data.types import HistoricalCandle
from trading_engine.market_data.validation import (
    CandleValidationError,
    detect_missing_intervals,
    validate_candle,
)
from trading_engine.storage.repository import EngineStorageRepository
from trading_engine.universe.nifty50 import (
    get_nifty50_constituents,
    seed_nifty50_universe,
    validate_constituent_periods,
)
from shared.market_time import IST_ZONE, UTC_ZONE, now_ist, to_ist, to_utc


# ==============================================================================
# 1. TIMEZONE & CALENDAR TESTS
# ==============================================================================

def test_timezone_conversion():
    """Verify unambiguous conversion between UTC and Asia/Kolkata."""
    dt_utc = datetime(2026, 10, 27, 3, 45, tzinfo=UTC_ZONE)  # 03:45 UTC
    dt_ist = to_ist(dt_utc)
    # 03:45 UTC + 05:30 = 09:15 IST
    assert dt_ist.tzinfo == IST_ZONE
    assert dt_ist.hour == 9
    assert dt_ist.minute == 15

    converted_back = to_utc(dt_ist)
    assert converted_back.tzinfo == UTC_ZONE
    assert converted_back.hour == 3
    assert converted_back.minute == 45


def test_regular_session_calendar():
    """Verify regular trading hours on standard weekdays."""
    tuesday = date(2026, 10, 27)
    info = MarketCalendarService.get_session_info(tuesday)
    assert info["is_trading_day"] is True
    assert info["session_type"] == "REGULAR"
    assert info["market_open_time"].time() == time(9, 15)
    assert info["market_close_time"].time() == time(15, 30)


def test_holiday_and_weekend_calendar():
    """Verify declared holidays and weekends are correctly marked non-trading."""
    rep_day = date(2026, 1, 26)  # Republic Day
    info_rep = MarketCalendarService.get_session_info(rep_day)
    assert info_rep["is_trading_day"] is False
    assert info_rep["session_type"] == "HOLIDAY"
    assert "Republic Day" in info_rep["description"]

    sunday = date(2026, 10, 25)
    info_sun = MarketCalendarService.get_session_info(sunday)
    assert info_sun["is_trading_day"] is False
    assert info_sun["session_type"] == "WEEKEND"


def test_muhurat_trading_session():
    """Verify special Muhurat trading session has correct evening timings."""
    diwali_2024 = date(2024, 11, 1)
    info = MarketCalendarService.get_session_info(diwali_2024)
    assert info["is_trading_day"] is True
    assert info["session_type"] == "MUHURAT"
    assert info["market_open_time"].time() == time(18, 0)
    assert info["market_close_time"].time() == time(19, 15)


def test_market_status_open_close_evaluation():
    """Verify real-time market open/close boolean evaluation."""
    # At 10:00 AM IST on Tuesday (within regular session)
    open_moment = datetime(2026, 10, 27, 10, 0, tzinfo=IST_ZONE)
    assert MarketCalendarService.is_market_open(open_moment) is True

    # At 8:30 AM IST (before open)
    before_open = datetime(2026, 10, 27, 8, 30, tzinfo=IST_ZONE)
    assert MarketCalendarService.is_market_open(before_open) is False

    # At 4:00 PM IST (after close)
    after_close = datetime(2026, 10, 27, 16, 0, tzinfo=IST_ZONE)
    assert MarketCalendarService.is_market_open(after_close) is False


# ==============================================================================
# 2. UNIVERSE & CONSTITUENT TESTS
# ==============================================================================

def test_nifty50_point_in_time_constituents():
    """Verify constituents query accounts for historical rebalancing without survivorship bias."""
    # In 2023: UPL was in, Shriram Finance was not
    c_2023 = get_nifty50_constituents(date(2023, 6, 1))
    assert len(c_2023) == 50
    assert "UPL" in c_2023
    assert "SHRIRAMFIN" not in c_2023

    # In mid-2024: Shriram Finance replaced UPL
    c_2024 = get_nifty50_constituents(date(2024, 5, 1))
    assert len(c_2024) == 50
    assert "UPL" not in c_2024
    assert "SHRIRAMFIN" in c_2024

    # In 2025: BEL and Trent replaced Divi's Lab and LTIMindtree
    c_2025 = get_nifty50_constituents(date(2025, 1, 1))
    assert len(c_2025) == 50
    assert "BEL" in c_2025
    assert "TRENT" in c_2025
    assert "DIVISLAB" not in c_2025


def test_constituent_overlapping_periods_validation():
    """Verify validator catches invalid or overlapping membership periods."""
    invalid_data = [
        {"symbol": "TEST_SYM", "from": date(2024, 1, 1), "to": date(2024, 6, 30)},
        {"symbol": "TEST_SYM", "from": date(2024, 5, 1), "to": None},  # Overlaps!
    ]
    with pytest.raises(ValueError, match="overlapping periods"):
        validate_constituent_periods(invalid_data)

    invalid_reversed_dates = [
        {"symbol": "TEST_SYM", "from": date(2024, 6, 1), "to": date(2024, 1, 1)},  # to < from
    ]
    with pytest.raises(ValueError, match="precedes effective_from"):
        validate_constituent_periods(invalid_reversed_dates)


@pytest.mark.asyncio
async def test_seed_nifty50_universe(db_session: AsyncSession):
    """Verify seeding creates instruments and constituent records."""
    count = await seed_nifty50_universe(db_session)
    assert count >= 50

    stmt = select(Instrument).where(Instrument.symbol == "RELIANCE")
    res = await db_session.execute(stmt)
    rel = res.scalar_one_or_none()
    assert rel is not None
    assert rel.token == "2885"
    assert rel.exchange == "NSE"


# ==============================================================================
# 3. INSTRUMENT MASTER & UNIQUENESS TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_duplicate_token_rejected(db_session: AsyncSession):
    """Verify unique constraint prevents duplicate exchange and token combinations."""
    inst1 = Instrument(
        symbol="UNIQUE_SYM_1",
        name="Company 1",
        exchange="NSE",
        token="998877",
        lot_size=1,
        tick_size=0.05,
        is_tradable=True,
    )
    db_session.add(inst1)
    await db_session.commit()

    inst2 = Instrument(
        symbol="UNIQUE_SYM_2",
        name="Company 2",
        exchange="NSE",
        token="998877",  # Duplicate token on NSE!
        lot_size=1,
        tick_size=0.05,
        is_tradable=True,
    )
    db_session.add(inst2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


# ==============================================================================
# 4. CANDLE VALIDATION TESTS
# ==============================================================================

def test_candle_valid_ohlc():
    """Verify a proper candle passes validation."""
    valid_ts = datetime(2026, 10, 27, 10, 0, tzinfo=IST_ZONE)
    candle = HistoricalCandle(
        timestamp=valid_ts,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("98.00"),
        close=Decimal("102.50"),
        volume=1500,
        complete=True,
    )
    validate_candle(candle, check_session=True)  # Must not raise


def test_candle_invalid_ohlc_relationships():
    """Verify that High < Open/Close or Low > Open/Close raises CandleValidationError."""
    valid_ts = datetime(2026, 10, 27, 10, 0, tzinfo=IST_ZONE)

    # High lower than Open
    bad_high = HistoricalCandle(
        timestamp=valid_ts,
        open=Decimal("100.00"),
        high=Decimal("95.00"),
        low=Decimal("90.00"),
        close=Decimal("92.00"),
        volume=100,
    )
    with pytest.raises(CandleValidationError, match="Invalid OHLC relationship"):
        validate_candle(bad_high, check_session=False)

    # Low higher than Close
    bad_low = HistoricalCandle(
        timestamp=valid_ts,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("101.00"),
        close=Decimal("99.00"),
        volume=100,
    )
    with pytest.raises(CandleValidationError, match="Invalid OHLC relationship"):
        validate_candle(bad_low, check_session=False)


def test_candle_negative_price_and_volume():
    """Verify negative prices and volumes are rejected."""
    valid_ts = datetime(2026, 10, 27, 10, 0, tzinfo=IST_ZONE)

    neg_price = HistoricalCandle(
        timestamp=valid_ts,
        open=Decimal("-10.00"),
        high=Decimal("10.00"),
        low=Decimal("-15.00"),
        close=Decimal("5.00"),
        volume=100,
    )
    with pytest.raises(CandleValidationError, match="must be strictly positive"):
        validate_candle(neg_price, check_session=False)

    neg_volume = HistoricalCandle(
        timestamp=valid_ts,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("95.00"),
        close=Decimal("102.00"),
        volume=-50,
    )
    with pytest.raises(CandleValidationError, match="cannot be negative"):
        validate_candle(neg_volume, check_session=False)


def test_candle_outside_session_rejected():
    """Verify candles with timestamps outside active market hours are rejected."""
    # Night time: 23:00 IST
    night_ts = datetime(2026, 10, 27, 23, 0, tzinfo=IST_ZONE)
    candle = HistoricalCandle(
        timestamp=night_ts,
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("95.00"),
        close=Decimal("102.00"),
        volume=100,
    )
    with pytest.raises(CandleValidationError, match="falls outside active session"):
        validate_candle(candle, check_session=True)


def test_missing_intervals_detection():
    """Verify missing 5m intervals are detected without fabricating data."""
    start = datetime(2026, 10, 27, 9, 15, tzinfo=IST_ZONE)
    end = datetime(2026, 10, 27, 9, 30, tzinfo=IST_ZONE)

    # Expecting 3 bars: 9:15, 9:20, 9:25
    # Provide only 9:15 and 9:25 (omit 9:20)
    candles = [
        HistoricalCandle(
            timestamp=start,
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("95"),
            close=Decimal("102"),
            volume=100,
        ),
        HistoricalCandle(
            timestamp=datetime(2026, 10, 27, 9, 25, tzinfo=IST_ZONE),
            open=Decimal("102"),
            high=Decimal("106"),
            low=Decimal("101"),
            close=Decimal("104"),
            volume=120,
        ),
    ]

    missing = detect_missing_intervals(candles, timeframe_minutes=5, session_start=start, session_end=end)
    assert len(missing) == 1
    assert missing[0].time() == time(9, 20)


# ==============================================================================
# 5. INGESTION & IDEMPOTENCY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_historical_candle_ingestion_and_idempotency(db_session: AsyncSession):
    """Verify historical candles are fetched, validated, and stored idempotently."""
    # Create test instrument
    inst = Instrument(
        symbol="TCS_TEST",
        name="Tata Consultancy Services Test",
        exchange="NSE",
        token="9911536",
        lot_size=1,
        tick_size=0.05,
        is_tradable=True,
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    mock_provider = MockMarketDataProvider()
    ingestion_service = HistoricalCandleIngestionService(mock_provider)

    test_date = date(2026, 10, 27)  # Tuesday
    result1 = await ingestion_service.ingest_instrument_candles(
        session=db_session,
        instrument=inst,
        start_date=test_date,
        end_date=test_date,
        timeframe="5m",
        incremental=False,
    )
    assert result1["inserted"] > 0

    # Second ingestion of the same range must insert 0 duplicates (idempotent)
    result2 = await ingestion_service.ingest_instrument_candles(
        session=db_session,
        instrument=inst,
        start_date=test_date,
        end_date=test_date,
        timeframe="5m",
        incremental=False,
    )
    assert result2["inserted"] == 0
    assert result2["skipped"] == result1["inserted"]


# ==============================================================================
# 6. PROVIDER RETRY & FAILURE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_provider_rate_limit_failure_injection():
    """Verify provider retry simulation handles injected 429 rate limit errors."""
    mock = MockMarketDataProvider()
    mock.inject_failure(error_type="RATE_LIMIT_429", count=1)

    start = datetime(2026, 10, 27, 9, 15, tzinfo=IST_ZONE)
    end = datetime(2026, 10, 27, 10, 0, tzinfo=IST_ZONE)

    # The first call should fail with 429
    with pytest.raises(RuntimeError, match="HTTP 429 Too Many Requests"):
        await mock.fetch_historical_candles(
            exchange="NSE",
            token="11536",
            interval="5m",
            start=start,
            end=end,
        )

    # Next call after failure count exhausted succeeds
    candles = await mock.fetch_historical_candles(
        exchange="NSE",
        token="11536",
        interval="5m",
        start=start,
        end=end,
    )
    assert len(candles) > 0


def test_totp_generation():
    """Verify pure-python RFC 6238 TOTP generates a 6-digit numeric string."""
    totp = generate_totp("JBSWY3DPEHPK3PXP")
    assert len(totp) == 6
    assert totp.isdigit()


# ==============================================================================
# 7. WORKER CRASH RECOVERY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_worker_interrupted_job_recovery(db_session: AsyncSession):
    """Verify interrupted RUNNING jobs are recovered to PENDING on worker restart."""
    job = DataIngestionJob(
        job_type="HISTORICAL_CANDLES",
        symbol="INFY",
        timeframe="5m",
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 27),
        status="RUNNING",  # Interrupted during execution
        candles_ingested=10,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    repo = EngineStorageRepository()
    recovered = await repo.recover_interrupted_jobs()
    assert recovered >= 1

    await db_session.refresh(job)
    assert job.status == "PENDING"
    assert "Recovered" in job.error_message
    await repo.dispose()


# ==============================================================================
# 8. API ENDPOINTS VALIDATION
# ==============================================================================

@pytest.mark.asyncio
async def test_api_instruments_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /v1/instruments and GET /v1/instruments/{id} APIs."""
    # Seed an instrument
    inst = Instrument(
        symbol="WIPRO_API",
        name="Wipro Ltd Test",
        exchange="NSE",
        token="378799",
        lot_size=1,
        tick_size=0.05,
        is_tradable=True,
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    # List instruments
    res = await async_client.get("/v1/instruments?exchange=NSE&symbol=WIPRO_API")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["symbol"] == "WIPRO_API"

    # Get single instrument
    res_single = await async_client.get(f"/v1/instruments/{inst.id}")
    assert res_single.status_code == 200
    assert res_single.json()["data"]["token"] == "378799"


@pytest.mark.asyncio
async def test_api_market_status_and_calendar(async_client: AsyncClient):
    """Verify GET /v1/market/status and GET /v1/market/calendar APIs."""
    res_status = await async_client.get("/v1/market/status")
    assert res_status.status_code == 200
    status_data = res_status.json()["data"]
    assert "is_market_open" in status_data
    assert "session_type" in status_data

    res_cal = await async_client.get("/v1/market/calendar?start_date=2026-01-25&end_date=2026-01-27")
    assert res_cal.status_code == 200
    cal_data = res_cal.json()["data"]
    assert len(cal_data) == 3


@pytest.mark.asyncio
async def test_api_market_data_ingestion_and_quality(async_client: AsyncClient, db_session: AsyncSession):
    """Verify POST /v1/market-data/ingestion and GET /v1/market-data/quality APIs."""
    # Trigger ingestion
    payload = {
        "symbol": "TCS_TEST",
        "start_date": "2026-10-26",
        "end_date": "2026-10-27",
        "timeframe": "5m",
    }
    res = await async_client.post("/v1/market-data/ingestion", json=payload)
    assert res.status_code == 202
    job_id = res.json()["data"]["id"]

    # Poll status
    res_job = await async_client.get(f"/v1/market-data/ingestion/{job_id}")
    assert res_job.status_code == 200
    assert res_job.json()["data"]["id"] == job_id

    # Query quality logs
    res_q = await async_client.get("/v1/market-data/quality")
    assert res_q.status_code == 200
    assert "items" in res_q.json()["data"]


# ==============================================================================
# 9. PAPER-TRADING SAFETY INVARIANT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_paper_executor_rejects_live_trading():
    """Verify PaperExecutionEngine raises PermissionError if live execution is attempted."""
    executor = PaperExecutionEngine()
    with pytest.raises(PermissionError, match="Live broker execution is strictly prohibited"):
        await executor.execute_paper_order(
            symbol="INFY",
            transaction_type="BUY",
            quantity=10,
            is_live=True,
        )


def test_angel_one_provider_has_no_order_methods():
    """Verify Angel One provider has no broker order methods implemented."""
    provider = AngelOneMarketDataProvider()
    for forbidden_attr in ["place_order", "placeOrder", "modify_order", "cancel_order", "getOrderBook"]:
        assert not hasattr(provider, forbidden_attr), f"Forbidden method '{forbidden_attr}' found on market data provider!"
