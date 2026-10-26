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

# Run Alembic migrations
if [ -f ".venv/bin/alembic" ]; then
    .venv/bin/alembic -c backend/alembic.ini upgrade head
else
    alembic -c backend/alembic.ini upgrade head
fi

echo "=================================================="
echo "  Database migration completed successfully!"
echo "  Database file: ${ROOT_DIR}/data/nse_paper_trading.db"
echo "=================================================="
