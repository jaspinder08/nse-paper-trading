#!/usr/bin/env bash
set -e

# Resolve repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "=================================================="
echo "  Setting up NSE Paper-Trading SQLite Database"
echo "=================================================="

# Ensure data directory exists
mkdir -p data

# Initialize SQLite tables directly from SQLAlchemy metadata (no Alembic migrations)
PYTHON_BIN="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

${PYTHON_BIN} -c "
import asyncio
from backend.app.database.session import async_engine
from backend.app.database.base import Base
import backend.app.models

async def init():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await async_engine.dispose()
    print('  All tables verified/created directly in local SQLite.')

asyncio.run(init())
"

echo "=================================================="
echo "  Database migration completed successfully!"
echo "  Database file: ${ROOT_DIR}/data/nse_paper_trading.db"
echo "=================================================="
