"""
AEGIS — WebSocket Router
Dashboard connects here for live updates.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.websocket_manager import ws_manager

logger = logging.getLogger("aegis.router.ws")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard real-time updates.
    Dashboard connects here on load, receives all pipeline events.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — receive pings/heartbeats from client
            data = await websocket.receive_text()
            # Handle ping/pong keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("Dashboard WebSocket disconnected.")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.warning(f"WebSocket error: {e}")
