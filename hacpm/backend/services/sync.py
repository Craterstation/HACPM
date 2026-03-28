"""
Real-time sync service using WebSockets.

Manages WebSocket connections and broadcasts task/user changes to all
connected clients for instant UI updates.
"""

import json
import logging
from fastapi import WebSocket
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time sync."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._user_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int | None = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id is not None:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = []
            self._user_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: int | None = None):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id is not None and user_id in self._user_connections:
            conns = self._user_connections[user_id]
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                del self._user_connections[user_id]
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, event: str, data: Any):
        """Broadcast a message to all connected clients."""
        message = json.dumps({"event": event, "data": data})
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to_user(self, user_id: int, event: str, data: Any):
        """Send a message to all connections for a specific user."""
        if user_id not in self._user_connections:
            return
        message = json.dumps({"event": event, "data": data})
        disconnected = []
        for connection in self._user_connections[user_id]:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn, user_id)


# Global connection manager instance
manager = ConnectionManager()


# ── Event helpers ──

async def broadcast_task_created(task_data: dict):
    await manager.broadcast("task_created", task_data)


async def broadcast_task_updated(task_data: dict):
    await manager.broadcast("task_updated", task_data)


async def broadcast_task_deleted(task_id: int):
    await manager.broadcast("task_deleted", {"task_id": task_id})


async def broadcast_task_completed(task_data: dict, completion_data: dict):
    await manager.broadcast("task_completed", {
        "task": task_data,
        "completion": completion_data,
    })


async def broadcast_user_updated(user_data: dict):
    await manager.broadcast("user_updated", user_data)
