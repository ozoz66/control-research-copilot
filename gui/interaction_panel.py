# -*- coding: utf-8 -*-
"""
交互配置面板 - AutoControl-Scientist

提供用户自定义Agent交互行为的GUI配置界面
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QGridLayout, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal

from core.signal_manager import get_interaction_config, InteractionConfig


class InteractionConfigPanel(QWidget):
    """
    交互配置面板
    
    允许用户配置:
    - 哪些阶段需要确认
    - 是否启用快速模式
    - 监督评分阈值
    - 最大重试次数等
    """
    
    config_changed = pyqtSignal()  # 配置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = get_interaction_config()
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # ===== 阶段确认配置 =====
        stage_group = QGroupBox("阶段确认设置")
        stage_layout = QVBoxLayout(stage_group)
        
        hint_label = QLabel("选择需要用户手动确认的阶段。勾选的阶段在完成后会暂停等待确认。")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 10px;")
        stage_layout.addWidget(hint_label)
        
        self._stage_checks: Dict[str, QCheckBox] = {}
        
        stages = [
            ("architect", "📚 文献检索与课题设计"),
            ("theorist", "📐 数学推导与稳定性分析"),
            ("engineer", "⚙️ MATLAB代码生成"),
            ("simulator", "🔬 MATLAB仿真执行"),
            ("dsp_coder", "💻 DSP代码生成"),
            ("scribe", "📝 论文撰写"),
        ]
        
        grid = QGridLayout()
        for i, (key, label) in enumerate(stages):
            checkbox = QCheckBox(label)
            self._stage_checks[key] = checkbox
            grid.addWidget(checkbox, i // 2, i % 2)
        stage_layout.addLayout(grid)
        
        # 快速模式按钮
        btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.clicked.connect(self._select_all_stages)
        self.btn_deselect_all = QPushButton("全不选 (快速模式)")
        self.btn_deselect_all.clicked.connect(self._deselect_all_stages)
        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_deselect_all)
        btn_layout.addStretch()
        stage_layout.addLayout(btn_layout)
        
        content_layout.addWidget(stage_group)
        
        # ===== 监督评估配置 =====
        eval_group = QGroupBox("监督评估设置")
        eval_layout = QGridLayout(eval_group)
        
        eval_layout.addWidget(QLabel("显示监督评估详情:"), 0, 0)
        self.check_show_details = QCheckBox("启用")
        eval_layout.addWidget(self.check_show_details, 0, 1)
        
        eval_layout.addWidget(QLabel("低分强制确认阈值:"), 1, 0)
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0, 100)
        self.spin_threshold.setSingleStep(5)
        self.spin_threshold.setSuffix(" 分")
        eval_layout.addWidget(self.spin_threshold, 1, 1)
        
        threshold_hint = QLabel("低于此分数的阶段将强制要求用户确认，即使在快速模式下。")
        threshold_hint.setWordWrap(True)
        threshold_hint.setStyleSheet("color: #888; font-size: 11px;")
        eval_layout.addWidget(threshold_hint, 2, 0, 1, 2)
        
        content_layout.addWidget(eval_group)
        
        # ===== 重试配置 =====
        retry_group = QGroupBox("自动重试设置")
        retry_layout = QGridLayout(retry_group)
        
        retry_layout.addWidget(QLabel("最大自动重试次数:"), 0, 0)
        self.spin_max_retry = QSpinBox()
        self.spin_max_retry.setRange(0, 5)
        retry_layout.addWidget(self.spin_max_retry, 0, 1)
        
        retry_hint = QLabel("Agent执行失败或评分过低时，自动重试的最大次数。设为0禁用自动重试。")
        retry_hint.setWordWrap(True)
        retry_hint.setStyleSheet("color: #888; font-size: 11px;")
        retry_layout.addWidget(retry_hint, 1, 0, 1, 2)
        
        content_layout.addWidget(retry_group)
        
        # ===== 预览配置 =====
        preview_group = QGroupBox("内容预览设置")
        preview_layout = QGridLayout(preview_group)
        
        preview_layout.addWidget(QLabel("显示Agent产出预览:"), 0, 0)
        self.check_show_preview = QCheckBox("启用")
        preview_layout.addWidget(self.check_show_preview, 0, 1)
        
        preview_layout.addWidget(QLabel("预览最大长度:"), 1, 0)
        self.spin_preview_length = QSpinBox()
        self.spin_preview_length.setRange(100, 2000)
        self.spin_preview_length.setSingleStep(100)
        self.spin_preview_length.setSuffix(" 字符")
        preview_layout.addWidget(self.spin_preview_length, 1, 1)
        
        content_layout.addWidget(preview_group)
        
        # ===== 课题对话配置 =====
        chat_group = QGroupBox("课题对话设置")
        chat_layout = QHBoxLayout(chat_group)
        
        chat_layout.addWidget(QLabel("启用与AI对话优化课题:"))
        self.check_topic_chat = QCheckBox("启用")
        chat_layout.addWidget(self.check_topic_chat)
        chat_layout.addStretch()
        
        content_layout.addWidget(chat_group)
        
        # 弹性空间
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 底部按钮
        btn_bar = QHBoxLayout()
        self.btn_apply = QPushButton("应用配置")
        self.btn_apply.clicked.connect(self._apply_config)
        self.btn_reset = QPushButton("重置默认")
        self.btn_reset.clicked.connect(self._reset_config)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_reset)
        btn_bar.addWidget(self.btn_apply)
        layout.addLayout(btn_bar)
    
    def _load_config(self):
        """从配置加载UI状态"""
        # 阶段确认
        for key, checkbox in self._stage_checks.items():
            in_confirm = key in self._config.confirm_stages
            in_auto = key in self._config.auto_confirm_stages
            checkbox.setChecked(in_confirm and not in_auto)
        
        # 其他配置
        self.check_show_details.setChecked(self._config.show_supervision_details)
        self.spin_threshold.setValue(self._config.supervision_threshold)
        self.spin_max_retry.setValue(self._config.max_auto_retry)
        self.check_show_preview.setChecked(self._config.show_output_preview)
        self.spin_preview_length.setValue(self._config.preview_max_length)
        self.check_topic_chat.setChecked(self._config.enable_topic_chat)
    
    def _apply_config(self):
        """应用配置"""
        # 更新阶段确认配置
        self._config.confirm_stages = set()
        self._config.auto_confirm_stages = set()
        
        for key, checkbox in self._stage_checks.items():
            if checkbox.isChecked():
                self._config.confirm_stages.add(key)
            else:
                self._config.auto_confirm_stages.add(key)
        
        # 更新其他配置
        self._config.show_supervision_details = self.check_show_details.isChecked()
        self._config.supervision_threshold = self.spin_threshold.value()
        self._config.max_auto_retry = self.spin_max_retry.value()
        self._config.show_output_preview = self.check_show_preview.isChecked()
        self._config.preview_max_length = self.spin_preview_length.value()
        self._config.enable_topic_chat = self.check_topic_chat.isChecked()
        
        self.config_changed.emit()
        QMessageBox.information(self, "成功", "交互配置已应用")
    
    def _reset_config(self):
        """重置为默认配置"""
        self._config = InteractionConfig()
        self._load_config()
        QMessageBox.information(self, "成功", "已重置为默认配置")
    
    def _select_all_stages(self):
        """全选所有阶段"""
        for checkbox in self._stage_checks.values():
            checkbox.setChecked(True)
    
    def _deselect_all_stages(self):
        """取消选择所有阶段（快速模式）"""
        for checkbox in self._stage_checks.values():
            checkbox.setChecked(False)
    
    def get_config(self) -> InteractionConfig:
        """获取当前配置"""
        return self._config


class HistoryViewerPanel(QWidget):
    """
    交互历史查看面板
    
    显示Agent执行的历史记录
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("Agent交互历史")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        hint = QLabel("查看Agent执行过程中的所有交互记录，用于调试和分析。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(hint)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.clicked.connect(self._refresh)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_export_json = QPushButton("导出JSON")
        self.btn_export_json.clicked.connect(self._export_json)
        btn_layout.addWidget(self.btn_export_json)
        
        self.btn_export_md = QPushButton("导出Markdown")
        self.btn_export_md.clicked.connect(self._export_markdown)
        btn_layout.addWidget(self.btn_export_md)
        
        self.btn_clear = QPushButton("清空历史")
        self.btn_clear.clicked.connect(self._clear)
        btn_layout.addWidget(self.btn_clear)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 摘要显示
        from PyQt6.QtWidgets import QTextEdit
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                font-family: Consolas, monospace;
            }
        """)
        layout.addWidget(self.summary_text)
        
        self._refresh()
    
    def _refresh(self):
        """刷新摘要"""
        try:
            from core.agent_history import get_agent_history
            history = get_agent_history()
            summary = history.get_session_summary()
            
            lines = [
                f"会话ID: {summary['session_id']}",
                f"总记录数: {summary['total_records']}",
                f"涉及Agent: {', '.join(summary['agents']) if summary['agents'] else '无'}",
                "",
            ]
            
            for agent_key, agent_summary in summary.get("agent_summaries", {}).items():
                lines.append(f"=== {agent_key} ===")
                lines.append(f"  记录数: {agent_summary['total_records']}")
                lines.append(f"  LLM调用: {agent_summary.get('llm_calls', 0)}")
                lines.append(f"  总Token: {agent_summary.get('total_tokens', 0)}")
                lines.append(f"  平均响应: {agent_summary.get('avg_response_time', 0)}秒")
                lines.append("")
            
            self.summary_text.setText("\n".join(lines))
        except ImportError:
            self.summary_text.setText("交互历史模块未加载")
    
    def _export_json(self):
        """导出JSON"""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出JSON", "agent_history.json", "JSON文件 (*.json)"
        )
        if path:
            try:
                from core.agent_history import get_agent_history
                get_agent_history().export_json(path)
                QMessageBox.information(self, "成功", f"已导出到: {path}")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"导出失败: {e}")
    
    def _export_markdown(self):
        """导出Markdown"""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出Markdown", "agent_history.md", "Markdown文件 (*.md)"
        )
        if path:
            try:
                from core.agent_history import get_agent_history
                get_agent_history().export_markdown(path)
                QMessageBox.information(self, "成功", f"已导出到: {path}")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"导出失败: {e}")
    
    def _clear(self):
        """清空历史"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有交互历史吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from core.agent_history import get_agent_history
                get_agent_history().clear()
                self._refresh()
                QMessageBox.information(self, "成功", "交互历史已清空")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"清空失败: {e}")
