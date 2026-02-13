# -*- coding: utf-8 -*-
"""
API 路由定义 - AutoControl-Scientist
"""

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from .models import (
    ResearchRequest,
    ResearchStartResponse,
    ResearchStatusResponse,
    HistoryResponse,
    HealthResponse,
    ConfirmRequest,
)
from .session_manager import SessionManager
from .ws_handler import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


@router.get("/health", response_model=HealthResponse)
async def health_check(session_manager: SessionManager = Depends(get_session_manager)):
    """健康检查"""
    return HealthResponse(active_sessions=session_manager.active_count)


@router.post("/research", response_model=ResearchStartResponse)
async def start_research(
    request: ResearchRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """启动研究工作流"""
    config = request.to_research_config()

    try:
        session = session_manager.create_session(config)
    except Exception as e:
        logger.error("启动研究失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return ResearchStartResponse(session_id=session.session_id)


@router.get("/research/{session_id}/status", response_model=ResearchStatusResponse)
async def get_research_status(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """查询研究工作流状态"""
    status = session_manager.get_status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return ResearchStatusResponse(**status)


@router.get("/research/{session_id}/history", response_model=HistoryResponse)
async def get_research_history(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """获取交互历史"""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = session.history.get_session_summary()
    return HistoryResponse(
        session_id=session_id,
        total_records=summary.get("total_records", 0),
        agents=summary.get("agents", []),
        agent_summaries=summary.get("agent_summaries", {}),
    )


@router.post("/research/{session_id}/confirm")
async def confirm_stage(
    session_id: str,
    request: ConfirmRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """确认当前阶段（支持 modification / rollback_to）"""
    session = session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session.orchestrator.confirm_stage(
            modification=request.modification,
            rollback_to=request.rollback_to,
        )
    except Exception as e:
        logger.error("确认阶段失败 [%s]: %s", session_id, e)
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "confirmed", "session_id": session_id}


@router.delete("/research/{session_id}")
async def delete_research_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """删除会话并释放内存。"""
    deleted = session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """实时 WebSocket"""
    session_manager: SessionManager = websocket.app.state.session_manager
    ws_manager: ConnectionManager = websocket.app.state.ws_manager
    session = session_manager.get_session(session_id)
    if session is None:
        await websocket.close(code=4004)
        return

    await ws_manager.connect(session_id, websocket)
    last_seq = 0
    try:
        while True:
            with session.event_lock:
                events = [event for event in session.event_log if event.get("_seq", 0) > last_seq]
                if events:
                    last_seq = max(int(event.get("_seq", 0)) for event in events)

            for event in events:
                payload = {k: v for k, v in event.items() if k != "_seq"}
                await websocket.send_json(payload)

            if session_manager.get_session(session_id) is None:
                await websocket.send_json({"type": "done", "state": "deleted"})
                break

            state = session.orchestrator.get_state().value
            if state in ("completed", "error", "stopped"):
                await websocket.send_json({"type": "done", "state": state})
                break

            # Event-driven wait to avoid polling busy loops.
            with session.event_lock:
                latest_seq = int(session.event_log[-1].get("_seq", 0)) if session.event_log else 0
                has_new = latest_seq > last_seq
            if has_new:
                continue
            session.event_notifier.clear()
            with session.event_lock:
                latest_seq = int(session.event_log[-1].get("_seq", 0)) if session.event_log else 0
                has_new = latest_seq > last_seq
            if has_new:
                continue
            await asyncio.to_thread(session.event_notifier.wait, 30.0)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(session_id, websocket)
