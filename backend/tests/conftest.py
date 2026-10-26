import os
import sys
import shutil
import tempfile
from pathlib import Path
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test-only paths before importing any settings or SQLAlchemy engine.
TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="nse-paper-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "test.db"
os.environ["DATABASE_ASYNC_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["DATABASE_SYNC_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["TRADING_MODE"] = "PAPER"
os.environ["DEBUG"] = "false"

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.config import settings
from backend.app.database.session import AsyncSessionLocal, get_db
from backend.app.database.base import Base
import backend.app.models  # noqa: F401
from backend.app.database.session import async_engine
from backend.app.main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def isolated_schema():
    """Create and remove only the disposable test database schema."""
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()
    shutil.rmtree(TEST_DB_DIR)


@pytest_asyncio.fixture
async def db_session():
    """Async session fixture connected to the database with active SQLite PRAGMAs."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    """FastAPI AsyncClient fixture overriding get_db dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
