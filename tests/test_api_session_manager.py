# -*- coding: utf-8 -*-

import threading
import time

import pytest

from api import session_manager as session_manager_module
from core.events import EventEmitter
from core.workflow_engine import WorkflowState


class DummyHistory:
    def get_session_summary(self):
        return {
            "total_records": 0,
            "agents": [],
            "agent_summaries": {},
        }


class DummyOrchestrator:
    def __init__(self):
        self.events = EventEmitter()
        self._state = WorkflowState.IDLE
        self.started_config = None
        self.stop_called = False

    def start_workflow(self, config):
        self.started_config = config

    def get_state(self):
        return self._state

    def is_running(self):
        return self._state == WorkflowState.RUNNING

    def stop_workflow(self):
        self.stop_called = True
        self._state = WorkflowState.STOPPED

    def register_agent(self, key, agent):
        return None

    def set_supervisor(self, supervisor):
        return None


@pytest.fixture
def manager(monkeypatch):
    orchestrators = []

    def factory(output_dir):  # noqa: ARG001
        orchestrator = DummyOrchestrator()
        orchestrators.append(orchestrator)
        return orchestrator

    monkeypatch.setattr(session_manager_module, "ResearchOrchestrator", factory)
    monkeypatch.setattr(session_manager_module, "AgentHistory", DummyHistory)
    monkeypatch.setattr(
        session_manager_module.SessionManager,
        "_register_agents",
        lambda self, orchestrator: None,
    )

    mgr = session_manager_module.SessionManager()
    return mgr, orchestrators


class TestSessionManager:
    def test_create_session_starts_workflow(self, manager):
        mgr, orchestrators = manager

        session = mgr.create_session({"topic": "test"})

        assert session.session_id
        assert orchestrators[0].started_config == {"topic": "test"}
        assert mgr.get_session(session.session_id) is session

    def test_event_log_uses_bounded_deque_with_sequence(self, manager):
        mgr, orchestrators = manager
        session = mgr.create_session({"topic": "test"})
        orchestrator = orchestrators[0]

        for i in range(session_manager_module.MAX_EVENT_LOG + 5):
            orchestrator.events.emit("log_message", {"index": i})

        events = list(session.event_log)
        assert len(events) == session_manager_module.MAX_EVENT_LOG
        assert events[0]["_seq"] == 6
        assert events[-1]["_seq"] == session_manager_module.MAX_EVENT_LOG + 5

    def test_delete_session_stops_running_workflow(self, manager):
        mgr, orchestrators = manager
        session = mgr.create_session({})
        orchestrator = orchestrators[0]
        orchestrator._state = WorkflowState.RUNNING

        deleted = mgr.delete_session(session.session_id, stop_if_running=True)

        assert deleted is True
        assert orchestrator.stop_called is True
        assert mgr.get_session(session.session_id) is None

    def test_cleanup_stale_sessions_removes_only_terminal_sessions(self, manager):
        mgr, orchestrators = manager
        old_terminal = mgr.create_session({"name": "old_terminal"})
        old_running = mgr.create_session({"name": "old_running"})
        recent_terminal = mgr.create_session({"name": "recent_terminal"})

        orchestrators[0]._state = WorkflowState.COMPLETED
        orchestrators[1]._state = WorkflowState.RUNNING
        orchestrators[2]._state = WorkflowState.ERROR

        old_terminal.created_at = time.time() - 3600
        old_running.created_at = time.time() - 3600
        recent_terminal.created_at = time.time()

        cleaned = mgr.cleanup_stale_sessions(max_age_seconds=10)

        assert cleaned == 1
        assert mgr.get_session(old_terminal.session_id) is None
        assert mgr.get_session(old_running.session_id) is not None
        assert mgr.get_session(recent_terminal.session_id) is not None

    def test_progress_event_tolerates_non_dict_payload(self, manager):
        mgr, orchestrators = manager
        session = mgr.create_session({"topic": "robust-progress"})
        orchestrator = orchestrators[0]

        orchestrator.events.emit("progress_updated", "bad-payload")

        status = mgr.get_status(session.session_id)
        assert status is not None
        assert status["progress"] == 0
        assert status["current_stage"] == ""
        assert session.event_log[-1]["type"] == "progress"
        assert session.event_log[-1]["data"] == {"raw": "bad-payload"}

    def test_completed_event_sets_progress_to_100(self, manager):
        mgr, orchestrators = manager
        session = mgr.create_session({"topic": "done"})
        orchestrator = orchestrators[0]

        orchestrator.events.emit("workflow_completed", {"ok": True})

        status = mgr.get_status(session.session_id)
        assert status is not None
        assert status["progress"] == 100
        assert session.event_log[-1]["type"] == "completed"

    def test_concurrent_delete_is_safe(self, manager):
        mgr, _ = manager
        session = mgr.create_session({"topic": "race"})

        results = []

        def worker():
            results.append(mgr.delete_session(session.session_id))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results.count(True) == 1
        assert results.count(False) == 7


def test_create_session_rolls_back_when_start_fails(monkeypatch):
    class FailingOrchestrator(DummyOrchestrator):
        def start_workflow(self, config):  # noqa: ARG002
            raise RuntimeError("boom")

    monkeypatch.setattr(
        session_manager_module,
        "ResearchOrchestrator",
        lambda output_dir: FailingOrchestrator(),  # noqa: ARG005
    )
    monkeypatch.setattr(session_manager_module, "AgentHistory", DummyHistory)
    monkeypatch.setattr(
        session_manager_module.SessionManager,
        "_register_agents",
        lambda self, orchestrator: None,
    )

    mgr = session_manager_module.SessionManager()
    with pytest.raises(RuntimeError, match="boom"):
        mgr.create_session({"topic": "will-fail"})

    assert mgr.list_sessions() == []
