# -*- coding: utf-8 -*-
"""
WebSocket 连接管理 - AutoControl-Scientist API
"""

import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理按 session_id 分组的 WebSocket 连接"""

    def __init__(self):
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = []
        self._connections[session_id].append(websocket)
        logger.info("WebSocket 连接: session=%s", session_id)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self._connections:
            self._connections[session_id] = [
                ws for ws in self._connections[session_id] if ws is not websocket
            ]
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info("WebSocket 断开: session=%s", session_id)

    async def broadcast(self, session_id: str, message: dict) -> None:
        """向指定 session 的所有连接广播消息"""
        if session_id not in self._connections:
            return
        dead = []
        for ws in self._connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)
