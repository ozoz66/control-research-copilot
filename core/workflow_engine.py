# -*- coding: utf-8 -*-
"""
工作流执行引擎 - 纯 Python 实现

不依赖 PyQt6，可在任何 Python 环境中运行。
支持:
- 异步执行
- 断点续跑
- 回退机制
- 事件通知
"""

import asyncio
import json
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from .events import EventEmitter, Event
from .telemetry import trace_workflow_stage

# Default stage ↔ agent mapping (can be overridden via set_stage_agent_map)
_DEFAULT_STAGE_AGENT_MAP: Dict[str, str] = {
    "literature": "architect",
    "derivation": "theorist",
    "simulation": "engineer",
    "sim_run": "simulator",
    "dsp_code": "dsp_coder",
    "paper": "scribe",
}


class WorkflowState(Enum):
    """工作流状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class StageResult:
    """阶段执行结果"""
    stage_key: str
    success: bool
    duration: float = 0.0
    error: Optional[str] = None
    output: Any = None


class WorkflowEngine:
    """
    工作流执行引擎 - 纯 Python 异步实现

    用法:
        engine = WorkflowEngine()

        # 注册阶段处理器
        engine.register_stage("architect", architect_handler)
        engine.register_stage("theorist", theorist_handler)

        # 订阅事件
        engine.events.on("progress_updated", on_progress)
        engine.events.on("stage_completed", on_stage_complete)

        # 启动工作流
        await engine.run(context, stages=["architect", "theorist", "engineer"])

        # 或在线程中运行
        engine.run_in_thread(context, stages)
    """

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        stage_agent_map: Optional[Dict[str, str]] = None,
    ):
        self.events = EventEmitter()
        self._stages: Dict[str, Callable] = {}
        self._stage_descriptions: Dict[str, str] = {}
        self._stage_progress: Dict[str, int] = {}
        self._supervisor: Optional[Callable] = None

        # Stage ↔ Agent mapping (single source of truth)
        self._stage_agent_map: Dict[str, str] = dict(stage_agent_map or _DEFAULT_STAGE_AGENT_MAP)
        self._agent_stage_map: Dict[str, str] = {v: k for k, v in self._stage_agent_map.items()}

        self._lock = threading.Lock()
        self._state = WorkflowState.IDLE
        self._current_stage_index = 0
        self._context: Any = None
        self._checkpoint_dir = checkpoint_dir

        self._stop_flag = threading.Event()
        self._confirmation_event = threading.Event()
        self._confirmation_result: Optional[Dict] = None

        self._worker_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def state(self) -> WorkflowState:
        with self._lock:
            return self._state

    @property
    def current_stage_index(self) -> int:
        with self._lock:
            return self._current_stage_index

    def register_stage(
        self,
        key: str,
        handler: Callable,
        description: str = "",
        progress: int = 0
    ) -> 'WorkflowEngine':
        """
        注册阶段处理器

        Args:
            key: 阶段标识
            handler: 异步处理函数，签名: async def handler(context) -> context
            description: 阶段描述
            progress: 该阶段完成时的进度百分比

        Returns:
            self
        """
        self._stages[key] = handler
        self._stage_descriptions[key] = description or key
        self._stage_progress[key] = progress
        return self

    def set_supervisor(self, supervisor: Callable) -> 'WorkflowEngine':
        """设置监督器"""
        self._supervisor = supervisor
        return self

    def set_checkpoint_dir(self, path: Path) -> 'WorkflowEngine':
        """设置检查点目录"""
        self._checkpoint_dir = path
        return self

    async def run(
        self,
        context: Any,
        stages: List[str],
        resume_index: int = 0
    ) -> Any:
        """
        异步执行工作流

        Args:
            context: 上下文对象
            stages: 要执行的阶段列表
            resume_index: 从哪个阶段开始（用于断点续跑）

        Returns:
            执行完成后的上下文
        """
        self._context = context
        self._state = WorkflowState.RUNNING
        self._stop_flag.clear()
        self._current_stage_index = resume_index

        await self.events.emit_async("workflow_started", {
            "stages": stages,
            "resume_index": resume_index
        })

        if resume_index > 0:
            self._emit_log(f"从检查点恢复，跳过前 {resume_index} 个阶段", "info")

        try:
            while self._current_stage_index < len(stages):
                if self._stop_flag.is_set():
                    self._state = WorkflowState.STOPPED
                    self._emit_log("工作流被用户中断", "warning")
                    await self.events.emit_async("workflow_stopped", self._context)
                    return self._context

                stage_key = stages[self._current_stage_index]
                result = await self._execute_stage(stage_key)

                if self._stop_flag.is_set():
                    self._state = WorkflowState.STOPPED
                    self._emit_log("工作流被用户中断", "warning")
                    await self.events.emit_async("workflow_stopped", self._context)
                    return self._context

                if not result.success:
                    self._state = WorkflowState.ERROR
                    await self.events.emit_async("workflow_error", result.error)
                    return self._context

                # 检查Agent是否请求重做上游任务
                if self._context and hasattr(self._context, 'redo_request') and self._context.redo_request:
                    redo = self._context.redo_request
                    self._context.redo_request = None
                    target_key = redo.get("agent", "")
                    redo_reason = redo.get("reason", "")
                    # 查找目标阶段（通过agent_key映射）
                    target_stage_idx = self._find_stage_by_agent(stages, target_key)
                    if target_stage_idx is not None and target_stage_idx < self._current_stage_index:
                        target_stage_key = stages[target_stage_idx]
                        self._emit_log(
                            f"[重做请求] {stage_key} 请求重做 {target_key}: {redo_reason}",
                            "warning"
                        )
                        # 注入反馈并重新执行目标阶段
                        self._inject_supervisor_feedback(target_key, f"下游Agent反馈: {redo_reason}")
                        target_result = await self._execute_stage(target_stage_key)
                        self._clear_supervisor_feedback(target_key)
                        if target_result.success:
                            self._save_checkpoint(target_stage_key)
                        # 重新执行当前阶段
                        self._emit_log(f"[重做] 重新执行 {stage_key}", "agent")
                        result = await self._execute_stage(stage_key)
                        if not result.success:
                            self._state = WorkflowState.ERROR
                            await self.events.emit_async("workflow_error", result.error)
                            return self._context

                # 保存检查点
                self._save_checkpoint(stage_key)

                # 监督评估（带重试和反馈注入）
                eval_result = None
                if self._supervisor:
                    eval_result = await self._run_supervisor_with_retry(stage_key, stages)

                # 等待用户确认
                confirmation = await self._wait_for_confirmation(
                    stage_key, eval_result
                )

                if confirmation and confirmation.get("rollback_to"):
                    rollback_target = confirmation["rollback_to"]
                    rollback_idx = stages.index(rollback_target) if rollback_target in stages else -1
                    if 0 <= rollback_idx < self._current_stage_index:
                        self._emit_log(f"回退到 {rollback_target}", "warning")
                        self._clear_context_from(stages, rollback_idx)
                        self._current_stage_index = rollback_idx
                        continue

                self._current_stage_index += 1

            # 完成
            self._state = WorkflowState.COMPLETED
            self._emit_progress(100, "工作流完成")
            self._emit_log("全部阶段执行完毕！", "success")
            await self.events.emit_async("workflow_completed", self._context)

        except Exception as e:
            self._state = WorkflowState.ERROR
            self._emit_log(f"工作流执行错误: {e}", "error")
            await self.events.emit_async("workflow_error", str(e))

        return self._context

    async def _execute_stage(self, stage_key: str) -> StageResult:
        """执行单个阶段"""
        if stage_key not in self._stages:
            self._emit_log(f"阶段 '{stage_key}' 未注册，跳过", "warning")
            return StageResult(stage_key=stage_key, success=True)

        handler = self._stages[stage_key]
        description = self._stage_descriptions.get(stage_key, stage_key)
        progress = self._stage_progress.get(stage_key, 0)

        self._emit_progress(progress, description)
        self._emit_log(f"开始执行: {description}", "agent")

        start_time = datetime.now()
        try:
            with trace_workflow_stage(stage_key, description):
                self._context = await handler(self._context)
            duration = (datetime.now() - start_time).total_seconds()

            self._emit_log(f"完成: {description}", "success")
            await self.events.emit_async("stage_completed", {
                "stage_key": stage_key,
                "description": description
            })

            return StageResult(
                stage_key=stage_key,
                success=True,
                duration=duration,
                output=self._context
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"{description} 执行失败: {e}"
            self._emit_log(error_msg, "error")

            return StageResult(
                stage_key=stage_key,
                success=False,
                duration=duration,
                error=str(e)
            )

    async def _run_supervisor(self, stage_key: str) -> Optional[Any]:
        """运行监督评估（单次）"""
        if not self._supervisor:
            return None

        try:
            result = await self._supervisor(stage_key, self._context)
            score = getattr(result, 'score', 0)
            passed = getattr(result, 'passed', True)

            # 使用 agent_key 而不是 stage_key 显示日志
            agent_key = self._stage_to_agent_key(stage_key, [])
            self._emit_log(
                f"[监督] {agent_key} 评分: {score}/100",
                "success" if passed else "warning"
            )

            suggestions = getattr(result, 'suggestions', [])
            for suggestion in suggestions:
                self._emit_log(f"[建议] {suggestion}", "info")

            return result
        except Exception as e:
            self._emit_log(f"[监督] 评估失败: {e}", "warning")
            return None

    async def _run_supervisor_with_retry(
        self, stage_key: str, stages: List[str], max_retries: int = 3
    ) -> Optional[Any]:
        """运行监督评估，评分不通过时自动重做并注入反馈"""
        result = await self._run_supervisor(stage_key)
        if result is None:
            return None

        iteration = 0
        while iteration < max_retries:
            passed = getattr(result, 'passed', True)
            if passed:
                break

            issues = getattr(result, 'issues', [])
            suggestions = getattr(result, 'suggestions', [])
            for issue in issues:
                self._emit_log(f"[问题] {issue}", "warning")

            # 注入反馈
            feedback_parts = []
            if issues:
                feedback_parts.append("问题: " + "; ".join(str(i) for i in issues))
            if suggestions:
                feedback_parts.append("建议: " + "; ".join(str(s) for s in suggestions))
            feedback = "\n".join(feedback_parts)

            # 查找stage_key对应的agent_key并注入反馈
            agent_key = self._stage_to_agent_key(stage_key, stages)
            self._inject_supervisor_feedback(agent_key, feedback)

            iteration += 1
            self._emit_log(f"[监督] 重新执行 {agent_key} (第{iteration+1}次)", "agent")

            # 重新执行阶段
            stage_result = await self._execute_stage(stage_key)
            self._clear_supervisor_feedback(agent_key)

            if not stage_result.success:
                self._emit_log(f"[监督] 重做失败: {stage_result.error}", "error")
                break

            self._save_checkpoint(stage_key)

            # 重新评估
            result = await self._run_supervisor(stage_key)
            if result is None:
                break

        return result

    def _stage_to_agent_key(self, stage_key: str, stages: List[str]) -> str:
        """将stage_key映射到agent_key"""
        return self._stage_agent_map.get(stage_key, stage_key)

    def _find_stage_by_agent(self, stages: List[str], agent_key: str) -> Optional[int]:
        """通过agent_key查找对应的stage索引"""
        target_stage = self._agent_stage_map.get(agent_key, agent_key)
        try:
            return stages.index(target_stage)
        except ValueError:
            return None

    def _inject_supervisor_feedback(self, agent_key: str, feedback: str):
        """注入监督反馈到Agent"""
        # 通过ResearchOrchestrator的_agents访问Agent
        # 由于WorkflowEngine不直接持有agents引用，我们通过context传递
        if self._context and hasattr(self._context, '_pending_feedback'):
            self._context._pending_feedback[agent_key] = feedback
        elif self._context:
            self._context._pending_feedback = {agent_key: feedback}

    def _clear_supervisor_feedback(self, agent_key: str):
        """清除监督反馈"""
        if self._context and hasattr(self._context, '_pending_feedback'):
            self._context._pending_feedback.pop(agent_key, None)

    async def _wait_for_confirmation(
        self,
        stage_key: str,
        eval_result: Any
    ) -> Optional[Dict]:
        """等待用户确认"""
        self._state = WorkflowState.WAITING_CONFIRMATION
        self._confirmation_event.clear()
        self._confirmation_result = None

        agent_key = self._stage_to_agent_key(stage_key, [])
        self._emit_log(f"阶段 {agent_key} 完成，等待确认...", "info")
        await self.events.emit_async("stage_confirmation_required", {
            "stage_key": stage_key,
            "eval_result": eval_result,
            "context": self._context
        })

        # 等待确认（使用 to_thread 避免忙轮询）
        while not self._confirmation_event.is_set():
            if self._stop_flag.is_set():
                return None
            await asyncio.to_thread(self._confirmation_event.wait, 1.0)

        self._state = WorkflowState.RUNNING
        self._emit_log(f"用户已确认 {agent_key} 阶段", "success")
        return self._confirmation_result

    def confirm_stage(
        self,
        modification: str = None,
        rollback_to: str = None
    ):
        """确认当前阶段"""
        self._confirmation_result = {
            "modification": modification,
            "rollback_to": rollback_to
        }
        self._confirmation_event.set()

    def stop(self):
        """停止工作流"""
        self._stop_flag.set()
        self._confirmation_event.set()  # 解除等待

    def _save_checkpoint(self, stage_key: str):
        """保存检查点"""
        if not self._checkpoint_dir or not self._context:
            return

        try:
            self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
            cp_file = self._checkpoint_dir / f"checkpoint_{stage_key}.json"

            if hasattr(self._context, 'save_to_file'):
                self._context.save_to_file(str(cp_file))
                self._emit_log(f"[检查点] 已保存 {cp_file.name}", "info")
        except Exception as e:
            self._emit_log(f"[检查点] 保存失败: {e}", "warning")

    def _clear_context_from(self, stages: List[str], from_index: int):
        """清除指定阶段及之后的输出"""
        if not self._context or not hasattr(self._context, 'clear_stage_outputs'):
            return

        try:
            from global_context import WorkflowStage
        except Exception:
            WorkflowStage = None

        stage_to_enum = {
            "literature": "LITERATURE_REVIEW",
            "derivation": "MATH_DERIVATION",
            "simulation": "MATLAB_SIMULATION",
            "sim_run": "MATLAB_EXECUTION",
            "dsp_code": "DSP_CODE_GEN",
            "paper": "PAPER_WRITING",
        }

        for i in range(from_index, len(stages)):
            stage_key = stages[i]
            if WorkflowStage is not None:
                enum_name = stage_to_enum.get(stage_key)
                if enum_name and hasattr(WorkflowStage, enum_name):
                    self._context.clear_stage_outputs(getattr(WorkflowStage, enum_name))
            self._emit_log(f"[回退] 已清除 {stage_key} 阶段输出", "info")

    def _emit_progress(self, progress: int, description: str):
        """发射进度事件"""
        self.events.emit("progress_updated", {
            "progress": progress,
            "description": description
        })

    def _emit_log(self, message: str, level: str = "info"):
        """发射日志事件"""
        self.events.emit("log_message", {
            "message": message,
            "level": level
        })

    # ========== 线程运行支持 ==========

    def run_in_thread(
        self,
        context: Any,
        stages: List[str],
        resume_index: int = 0
    ) -> threading.Thread:
        """
        在后台线程中运行工作流

        Args:
            context: 上下文
            stages: 阶段列表
            resume_index: 起始索引

        Returns:
            工作线程
        """
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                raise RuntimeError("工作流已在运行中，请先停止当前工作流")

        def _thread_target():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(
                    self.run(context, stages, resume_index)
                )
            finally:
                self._loop.close()

        self._worker_thread = threading.Thread(target=_thread_target, daemon=True)
        self._worker_thread.start()
        return self._worker_thread

    def wait(self, timeout: float = None):
        """等待工作线程完成"""
        if self._worker_thread:
            self._worker_thread.join(timeout)

    def is_running(self) -> bool:
        """检查是否正在运行"""
        with self._lock:
            return self._state == WorkflowState.RUNNING
