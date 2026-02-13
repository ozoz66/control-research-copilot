# -*- coding: utf-8 -*-
"""
自定义研究方向标签页模块

用户输入研究方向，AI 自动搜索文献并提出课题。
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .widgets import style_button
from .research_tab_base import ResearchTabBase


class CustomResearchTab(ResearchTabBase):
    """
    Tab 3: 自定义研究方向
    用户输入研究方向，AI 自动搜索文献并提出课题
    """

    start_research = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    # ------------------------------------------------------------------
    # 配置区（覆写基类）
    # ------------------------------------------------------------------

    def _create_config_widget(self) -> QWidget:
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)

        direction_group = QGroupBox("输入您的研究方向")
        direction_layout = QVBoxLayout(direction_group)

        hint_label = QLabel(
            "请输入您想研究的方向或领域，AI 将自动搜索近期文献，"
            "分析研究现状，并为您提出具体的研究课题和创新点。"
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #FFFFFF; font-size: 13px; padding: 5px;")
        direction_layout.addWidget(hint_label)

        self.edit_research_direction = QTextEdit()
        self.edit_research_direction.setPlaceholderText(
            "例如：\n"
            "- 基于深度强化学习的机械臂轨迹跟踪控制\n"
            "- 电动汽车电池管理系统的故障诊断方法\n"
            "- 多无人机协同编队控制策略"
        )
        self.edit_research_direction.setMinimumHeight(120)
        self.edit_research_direction.textChanged.connect(self._on_text_changed)
        direction_layout.addWidget(self.edit_research_direction)

        self.label_char_count = QLabel("0 / 500 字")
        self.label_char_count.setStyleSheet("color: #858585; font-size: 11px;")
        self.label_char_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        direction_layout.addWidget(self.label_char_count)

        input_layout.addWidget(direction_group)
        return input_widget

    # ------------------------------------------------------------------
    # 覆写基类按钮：启动按钮文字和初始状态不同
    # ------------------------------------------------------------------

    def _init_base_ui(self) -> None:
        super()._init_base_ui()
        # 调整启动按钮文字
        self.btn_start.setText("开始AI文献分析与课题生成")
        self.btn_start.setEnabled(False)  # 需要输入内容后才启用

    # ------------------------------------------------------------------
    # 业务逻辑
    # ------------------------------------------------------------------

    def _on_text_changed(self) -> None:
        text = self.edit_research_direction.toPlainText()
        char_count = len(text.strip())
        self.label_char_count.setText(f"{char_count} / 500 字")
        if char_count > 500:
            self.label_char_count.setStyleSheet("color: #f14c4c; font-size: 11px;")
        elif char_count > 0:
            self.label_char_count.setStyleSheet("color: #4ec9b0; font-size: 11px;")
        else:
            self.label_char_count.setStyleSheet("color: #858585; font-size: 11px;")
        # 仅在未运行时允许启用启动按钮
        if not self._workflow_running:
            self.btn_start.setEnabled(char_count > 0)

    def get_research_config(self) -> dict:
        custom_topic = self.edit_research_direction.toPlainText().strip()
        return {"custom_topic": custom_topic}

    def _start_research(self) -> None:
        config = self.get_research_config()
        if not config["custom_topic"]:
            QMessageBox.warning(self, "提示", "请输入您想研究的方向")
            return

        self.log_widget.log("研究流程启动中...", "agent")
        self.log_widget.log(f"研究方向: {config['custom_topic'][:50]}...", "info")
        self._do_start(config)
