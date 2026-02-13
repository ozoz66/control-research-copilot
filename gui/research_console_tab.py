# -*- coding: utf-8 -*-
"""
研究控制台标签页模块

实现三层级控制策略选择器。
"""

from typing import Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QPushButton, QGridLayout,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from .constants import (
    MAIN_ALGORITHMS, PERFORMANCE_OBJECTIVES,
    FEEDBACK_CONTROLLERS, FEEDFORWARD_CONTROLLERS, OBSERVERS,
    APPLICATION_SCENARIOS
)
from .widgets import style_button
from .research_tab_base import ResearchTabBase


class ResearchConsoleTab(ResearchTabBase):
    """
    Tab 2: 研究控制台
    实现三层级控制策略选择器
    """

    # 重新声明信号（PyQt 要求每个类自己声明）
    start_research = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    # ------------------------------------------------------------------
    # 配置区（覆写基类）
    # ------------------------------------------------------------------

    def _create_config_widget(self) -> QWidget:
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(0, 0, 0, 0)

        # Section A: 主算法域
        section_a = QGroupBox("Section A: 主算法域 (核心研究方向)")
        section_a_layout = QHBoxLayout(section_a)
        section_a_layout.addWidget(QLabel("选择主要研究领域:"))
        self.combo_main_algo = QComboBox()
        for key, value in MAIN_ALGORITHMS.items():
            self.combo_main_algo.addItem(value, key)
        self.combo_main_algo.setMinimumWidth(300)
        section_a_layout.addWidget(self.combo_main_algo)
        section_a_layout.addStretch()
        config_layout.addWidget(section_a)

        # Section B: 性能目标 — 用 QGridLayout 每行 4 个
        section_b = QGroupBox("Section B: 性能目标 (研究目标)")
        grid = QGridLayout(section_b)
        self.performance_checks: Dict[str, QCheckBox] = {}
        for i, (key, value) in enumerate(PERFORMANCE_OBJECTIVES.items()):
            checkbox = QCheckBox(value)
            self.performance_checks[key] = checkbox
            grid.addWidget(checkbox, i // 4, i % 4)
        config_layout.addWidget(section_b)

        # Section C: 复合架构 — 2 列 grid (label + combo)
        section_c = QGroupBox("Section C: 复合架构 (控制器结构设计)")
        c_grid = QGridLayout(section_c)

        c_grid.addWidget(QLabel("反馈控制器:"), 0, 0)
        self.combo_feedback = QComboBox()
        for key, value in FEEDBACK_CONTROLLERS.items():
            self.combo_feedback.addItem(value, key)
        c_grid.addWidget(self.combo_feedback, 0, 1)

        c_grid.addWidget(QLabel("前馈控制器:"), 1, 0)
        self.combo_feedforward = QComboBox()
        for key, value in FEEDFORWARD_CONTROLLERS.items():
            self.combo_feedforward.addItem(value, key)
        c_grid.addWidget(self.combo_feedforward, 1, 1)

        c_grid.addWidget(QLabel("观测器:"), 0, 2)
        self.combo_observer = QComboBox()
        for key, value in OBSERVERS.items():
            self.combo_observer.addItem(value, key)
        c_grid.addWidget(self.combo_observer, 0, 3)

        tip_label = QLabel("提示: 系统将综合以上三个部分的选择生成研究课题。")
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: #FFFFFF; font-size: 13px; padding: 5px;")
        c_grid.addWidget(tip_label, 2, 0, 1, 4)

        config_layout.addWidget(section_c)

        # Section D: 应用场景
        section_d = QGroupBox("Section D: 应用场景 (目标系统)")
        section_d_layout = QHBoxLayout(section_d)
        section_d_layout.addWidget(QLabel("选择应用场景:"))
        self.combo_application = QComboBox()
        for key, value in APPLICATION_SCENARIOS.items():
            self.combo_application.addItem(value, key)
        self.combo_application.setMinimumWidth(300)
        section_d_layout.addWidget(self.combo_application)
        section_d_layout.addStretch()
        config_layout.addWidget(section_d)

        # 预览按钮（在 action buttons 之前）
        preview_layout = QHBoxLayout()
        self.btn_preview = QPushButton("预览研究课题")
        self.btn_preview.setToolTip("预览根据当前配置生成的研究课题描述")
        self.btn_preview.clicked.connect(self._preview_topic)
        preview_layout.addWidget(self.btn_preview)
        preview_layout.addStretch()
        config_layout.addLayout(preview_layout)

        return config_widget

    # ------------------------------------------------------------------
    # 业务逻辑
    # ------------------------------------------------------------------

    def get_research_config(self) -> dict:
        config = {
            "custom_topic": "",
            "main_algorithm": {
                "key": self.combo_main_algo.currentData(),
                "name": self.combo_main_algo.currentText()
            },
            "performance_objectives": [
                {"key": key, "name": cb.text()}
                for key, cb in self.performance_checks.items()
                if cb.isChecked()
            ],
            "composite_architecture": {
                "feedback": {
                    "key": self.combo_feedback.currentData(),
                    "name": self.combo_feedback.currentText()
                },
                "feedforward": {
                    "key": self.combo_feedforward.currentData(),
                    "name": self.combo_feedforward.currentText()
                },
                "observer": {
                    "key": self.combo_observer.currentData(),
                    "name": self.combo_observer.currentText()
                }
            },
            "application_scenario": {
                "key": self.combo_application.currentData(),
                "name": self.combo_application.currentText()
            }
        }
        return config

    def _preview_topic(self) -> None:
        config = self.get_research_config()
        main_algo = config["main_algorithm"]["name"]
        objectives = [obj["name"] for obj in config["performance_objectives"]]
        feedback = config["composite_architecture"]["feedback"]["name"]
        feedforward = config["composite_architecture"]["feedforward"]["name"]
        observer = config["composite_architecture"]["observer"]["name"]

        topic_parts = [main_algo]
        if feedback != "无 (None)":
            topic_parts.append(f"结合{feedback}")
        if feedforward != "无 (None)":
            topic_parts.append(f"采用{feedforward}前馈")
        if observer != "无 (None)":
            topic_parts.append(f"基于{observer}")
        if objectives:
            topic_parts.append(f"实现{', '.join(objectives)}")
        topic = " ".join(topic_parts)

        preview_msg = f"""
研究课题预览
{'='*50}

【主算法】{main_algo}
【性能目标】{', '.join(objectives) if objectives else '未选择'}
【反馈控制】{feedback}
【前馈控制】{feedforward}
【观测器】{observer}

【综合课题】
{topic}

{'='*50}
Agent将基于以上配置进行文献检索、数学推导、MATLAB仿真和论文撰写。
        """
        QMessageBox.information(self, "研究课题预览", preview_msg)

    def _start_research(self) -> None:
        config = self.get_research_config()

        warnings = []
        if not config["performance_objectives"]:
            warnings.append("未选择性能目标")
        fb = config.get("composite_architecture", {}).get("feedback", {})
        if fb.get("key") == "none":
            warnings.append("未选择反馈控制器")
        obs = config.get("composite_architecture", {}).get("observer", {})
        if obs.get("key") == "none":
            warnings.append("未选择观测器")

        if warnings:
            msg = "以下配置项未设置，可能影响生成质量：\n\n" + "\n".join(
                f"  - {w}" for w in warnings
            ) + "\n\n是否仍然继续？"
            reply = QMessageBox.question(
                self, "配置确认", msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.log_widget.log("研究流程启动中...", "agent")
        self.log_widget.log(f"主算法: {config['main_algorithm']['name']}", "info")
        self._do_start(config)
