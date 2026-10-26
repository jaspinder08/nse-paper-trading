import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.core.logging import logger
from backend.app.websocket.manager import manager

router = APIRouter()
MAX_WEBSOCKET_PAYLOAD_BYTES = 16_384


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time WebSocket connection for market events, order fills, and position updates."""
    await manager.connect(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                if len(raw_data.encode("utf-8")) > MAX_WEBSOCKET_PAYLOAD_BYTES:
                    await websocket.close(code=1009, reason="Payload too large")
                    return
                payload = json.loads(raw_data)
                action = payload.get("action")
                channel = payload.get("channel")

                if action == "subscribe" and channel:
                    manager.subscribe(websocket, channel)
                    await websocket.send_text(
                        json.dumps({"event": "subscribed", "channel": channel})
                    )
                elif action == "unsubscribe" and channel:
                    manager.unsubscribe(websocket, channel)
                    await websocket.send_text(
                        json.dumps({"event": "unsubscribed", "channel": channel})
                    )
                elif action == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
            except (json.JSONDecodeError, ValueError) as exc:
                await websocket.send_text(
                    json.dumps({"error": str(exc) if isinstance(exc, ValueError) else "Invalid JSON format payload"})
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket exception: %s", str(e))
        manager.disconnect(websocket)
