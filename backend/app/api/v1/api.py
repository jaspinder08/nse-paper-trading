from fastapi import APIRouter
from backend.app.api.v1.endpoints import health, ws

api_v1_router = APIRouter()

# Mount health routes
api_v1_router.include_router(health.router, tags=["Health"])

# Mount websocket routes
api_v1_router.include_router(ws.router, tags=["WebSocket"])
