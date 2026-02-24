# -*- coding: utf-8 -*-
"""
WebSocket connection manager for API sessions.
"""

import logging
import threading
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections grouped by session_id."""

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}
        self._lock = threading.RLock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = []
            if websocket not in self._connections[session_id]:
                self._connections[session_id].append(websocket)
        logger.info("WebSocket connected: session=%s", session_id)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        with self._lock:
            if session_id in self._connections:
                self._connections[session_id] = [
                    ws for ws in self._connections[session_id] if ws is not websocket
                ]
                if not self._connections[session_id]:
                    del self._connections[session_id]
        logger.info("WebSocket disconnected: session=%s", session_id)

    async def broadcast(self, session_id: str, message: dict) -> None:
        """Broadcast one message to all active sockets in a session."""
        with self._lock:
            targets = list(self._connections.get(session_id, []))
        if not targets:
            return

        dead = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        if not dead:
            return

        dead_ids = {id(ws) for ws in dead}
        with self._lock:
            current = self._connections.get(session_id, [])
            survivors = [ws for ws in current if id(ws) not in dead_ids]
            if survivors:
                self._connections[session_id] = survivors
            else:
                self._connections.pop(session_id, None)
