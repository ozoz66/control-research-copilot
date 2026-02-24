# -*- coding: utf-8 -*-
"""
研究会话生命周期管理 - AutoControl-Scientist API
"""

import time
import uuid
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

from core.research_orchestrator import ResearchOrchestrator
from core.workflow_engine import WorkflowState
from core.agent_history import AgentHistory

logger = logging.getLogger(__name__)
MAX_EVENT_LOG = 2000


@dataclass
class ResearchSession:
    """一次研究会话"""
    session_id: str
    orchestrator: ResearchOrchestrator
    history: AgentHistory
    event_log: Deque[Dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=MAX_EVENT_LOG)
    )
    event_seq: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    progress: int = 0
    current_stage: str = ""
    error: Optional[str] = None
    event_notifier: threading.Event = field(default_factory=threading.Event)
    event_lock: threading.Lock = field(default_factory=threading.Lock)
    created_at: float = field(default_factory=time.time)


class SessionManager:
    """管理多个研究会话的创建/查询/列出"""

    def __init__(self):
        self._sessions: Dict[str, ResearchSession] = {}
        self._lock = threading.RLock()

    def create_session(self, config: Dict[str, Any]) -> ResearchSession:
        """
        创建并启动一个新的研究会话。

        Args:
            config: 研究配置字典

        Returns:
            创建的 ResearchSession
        """
        session_id = uuid.uuid4().hex[:12]
        orchestrator = ResearchOrchestrator(output_dir="./output")
        history = AgentHistory()

        session = ResearchSession(
            session_id=session_id,
            orchestrator=orchestrator,
            history=history,
            config=config,
        )

        # 注册 agents
        self._register_agents(orchestrator)

        # 绑定事件
        self._bind_events(session)

        with self._lock:
            self._sessions[session_id] = session

        # 启动工作流（失败时回滚会话，避免泄漏僵尸 session）
        try:
            orchestrator.start_workflow(config)
        except Exception:
            with self._lock:
                self._sessions.pop(session_id, None)
            raise

        logger.info("创建会话: %s", session_id)
        return session

    def get_session(self, session_id: str) -> Optional[ResearchSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str, stop_if_running: bool = True) -> bool:
        """删除会话并释放内存。"""
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if not session:
            return False

        if stop_if_running and session.orchestrator.is_running():
            session.orchestrator.stop_workflow()

        session.event_notifier.set()
        logger.info("删除会话: %s", session_id)
        return True

    def get_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.get_session(session_id)
        if not session:
            return None

        with session.event_lock:
            progress = session.progress
            current_stage = session.current_stage
            error = session.error
        state = session.orchestrator.get_state()
        return {
            "session_id": session_id,
            "state": state.value,
            "progress": progress,
            "current_stage": current_stage,
            "error": error,
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._sessions.items())
        results = []
        for sid, session in items:
            with session.event_lock:
                progress = session.progress
            state = session.orchestrator.get_state()
            results.append({
                "session_id": sid,
                "state": state.value,
                "progress": progress,
            })
        return results

    @property
    def active_count(self) -> int:
        with self._lock:
            sessions = list(self._sessions.values())
        return sum(
            1 for s in sessions
            if s.orchestrator.get_state() in (WorkflowState.RUNNING, WorkflowState.WAITING_CONFIRMATION)
        )

    def cleanup_stale_sessions(self, max_age_seconds: float = 86400) -> int:
        """清理超过 max_age_seconds 的已完成/出错会话，返回清理数量"""
        now = time.time()
        to_remove = []
        with self._lock:
            items = list(self._sessions.items())
        for sid, session in items:
            age = now - session.created_at
            if age < max_age_seconds:
                continue
            state = session.orchestrator.get_state()
            if state in (WorkflowState.COMPLETED, WorkflowState.ERROR, WorkflowState.STOPPED):
                to_remove.append(sid)
        for sid in to_remove:
            self.delete_session(sid, stop_if_running=False)
        if to_remove:
            logger.info("自动清理 %d 个过期会话", len(to_remove))
        return len(to_remove)

    def _register_agents(self, orchestrator: ResearchOrchestrator) -> None:
        """注册所有 Agent（无 Qt 依赖版本）"""
        try:
            from config_manager import get_config_manager
            config_manager = get_config_manager()
        except Exception:
            logger.warning("无法加载 config_manager，agents 将使用默认配置")
            return

        fallback_config = config_manager.find_fallback_config()

        from agents import (
            ArchitectAgent, TheoristAgent, EngineerAgent,
            SimulatorAgent, DSPCoderAgent, ScribeAgent, SupervisorAgent,
        )

        matlab_path = getattr(config_manager.settings, 'matlab_path', None) or None

        agent_defs = [
            ("architect", ArchitectAgent, "architect", {}),
            ("theorist", TheoristAgent, "theorist", {}),
            ("engineer", EngineerAgent, "engineer", {"matlab_path": matlab_path}),
            ("simulator", SimulatorAgent, "simulator", {"matlab_path": matlab_path}),
            ("dsp_coder", DSPCoderAgent, "dsp_coder", {}),
            ("scribe", ScribeAgent, "scribe", {}),
        ]

        for key, cls, config_type, kwargs in agent_defs:
            agent = cls(**kwargs)
            agent.api_config = config_manager.get_agent_by_type(config_type) or fallback_config
            orchestrator.register_agent(key, agent)

        supervisor = SupervisorAgent()
        supervisor.api_config = config_manager.get_agent_by_type("supervisor") or fallback_config
        orchestrator.set_supervisor(supervisor)

    def _bind_events(self, session: ResearchSession) -> None:
        """订阅 orchestrator 事件并存入 event_log"""
        orch = session.orchestrator
        
        def append_event(
            event: Dict[str, Any], update: Optional[Callable[[], None]] = None
        ) -> None:
            with session.event_lock:
                if update:
                    update()
                session.event_seq += 1
                payload = dict(event)
                payload["_seq"] = session.event_seq
                session.event_log.append(payload)
            session.event_notifier.set()

        def on_progress(event):
            data = event.data if isinstance(event.data, dict) else {"raw": event.data}

            def update_progress() -> None:
                raw_progress = data.get("progress", 0)
                session.progress = int(raw_progress) if isinstance(raw_progress, (int, float)) else 0
                session.current_stage = str(data.get("description", ""))

            append_event({"type": "progress", "data": data}, update=update_progress)

        def on_log(event):
            append_event({"type": "log", "data": event.data})

        def on_error(event):
            append_event(
                {"type": "error", "data": event.data},
                update=lambda: setattr(session, "error", str(event.data)),
            )

        def on_completed(event):
            append_event({"type": "completed"}, update=lambda: setattr(session, "progress", 100))

        orch.events.on("progress_updated", on_progress)
        orch.events.on("log_message", on_log)
        orch.events.on("workflow_error", on_error)
        orch.events.on("workflow_completed", on_completed)
