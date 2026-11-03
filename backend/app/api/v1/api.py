"""Centralized API v1 Router aggregating all functional research endpoints."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    backtesting,
    exports,
    health,
    instruments,
    journal,
    market,
    market_data,
    orders,
    portfolio,
    risk,
    scanner,
    sessions,
    ws,
)

api_v1_router = APIRouter()

# 1. System Health
api_v1_router.include_router(health.router, tags=["Health"])

# 2. Instruments Master
api_v1_router.include_router(instruments.router, tags=["Instruments"])

# 3. Market Status & Calendar
api_v1_router.include_router(market.router, tags=["Market"])

# 4. Market Data Ingestion & Quality
api_v1_router.include_router(market_data.router, tags=["Market Data Ingestion"])

# 5. Stock Scanner & ORB Signals
api_v1_router.include_router(scanner.router, tags=["Scanner & Signals"])

# 6. Simulated Paper Orders
api_v1_router.include_router(orders.router, tags=["Paper Orders"])

# 7. Portfolio & Positions
api_v1_router.include_router(portfolio.router, tags=["Portfolio & Positions"])

# 8. Trading Sessions
api_v1_router.include_router(sessions.router, tags=["Trading Sessions"])

# 9. Risk Management & Gatekeeper
api_v1_router.include_router(risk.router, tags=["Risk Management"])

# 10. Trade Journal & System Logs
api_v1_router.include_router(journal.router, tags=["Trade Journal & System Logs"])

# 11. Historical Backtesting
api_v1_router.include_router(backtesting.router, tags=["Backtesting"])

# 12. Exports (CSV / JSON)
api_v1_router.include_router(exports.router, tags=["Exports (CSV / JSON)"])

# 13. WebSocket Real-time Feed
api_v1_router.include_router(ws.router, tags=["WebSocket"])
