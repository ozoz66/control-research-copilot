# -*- coding: utf-8 -*-
"""
Dashboard 执行时间线（Gantt 图） - QPainter 自绘

每个 Agent 一行泳道，矩形条表示执行时段。
交替泳道背景、水平分隔线、耗时标注、底部时间刻度。

数据源: AgentHistory 的 AGENT_START / AGENT_COMPLETE 记录。
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from core.agent_history import get_agent_history, InteractionType
from .constants import THEME_STYLES

_THEME = THEME_STYLES["dark"]

_LANE_HEIGHT = 36
_LEFT_MARGIN = 80
_TOP_MARGIN = 10
_BOTTOM_MARGIN = 28
_RIGHT_PADDING = 20
_COLORS = [
    QColor("#0078d4"), QColor("#00b294"), QColor("#e74856"),
    QColor("#ffb900"), QColor("#8764b8"), QColor("#00bcf2"),
]
_BG = QColor(_THEME["background"])          # #1e1e1e
_BG_ALT = QColor("#242424")
_TEXT = QColor(_THEME["text"])              # #d4d4d4
_TEXT_DIM = QColor("#888888")
_GRID = QColor("#333333")
_EMPTY_COLOR = QColor("#555555")


class ExecutionTimelineWidget(QWidget):
    """水平泳道 Gantt 图 - 交替泳道 + 时间刻度 + 耗时标注"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self._segments: List[Tuple[str, float, float]] = []  # (agent, start_ts, end_ts)
        self._agents: List[str] = []
        self.refresh()

    def refresh(self):
        history = get_agent_history()
        starts: Dict[str, float] = {}
        segments: List[Tuple[str, float, float]] = []

        for r in history.query(limit=2000):
            ts = self._parse_ts(r.timestamp)
            if ts is None:
                continue
            if r.interaction_type == InteractionType.AGENT_START.value:
                starts[r.agent_key] = ts
            elif r.interaction_type == InteractionType.AGENT_COMPLETE.value:
                if r.agent_key in starts:
                    segments.append((r.agent_key, starts.pop(r.agent_key), ts))

        self._segments = segments
        self._agents = sorted({s[0] for s in segments})
        self.update()

    @staticmethod
    def _parse_ts(iso: str) -> Optional[float]:
        try:
            return datetime.fromisoformat(iso).timestamp()
        except (ValueError, TypeError):
            return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _BG)

        if not self._segments:
            self._draw_empty(painter)
            painter.end()
            return

        w = self.width()
        h = self.height()

        # 时间范围
        t_min = min(s[1] for s in self._segments)
        t_max = max(s[2] for s in self._segments)
        t_range = max(t_max - t_min, 0.001)

        lane_map = {a: i for i, a in enumerate(self._agents)}
        chart_w = w - _LEFT_MARGIN - _RIGHT_PADDING
        chart_h = h - _TOP_MARGIN - _BOTTOM_MARGIN

        # 绘制交替泳道背景 + 水平分隔线
        for i, agent in enumerate(self._agents):
            y = _TOP_MARGIN + i * _LANE_HEIGHT
            bg = _BG_ALT if i % 2 == 0 else _BG
            painter.fillRect(QRectF(0, y, w, _LANE_HEIGHT), bg)

            # 水平分隔线
            if i > 0:
                painter.setPen(QPen(_GRID, 1))
                painter.drawLine(0, int(y), w, int(y))

        # 底部分隔线 (泳道区域结束)
        lanes_bottom = _TOP_MARGIN + len(self._agents) * _LANE_HEIGHT
        painter.setPen(QPen(_GRID, 1))
        painter.drawLine(0, int(lanes_bottom), w, int(lanes_bottom))

        # 泳道标签
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(_TEXT_DIM)
        for agent, idx in lane_map.items():
            y = _TOP_MARGIN + idx * _LANE_HEIGHT
            label_rect = QRectF(4, y, _LEFT_MARGIN - 8, _LANE_HEIGHT)
            painter.drawText(
                label_rect,
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                agent,
            )

        # 绘制矩形条 + 耗时标注
        painter.setFont(QFont("Consolas", 7))
        for seg_agent, seg_start, seg_end in self._segments:
            lane = lane_map[seg_agent]
            y = _TOP_MARGIN + lane * _LANE_HEIGHT
            color = _COLORS[lane % len(_COLORS)]
            duration = seg_end - seg_start

            x1 = _LEFT_MARGIN + (seg_start - t_min) / t_range * chart_w
            x2 = _LEFT_MARGIN + (seg_end - t_min) / t_range * chart_w
            bar_w = max(x2 - x1, 3)
            rect = QRectF(x1, y + 6, bar_w, _LANE_HEIGHT - 12)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 3, 3)

            # 耗时文字叠加在矩形上
            duration_text = f"{duration:.1f}s"
            painter.setPen(QColor("#ffffff"))
            if bar_w > 35:
                # 文字在矩形内
                painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), duration_text)
            elif bar_w > 3:
                # 文字在矩形右侧
                painter.drawText(
                    int(x2 + 3), int(y + _LANE_HEIGHT // 2 + 3), duration_text,
                )

        # 底部时间刻度
        self._draw_time_axis(painter, t_min, t_range, chart_w, lanes_bottom)

        painter.end()

    def _draw_time_axis(
        self, painter: QPainter, t_min: float, t_range: float,
        chart_w: float, y_base: int,
    ):
        """绘制底部时间刻度 (3-5 个标记)"""
        num_ticks = 5
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(_TEXT_DIM)

        for i in range(num_ticks + 1):
            frac = i / num_ticks
            x = _LEFT_MARGIN + frac * chart_w
            t_val = frac * t_range

            # 刻度线
            painter.setPen(QPen(_GRID, 1))
            painter.drawLine(int(x), y_base, int(x), y_base + 5)

            # 刻度标签
            painter.setPen(_TEXT_DIM)
            label = f"{t_val:.0f}s"
            painter.drawText(int(x) - 12, y_base + 18, label)

    def _draw_empty(self, painter: QPainter):
        """空态显示"""
        painter.setPen(_EMPTY_COLOR)
        painter.setFont(QFont("Arial", 13, QFont.Weight.Normal))
        painter.drawText(
            self.rect(), int(Qt.AlignmentFlag.AlignCenter), "Waiting for data...",
        )
