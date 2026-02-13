# -*- coding: utf-8 -*-

from api.app import create_app
from api.session_manager import SessionManager
from api.ws_handler import ConnectionManager


def test_create_app_initializes_runtime_services(monkeypatch):
    import api.app as app_module

    monkeypatch.setattr(app_module, "init_telemetry", lambda service_name: None)

    app = create_app()

    assert isinstance(app.state.session_manager, SessionManager)
    assert isinstance(app.state.ws_manager, ConnectionManager)
