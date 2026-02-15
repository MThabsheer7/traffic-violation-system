"""
WebSocket connection manager for live alert push.

Manages active dashboard connections and broadcasts new violation
alerts in real-time.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Tracks active WebSocket connections and broadcasts messages.

    Usage:
        manager = ConnectionManager()

        @app.websocket("/api/ws/alerts")
        async def ws_endpoint(websocket: WebSocket):
            await manager.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()  # Keep alive
            except WebSocketDisconnect:
                manager.disconnect(websocket)
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket connected — %d active connections",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket disconnected — %d active connections",
            len(self.active_connections),
        )

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Singleton instance shared across the app
ws_manager = ConnectionManager()
