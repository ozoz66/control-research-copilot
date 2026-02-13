# -*- coding: utf-8 -*-
"""
PyQt6 适配器 - 连接纯 Python 核心层与 PyQt6 GUI

提供:
- QtEventBridge: 将 EventEmitter 事件转换为 pyqtSignal
- QtWorkflowAdapter: 包装 WorkflowEngine 提供 Qt 兼容接口
"""

from typing import Optional, Any, Dict
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from logger_config import get_logger

logger = get_logger(__name__)

from .events import EventEmitter
from .workflow_engine import WorkflowEngine, WorkflowState
from .research_orchestrator import ResearchOrchestrator


class QtEventBridge(QObject):
    """
    Qt 事件桥接器

    将 EventEmitter 的事件转换为 pyqtSignal，
    实现核心层与 Qt GUI 的解耦通信。

    用法:
        bridge = QtEventBridge()
        bridge.connect_emitter(orchestrator.events)

        # 连接 Qt 信号
        bridge.progress_updated.connect(self.on_progress)
        bridge.log_message.connect(self.on_log)
    """

    # Qt 信号定义
    progress_updated = pyqtSignal(int, str)
    log_message = pyqtSignal(str, str)
    stage_completed = pyqtSignal(str, dict)
    workflow_completed = pyqtSignal(object)
    workflow_error = pyqtSignal(str)
    topic_confirmation_required = pyqtSignal(object)
    stage_confirmation_required = pyqtSignal(str, object, object)
    workflow_started = pyqtSignal()
    workflow_stopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emitter: Optional[EventEmitter] = None

    def connect_emitter(self, emitter: EventEmitter) -> 'QtEventBridge':
        """连接 EventEmitter"""
        if self._emitter:
            self.disconnect_emitter()

        self._emitter = emitter

        # 注册事件处理器
        emitter.on("progress_updated", self._on_progress)
        emitter.on("log_message", self._on_log)
        emitter.on("stage_completed", self._on_stage_completed)
        emitter.on("workflow_completed", self._on_workflow_completed)
        emitter.on("workflow_error", self._on_workflow_error)
        emitter.on("topic_confirmation_required", self._on_topic_confirmation)
        emitter.on("stage_confirmation_required", self._on_stage_confirmation)
        emitter.on("workflow_started", self._on_workflow_started)
        emitter.on("workflow_stopped", self._on_workflow_stopped)

        return self

    def disconnect_emitter(self) -> 'QtEventBridge':
        """断开 EventEmitter"""
        if self._emitter:
            self._emitter.off("progress_updated")
            self._emitter.off("log_message")
            self._emitter.off("stage_completed")
            self._emitter.off("workflow_completed")
            self._emitter.off("workflow_error")
            self._emitter.off("topic_confirmation_required")
            self._emitter.off("stage_confirmation_required")
            self._emitter.off("workflow_started")
            self._emitter.off("workflow_stopped")
            self._emitter = None
        return self

    def _on_progress(self, event):
        data = event.data or {}
        self.progress_updated.emit(
            data.get("progress", 0),
            data.get("description", "")
        )

    def _on_log(self, event):
        data = event.data or {}
        self.log_message.emit(
            data.get("message", ""),
            data.get("level", "info")
        )

    def _on_stage_completed(self, event):
        data = event.data or {}
        self.stage_completed.emit(
            data.get("stage_key", ""),
            data
        )

    def _on_workflow_completed(self, event):
        self.workflow_completed.emit(event.data)

    def _on_workflow_error(self, event):
        error = event.data if isinstance(event.data, str) else str(event.data)
        self.workflow_error.emit(error)

    def _on_topic_confirmation(self, event):
        self.topic_confirmation_required.emit(event.data)

    def _on_stage_confirmation(self, event):
        data = event.data or {}
        self.stage_confirmation_required.emit(
            data.get("stage_key", ""),
            data.get("eval_result"),
            data.get("context")
        )

    def _on_workflow_started(self, event):
        self.workflow_started.emit()

    def _on_workflow_stopped(self, event):
        self.workflow_stopped.emit()


class QtOrchestratorAdapter(QObject):
    """
    Qt 编排器适配器

    包装 ResearchOrchestrator，提供与原 Orchestrator 兼容的 Qt 接口。
    可作为 gui_main.py 中 Orchestrator 的替代品。

    用法:
        adapter = QtOrchestratorAdapter(output_dir="./output")
        adapter.register_agent("architect", architect_agent)

        # 连接信号（与原 Orchestrator 相同）
        adapter.progress_updated.connect(self.on_progress)
        adapter.log_message.connect(self.on_log)

        # 启动工作流
        adapter.start_workflow(config)
    """

    # Qt 信号 - 与原 Orchestrator 保持一致
    progress_updated = pyqtSignal(int, str)
    log_message = pyqtSignal(str, str)
    workflow_completed = pyqtSignal(object)
    workflow_error = pyqtSignal(str)
    topic_confirmation_required = pyqtSignal(object)
    stage_confirmation_required = pyqtSignal(str, object, object)

    def __init__(self, output_dir: str = "./output", parent=None):
        super().__init__(parent)

        # 创建核心编排器
        self._orchestrator = ResearchOrchestrator(output_dir=output_dir)

        # 创建事件桥接器
        self._bridge = QtEventBridge(self)
        self._bridge.connect_emitter(self._orchestrator.events)

        # 转发桥接器信号
        self._bridge.progress_updated.connect(self.progress_updated.emit)
        self._bridge.log_message.connect(self.log_message.emit)
        self._bridge.workflow_completed.connect(self.workflow_completed.emit)
        self._bridge.workflow_error.connect(self.workflow_error.emit)
        self._bridge.topic_confirmation_required.connect(
            self.topic_confirmation_required.emit
        )
        self._bridge.stage_confirmation_required.connect(
            self.stage_confirmation_required.emit
        )

    @property
    def agents(self) -> Dict[str, Any]:
        """获取已注册的 Agent"""
        return self._orchestrator._agents

    def register_agent(self, key: str, agent: Any):
        """注册 Agent"""
        self._orchestrator.register_agent(key, agent)
        logger.info("已注册Agent: %s -> %s", key, agent.name)

    def unregister_agent(self, key: str):
        """注销 Agent"""
        self._orchestrator.unregister_agent(key)

    def set_supervisor(self, supervisor: Any):
        """设置监督 Agent"""
        self._orchestrator.set_supervisor(supervisor)

    def start_workflow(self, research_config: Dict[str, Any],
                       resume_from: str = None):
        """启动工作流"""
        self._orchestrator.start_workflow(research_config, resume_from)

    def stop_workflow(self):
        """停止工作流"""
        self._orchestrator.stop_workflow()

    def confirm_topic(self, updated_context: Any = None):
        """确认课题"""
        self._orchestrator.confirm_topic(updated_context)

    def confirm_stage(self, modification: str = None, rollback_to: str = None):
        """确认阶段"""
        self._orchestrator.confirm_stage(modification, rollback_to)

    def get_current_context(self) -> Optional[Any]:
        """获取当前上下文"""
        return self._orchestrator.get_context()
