# omagent/server/ws.py
import asyncio
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}  # connection_id -> websocket
        self._session_connections: dict[str, set[str]] = {}  # session_id -> {connection_ids}

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        await websocket.accept()
        self._connections[connection_id] = websocket
        logger.info("WebSocket connected: %s", connection_id)

    def disconnect(self, connection_id: str) -> None:
        self._connections.pop(connection_id, None)
        # Remove from session mappings
        for session_id, conn_ids in list(self._session_connections.items()):
            conn_ids.discard(connection_id)
            if not conn_ids:
                del self._session_connections[session_id]
        logger.info("WebSocket disconnected: %s", connection_id)

    def bind_session(self, connection_id: str, session_id: str) -> None:
        if session_id not in self._session_connections:
            self._session_connections[session_id] = set()
        self._session_connections[session_id].add(connection_id)

    async def send_to_connection(self, connection_id: str, data: dict) -> None:
        ws = self._connections.get(connection_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning("Failed to send to %s: %s", connection_id, e)
                self.disconnect(connection_id)

    async def broadcast_to_session(self, session_id: str, data: dict) -> None:
        conn_ids = self._session_connections.get(session_id, set())
        for conn_id in list(conn_ids):
            await self.send_to_connection(conn_id, data)

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Singleton manager
manager = ConnectionManager()
