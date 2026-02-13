# -*- coding: utf-8 -*-
"""
工作流引擎单元测试
"""

import pytest
import asyncio
import threading
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.workflow_engine import WorkflowEngine, WorkflowState


class MockContext:
    """模拟上下文"""
    def __init__(self):
        self.data = {}
        self.stages_executed = []

    def save_to_file(self, path: str):
        pass


class TestWorkflowEngine:
    """WorkflowEngine 测试类"""

    def test_initial_state(self):
        """测试初始状态"""
        engine = WorkflowEngine()
        assert engine.state == WorkflowState.IDLE
        assert engine.current_stage_index == 0

    def test_register_stage(self):
        """测试注册阶段"""
        engine = WorkflowEngine()

        async def handler(ctx):
            return ctx

        engine.register_stage("test", handler, "测试阶段", 50)

        assert "test" in engine._stages
        assert engine._stage_descriptions["test"] == "测试阶段"
        assert engine._stage_progress["test"] == 50

    def test_chain_registration(self):
        """测试链式注册"""
        engine = WorkflowEngine()

        async def h1(ctx): return ctx
        async def h2(ctx): return ctx

        result = engine.register_stage("s1", h1).register_stage("s2", h2)

        assert result is engine
        assert "s1" in engine._stages
        assert "s2" in engine._stages

    @pytest.mark.asyncio
    async def test_run_single_stage(self):
        """测试运行单个阶段"""
        engine = WorkflowEngine()
        context = MockContext()

        async def handler(ctx):
            ctx.stages_executed.append("stage1")
            return ctx

        engine.register_stage("stage1", handler, "阶段1", 100)

        # 自动确认
        def auto_confirm():
            time.sleep(0.1)
            engine.confirm_stage()

        threading.Thread(target=auto_confirm, daemon=True).start()

        result = await engine.run(context, ["stage1"])

        assert "stage1" in result.stages_executed
        assert engine.state == WorkflowState.COMPLETED

    @pytest.mark.asyncio
    async def test_run_multiple_stages(self):
        """测试运行多个阶段"""
        engine = WorkflowEngine()
        context = MockContext()

        async def handler1(ctx):
            ctx.stages_executed.append("s1")
            return ctx

        async def handler2(ctx):
            ctx.stages_executed.append("s2")
            return ctx

        async def handler3(ctx):
            ctx.stages_executed.append("s3")
            return ctx

        engine.register_stage("s1", handler1, "阶段1", 33)
        engine.register_stage("s2", handler2, "阶段2", 66)
        engine.register_stage("s3", handler3, "阶段3", 100)

        # 自动确认所有阶段
        def auto_confirm():
            for _ in range(3):
                time.sleep(0.1)
                engine.confirm_stage()

        threading.Thread(target=auto_confirm, daemon=True).start()

        result = await engine.run(context, ["s1", "s2", "s3"])

        assert result.stages_executed == ["s1", "s2", "s3"]
        assert engine.state == WorkflowState.COMPLETED

    @pytest.mark.asyncio
    async def test_stop_workflow(self):
        """测试停止工作流"""
        engine = WorkflowEngine()
        context = MockContext()

        async def slow_handler(ctx):
            await asyncio.sleep(1)
            ctx.stages_executed.append("slow")
            return ctx

        engine.register_stage("slow", slow_handler)

        # 立即停止
        def stop_soon():
            time.sleep(0.05)
            engine.stop()

        threading.Thread(target=stop_soon, daemon=True).start()

        await engine.run(context, ["slow"])

        assert engine.state == WorkflowState.STOPPED

    @pytest.mark.asyncio
    async def test_resume_from_index(self):
        """测试从指定索引恢复"""
        engine = WorkflowEngine()
        context = MockContext()

        async def h1(ctx):
            ctx.stages_executed.append("s1")
            return ctx

        async def h2(ctx):
            ctx.stages_executed.append("s2")
            return ctx

        async def h3(ctx):
            ctx.stages_executed.append("s3")
            return ctx

        engine.register_stage("s1", h1)
        engine.register_stage("s2", h2)
        engine.register_stage("s3", h3)

        # 自动确认
        def auto_confirm():
            for _ in range(2):  # 只需确认 s2, s3
                time.sleep(0.1)
                engine.confirm_stage()

        threading.Thread(target=auto_confirm, daemon=True).start()

        # 从索引 1 开始（跳过 s1）
        result = await engine.run(context, ["s1", "s2", "s3"], resume_index=1)

        assert "s1" not in result.stages_executed
        assert "s2" in result.stages_executed
        assert "s3" in result.stages_executed

    @pytest.mark.asyncio
    async def test_events_emitted(self):
        """测试事件发射"""
        engine = WorkflowEngine()
        context = MockContext()
        events_received = []

        async def handler(ctx):
            return ctx

        engine.register_stage("test", handler, "测试", 100)

        engine.events.on("progress_updated", lambda e: events_received.append(("progress", e.data)))
        engine.events.on("log_message", lambda e: events_received.append(("log", e.data)))
        engine.events.on("stage_completed", lambda e: events_received.append(("completed", e.data)))

        def auto_confirm():
            time.sleep(0.1)
            engine.confirm_stage()

        threading.Thread(target=auto_confirm, daemon=True).start()

        await engine.run(context, ["test"])

        # 检查是否收到了预期的事件
        event_types = [e[0] for e in events_received]
        assert "progress" in event_types
        assert "log" in event_types
        assert "completed" in event_types

    @pytest.mark.asyncio
    async def test_stage_error_handling(self):
        """测试阶段错误处理"""
        engine = WorkflowEngine()
        context = MockContext()

        async def failing_handler(ctx):
            raise ValueError("测试错误")

        engine.register_stage("fail", failing_handler)

        def auto_confirm():
            time.sleep(0.1)
            engine.confirm_stage()

        threading.Thread(target=auto_confirm, daemon=True).start()

        await engine.run(context, ["fail"])

        assert engine.state == WorkflowState.ERROR

    def test_run_in_thread(self):
        """测试在线程中运行"""
        engine = WorkflowEngine()
        context = MockContext()

        async def handler(ctx):
            ctx.stages_executed.append("threaded")
            return ctx

        engine.register_stage("test", handler)

        def auto_confirm():
            time.sleep(0.1)
            engine.confirm_stage()

        threading.Thread(target=auto_confirm, daemon=True).start()

        thread = engine.run_in_thread(context, ["test"])
        engine.wait(timeout=2)

        assert "threaded" in context.stages_executed

    def test_is_running(self):
        """测试运行状态检查"""
        engine = WorkflowEngine()
        assert not engine.is_running()


class TestWorkflowState:
    """WorkflowState 枚举测试"""

    def test_states_exist(self):
        """测试状态枚举值"""
        assert WorkflowState.IDLE.value == "idle"
        assert WorkflowState.RUNNING.value == "running"
        assert WorkflowState.PAUSED.value == "paused"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.ERROR.value == "error"
        assert WorkflowState.STOPPED.value == "stopped"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
