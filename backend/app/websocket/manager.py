import json
from typing import Any, Dict, List, Set
from fastapi import WebSocket
from backend.app.core.logging import logger


class ConnectionManager:
    """Manages active WebSocket connections and channel subscriptions."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self.channel_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts a new client connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected. Total active clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for channel, subscribers in self.channel_subscribers.items():
            subscribers.discard(websocket)
        logger.info("WebSocket disconnected. Total active clients: %d", len(self.active_connections))

    def subscribe(self, websocket: WebSocket, channel: str) -> None:
        """Subscribes a client to a specific topic channel."""
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(websocket)
        logger.debug("Client subscribed to channel '%s'", channel)

    def unsubscribe(self, websocket: WebSocket, channel: str) -> None:
        """Unsubscribes a client from a topic channel."""
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(websocket)

    async def broadcast_to_all(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON message to all connected clients."""
        payload = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning("Failed to send broadcast to connection: %s", str(e))
                self.disconnect(connection)

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON message to all subscribers of a channel."""
        if channel not in self.channel_subscribers:
            return
        payload = json.dumps({"channel": channel, "data": message})
        for connection in list(self.channel_subscribers[channel]):
            try:
                await connection.send_text(payload)
            except Exception as e:
                logger.warning("Failed to send channel message: %s", str(e))
                self.disconnect(connection)


manager = ConnectionManager()
