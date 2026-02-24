# -*- coding: utf-8 -*-
"""
事件系统 - 替代 PyQt6 的 pyqtSignal

提供纯 Python 的事件发射/订阅机制，支持:
- 同步回调
- 异步回调
- 线程安全
"""

import asyncio
import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from logger_config import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """预定义事件类型"""
    PROGRESS_UPDATED = "progress_updated"
    LOG_MESSAGE = "log_message"
    STAGE_COMPLETED = "stage_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_ERROR = "workflow_error"
    TOPIC_CONFIRMATION_REQUIRED = "topic_confirmation_required"
    STAGE_CONFIRMATION_REQUIRED = "stage_confirmation_required"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STOPPED = "workflow_stopped"


@dataclass
class Event:
    """事件数据类"""
    type: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""


class EventEmitter:
    """
    事件发射器 - 纯 Python 实现

    用法:
        emitter = EventEmitter()

        # 订阅事件
        emitter.on("progress_updated", lambda e: print(e.data))

        # 发射事件
        emitter.emit("progress_updated", {"progress": 50, "stage": "理论推导"})

        # 异步发射
        await emitter.emit_async("workflow_completed", context)
    """

    def __init__(self, max_history: int = 100):
        self._listeners: Dict[str, List[Callable]] = {}
        self._async_listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._max_history = max_history
        self._event_history: deque[Event] = deque(maxlen=max_history)

    def on(self, event_type: str, callback: Callable) -> 'EventEmitter':
        """
        订阅事件（同步回调）

        Args:
            event_type: 事件类型
            callback: 回调函数，接收 Event 对象

        Returns:
            self，支持链式调用
        """
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            # 避免重复注册同一个回调
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)
        return self

    def on_async(self, event_type: str, callback: Callable) -> 'EventEmitter':
        """
        订阅事件（异步回调）

        Args:
            event_type: 事件类型
            callback: 异步回调函数

        Returns:
            self，支持链式调用
        """
        with self._lock:
            if event_type not in self._async_listeners:
                self._async_listeners[event_type] = []
            # 避免重复注册同一个回调
            if callback not in self._async_listeners[event_type]:
                self._async_listeners[event_type].append(callback)
        return self

    def off(self, event_type: str, callback: Callable = None) -> 'EventEmitter':
        """
        取消订阅

        Args:
            event_type: 事件类型
            callback: 要移除的回调，None 则移除该类型所有回调

        Returns:
            self
        """
        with self._lock:
            if callback is None:
                self._listeners.pop(event_type, None)
                self._async_listeners.pop(event_type, None)
            else:
                if event_type in self._listeners:
                    self._listeners[event_type] = [
                        cb for cb in self._listeners[event_type] if cb != callback
                    ]
                if event_type in self._async_listeners:
                    self._async_listeners[event_type] = [
                        cb for cb in self._async_listeners[event_type] if cb != callback
                    ]
        return self

    def emit(self, event_type: str, data: Any = None, source: str = "") -> Event:
        """
        发射事件（同步）

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源

        Returns:
            创建的 Event 对象
        """
        event = Event(type=event_type, data=data, source=source)

        with self._lock:
            # 记录历史 (deque auto-evicts oldest when maxlen exceeded)
            self._event_history.append(event)

            # 获取监听器副本
            listeners = list(self._listeners.get(event_type, []))

        # 在锁外执行回调
        for callback in listeners:
            try:
                callback(event)
            except Exception as e:
                logger.error("回调执行错误: %s", e)

        return event

    async def emit_async(self, event_type: str, data: Any = None, source: str = "") -> Event:
        """
        发射事件（异步）

        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源

        Returns:
            创建的 Event 对象
        """
        event = Event(type=event_type, data=data, source=source)

        with self._lock:
            self._event_history.append(event)

            sync_listeners = list(self._listeners.get(event_type, []))
            async_listeners = list(self._async_listeners.get(event_type, []))

        # 执行同步回调
        for callback in sync_listeners:
            try:
                callback(event)
            except Exception as e:
                logger.error("同步回调错误: %s", e)

        # 执行异步回调
        for callback in async_listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error("异步回调错误: %s", e)

        return event

    def once(self, event_type: str, callback: Callable) -> 'EventEmitter':
        """
        订阅一次性事件

        Args:
            event_type: 事件类型
            callback: 回调函数

        Returns:
            self
        """
        def wrapper(event: Event):
            self.off(event_type, wrapper)
            callback(event)

        return self.on(event_type, wrapper)

    def clear(self) -> 'EventEmitter':
        """清除所有监听器"""
        with self._lock:
            self._listeners.clear()
            self._async_listeners.clear()
        return self

    def get_history(self, event_type: str = None, limit: int = 10) -> List[Event]:
        """
        获取事件历史

        Args:
            event_type: 过滤的事件类型，None 返回所有
            limit: 返回数量限制

        Returns:
            事件列表（最近的在末尾）
        """
        with self._lock:
            if event_type:
                events = [e for e in self._event_history if e.type == event_type]
            else:
                events = list(self._event_history)
        return events[-limit:] if limit < len(events) else events

    def listener_count(self, event_type: str = None) -> int:
        """获取监听器数量"""
        with self._lock:
            if event_type:
                return (len(self._listeners.get(event_type, [])) +
                        len(self._async_listeners.get(event_type, [])))
            return sum(len(v) for v in self._listeners.values()) + \
                   sum(len(v) for v in self._async_listeners.values())


# 便捷函数：创建预配置的事件发射器
def create_workflow_emitter() -> EventEmitter:
    """创建工作流专用的事件发射器"""
    return EventEmitter(max_history=500)
