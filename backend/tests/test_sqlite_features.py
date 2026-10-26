import asyncio
from datetime import datetime, timezone, date
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import settings
from backend.app.models.instrument import Instrument
from backend.app.models.market_candle import MarketCandle
from backend.app.models.trading_session import TradingSession
from backend.app.models.trading_config import TradingConfig


@pytest.mark.asyncio
async def test_crud_operations(db_session: AsyncSession):
    """Test Model creation, query, update, and deletion in SQLite."""
    # Create
    config = TradingConfig(
        key="TEST_KEY_CRUD",
        value="initial_value",
        description="Test configuration item",
        is_active=True,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    assert config.id is not None
    assert config.key == "TEST_KEY_CRUD"

    # Read
    fetched = await db_session.get(TradingConfig, config.id)
    assert fetched is not None
    assert fetched.value == "initial_value"

    # Update
    fetched.value = "updated_value"
    await db_session.commit()
    await db_session.refresh(fetched)
    assert fetched.value == "updated_value"

    # Delete
    await db_session.delete(fetched)
    await db_session.commit()
    deleted = await db_session.get(TradingConfig, config.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_foreign_key_enforcement(db_session: AsyncSession):
    """Test that SQLite PRAGMA foreign_keys=ON prevents orphan rows."""
    non_existent_instrument_id = 999999
    now = datetime.now(timezone.utc)

    candle = MarketCandle(
        instrument_id=non_existent_instrument_id,
        timeframe="5m",
        candle_timestamp=now,
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000,
    )
    db_session.add(candle)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_unique_candle_constraint(db_session: AsyncSession):
    """Test unique constraint on (instrument_id, timeframe, candle_timestamp)."""
    # Create valid instrument first
    import uuid
    unique_symbol = f"TCS_{uuid.uuid4().hex[:6].upper()}"
    inst = Instrument(
        symbol=unique_symbol,
        name="Tata Consultancy Services",
        exchange="NSE",
        token="11536",
        segment="EQUITY",
        lot_size=1,
        tick_size=0.05,
        is_tradable=True,
    )
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)

    fixed_timestamp = datetime(2026, 10, 26, 9, 15, 0, tzinfo=timezone.utc)

    # First candle succeeds
    candle1 = MarketCandle(
        instrument_id=inst.id,
        timeframe="15m",
        candle_timestamp=fixed_timestamp,
        open=3500.0,
        high=3520.0,
        low=3495.0,
        close=3510.0,
        volume=50000,
    )
    db_session.add(candle1)
    await db_session.commit()

    # Second duplicate candle must fail
    candle2 = MarketCandle(
        instrument_id=inst.id,
        timeframe="15m",
        candle_timestamp=fixed_timestamp,
        open=3510.0,
        high=3530.0,
        low=3505.0,
        close=3525.0,
        volume=30000,
    )
    db_session.add(candle2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_concurrent_reads():
    """Verify multiple concurrent readers operate seamlessly in WAL mode across sessions."""
    engine = create_async_engine(
        settings.DATABASE_ASYNC_URL,
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def read_count():
        async with session_maker() as session:
            result = await session.execute(text("SELECT count(*) FROM instruments"))
            return result.scalar()

    tasks = [read_count() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
    assert all(isinstance(r, int) for r in results)
    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_backend_and_worker_access():
    """Simulate independent processes (FastAPI backend and trading worker) accessing SQLite concurrently."""
    engine = create_async_engine(
        settings.DATABASE_ASYNC_URL,
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def worker_write_task(index: int):
        async with session_maker() as session:
            cfg = TradingConfig(
                key=f"CONCURRENT_WORKER_{index}_{datetime.now().timestamp()}",
                value=f"worker_val_{index}",
                description="Worker simulated concurrent write",
                is_active=True,
            )
            session.add(cfg)
            await session.commit()

    async def backend_read_task():
        async with session_maker() as session:
            res = await session.execute(text("SELECT count(*) FROM trading_configs"))
            return res.scalar()

    # Concurrently fire writes and reads
    tasks = [worker_write_task(i) for i in range(5)] + [backend_read_task() for _ in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    assert len(results) == 10

    await engine.dispose()
