# -*- coding: utf-8 -*-
"""
Dashboard DAG（有向无环图）可视化 - QPainter 自绘

显示 Agent 工作流的拓扑结构和当前执行状态。
节点状态: pending(灰), active(蓝), done(青), error(红)

增强: 大节点(100x44), 状态图标, 彩色边, 图例, active 发光效果。
"""

import math
from typing import Dict, List, Tuple

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPolygonF

from core.agent_history import get_agent_history, InteractionType
from .constants import THEME_STYLES

_THEME = THEME_STYLES["dark"]

# 节点定义: (key, display_name, x_ratio, y_ratio)
_NODES = [
    ("architect", "Architect", 0.10, 0.50),
    ("theorist", "Theorist", 0.30, 0.30),
    ("engineer", "Engineer", 0.50, 0.30),
    ("simulator", "Simulator", 0.70, 0.30),
    ("dsp_coder", "DSP Coder", 0.70, 0.70),
    ("scribe", "Scribe", 0.90, 0.50),
]

# 有向边: (from, to)
_EDGES = [
    ("architect", "theorist"),
    ("theorist", "engineer"),
    ("engineer", "simulator"),
    ("simulator", "dsp_coder"),
    ("theorist", "scribe"),
    ("simulator", "scribe"),
]

_NODE_W = 100
_NODE_H = 44

_STATUS_COLORS = {
    "pending": QColor("#555555"),
    "active": QColor("#0078d4"),
    "done": QColor("#00b294"),
    "error": QColor("#e74856"),
}
_STATUS_SYMBOLS = {
    "pending": "\u25CB",   # ○
    "active": "\u25C9",    # ◉
    "done": "\u25CF",      # ●
    "error": "\u2716",     # ✖
}
_STATUS_LABELS = ["Pending", "Active", "Done", "Error"]
_STATUS_KEYS = ["pending", "active", "done", "error"]

_BG = QColor(_THEME["background"])
_TEXT = QColor("#ffffff")
_TEXT_DIM = QColor("#888888")
_EDGE_DEFAULT = QColor("#444444")
_EMPTY_COLOR = QColor("#555555")

# 发光效果
_GLOW_COLOR = QColor(0, 120, 212, 50)  # 半透明蓝


class DAGWidget(QWidget):
    """Agent 工作流 DAG 可视化 - 大节点 + 状态图标 + 图例"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self._node_status: Dict[str, str] = {n[0]: "pending" for n in _NODES}
        self.refresh()

    def refresh(self):
        """从 AgentHistory 更新节点状态"""
        history = get_agent_history()
        status: Dict[str, str] = {n[0]: "pending" for n in _NODES}

        for r in history.query(limit=2000):
            if r.interaction_type == InteractionType.AGENT_START.value:
                if status.get(r.agent_key) != "done":
                    status[r.agent_key] = "active"
            elif r.interaction_type == InteractionType.AGENT_COMPLETE.value:
                status[r.agent_key] = "done"
            elif r.interaction_type == InteractionType.AGENT_ERROR.value:
                status[r.agent_key] = "error"

        self._node_status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), _BG)

        if all(s == "pending" for s in self._node_status.values()):
            # 仍然绘制 DAG 结构，但同时检查是否没有历史数据
            history = get_agent_history()
            if not history.query(limit=1):
                self._draw_empty(painter)
                self._draw_dag(painter)
                painter.end()
                return

        self._draw_dag(painter)
        painter.end()

    def _draw_dag(self, painter: QPainter):
        w = self.width()
        h = self.height()

        # 绘图区域留出图例空间
        draw_h = h - 30

        # 计算节点中心位置
        centers: Dict[str, QPointF] = {}
        for key, name, xr, yr in _NODES:
            cx = xr * w
            cy = yr * draw_h + 10
            centers[key] = QPointF(cx, cy)

        # 绘制边（带箭头, 颜色跟随源节点状态）
        for src, dst in _EDGES:
            src_status = self._node_status.get(src, "pending")
            edge_color = self._edge_color_for_status(src_status)
            painter.setPen(QPen(edge_color, 2))
            p1 = centers[src]
            p2 = centers[dst]
            self._draw_arrow(painter, p1, p2, edge_color)

        # 绘制节点
        for key, name, xr, yr in _NODES:
            center = centers[key]
            status = self._node_status.get(key, "pending")
            color = _STATUS_COLORS.get(status, _STATUS_COLORS["pending"])
            symbol = _STATUS_SYMBOLS.get(status, "\u25CB")

            rect = QRectF(
                center.x() - _NODE_W / 2,
                center.y() - _NODE_H / 2,
                _NODE_W,
                _NODE_H,
            )

            # Active 节点发光效果
            if status == "active":
                glow_rect = rect.adjusted(-4, -4, 4, 4)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(_GLOW_COLOR)
                painter.drawRoundedRect(glow_rect, 10, 10)

            # 节点背景
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 8, 8)

            # 状态符号 (上方小字)
            painter.setPen(_TEXT)
            painter.setFont(QFont("Arial", 8))
            symbol_rect = QRectF(rect.x(), rect.y() + 2, rect.width(), 14)
            painter.drawText(symbol_rect, int(Qt.AlignmentFlag.AlignCenter), symbol)

            # 名称 (下方)
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            name_rect = QRectF(rect.x(), rect.y() + 16, rect.width(), rect.height() - 18)
            painter.drawText(name_rect, int(Qt.AlignmentFlag.AlignCenter), name)

        # 图例 (右下角)
        self._draw_legend(painter, w, h)

    @staticmethod
    def _edge_color_for_status(status: str) -> QColor:
        if status == "done":
            return QColor("#00b294")
        elif status == "active":
            return QColor("#0078d4")
        return _EDGE_DEFAULT

    @staticmethod
    def _draw_arrow(painter: QPainter, p1: QPointF, p2: QPointF, color: QColor):
        """绘制带箭头的有向边"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)
        if length < 1:
            return

        ux, uy = dx / length, dy / length
        offset = _NODE_W / 2 + 4
        start = QPointF(p1.x() + ux * offset, p1.y() + uy * offset)
        end = QPointF(p2.x() - ux * offset, p2.y() - uy * offset)

        painter.drawLine(start, end)

        # 箭头
        arrow_size = 9
        angle = math.atan2(dy, dx)
        a1 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi / 6),
            end.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        a2 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi / 6),
            end.y() - arrow_size * math.sin(angle + math.pi / 6),
        )
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([end, a1, a2]))

    @staticmethod
    def _draw_legend(painter: QPainter, w: int, h: int):
        """右下角绘制图例"""
        legend_x = w - 260
        legend_y = h - 24
        box_size = 10
        spacing = 62

        painter.setFont(QFont("Arial", 8))
        for i, (key, label) in enumerate(zip(_STATUS_KEYS, _STATUS_LABELS)):
            x = legend_x + i * spacing
            color = _STATUS_COLORS[key]

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, legend_y, box_size, box_size), 2, 2)

            painter.setPen(_TEXT_DIM)
            painter.drawText(int(x + box_size + 4), int(legend_y + box_size - 1), label)

    def _draw_empty(self, painter: QPainter):
        """空态叠加文字"""
        painter.setPen(_EMPTY_COLOR)
        painter.setFont(QFont("Arial", 13))
        painter.drawText(
            self.rect(), int(Qt.AlignmentFlag.AlignCenter), "Waiting for data...",
        )
