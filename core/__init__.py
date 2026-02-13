# -*- coding: utf-8 -*-
"""
Core 模块 - 纯 Python 核心逻辑层
与 GUI 框架解耦，支持 CLI/Web/Desktop 多端

主要组件:
- EventEmitter: 事件系统（替代 pyqtSignal）
- WorkflowEngine: 工作流执行引擎
- ResearchOrchestrator: 研究流程编排器
- SignalManager: PyQt6信号管理器
- AgentHistory: Agent交互历史记录
"""

from .events import EventEmitter, Event, EventType
from .workflow_engine import WorkflowEngine, WorkflowState
from .research_orchestrator import ResearchOrchestrator
from .research_controller import ResearchController, UICallbacks

# 新增：信号管理和交互配置
from .signal_manager import SignalManager, InteractionConfig, get_interaction_config

# 新增：Agent交互历史
from .agent_history import (
    AgentHistory, 
    InteractionType, 
    InteractionRecord,
    get_agent_history
)

# 可观测性
from .telemetry import init_telemetry, get_tracer, trace_span
from .json_logging import JsonFormatter, enable_json_logging

# Qt 适配器延迟导入（避免非 Qt 环境报错）
def get_qt_adapter():
    """获取 Qt 适配器（延迟导入）"""
    from .qt_adapter import QtEventBridge, QtOrchestratorAdapter
    return QtEventBridge, QtOrchestratorAdapter

__all__ = [
    'EventEmitter',
    'Event',
    'EventType',
    'WorkflowEngine',
    'WorkflowState',
    'ResearchOrchestrator',
    'ResearchController',
    'UICallbacks',
    'get_qt_adapter',
    # 信号管理
    'SignalManager',
    'InteractionConfig',
    'get_interaction_config',
    # 可观测性
    'init_telemetry',
    'get_tracer',
    'trace_span',
    'JsonFormatter',
    'enable_json_logging',
    # 交互历史
    'AgentHistory',
    'InteractionType',
    'InteractionRecord',
    'get_agent_history',
]
