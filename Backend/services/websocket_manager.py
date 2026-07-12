"""
AEGIS — WebSocket Connection Manager
Manages active WebSocket connections and broadcasts events to all connected dashboard clients.
"""

import logging
from typing import Any
from fastapi import WebSocket
from schemas.websocket import WSEvent

logger = logging.getLogger("aegis.ws")


class WebSocketManager:
    """
    Manages WebSocket connections for live dashboard updates.
    Supports multiple concurrent dashboard connections.
    """

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, event: WSEvent):
        """
        Broadcast an event to all connected dashboard clients.
        Silently removes any broken connections.
        """
        if not self.active_connections:
            return

        dead_connections = []
        event_json = event.to_json()

        for connection in self.active_connections:
            try:
                await connection.send_text(event_json)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_dict(self, data: dict[str, Any]):
        """Broadcast a raw dict as JSON to all connections."""
        if not self.active_connections:
            return

        import json
        json_str = json.dumps(data, default=str)
        dead_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_text(json_str)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


# Singleton instance
ws_manager = WebSocketManager()
