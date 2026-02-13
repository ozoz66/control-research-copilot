# -*- coding: utf-8 -*-
"""
GUI 可复用组件模块

包含可复用的 PyQt6 组件。
"""

import datetime
import html as _html
from typing import Optional
from PyQt6.QtWidgets import (
    QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from .constants import LOG_COLORS, THEME_STYLES


# ---------------------------------------------------------------------------
# 按钮样式工具函数
# ---------------------------------------------------------------------------

_BUTTON_STYLES = {
    "primary": {
        "bg": "#0078d4", "hover": "#106ebe", "pressed": "#005a9e", "text": "#ffffff",
    },
    "success": {
        "bg": "#4CAF50", "hover": "#43A047", "pressed": "#388E3C", "text": "#ffffff",
    },
    "danger": {
        "bg": "#f44336", "hover": "#e53935", "pressed": "#c62828", "text": "#ffffff",
    },
    "warning": {
        "bg": "#FF9800", "hover": "#FB8C00", "pressed": "#E65100", "text": "#ffffff",
    },
}


def style_button(btn: QPushButton, role: str) -> None:
    """
    为按钮应用统一的角色样式。

    Args:
        btn: 目标按钮
        role: 'primary' | 'success' | 'danger' | 'warning'
    """
    s = _BUTTON_STYLES.get(role)
    if s is None:
        return
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {s['bg']};
            color: {s['text']};
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {s['hover']};
        }}
        QPushButton:pressed {{
            background-color: {s['pressed']};
        }}
        QPushButton:disabled {{
            background-color: #555;
            color: #999;
        }}
    """)


# ---------------------------------------------------------------------------
# LogWidget
# ---------------------------------------------------------------------------

class LogWidget(QTextEdit):
    """
    实时日志显示控件
    支持不同级别的日志着色
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面"""
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))

        # 使用主题样式
        theme = THEME_STYLES["dark"]
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme['background']};
                color: {theme['text']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
            }}
        """)

    def log(self, message: str, level: str = "info") -> None:
        """
        添加日志消息

        Args:
            message: 日志内容
            level: 日志级别 (info, success, warning, error, agent)
        """
        color = LOG_COLORS.get(level, LOG_COLORS["info"])

        # 格式化消息（HTML-escape 防止渲染异常）
        safe_message = _html.escape(message)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f'<span style="color: #858585;">[{timestamp}]</span> '
        formatted_msg += f'<span style="color: {color};">{safe_message}</span>'

        self.append(formatted_msg)
        # 自动滚动到底部
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


# ---------------------------------------------------------------------------
# StagePipelineWidget
# ---------------------------------------------------------------------------

class StagePipelineWidget(QWidget):
    """
    可视化阶段流水线指示器
    显示各Agent执行阶段的完成状态
    """

    STAGES = [
        ("architect", "文献检索", 20),
        ("theorist", "数学推导", 40),
        ("engineer", "MATLAB仿真", 60),
        ("dsp_coder", "DSP代码", 75),
        ("scribe", "论文撰写", 95),
    ]

    # 状态颜色
    COLOR_PENDING = "#555"
    COLOR_ACTIVE = "#0078d4"
    COLOR_DONE = "#4ec9b0"
    COLOR_ERROR = "#f14c4c"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stage_states = {key: "pending" for key, _, _ in self.STAGES}
        self._labels = {}
        self._dots = {}
        self._lines: dict[str, QLabel] = {}  # key → line label (line *after* that stage)
        self._blink_timer: Optional[QTimer] = None
        self._blink_visible = True
        self._init_ui()
        self.destroyed.connect(self.cleanup)

    def cleanup(self):
        """Stop blink timer. Call before destruction or connect to destroyed signal."""
        if self._blink_timer is not None:
            self._blink_timer.stop()
            self._blink_timer = None

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        for i, (key, name, _) in enumerate(self.STAGES):
            if i > 0:
                # 连接线 — 存储引用以便着色
                line = QLabel("───")
                line.setStyleSheet("color: #555; font-size: 10px;")
                line.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(line)
                # 以前一阶段的 key 存储
                prev_key = self.STAGES[i - 1][0]
                self._lines[prev_key] = line

            # 阶段指示
            stage_widget = QWidget()
            stage_layout = QVBoxLayout(stage_widget)
            stage_layout.setContentsMargins(0, 0, 0, 0)
            stage_layout.setSpacing(2)

            dot = QLabel("●")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setStyleSheet(f"color: {self.COLOR_PENDING}; font-size: 16px;")
            stage_layout.addWidget(dot)

            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #999; font-size: 11px;")
            stage_layout.addWidget(label)

            layout.addWidget(stage_widget)
            self._dots[key] = dot
            self._labels[key] = label

    def set_stage_state(self, key: str, state: str):
        """设置阶段状态: pending, active, done, error"""
        if key not in self._dots:
            return
        self._stage_states[key] = state
        color_map = {
            "pending": self.COLOR_PENDING,
            "active": self.COLOR_ACTIVE,
            "done": self.COLOR_DONE,
            "error": self.COLOR_ERROR,
        }
        color = color_map.get(state, self.COLOR_PENDING)
        symbol = {"pending": "○", "active": "◉", "done": "●", "error": "✖"}.get(state, "○")
        self._dots[key].setStyleSheet(f"color: {color}; font-size: 16px;")
        self._dots[key].setText(symbol)
        label_color = "#d4d4d4" if state in ("active", "done") else "#999"
        font_weight = "bold" if state == "active" else "normal"
        self._labels[key].setStyleSheet(
            f"color: {label_color}; font-size: 11px; font-weight: {font_weight};"
        )

        # 连接线着色：根据前一阶段状态
        if key in self._lines:
            line_color = {
                "done": self.COLOR_DONE,
                "active": self.COLOR_ACTIVE,
            }.get(state, "#555")
            self._lines[key].setStyleSheet(f"color: {line_color}; font-size: 10px;")

        # 管理脉冲动画
        self._update_blink_timer()

    def _update_blink_timer(self):
        """如果有 active 阶段则启动闪烁 timer，否则停止。"""
        has_active = any(s == "active" for s in self._stage_states.values())
        if has_active and self._blink_timer is None:
            self._blink_timer = QTimer(self)
            self._blink_timer.timeout.connect(self._blink_tick)
            self._blink_timer.start(600)
        elif not has_active and self._blink_timer is not None:
            self._blink_timer.stop()
            self._blink_timer = None
            self._blink_visible = True
            # 确保所有 dot 可见
            for k, s in self._stage_states.items():
                if k in self._dots:
                    color_map = {
                        "pending": self.COLOR_PENDING, "active": self.COLOR_ACTIVE,
                        "done": self.COLOR_DONE, "error": self.COLOR_ERROR,
                    }
                    self._dots[k].setStyleSheet(
                        f"color: {color_map.get(s, self.COLOR_PENDING)}; font-size: 16px;"
                    )

    def _blink_tick(self):
        self._blink_visible = not self._blink_visible
        for key, state in self._stage_states.items():
            if state == "active" and key in self._dots:
                color = self.COLOR_ACTIVE if self._blink_visible else "#1a3a5c"
                self._dots[key].setStyleSheet(f"color: {color}; font-size: 16px;")

    def update_from_progress(self, progress: int):
        """根据进度百分比自动更新各阶段状态"""
        for key, _, threshold in self.STAGES:
            if progress >= threshold:
                self.set_stage_state(key, "done")
            elif progress >= threshold - 19:
                self.set_stage_state(key, "active")
            else:
                self.set_stage_state(key, "pending")

    def reset(self):
        """重置所有阶段"""
        for key, _, _ in self.STAGES:
            self.set_stage_state(key, "pending")


def make_selectable(label: QLabel) -> None:
    """
    使 QLabel 文字可选中复制

    Args:
        label: 要设置的 QLabel 对象
    """
    label.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard
    )
