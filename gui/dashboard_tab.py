# -*- coding: utf-8 -*-
"""
Dashboard 主 Tab - KPI 概览行 + 2x2 卡片布局

┌──────────────────────────────────────────────────────┐
│  [LLM Calls]  [Total Tokens]  [Agents]  [Avg Time]  [Status] │  ← KPI 行
├──────────────────────────┬───────────────────────────┤
│  ▎ Token Usage           │  ▎ Score Trend            │  ← 卡片
├──────────────────────────┼───────────────────────────┤
│  ▎ Execution Timeline    │  ▎ Workflow DAG           │
└──────────────────────────┴───────────────────────────┘

QTimer 每 2 秒自动刷新。
"""

from typing import Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, QTimer

from .dashboard_charts import TokenUsageChart, ScoreTrendChart
from .dashboard_timeline import ExecutionTimelineWidget
from .dashboard_dag import DAGWidget
from .constants import THEME_STYLES

from core.agent_history import get_agent_history

_THEME = THEME_STYLES["dark"]
_CARD_BG = "#252525"
_CARD_BORDER = _THEME["border"]       # #3c3c3c
_ACCENT = _THEME["button_primary"]    # #0078d4
_TEXT = _THEME["text"]                # #d4d4d4
_TEXT_DIM = "#888888"
_KPI_ACCENT = "#0078d4"


# -----------------------------------------------------------------------
# Helper: 深色卡片容器
# -----------------------------------------------------------------------

def _wrap_card(title: str, widget: QWidget) -> QFrame:
    """
    将 widget 包裹在深色卡片容器中。

    卡片: #252525 背景, 6px 圆角, 1px 边框.
    顶部: 3px 竖线(accent) + 标题文字.
    """
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame#dashCard {{
            background-color: {_CARD_BG};
            border: 1px solid {_CARD_BORDER};
            border-radius: 6px;
        }}
    """)
    card.setObjectName("dashCard")

    layout = QVBoxLayout(card)
    layout.setContentsMargins(10, 8, 10, 8)
    layout.setSpacing(4)

    # 标题行
    title_row = QHBoxLayout()
    title_row.setContentsMargins(0, 0, 0, 0)
    title_row.setSpacing(6)

    accent_bar = QLabel()
    accent_bar.setFixedSize(3, 14)
    accent_bar.setStyleSheet(f"background-color: {_ACCENT}; border: none; border-radius: 1px;")
    title_row.addWidget(accent_bar)

    title_label = QLabel(title)
    title_label.setStyleSheet(
        f"color: {_TEXT}; font-size: 11px; font-weight: bold; border: none; background: transparent;"
    )
    title_row.addWidget(title_label)
    title_row.addStretch()
    layout.addLayout(title_row)

    layout.addWidget(widget, stretch=1)
    return card


# -----------------------------------------------------------------------
# KPI 单项卡片
# -----------------------------------------------------------------------

class _KPICard(QFrame):
    """单个 KPI 指标卡片"""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setStyleSheet(f"""
            QFrame#kpiCard {{
                background-color: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-radius: 6px;
                border-top: 2px solid {_KPI_ACCENT};
            }}
        """)
        self.setFixedHeight(70)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._title = QLabel(label)
        self._title.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 10px; border: none; background: transparent;"
        )
        self._title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._title)

        self._value = QLabel("0")
        self._value.setStyleSheet(
            f"color: #ffffff; font-size: 20px; font-weight: bold; border: none; background: transparent;"
        )
        self._value.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._value)

    def set_value(self, text: str):
        self._value.setText(text)


# -----------------------------------------------------------------------
# DashboardTab
# -----------------------------------------------------------------------

class DashboardTab(QWidget):
    """仪表盘主 Tab - KPI 行 + 2x2 卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

        # 定时刷新
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_all)
        self._timer.start(2000)
        self.destroyed.connect(self.cleanup)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # --- KPI 概览行 ---
        kpi_row = self._create_kpi_row()
        layout.addLayout(kpi_row)

        # --- 2x2 卡片区 ---
        outer = QSplitter(Qt.Orientation.Vertical)

        # 上半部分
        top = QSplitter(Qt.Orientation.Horizontal)
        self.token_chart = TokenUsageChart()
        self.score_chart = ScoreTrendChart()
        top.addWidget(_wrap_card("Token Usage", self.token_chart))
        top.addWidget(_wrap_card("Score Trend", self.score_chart))
        top.setSizes([1, 1])

        # 下半部分
        bottom = QSplitter(Qt.Orientation.Horizontal)
        self.timeline = ExecutionTimelineWidget()
        self.dag = DAGWidget()
        bottom.addWidget(_wrap_card("Execution Timeline", self.timeline))
        bottom.addWidget(_wrap_card("Workflow DAG", self.dag))
        bottom.setSizes([1, 1])

        outer.addWidget(top)
        outer.addWidget(bottom)
        outer.setSizes([1, 1])

        layout.addWidget(outer, stretch=1)

    def _create_kpi_row(self) -> QHBoxLayout:
        """创建 KPI 指标行 (5 个卡片)"""
        row = QHBoxLayout()
        row.setSpacing(8)

        self._kpi_llm_calls = _KPICard("LLM Calls")
        self._kpi_total_tokens = _KPICard("Total Tokens")
        self._kpi_agents = _KPICard("Active Agents")
        self._kpi_avg_time = _KPICard("Avg Response Time")
        self._kpi_status = _KPICard("Status")

        for card in [
            self._kpi_llm_calls,
            self._kpi_total_tokens,
            self._kpi_agents,
            self._kpi_avg_time,
            self._kpi_status,
        ]:
            row.addWidget(card)

        return row

    def _refresh_kpi(self):
        """从 AgentHistory 刷新 KPI 数据"""
        summary = get_agent_history().get_session_summary()
        agent_summaries: Dict[str, Any] = summary.get("agent_summaries", {})

        total_llm = 0
        total_tokens = 0
        total_time = 0.0
        time_count = 0

        for data in agent_summaries.values():
            total_llm += data.get("llm_calls", 0)
            total_tokens += data.get("total_tokens", 0)
            avg_t = data.get("avg_response_time", 0)
            if avg_t > 0:
                total_time += avg_t
                time_count += 1

        active_agents = len(agent_summaries)
        avg_resp = total_time / time_count if time_count > 0 else 0

        self._kpi_llm_calls.set_value(str(total_llm))
        self._kpi_total_tokens.set_value(f"{total_tokens:,}")
        self._kpi_agents.set_value(str(active_agents))
        self._kpi_avg_time.set_value(f"{avg_resp:.1f}s" if avg_resp > 0 else "0s")

        # 状态: 检查是否有错误
        has_error = any(
            "agent_error" in (data.get("type_counts") or {})
            for data in agent_summaries.values()
        )
        if has_error:
            self._kpi_status.set_value("Error")
            self._kpi_status._value.setStyleSheet(
                "color: #e74856; font-size: 20px; font-weight: bold; border: none; background: transparent;"
            )
        elif active_agents > 0:
            self._kpi_status.set_value("Running")
            self._kpi_status._value.setStyleSheet(
                "color: #00b294; font-size: 20px; font-weight: bold; border: none; background: transparent;"
            )
        else:
            self._kpi_status.set_value("Idle")
            self._kpi_status._value.setStyleSheet(
                "color: #ffffff; font-size: 20px; font-weight: bold; border: none; background: transparent;"
            )

    def refresh_all(self):
        """刷新全部图表 + KPI"""
        self._refresh_kpi()
        self.token_chart.refresh()
        self.score_chart.refresh()
        self.timeline.refresh()
        self.dag.refresh()

    def cleanup(self):
        """停止定时器"""
        self._timer.stop()
