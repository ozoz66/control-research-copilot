# -*- coding: utf-8 -*-
"""
研究控制器 - GUI 与核心逻辑的桥接层

消除 gui_main.py 中 ResearchConsoleTab 和 CustomResearchTab 的重复代码。
统一处理两个 Tab 的信号连接和事件处理。
"""

from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .events import EventEmitter


@dataclass
class UICallbacks:
    """UI 回调函数集合"""
    add_log: Callable[[str, str], None]  # (message, level)
    update_progress: Callable[[int, str], None]  # (progress, description)
    set_buttons_running: Callable[[], None]  # 设置按钮为运行状态
    set_buttons_stopped: Callable[[], None]  # 设置按钮为停止状态
    show_topic_dialog: Callable[[Any], Optional[Any]]  # 显示课题确认对话框
    show_stage_dialog: Callable[[str, Any, Any], Optional[Dict]]  # 显示阶段确认对话框
    update_status_bar: Callable[[str], None]  # 更新状态栏


class ResearchController:
    """
    研究控制器 - 统一处理研究流程的 UI 交互

    用法:
        controller = ResearchController(orchestrator)

        # 绑定 UI 回调
        controller.bind_ui(UICallbacks(
            add_log=tab.add_log,
            update_progress=tab.update_progress,
            ...
        ))

        # 启动研究
        controller.start_research(config)

        # 停止
        controller.stop_research()
    """

    def __init__(self, orchestrator):
        """
        Args:
            orchestrator: ResearchOrchestrator 或兼容的编排器实例
        """
        self.orchestrator = orchestrator
        self._ui: Optional[UICallbacks] = None
        self._connected = False

    def bind_ui(self, ui: UICallbacks) -> 'ResearchController':
        """绑定 UI 回调"""
        self._ui = ui
        return self

    def start_research(self, config: Dict[str, Any]):
        """启动研究流程"""
        if not self._ui:
            raise RuntimeError("未绑定 UI 回调")

        self._ui.add_log("配置解析完成", "success")
        self._ui.set_buttons_running()
        self._ui.update_status_bar("研究流程运行中...")

        # 连接事件
        self._connect_events()

        # 启动工作流
        resume_from = config.pop("_resume_from", None)
        self.orchestrator.start_workflow(config, resume_from=resume_from)

    def stop_research(self):
        """停止研究流程"""
        if self._ui:
            self._ui.add_log("用户请求停止研究流程", "warning")
            self._ui.set_buttons_stopped()
            self._ui.update_status_bar("已停止")

        self.orchestrator.stop_workflow()

    def confirm_stage(self, modification: str = None, rollback_to: str = None):
        """确认当前阶段"""
        self.orchestrator.confirm_stage(modification, rollback_to)

    def confirm_topic(self, updated_context=None):
        """确认课题"""
        self.orchestrator.confirm_topic(updated_context)

    def _connect_events(self):
        """连接编排器事件到 UI"""
        if self._connected:
            self._disconnect_events()

        events = self.orchestrator.events

        events.on("log_message", self._on_log_message)
        events.on("progress_updated", self._on_progress_updated)
        events.on("workflow_completed", self._on_workflow_completed)
        events.on("workflow_error", self._on_workflow_error)
        events.on("stage_confirmation_required", self._on_stage_confirmation)

        self._connected = True

    def _disconnect_events(self):
        """断开事件连接"""
        if not self._connected:
            return

        events = self.orchestrator.events
        events.off("log_message", self._on_log_message)
        events.off("progress_updated", self._on_progress_updated)
        events.off("workflow_completed", self._on_workflow_completed)
        events.off("workflow_error", self._on_workflow_error)
        events.off("stage_confirmation_required", self._on_stage_confirmation)

        self._connected = False

    def _on_log_message(self, event):
        """处理日志消息"""
        if self._ui:
            data = event.data
            self._ui.add_log(data.get("message", ""), data.get("level", "info"))

    def _on_progress_updated(self, event):
        """处理进度更新"""
        if self._ui:
            data = event.data
            progress = data.get("progress", 0)
            description = data.get("description", "")
            self._ui.update_progress(progress, description)
            self._ui.update_status_bar(f"{description} ({progress}%)")

    def _on_workflow_completed(self, event):
        """处理工作流完成"""
        if self._ui:
            self._ui.update_status_bar("研究流程已完成")
            self._ui.add_log("研究流程已完成!", "success")
            self._ui.set_buttons_stopped()

    def _on_workflow_error(self, event):
        """处理工作流错误"""
        if self._ui:
            error_msg = event.data if isinstance(event.data, str) else str(event.data)
            self._ui.update_status_bar("研究流程出错")
            self._ui.add_log(f"错误: {error_msg}", "error")
            self._ui.set_buttons_stopped()

    def _on_stage_confirmation(self, event):
        """处理阶段确认请求"""
        if not self._ui:
            return

        data = event.data
        stage_key = data.get("stage_key", "")
        eval_result = data.get("eval_result")
        context = data.get("context")

        self._ui.update_status_bar(f"等待用户确认 {stage_key} 阶段结果...")

        # 调用 UI 显示对话框
        result = self._ui.show_stage_dialog(stage_key, eval_result, context)

        if result is None:
            # 用户取消
            self._ui.add_log("用户取消了研究流程", "warning")
            self.orchestrator.stop_workflow()
            self._ui.update_status_bar("研究流程已取消")
            self._ui.set_buttons_stopped()
        elif result.get("rollback_to"):
            self._ui.add_log(f"用户要求回退到: {result['rollback_to']}", "warning")
            self.confirm_stage(rollback_to=result["rollback_to"])
        elif result.get("modification"):
            self._ui.add_log(f"用户要求修改: {result['modification']}", "warning")
            self.confirm_stage(modification=result["modification"])
        else:
            self._ui.add_log(f"用户已确认 {stage_key} 阶段", "success")
            self.confirm_stage()
