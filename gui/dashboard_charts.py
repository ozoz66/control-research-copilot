# -*- coding: utf-8 -*-
"""
Dashboard 图表组件 - matplotlib (FigureCanvasQTAgg)

- TokenUsageChart: 水平柱状图，每个 Agent 的 token 消耗
- ScoreTrendChart: 折线图 + 网格线，监督评分趋势
"""

from typing import Dict, List, Any

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core.agent_history import get_agent_history, InteractionType
from .constants import THEME_STYLES

# 从主题取色
_THEME = THEME_STYLES["dark"]
_BG_COLOR = _THEME["background"]       # #1e1e1e
_AXES_COLOR = _THEME["input_background"]  # #2d2d2d
_TEXT_COLOR = _THEME["text"]            # #d4d4d4
_BORDER_COLOR = _THEME["border"]        # #3c3c3c
_PRIMARY = _THEME["button_primary"]     # #0078d4

_LINE_COLORS = [
    "#0078d4", "#00b294", "#e74856",
    "#ffb900", "#8764b8", "#00bcf2",
]

_EMPTY_TEXT_COLOR = "#555555"


class TokenUsageChart(QWidget):
    """Agent Token 消耗水平柱状图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._figure = Figure(figsize=(5, 3), facecolor=_BG_COLOR)
        self._canvas = FigureCanvas(self._figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.refresh()

    def refresh(self):
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(_AXES_COLOR)

        summary = get_agent_history().get_session_summary()
        agent_summaries: Dict[str, Any] = summary.get("agent_summaries", {})

        if not agent_summaries:
            # 空态: 隐藏坐标轴, 居中提示
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.text(
                0.5, 0.5, "Waiting for data...",
                ha="center", va="center",
                color=_EMPTY_TEXT_COLOR, fontsize=13, fontstyle="italic",
                transform=ax.transAxes,
            )
        else:
            agents = list(agent_summaries.keys())
            tokens = [agent_summaries[a].get("total_tokens", 0) for a in agents]
            colors = [_LINE_COLORS[i % len(_LINE_COLORS)] for i in range(len(agents))]

            bars = ax.barh(agents, tokens, color=colors, height=0.55)

            # 柱右侧标注数值
            max_val = max(tokens) if tokens else 1
            for bar, val in zip(bars, tokens):
                if val > 0:
                    ax.text(
                        bar.get_width() + max_val * 0.02,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val:,}",
                        ha="left", va="center",
                        color=_TEXT_COLOR, fontsize=8,
                    )

            ax.set_xlabel("Total Tokens", color=_TEXT_COLOR, fontsize=9)

            # 隐藏上/右 spine, 保留下/左
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color(_BORDER_COLOR)
            ax.spines["left"].set_color(_BORDER_COLOR)

            # 留出数值标注空间
            if max_val > 0:
                ax.set_xlim(0, max_val * 1.18)

        ax.tick_params(colors=_TEXT_COLOR, labelsize=8)
        self._figure.subplots_adjust(left=0.22, right=0.92, top=0.92, bottom=0.15)
        self._canvas.draw()


class ScoreTrendChart(QWidget):
    """监督评分趋势折线图 + 网格线"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._figure = Figure(figsize=(5, 3), facecolor=_BG_COLOR)
        self._canvas = FigureCanvas(self._figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.refresh()

    def refresh(self):
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(_AXES_COLOR)

        records = get_agent_history().query(
            interaction_type=InteractionType.SUPERVISOR_EVAL, limit=500,
        )

        if not records:
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.text(
                0.5, 0.5, "Waiting for data...",
                ha="center", va="center",
                color=_EMPTY_TEXT_COLOR, fontsize=13, fontstyle="italic",
                transform=ax.transAxes,
            )
        else:
            # 按 agent 分组
            agent_scores: Dict[str, List[float]] = {}
            for r in records:
                key = r.agent_key
                score = r.content.get("score", 0)
                agent_scores.setdefault(key, []).append(score)

            for idx, (agent, scores) in enumerate(agent_scores.items()):
                color = _LINE_COLORS[idx % len(_LINE_COLORS)]
                ax.plot(
                    range(1, len(scores) + 1), scores,
                    marker="o", markersize=4,
                    label=agent, color=color, linewidth=1.5,
                )

            ax.set_xlabel("Iteration", color=_TEXT_COLOR, fontsize=9)
            ax.set_ylabel("Score (0-100)", color=_TEXT_COLOR, fontsize=9)
            ax.set_ylim(0, 105)
            ax.legend(
                fontsize=8, facecolor=_AXES_COLOR,
                edgecolor=_BORDER_COLOR, labelcolor=_TEXT_COLOR,
            )

            # 网格线
            ax.grid(axis="y", color=_BORDER_COLOR, alpha=0.5, linestyle="--")
            ax.set_axisbelow(True)

            # 隐藏上/右 spine
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color(_BORDER_COLOR)
            ax.spines["left"].set_color(_BORDER_COLOR)

        ax.tick_params(colors=_TEXT_COLOR, labelsize=8)
        self._figure.subplots_adjust(left=0.15, right=0.95, top=0.92, bottom=0.15)
        self._canvas.draw()
