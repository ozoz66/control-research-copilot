# -*- coding: utf-8 -*-
"""
事件系统单元测试
"""

import pytest
import asyncio
import threading
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.events import EventEmitter, Event, EventType


class TestEventEmitter:
    """EventEmitter 测试类"""

    def test_basic_emit_and_listen(self):
        """测试基本的事件发射和监听"""
        emitter = EventEmitter()
        received = []

        def handler(event: Event):
            received.append(event.data)

        emitter.on("test_event", handler)
        emitter.emit("test_event", "hello")

        assert len(received) == 1
        assert received[0] == "hello"

    def test_multiple_listeners(self):
        """测试多个监听器"""
        emitter = EventEmitter()
        results = []

        emitter.on("event", lambda e: results.append(1))
        emitter.on("event", lambda e: results.append(2))
        emitter.on("event", lambda e: results.append(3))

        emitter.emit("event")

        assert results == [1, 2, 3]

    def test_off_specific_listener(self):
        """测试移除特定监听器"""
        emitter = EventEmitter()
        results = []

        def handler1(e):
            results.append(1)

        def handler2(e):
            results.append(2)

        emitter.on("event", handler1)
        emitter.on("event", handler2)
        emitter.off("event", handler1)

        emitter.emit("event")

        assert results == [2]

    def test_off_all_listeners(self):
        """测试移除所有监听器"""
        emitter = EventEmitter()
        results = []

        emitter.on("event", lambda e: results.append(1))
        emitter.on("event", lambda e: results.append(2))
        emitter.off("event")

        emitter.emit("event")

        assert results == []

    def test_once(self):
        """测试一次性监听器"""
        emitter = EventEmitter()
        count = [0]

        def handler(e):
            count[0] += 1

        emitter.once("event", handler)

        emitter.emit("event")
        emitter.emit("event")
        emitter.emit("event")

        assert count[0] == 1

    def test_event_data(self):
        """测试事件数据传递"""
        emitter = EventEmitter()
        received_event = [None]

        def handler(event: Event):
            received_event[0] = event

        emitter.on("test", handler)
        emitter.emit("test", {"key": "value"}, source="test_source")

        event = received_event[0]
        assert event is not None
        assert event.type == "test"
        assert event.data == {"key": "value"}
        assert event.source == "test_source"
        assert event.timestamp is not None

    def test_chain_calls(self):
        """测试链式调用"""
        emitter = EventEmitter()
        results = []

        emitter.on("a", lambda e: results.append("a")) \
               .on("b", lambda e: results.append("b")) \
               .on("c", lambda e: results.append("c"))

        emitter.emit("a")
        emitter.emit("b")
        emitter.emit("c")

        assert results == ["a", "b", "c"]

    def test_event_history(self):
        """测试事件历史记录"""
        emitter = EventEmitter()

        emitter.emit("event1", "data1")
        emitter.emit("event2", "data2")
        emitter.emit("event1", "data3")

        history = emitter.get_history(limit=10)
        assert len(history) == 3

        event1_history = emitter.get_history("event1")
        assert len(event1_history) == 2

    def test_listener_count(self):
        """测试监听器计数"""
        emitter = EventEmitter()

        assert emitter.listener_count() == 0

        emitter.on("a", lambda e: None)
        emitter.on("a", lambda e: None)
        emitter.on("b", lambda e: None)

        assert emitter.listener_count() == 3
        assert emitter.listener_count("a") == 2
        assert emitter.listener_count("b") == 1

    def test_clear(self):
        """测试清除所有监听器"""
        emitter = EventEmitter()

        emitter.on("a", lambda e: None)
        emitter.on("b", lambda e: None)

        emitter.clear()

        assert emitter.listener_count() == 0

    def test_error_in_handler(self):
        """测试处理器中的错误不影响其他处理器"""
        emitter = EventEmitter()
        results = []

        def bad_handler(e):
            raise ValueError("test error")

        def good_handler(e):
            results.append("ok")

        emitter.on("event", bad_handler)
        emitter.on("event", good_handler)

        # 不应抛出异常
        emitter.emit("event")

        assert results == ["ok"]

    def test_thread_safety(self):
        """测试线程安全"""
        emitter = EventEmitter()
        results = []
        lock = threading.Lock()

        def handler(e):
            with lock:
                results.append(e.data)

        emitter.on("event", handler)

        threads = []
        for i in range(10):
            t = threading.Thread(target=lambda x=i: emitter.emit("event", x))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 10


class TestAsyncEventEmitter:
    """异步事件测试"""

    @pytest.mark.asyncio
    async def test_async_emit(self):
        """测试异步发射"""
        emitter = EventEmitter()
        results = []

        async def async_handler(event: Event):
            await asyncio.sleep(0.01)
            results.append(event.data)

        emitter.on_async("event", async_handler)
        await emitter.emit_async("event", "async_data")

        assert results == ["async_data"]

    @pytest.mark.asyncio
    async def test_mixed_sync_async_handlers(self):
        """测试同步和异步处理器混合"""
        emitter = EventEmitter()
        results = []

        def sync_handler(event: Event):
            results.append("sync")

        async def async_handler(event: Event):
            results.append("async")

        emitter.on("event", sync_handler)
        emitter.on_async("event", async_handler)

        await emitter.emit_async("event")

        assert "sync" in results
        assert "async" in results


class TestEventType:
    """EventType 枚举测试"""

    def test_event_types_exist(self):
        """测试预定义事件类型存在"""
        assert EventType.PROGRESS_UPDATED.value == "progress_updated"
        assert EventType.LOG_MESSAGE.value == "log_message"
        assert EventType.WORKFLOW_COMPLETED.value == "workflow_completed"
        assert EventType.WORKFLOW_ERROR.value == "workflow_error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
