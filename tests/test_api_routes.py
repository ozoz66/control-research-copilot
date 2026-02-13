# -*- coding: utf-8 -*-

import threading
from collections import deque

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from core.workflow_engine import WorkflowState


class DummyHistory:
    def get_session_summary(self):
        return {
            "total_records": 3,
            "agents": ["architect"],
            "agent_summaries": {"architect": {"llm_calls": 1}},
        }


class DummyOrchestrator:
    def __init__(self, state=WorkflowState.RUNNING):
        self._state = state
        self.confirm_calls = []

    def get_state(self):
        return self._state

    def confirm_stage(self, modification=None, rollback_to=None):
        self.confirm_calls.append(
            {
                "modification": modification,
                "rollback_to": rollback_to,
            }
        )


class DummySession:
    def __init__(self, session_id: str, state=WorkflowState.RUNNING):
        self.session_id = session_id
        self.orchestrator = DummyOrchestrator(state=state)
        self.history = DummyHistory()
        self.event_log = deque()
        self.event_notifier = threading.Event()
        self.event_lock = threading.Lock()
        self.progress = 10
        self.current_stage = "demo"
        self.error = None


class DummySessionManager:
    def __init__(self):
        self.sessions = {}
        self.last_create_config = None

    @property
    def active_count(self):
        return sum(
            1
            for session in self.sessions.values()
            if session.orchestrator.get_state() in (WorkflowState.RUNNING, WorkflowState.WAITING_CONFIRMATION)
        )

    def create_session(self, config):
        self.last_create_config = config
        sid = f"session-{len(self.sessions) + 1}"
        session = DummySession(sid)
        self.sessions[sid] = session
        return session

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def get_status(self, session_id):
        session = self.sessions.get(session_id)
        if session is None:
            return None
        state = session.orchestrator.get_state()
        return {
            "session_id": session_id,
            "state": state.value,
            "progress": session.progress,
            "current_stage": session.current_stage,
            "error": session.error,
        }

    def delete_session(self, session_id, stop_if_running=True):  # noqa: ARG002
        if session_id not in self.sessions:
            return False
        del self.sessions[session_id]
        return True


@pytest.fixture
def client(monkeypatch):
    import api.app as app_module

    monkeypatch.setattr(app_module, "init_telemetry", lambda service_name: None)
    app = create_app()
    manager = DummySessionManager()
    app.state.session_manager = manager

    with TestClient(app) as test_client:
        yield test_client, manager


class TestRoutes:
    def test_health_uses_injected_manager(self, client):
        test_client, manager = client
        manager.sessions["s1"] = DummySession("s1", state=WorkflowState.RUNNING)
        manager.sessions["s2"] = DummySession("s2", state=WorkflowState.COMPLETED)

        response = test_client.get("/api/health")

        assert response.status_code == 200
        assert response.json()["active_sessions"] == 1

    def test_start_research_normalizes_config(self, client):
        test_client, manager = client
        payload = {
            "main_algorithm": "MPC",
            "performance_objectives": ["fast transient", "overshoot reduction"],
            "composite_architecture": "SMC + ZPETC + ESO",
            "custom_topic": "  precision motion control  ",
        }

        response = test_client.post("/api/research", json=payload)

        assert response.status_code == 200
        assert "session_id" in response.json()
        assert manager.last_create_config["main_algorithm"]["key"] == "mpc"
        assert manager.last_create_config["custom_topic"] == "precision motion control"

    def test_status_and_history(self, client):
        test_client, manager = client
        manager.sessions["session-1"] = DummySession("session-1", state=WorkflowState.WAITING_CONFIRMATION)

        missing_status = test_client.get("/api/research/not-found/status")
        assert missing_status.status_code == 404

        status = test_client.get("/api/research/session-1/status")
        assert status.status_code == 200
        assert status.json()["state"] == "waiting_confirmation"

        history = test_client.get("/api/research/session-1/history")
        assert history.status_code == 200
        assert history.json()["total_records"] == 3

    def test_confirm_and_delete(self, client):
        test_client, manager = client
        manager.sessions["session-1"] = DummySession("session-1")

        confirm_resp = test_client.post(
            "/api/research/session-1/confirm",
            json={"modification": "adjust", "rollback_to": "derivation"},
        )
        assert confirm_resp.status_code == 200
        calls = manager.sessions["session-1"].orchestrator.confirm_calls
        assert calls == [{"modification": "adjust", "rollback_to": "derivation"}]

        delete_resp = test_client.delete("/api/research/session-1")
        assert delete_resp.status_code == 200
        assert "session-1" not in manager.sessions

    def test_websocket_streams_events_without_internal_sequence(self, client):
        test_client, manager = client
        session = DummySession("ws-1", state=WorkflowState.COMPLETED)
        session.event_log.append({"type": "log", "data": {"message": "ok"}, "_seq": 1})
        manager.sessions["ws-1"] = session

        with test_client.websocket_connect("/api/ws/ws-1") as websocket:
            first = websocket.receive_json()
            done = websocket.receive_json()

        assert first == {"type": "log", "data": {"message": "ok"}}
        assert done == {"type": "done", "state": "completed"}
