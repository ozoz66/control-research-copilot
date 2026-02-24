# -*- coding: utf-8 -*-

import pytest

from api.ws_handler import ConnectionManager


class FakeWebSocket:
    def __init__(self, fail_send=False):
        self.accepted = False
        self.fail_send = fail_send
        self.messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        if self.fail_send:
            raise RuntimeError("socket closed")
        self.messages.append(message)


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        ws = FakeWebSocket()

        await manager.connect("session-1", ws)
        assert ws.accepted is True
        assert len(manager._connections["session-1"]) == 1

        manager.disconnect("session-1", ws)
        assert "session-1" not in manager._connections

    @pytest.mark.asyncio
    async def test_connect_is_idempotent_for_same_socket(self):
        manager = ConnectionManager()
        ws = FakeWebSocket()

        await manager.connect("session-1", ws)
        await manager.connect("session-1", ws)

        assert len(manager._connections["session-1"]) == 1

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        manager = ConnectionManager()
        alive = FakeWebSocket()
        dead = FakeWebSocket(fail_send=True)

        await manager.connect("session-1", alive)
        await manager.connect("session-1", dead)

        await manager.broadcast("session-1", {"type": "log", "data": {"ok": True}})

        assert alive.messages == [{"type": "log", "data": {"ok": True}}]
        assert manager._connections["session-1"] == [alive]
