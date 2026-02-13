# -*- coding: utf-8 -*-
"""
AutoControl-Scientist 应用程序入口
多Agent协作的控制系统研究自动化平台
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from logger_config import setup_logger

# 配置
logger = setup_logger("autocontrol_scientist", level="INFO")


def main() -> None:
    """应用程序入口"""
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setApplicationName("AutoControl-Scientist")
    app.setOrganizationName("AutoControl")

    # 设置应用样式
    app.setStyle("Fusion")

    # 设置全局深色主题
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Text, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(212, 212, 212))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, QColor(86, 156, 214))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(128, 128, 128))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(128, 128, 128))
    app.setPalette(palette)

    app.setStyleSheet("""
        QGroupBox {
            border: 1px solid #3c3c3c;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 14px;
            font-weight: bold;
            color: #d4d4d4;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 16px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #0078d4;
        }
        QPushButton:pressed {
            background-color: #333;
        }
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #666;
            border-color: #3c3c3c;
        }
        QComboBox {
            background-color: #2d2d2d;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #d4d4d4;
            selection-background-color: #0078d4;
        }
        QLineEdit {
            background-color: #2d2d2d;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border-color: #0078d4;
        }
        QTextEdit {
            background-color: #2d2d2d;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
        }
        QProgressBar {
            background-color: #2d2d2d;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            text-align: center;
            color: #d4d4d4;
            min-height: 20px;
        }
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 3px;
        }
        QTabWidget::pane {
            border: 1px solid #3c3c3c;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #999;
            border: 1px solid #3c3c3c;
            padding: 8px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border-bottom-color: #1e1e1e;
        }
        QTabBar::tab:hover:!selected {
            background-color: #383838;
            color: #d4d4d4;
        }
        QTableWidget {
            background-color: #2d2d2d;
            color: #d4d4d4;
            gridline-color: #3c3c3c;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
        }
        QTableWidget::item:selected {
            background-color: #0078d4;
        }
        QHeaderView::section {
            background-color: #333;
            color: #d4d4d4;
            border: 1px solid #3c3c3c;
            padding: 6px;
            font-weight: bold;
        }
        QCheckBox {
            color: #d4d4d4;
            spacing: 6px;
        }
        QSplitter::handle {
            background-color: #3c3c3c;
            height: 3px;
        }
        QStatusBar {
            background-color: #007acc;
            color: white;
        }
        QScrollBar:vertical {
            background-color: #1e1e1e;
            width: 12px;
            border: none;
        }
        QScrollBar::handle:vertical {
            background-color: #555;
            border-radius: 4px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #777;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
    """)

    # 创建并显示主窗口
    try:
        window = MainWindow()
        window.show()
        logger.info("应用程序已启动")
        sys.exit(app.exec())
    except Exception as e:
        logger.exception("应用程序启动失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
