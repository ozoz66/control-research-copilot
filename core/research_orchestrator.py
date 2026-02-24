# -*- coding: utf-8 -*-
"""
研究流程编排器 - 纯 Python 实现

整合 WorkflowEngine 和 Agent 管理，提供完整的研究流程控制。
不依赖 PyQt6，可在 CLI/Web/Desktop 环境中使用。
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass

from .events import EventEmitter
from .workflow_engine import WorkflowEngine, WorkflowState
from .telemetry import trace_agent_execution


@dataclass
class StageConfig:
    """阶段配置"""
    key: str
    agent_key: str
    description: str
    progress: int
    depends_on: List[str]


# 默认工作流阶段配置
DEFAULT_WORKFLOW_STAGES = [
    StageConfig("literature", "architect", "Agent A: 文献检索与课题设计", 15, []),
    StageConfig("derivation", "theorist", "Agent B: 数学推导", 30, ["literature"]),
    StageConfig("simulation", "engineer", "Agent C: MATLAB代码生成", 45, ["derivation"]),
    StageConfig("sim_run", "simulator", "Agent C2: 仿真执行", 60, ["simulation"]),
    StageConfig("dsp_code", "dsp_coder", "Agent E: DSP代码生成", 75, ["sim_run"]),
    StageConfig("paper", "scribe", "Agent D: 论文撰写", 95, ["derivation", "sim_run"]),
]


class ResearchOrchestrator:
    """
    研究流程编排器

    用法:
        orchestrator = ResearchOrchestrator(output_dir="./output")

        # 注册 Agent
        orchestrator.register_agent("architect", architect_agent)
        orchestrator.register_agent("theorist", theorist_agent)

        # 设置监督器
        orchestrator.set_supervisor(supervisor_agent)

        # 订阅事件
        orchestrator.events.on("progress_updated", on_progress)
        orchestrator.events.on("log_message", on_log)

        # 启动工作流
        orchestrator.start_workflow(research_config)

        # 确认阶段
        orchestrator.confirm_stage()

        # 停止
        orchestrator.stop_workflow()
    """

    def __init__(
        self,
        output_dir: str = "./output",
        stages: List[StageConfig] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._stages = stages or DEFAULT_WORKFLOW_STAGES
        self._agents: Dict[str, Any] = {}
        self._supervisor: Optional[Any] = None

        self._engine: Optional[WorkflowEngine] = None
        self._context: Optional[Any] = None
        self._current_project_dir: Optional[Path] = None

        # 事件发射器 - 转发引擎事件
        self.events = EventEmitter()

    def register_agent(self, key: str, agent: Any) -> 'ResearchOrchestrator':
        """注册 Agent"""
        self._agents[key] = agent
        return self

    def unregister_agent(self, key: str) -> 'ResearchOrchestrator':
        """注销 Agent"""
        self._agents.pop(key, None)
        return self

    def set_supervisor(self, supervisor: Any) -> 'ResearchOrchestrator':
        """设置监督 Agent"""
        self._supervisor = supervisor
        return self

    def start_workflow(
        self,
        research_config: Dict[str, Any],
        resume_from: str = None
    ):
        """
        启动研究工作流

        Args:
            research_config: 研究配置
            resume_from: 检查点目录路径（用于断点续跑）
        """
        resume_index = 0

        if resume_from:
            resume_index = self._load_checkpoint(resume_from)
        else:
            self._create_context(research_config)
            self._create_project_dir(research_config)

        # 将 output_manager 注入到需要的 Agent
        self._inject_output_manager()

        # Build stage->agent mapping from stage configs (single source of truth)
        stage_agent_map = {s.key: s.agent_key for s in self._stages}

        # 创建工作流引擎
        self._engine = WorkflowEngine(
            checkpoint_dir=self._current_project_dir / "checkpoints" if self._current_project_dir else None,
            stage_agent_map=stage_agent_map,
        )

        # 注册阶段处理器
        stage_keys = []
        for stage in self._stages:
            if stage.agent_key in self._agents:
                agent = self._agents[stage.agent_key]
                self._engine.register_stage(
                    key=stage.key,
                    handler=self._create_stage_handler(agent),
                    description=stage.description,
                    progress=stage.progress
                )
                stage_keys.append(stage.key)

        # 设置监督器
        if self._supervisor:
            self._engine.set_supervisor(self._create_supervisor_handler())

        # 传递Agent引用给引擎，用于反馈注入
        # 转发引擎事件
        self._forward_engine_events()

        # 在后台线程启动
        self._engine.run_in_thread(
            context=self._context,
            stages=stage_keys,
            resume_index=resume_index
        )

    def _create_stage_handler(self, agent: Any) -> Callable:
        """创建阶段处理器"""
        raw_agent_key = getattr(agent, 'agent_type', 'unknown')
        agent_key = raw_agent_key.value if hasattr(raw_agent_key, "value") else str(raw_agent_key)

        async def handler(context):
            with trace_agent_execution(str(agent_key)):
                return await agent.execute(context)
        return handler

    def _create_supervisor_handler(self) -> Callable:
        """创建监督处理器"""
        # 构建 stage_key -> agent_key 映射
        stage_to_agent = {s.key: s.agent_key for s in self._stages}

        async def handler(stage_key: str, context):
            # 转换 stage_key 为 agent_key
            agent_key = stage_to_agent.get(stage_key, stage_key)
            return await self._supervisor.evaluate(agent_key, context)
        return handler

    def _forward_engine_events(self):
        """转发引擎事件到编排器事件"""
        if not self._engine:
            return

        # 清除之前的监听器，避免重复注册
        self._engine.events.clear()

        # 进度更新
        self._engine.events.on("progress_updated", lambda e:
            self.events.emit("progress_updated", e.data))

        # 日志消息
        self._engine.events.on("log_message", lambda e:
            self.events.emit("log_message", e.data))

        # 阶段完成
        self._engine.events.on("stage_completed", lambda e:
            self.events.emit("stage_completed", e.data))

        # 工作流完成
        self._engine.events.on("workflow_completed", lambda e:
            self._on_workflow_completed(e.data))

        # 工作流错误
        self._engine.events.on("workflow_error", lambda e:
            self.events.emit("workflow_error", e.data))

        # 阶段确认请求
        self._engine.events.on("stage_confirmation_required", lambda e:
            self.events.emit("stage_confirmation_required", e.data))

    def _on_workflow_completed(self, context):
        """工作流完成回调"""
        self._context = context
        self._save_outputs()
        self.events.emit("workflow_completed", context)

    def _save_outputs(self):
        """保存输出文件"""
        if not self._context or not self._current_project_dir:
            return

        try:
            # 保存 LaTeX
            if hasattr(self._context, 'paper_latex') and self._context.paper_latex:
                paper_dir = self._current_project_dir / "paper"
                paper_dir.mkdir(exist_ok=True)
                (paper_dir / "main.tex").write_text(
                    self._context.paper_latex, encoding='utf-8'
                )

            # 保存 MATLAB 代码
            if hasattr(self._context, 'matlab_code') and self._context.matlab_code:
                code_dir = self._current_project_dir / "code"
                code_dir.mkdir(exist_ok=True)
                (code_dir / "controller.m").write_text(
                    self._context.matlab_code, encoding='utf-8'
                )

            # 保存 DSP 代码
            if hasattr(self._context, 'dsp_c_code') and self._context.dsp_c_code:
                code_dir = self._current_project_dir / "code"
                code_dir.mkdir(exist_ok=True)
                (code_dir / "controller.c").write_text(
                    self._context.dsp_c_code, encoding='utf-8'
                )

            if hasattr(self._context, 'dsp_header_code') and self._context.dsp_header_code:
                code_dir = self._current_project_dir / "code"
                (code_dir / "controller.h").write_text(
                    self._context.dsp_header_code, encoding='utf-8'
                )

            # 保存上下文
            if hasattr(self._context, 'save_to_file'):
                self._context.save_to_file(
                    str(self._current_project_dir / "context.json")
                )

        except Exception as e:
            self.events.emit("log_message", {
                "message": f"保存输出失败: {e}",
                "level": "error"
            })

    def stop_workflow(self):
        """停止工作流"""
        if self._engine:
            self._engine.stop()

    def _inject_output_manager(self):
        """将 output_manager 注入到需要的 Agent"""
        if not self._current_project_dir:
            return

        # 创建 OutputManager 实例
        try:
            from output_manager import OutputManager
            output_mgr = OutputManager(str(self.output_dir))
            output_mgr.current_project_dir = self._current_project_dir
            output_mgr.paper_dir = self._current_project_dir / "paper"
            output_mgr.code_dir = self._current_project_dir / "code"
            output_mgr.paper_dir.mkdir(exist_ok=True)
            output_mgr.code_dir.mkdir(exist_ok=True)

            # 注入到所有有 output_manager 属性的 Agent
            for agent in self._agents.values():
                if hasattr(agent, 'output_manager'):
                    agent.output_manager = output_mgr
        except ImportError:
            pass  # output_manager 模块不存在时跳过

    def confirm_stage(
        self,
        modification: str = None,
        rollback_to: str = None
    ):
        """确认当前阶段"""
        if self._engine:
            self._engine.confirm_stage(modification, rollback_to)

    def confirm_topic(self, updated_context: Any = None):
        """确认课题"""
        if updated_context:
            self._context = updated_context
        self.confirm_stage()

    def _create_context(self, research_config: Dict[str, Any]):
        """创建上下文"""
        # 延迟导入避免循环依赖
        from global_context import GlobalContext
        self._context = GlobalContext(research_config=research_config)

    def _create_project_dir(self, research_config: Dict[str, Any]):
        """创建项目目录"""
        from datetime import datetime

        # 简单命名：时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = timestamp

        self._current_project_dir = self.output_dir / dir_name
        self._current_project_dir.mkdir(parents=True, exist_ok=True)

    def _load_checkpoint(self, project_dir: str) -> int:
        """从检查点加载，返回恢复索引"""
        from global_context import GlobalContext

        self._current_project_dir = Path(project_dir)
        cp_dir = self._current_project_dir / "checkpoints"

        if not cp_dir.exists():
            return 0

        # 找到最后一个检查点
        for i, stage in reversed(list(enumerate(self._stages))):
            cp_file = cp_dir / f"checkpoint_{stage.key}.json"
            if cp_file.exists():
                self._context = GlobalContext.load_from_file(str(cp_file))
                return i + 1

        return 0

    def get_context(self) -> Optional[Any]:
        """获取当前上下文"""
        return self._context

    def get_state(self) -> WorkflowState:
        """获取工作流状态"""
        if self._engine:
            return self._engine.state
        return WorkflowState.IDLE

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._engine is not None and self._engine.is_running()
