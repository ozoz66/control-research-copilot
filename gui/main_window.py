# -*- coding: utf-8 -*-
"""
主窗口模块

AutoControl-Scientist 的主界面窗口。
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config_manager import get_config_manager
from core.qt_adapter import QtOrchestratorAdapter as Orchestrator
from agents import (
    ArchitectAgent, TheoristAgent, EngineerAgent, SimulatorAgent,
    DSPCoderAgent, ScribeAgent, SupervisorAgent
)
from .api_config_tab import ApiConfigTab
from .research_console_tab import ResearchConsoleTab
from .custom_research_tab import CustomResearchTab
from .dashboard_tab import DashboardTab
from .dialogs import StageConfirmationDialog, TopicConfirmationDialog


class MainWindow(QMainWindow):
    """
    AutoControl-Scientist 主窗口
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoControl-Scientist - 控制系统研究自动化平台")
        self.setMinimumSize(1000, 700)

        # 初始化 Orchestrator
        self.orchestrator = Orchestrator()
        self._register_agents()

        self._active_tab = None
        self._init_ui()
        self._connect_signals()

    def _register_agents(self) -> None:
        """注册所有 Agent，从配置中读取 API 设置"""
        config_manager = get_config_manager()

        architect_config = config_manager.find_fallback_config()

        # 注册 Agent，传入配置
        architect_agent = ArchitectAgent()
        architect_agent.api_config = architect_config
        self.orchestrator.register_agent("architect", architect_agent)

        theorist_agent = TheoristAgent()
        theorist_agent.api_config = config_manager.get_agent_by_type("theorist") or architect_config
        self.orchestrator.register_agent("theorist", theorist_agent)

        matlab_path = config_manager.settings.matlab_path or None

        engineer_agent = EngineerAgent(matlab_path=matlab_path)
        engineer_agent.api_config = config_manager.get_agent_by_type("engineer") or architect_config
        self.orchestrator.register_agent("engineer", engineer_agent)

        simulator_config = (
            config_manager.get_agent_by_type("simulator")
            or config_manager.get_agent_by_type("engineer")
            or architect_config
        )
        simulator_agent = SimulatorAgent(matlab_path=matlab_path)
        simulator_agent.api_config = simulator_config
        self.orchestrator.register_agent("simulator", simulator_agent)

        dsp_coder_agent = DSPCoderAgent()
        dsp_coder_agent.api_config = config_manager.get_agent_by_type("dsp_coder") or architect_config
        self.orchestrator.register_agent("dsp_coder", dsp_coder_agent)

        scribe_agent = ScribeAgent()
        scribe_agent.api_config = config_manager.get_agent_by_type("scribe") or architect_config
        self.orchestrator.register_agent("scribe", scribe_agent)

        supervisor = SupervisorAgent()
        supervisor.api_config = config_manager.get_agent_by_type("supervisor") or architect_config
        self.orchestrator.set_supervisor(supervisor)

        # 注入supervisor到scribe，用于逐节评审
        scribe_agent.supervisor = supervisor

    def _init_ui(self) -> None:
        """初始化主界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # 紧凑 header：标题 + 副标题同行
        header_layout = QHBoxLayout()
        title_label = QLabel("AutoControl-Scientist")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title_label)

        subtitle_label = QLabel("— 多Agent协作的控制系统研究自动化平台")
        subtitle_label.setStyleSheet("color: #888; font-size: 12px; margin-left: 4px;")
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Tab 页（带 unicode 图标）
        self.tab_widget = QTabWidget()

        self.api_tab = ApiConfigTab()
        self.tab_widget.addTab(self.api_tab, "\u2699 API与模型配置")  # ⚙

        self.research_tab = ResearchConsoleTab()
        self.tab_widget.addTab(self.research_tab, "\u25B6 研究控制台")  # ▶

        self.custom_research_tab = CustomResearchTab()
        self.tab_widget.addTab(self.custom_research_tab, "\u270E 自定义研究方向")  # ✎

        self.dashboard_tab = DashboardTab()
        self.tab_widget.addTab(self.dashboard_tab, "\u2630 Dashboard")  # ☰

        main_layout.addWidget(self.tab_widget)

        # 状态栏
        self.statusBar().showMessage("就绪")

    def _connect_signals(self) -> None:
        """连接信号槽"""
        self.research_tab.start_research.connect(
            lambda config: self._start_workflow(config, self.research_tab)
        )
        self.custom_research_tab.start_research.connect(
            lambda config: self._start_workflow(config, self.custom_research_tab)
        )
        self.api_tab.config_changed.connect(self._on_config_changed)

    def _disconnect_orchestrator_signals(self) -> None:
        """断开 Orchestrator 信号（避免重复连接）"""
        for sig in (
            self.orchestrator.log_message,
            self.orchestrator.progress_updated,
            self.orchestrator.workflow_completed,
            self.orchestrator.workflow_error,
            self.orchestrator.topic_confirmation_required,
            self.orchestrator.stage_confirmation_required,
        ):
            try:
                sig.disconnect()
            except (TypeError, RuntimeError):
                pass

    def _start_workflow(self, config: dict, tab) -> None:
        """启动研究工作流（通用，tab 为研究控制台或自定义研究 Tab）"""
        self._active_tab = tab
        self.statusBar().showMessage("研究流程运行中...")
        tab.add_log("配置解析完成", "success")

        self._disconnect_orchestrator_signals()

        self.orchestrator.log_message.connect(
            lambda msg, level: self._active_tab.add_log(msg, level)
        )
        self.orchestrator.progress_updated.connect(self._on_progress_updated)
        self.orchestrator.workflow_completed.connect(self._on_workflow_completed)
        self.orchestrator.workflow_error.connect(self._on_workflow_error)
        self.orchestrator.topic_confirmation_required.connect(self._on_topic_confirmation)
        self.orchestrator.stage_confirmation_required.connect(self._on_stage_confirmation)

        resume_from = config.pop("_resume_from", None)
        self.orchestrator.start_workflow(config, resume_from=resume_from)

    def _on_progress_updated(self, progress: int, description: str) -> None:
        if self._active_tab is None:
            return
        self._active_tab.update_progress(progress, description)
        self.statusBar().showMessage(f"{description} ({progress}%)")

    def _on_workflow_completed(self, context) -> None:
        self.statusBar().showMessage("研究流程已完成")
        if self._active_tab is None:
            return
        # add_log with "已完成" + "success" already triggers set_workflow_completed()
        self._active_tab.add_log("研究流程已完成!", "success")
        self._active_tab.btn_start.setEnabled(True)
        self._active_tab.btn_stop.setEnabled(False)

    def _on_workflow_error(self, error_msg: str) -> None:
        self.statusBar().showMessage("研究流程出错")
        if self._active_tab is None:
            return
        self._active_tab.add_log(f"错误: {error_msg}", "error")
        self._active_tab._workflow_running = False
        self._active_tab.btn_start.setEnabled(True)
        self._active_tab.btn_stop.setEnabled(False)
        self._active_tab.btn_resume.setEnabled(True)

    def _on_topic_confirmation(self, context) -> None:
        if self._active_tab is None:
            return
        self.statusBar().showMessage("等待用户确认课题...")
        dialog = TopicConfirmationDialog(context, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_context = dialog.get_updated_context()
            self._active_tab.add_log("用户已确认课题", "success")
            self.orchestrator.confirm_topic(updated_context)
        else:
            self._active_tab.add_log("用户取消了研究流程", "warning")
            self.orchestrator.stop_workflow()
            self.statusBar().showMessage("研究流程已取消")
            self._active_tab.btn_start.setEnabled(True)
            self._active_tab.btn_stop.setEnabled(False)

    def _on_config_changed(self) -> None:
        self._register_agents()
        self.statusBar().showMessage("配置已更新，Agent已重新注册", 3000)

    def _on_stage_confirmation(
        self, stage_name: str, eval_result: Optional[object], context
    ) -> None:
        if self._active_tab is None:
            return
        self.statusBar().showMessage(f"等待用户确认 {stage_name} 阶段结果...")
        dialog = StageConfirmationDialog(stage_name, eval_result, context, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.rollback_to:
                self._active_tab.add_log(
                    f"用户要求回退到: {dialog.rollback_to}", "warning"
                )
                self.orchestrator.confirm_stage(rollback_to=dialog.rollback_to)
            elif dialog.modification:
                self._active_tab.add_log(
                    f"用户要求修改: {dialog.modification}", "warning"
                )
                self.orchestrator.confirm_stage(dialog.modification)
            else:
                self._active_tab.add_log(
                    f"用户已确认 {stage_name} 阶段", "success"
                )
                self.orchestrator.confirm_stage()
        else:
            self._active_tab.add_log("用户取消了研究流程", "warning")
            self.orchestrator.stop_workflow()
            self.statusBar().showMessage("研究流程已取消")
            self._active_tab.btn_start.setEnabled(True)
            self._active_tab.btn_stop.setEnabled(False)
