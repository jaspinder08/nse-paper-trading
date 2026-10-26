"""Bounded SQLite write retry support."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")
MAX_SQLITE_WRITE_ATTEMPTS = 3


def is_sqlite_locked(error: OperationalError) -> bool:
    return "database is locked" in str(error).lower() or "database is busy" in str(error).lower()


async def commit_with_retry(session: AsyncSession, operation: Callable[[], Awaitable[T]]) -> T:
    """Run a short write operation with bounded exponential retry on SQLite locks."""
    for attempt in range(MAX_SQLITE_WRITE_ATTEMPTS):
        try:
            return await operation()
        except OperationalError as error:
            await session.rollback()
            if not is_sqlite_locked(error) or attempt == MAX_SQLITE_WRITE_ATTEMPTS - 1:
                raise
            await asyncio.sleep(0.05 * (2 ** attempt))
    raise RuntimeError("unreachable")
