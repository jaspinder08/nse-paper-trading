#!/usr/bin/env python3
"""Point-in-Time Nifty 50 Constituent Universe Synchronization Pipeline (FR-01, FR-02).

Validates:
- Unique expected constituents (50 active members).
- Valid, non-overlapping effective date ranges.
- Official Angel One NSE symbol-token mappings.
- Clean database synchronization into SQLite.
"""

import asyncio
from datetime import date
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from backend.app.database.session import AsyncSessionLocal
from trading_engine.universe.nifty50 import (
    HISTORICAL_NIFTY50_DATA,
    get_nifty50_constituents,
    seed_nifty50_universe,
    validate_constituent_periods,
)


async def main() -> None:
    print("==================================================")
    print("  NIFTY 50 Universe & Instrument Master Sync")
    print("==================================================")

    # 1. Validate intervals
    print("  Validating constituent historical date intervals...")
    try:
        validate_constituent_periods(HISTORICAL_NIFTY50_DATA)
        print("  ✓ Constituent intervals validated: No overlaps found.")
    except Exception as e:
        print(f"  ✗ Validation error: {e}")
        sys.exit(1)

    today = date.today()
    active = get_nifty50_constituents(today)
    print(f"  ✓ Active constituents as of {today}: {len(active)} symbols")

    # 2. Database synchronization
    print("  Synchronizing database records...")
    async with AsyncSessionLocal() as session:
        synced = await seed_nifty50_universe(session)
        print(f"  ✓ Successfully synchronized {synced} constituent history records.")

    print("==================================================")
    print("  Universe synchronization completed successfully!")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
