import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.instrument import Instrument


@pytest.mark.asyncio
async def test_database_connection(db_session: AsyncSession):
    """Test raw SQL execution over SQLAlchemy async connection."""
    result = await db_session.execute(text("SELECT 1 AS check_val"))
    val = result.scalar()
    assert val == 1


@pytest.mark.asyncio
async def test_instrument_model_query(db_session: AsyncSession):
    """Test querying the instruments table through SQLAlchemy ORM."""
    result = await db_session.execute(text("SELECT count(*) FROM instruments"))
    count = result.scalar()
    assert isinstance(count, int)
