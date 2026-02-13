# -*- coding: utf-8 -*-
"""
研究标签页基类

提取 ResearchConsoleTab 和 CustomResearchTab 的公共仪表盘部分，
包括 pipeline、progress bar、log widget 和 stop/resume/open_output 按钮。
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QProgressBar,
    QSplitter, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from .widgets import LogWidget, StagePipelineWidget, style_button


class ResearchTabBase(QWidget):
    """
    研究标签页基类。

    子类只需:
      1. 覆写 ``_create_config_widget()`` 返回上半部分配置区 QWidget
      2. 覆写 ``get_research_config()`` 返回配置 dict
      3. 覆写 ``_start_research()`` 实现启动逻辑（可调用 ``_do_start(config)``）
    """

    start_research = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._workflow_completed = False
        self._workflow_running = False
        self._init_base_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_base_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 上半部分：子类配置区
        config_widget = self._create_config_widget()
        # 在配置区底部追加按钮栏
        config_layout = config_widget.layout()
        if config_layout is not None:
            config_layout.addLayout(self._create_action_buttons())
        splitter.addWidget(config_widget)

        # 下半部分：仪表盘
        splitter.addWidget(self._create_dashboard())
        splitter.setSizes([400, 300])

        main_layout.addWidget(splitter)

    def _create_config_widget(self) -> QWidget:
        """子类覆写，返回配置区 QWidget（需设置 layout）。"""
        w = QWidget()
        QVBoxLayout(w)
        return w

    def _create_dashboard(self) -> QWidget:
        dashboard = QGroupBox("状态仪表盘")
        layout = QVBoxLayout(dashboard)

        # pipeline
        self.pipeline_widget = StagePipelineWidget()
        layout.addWidget(self.pipeline_widget)

        # progress bar
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("整体进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)
        self.label_current_stage = QLabel("等待启动...")
        progress_layout.addWidget(self.label_current_stage)
        layout.addLayout(progress_layout)

        # log
        self.log_widget = LogWidget()
        self.log_widget.setMinimumHeight(200)
        layout.addWidget(self.log_widget)

        return dashboard

    def _create_action_buttons(self) -> QHBoxLayout:
        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("启动自动化研究流程")
        self.btn_start.setToolTip("根据当前配置启动完整的多Agent研究流程")
        self.btn_start.clicked.connect(self._start_research)
        style_button(self.btn_start, "primary")
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setToolTip("停止当前正在运行的研究流程")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        style_button(self.btn_stop, "danger")
        btn_layout.addWidget(self.btn_stop)

        self.btn_resume = QPushButton("从检查点恢复")
        self.btn_resume.setToolTip("选择项目目录，从上次保存的检查点继续研究")
        self.btn_resume.clicked.connect(self._resume_from_checkpoint)
        btn_layout.addWidget(self.btn_resume)

        self.btn_open_output = QPushButton("打开输出目录")
        self.btn_open_output.setToolTip("打开研究输出文件所在的目录")
        self.btn_open_output.clicked.connect(self._open_output_dir)
        self.btn_open_output.setEnabled(False)
        btn_layout.addWidget(self.btn_open_output)

        btn_layout.addStretch()
        return btn_layout

    # ------------------------------------------------------------------
    # Shared slots / helpers
    # ------------------------------------------------------------------

    def _start_research(self) -> None:
        """子类覆写。"""
        pass

    def _do_start(self, config: dict) -> None:
        """公共启动逻辑——子类在 _start_research 中调用。"""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self._workflow_completed = False
        self._workflow_running = True
        # 重置仪表盘
        self.pipeline_widget.reset()
        self.progress_bar.setValue(0)
        self.label_current_stage.setText("初始化Agent...")
        self.start_research.emit(config)

    def _on_stop_clicked(self) -> None:
        """停止按钮增加确认对话框"""
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止当前研究流程吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._stop_research()

    def _stop_research(self) -> None:
        self.log_widget.log("用户请求停止研究流程", "warning")
        self._workflow_running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_resume.setEnabled(True)
        self.label_current_stage.setText("已停止")

    def _resume_from_checkpoint(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择项目目录（包含checkpoints文件夹）"
        )
        if not dir_path:
            return
        path = Path(dir_path)
        cp_dir = path / "checkpoints"
        if not cp_dir.exists():
            QMessageBox.warning(
                self, "错误",
                "所选目录中未找到checkpoints文件夹，请选择正确的项目目录。"
            )
            return
        self.log_widget.log(f"从检查点恢复: {path}", "agent")
        self._workflow_running = True
        self._workflow_completed = False
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_resume.setEnabled(False)
        self.pipeline_widget.reset()
        self.progress_bar.setValue(0)
        self.label_current_stage.setText("从检查点恢复中...")
        self.start_research.emit({"_resume_from": str(path)})

    def set_workflow_completed(self) -> None:
        """显式标记流程完成，启用打开输出目录按钮。"""
        self._workflow_completed = True
        self._workflow_running = False
        self.btn_open_output.setEnabled(True)
        self.btn_resume.setEnabled(True)

    def update_progress(self, progress: int, stage: str) -> None:
        self.progress_bar.setValue(progress)
        self.label_current_stage.setText(stage)
        self.pipeline_widget.update_from_progress(progress)

    def add_log(self, message: str, level: str = "info") -> None:
        self.log_widget.log(message, level)
        # 保留向后兼容：字符串匹配也触发
        if "已完成" in message and level == "success":
            self.set_workflow_completed()

    def _open_output_dir(self) -> None:
        output_path = Path("./output")
        if not output_path.exists():
            QMessageBox.information(self, "提示", "输出目录尚未创建")
            return
        resolved = str(output_path.resolve())
        try:
            if sys.platform == "win32":
                os.startfile(resolved)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", resolved])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", resolved])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开目录: {e}")
