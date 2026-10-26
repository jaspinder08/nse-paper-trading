import asyncio

import pytest
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.database.retry import MAX_SQLITE_WRITE_ATTEMPTS, commit_with_retry
from backend.app.database.session import AsyncSessionLocal
from shared.runtime_config import canonical_sqlite_url, sqlite_path_from_url
from trading_engine.config.settings import engine_settings


def test_backend_and_worker_use_same_absolute_database_path():
    assert sqlite_path_from_url(settings.DATABASE_ASYNC_URL).is_absolute()
    assert sqlite_path_from_url(settings.DATABASE_ASYNC_URL) == sqlite_path_from_url(engine_settings.DATABASE_ASYNC_URL)
    canonical = canonical_sqlite_url("sqlite+aiosqlite:///./data/nse_paper_trading.db", "async")
    assert sqlite_path_from_url(canonical).name == "nse_paper_trading.db"
    assert sqlite_path_from_url(canonical).is_absolute()


@pytest.mark.asyncio
async def test_application_connection_pragmas():
    async with AsyncSessionLocal() as session:
        foreign_keys = (await session.execute(text("PRAGMA foreign_keys"))).scalar_one()
        busy_timeout = (await session.execute(text("PRAGMA busy_timeout"))).scalar_one()
        synchronous = (await session.execute(text("PRAGMA synchronous"))).scalar_one()
    assert foreign_keys == 1
    assert busy_timeout == 10000
    assert synchronous == 1  # NORMAL


@pytest.mark.asyncio
async def test_retry_is_bounded_for_non_lock_error():
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        raise RuntimeError("not a database lock")

    class NoRollback:
        async def rollback(self):
            raise AssertionError("rollback should not run for non-SQLite errors")

    with pytest.raises(RuntimeError):
        await commit_with_retry(NoRollback(), operation)
    assert calls == 1
    assert MAX_SQLITE_WRITE_ATTEMPTS == 3
