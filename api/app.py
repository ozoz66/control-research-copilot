# -*- coding: utf-8 -*-
"""
FastAPI 应用工厂 - AutoControl-Scientist
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .session_manager import SessionManager
from .ws_handler import ConnectionManager
from core.telemetry import init_telemetry

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""

    app = FastAPI(
        title="AutoControl-Scientist API",
        description="多Agent协作的控制系统研究自动化平台 - Web API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Shared runtime services for dependency injection.
    app.state.session_manager = SessionManager()
    app.state.ws_manager = ConnectionManager()

    # CORS - 从环境变量读取允许的源，逗号分隔；默认仅允许本地开发
    raw_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins else [
        "http://localhost:3000", "http://127.0.0.1:3000"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(router)

    @app.on_event("startup")
    async def on_startup():
        # 初始化 telemetry（无 OTEL 时自动降级）
        init_telemetry(service_name="autocontrol-api")
        logger.info("AutoControl-Scientist API 已启动")

    return app
