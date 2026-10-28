from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, instruments, market, market_data, ws

api_v1_router = APIRouter()

# Mount health routes
api_v1_router.include_router(health.router, tags=["Health"])

# Mount instrument routes
api_v1_router.include_router(instruments.router, tags=["Instruments"])

# Mount market calendar and candlestick routes
api_v1_router.include_router(market.router, tags=["Market"])

# Mount market data ingestion and quality routes
api_v1_router.include_router(market_data.router, tags=["Market Data Ingestion"])

# Mount websocket routes
api_v1_router.include_router(ws.router, tags=["WebSocket"])
