from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger
from shared.runtime_config import sqlite_path_from_url


def ensure_sqlite_dir(url: str) -> None:
    """Create only the validated parent directory for the canonical local DB."""
    sqlite_path_from_url(url).parent.mkdir(parents=True, exist_ok=True)


# Ensure data directory exists before establishing connection
ensure_sqlite_dir(settings.DATABASE_ASYNC_URL)

is_sqlite = "sqlite" in settings.DATABASE_ASYNC_URL.lower()

# SQLite-specific connection arguments
engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True

# Create async engine for high-performance non-blocking I/O
async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_ASYNC_URL,
    **engine_kwargs,
)

def setup_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Configure WAL mode, busy timeout, and foreign key enforcement on any SQLite engine."""
    @event.listens_for(engine.sync_engine, "connect")
    def configure_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")  # 10s timeout prevents lock collisions
        cursor.execute("PRAGMA foreign_keys=ON")      # Enforce relational integrity
        cursor.execute("PRAGMA synchronous=NORMAL")   # Optimal balance of durability and performance
        cursor.close()


# Apply performance and concurrency PRAGMAs for SQLite connections
if is_sqlite:
    setup_sqlite_pragmas(async_engine)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session per request with clean transaction lifecycle."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session rolled back due to error: %s", str(e))
            raise
        finally:
            await session.close()
