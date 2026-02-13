# -*- coding: utf-8 -*-
"""
API 配置标签页模块

提供 API 和模型配置管理界面。
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QComboBox, QMessageBox, QFileDialog,
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from config_manager import get_config_manager, AgentConfig
from .widgets import style_button


class ApiConfigTab(QWidget):
    """
    Tab 1: API与模型配置
    支持对各类 Agent 进行 CRUD 管理
    """

    config_changed = pyqtSignal()  # 配置变更信号

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = get_config_manager()
        self._init_ui()
        self._load_agents()

    def _init_ui(self) -> None:
        """初始化界面布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ===== Agent配置表格 =====
        table_group = QGroupBox("模型配置管理中心")
        table_layout = QVBoxLayout(table_group)

        # 表格控件
        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(6)
        self.agent_table.setHorizontalHeaderLabels([
            "Agent类型", "提供商", "API Key", "Base URL", "模型名称", "启用"
        ])
        self.agent_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.agent_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.agent_table.itemSelectionChanged.connect(self._on_selection_changed)
        table_layout.addWidget(self.agent_table)

        # 表格操作按钮
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("添加")
        self.btn_edit = QPushButton("编辑")
        self.btn_delete = QPushButton("删除")
        self.btn_save = QPushButton("保存配置")

        style_button(self.btn_delete, "danger")
        style_button(self.btn_save, "success")

        self.btn_add.clicked.connect(self._add_agent)
        self.btn_edit.clicked.connect(self._edit_agent)
        self.btn_delete.clicked.connect(self._delete_agent)
        self.btn_save.clicked.connect(self._save_config)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        table_layout.addLayout(btn_layout)

        layout.addWidget(table_group)

        # ===== Agent编辑区域 — 用 QGridLayout 对齐 =====
        edit_group = QGroupBox("编辑Agent配置")
        grid = QGridLayout(edit_group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Row 0: Agent类型 + 提供商
        grid.addWidget(QLabel("Agent类型:"), 0, 0)
        self.combo_agent_type = QComboBox()
        self.combo_agent_type.addItems([
            "architect (架构师)",
            "theorist (理论家)",
            "engineer (工程师/代码生成)",
            "simulator (仿真执行)",
            "dsp_coder (DSP编码器)",
            "scribe (撰稿人)",
            "supervisor (监督者)"
        ])
        grid.addWidget(self.combo_agent_type, 0, 1)

        grid.addWidget(QLabel("提供商名称:"), 0, 2)
        self.edit_provider = QLineEdit()
        self.edit_provider.setPlaceholderText("例如: OpenAI, Anthropic, 本地代理")
        grid.addWidget(self.edit_provider, 0, 3)

        # Row 1: API Key
        grid.addWidget(QLabel("API Key:"), 1, 0)
        key_layout = QHBoxLayout()
        self.edit_api_key = QLineEdit()
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_api_key.setPlaceholderText("输入API密钥")
        key_layout.addWidget(self.edit_api_key)
        self.btn_toggle_key = QPushButton("👁")
        self.btn_toggle_key.setFixedWidth(30)
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        key_layout.addWidget(self.btn_toggle_key)
        grid.addLayout(key_layout, 1, 1, 1, 3)

        # Row 2: Base URL
        grid.addWidget(QLabel("Base URL:"), 2, 0)
        url_layout = QHBoxLayout()
        self.edit_base_url = QLineEdit()
        self.edit_base_url.setPlaceholderText("https://api.openai.com/v1")
        self.edit_base_url.editingFinished.connect(self._validate_base_url)
        url_layout.addWidget(self.edit_base_url)
        self.label_url_status = QLabel("")
        self.label_url_status.setFixedWidth(24)
        url_layout.addWidget(self.label_url_status)
        grid.addLayout(url_layout, 2, 1, 1, 3)

        # Row 3: 模型名称 + 启用 + 应用按钮
        grid.addWidget(QLabel("模型名称:"), 3, 0)
        self.combo_model_name = QComboBox()
        self.combo_model_name.setEditable(True)
        self.combo_model_name.addItems([
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
            "deepseek-chat",
            "deepseek-coder",
            "qwen-plus",
            "qwen-turbo",
        ])
        self.combo_model_name.setCurrentText("")
        self.combo_model_name.lineEdit().setPlaceholderText("选择或输入模型名称")
        grid.addWidget(self.combo_model_name, 3, 1)

        self.check_enabled = QCheckBox("启用此Agent")
        self.check_enabled.setChecked(True)
        grid.addWidget(self.check_enabled, 3, 2)

        self.btn_apply_edit = QPushButton("应用编辑")
        self.btn_apply_edit.clicked.connect(self._apply_edit)
        grid.addWidget(self.btn_apply_edit, 3, 3)

        layout.addWidget(edit_group)

        # ===== MATLAB路径配置 =====
        matlab_group = QGroupBox("MATLAB配置")
        matlab_layout = QHBoxLayout(matlab_group)

        matlab_layout.addWidget(QLabel("MATLAB路径:"))
        self.edit_matlab_path = QLineEdit()
        self.edit_matlab_path.setText(self.config_manager.settings.matlab_path)
        matlab_layout.addWidget(self.edit_matlab_path)

        self.btn_browse_matlab = QPushButton("浏览...")
        self.btn_browse_matlab.clicked.connect(self._browse_matlab)
        matlab_layout.addWidget(self.btn_browse_matlab)

        layout.addWidget(matlab_group)

        # 底部弹性空间
        layout.addStretch()

        # 初始按钮状态
        self._update_button_states()

    def _load_agents(self) -> None:
        """从配置管理器加载 Agent 列表"""
        self.agent_table.setRowCount(0)
        agents = self.config_manager.get_all_agents()

        for agent in agents:
            row = self.agent_table.rowCount()
            self.agent_table.insertRow(row)

            self.agent_table.setItem(row, 0, QTableWidgetItem(agent.agent_type))
            self.agent_table.setItem(row, 1, QTableWidgetItem(agent.provider_name))
            key_display = "****" + agent.api_key[-4:] if len(agent.api_key) > 4 else "****"
            self.agent_table.setItem(row, 2, QTableWidgetItem(key_display))
            self.agent_table.setItem(row, 3, QTableWidgetItem(agent.base_url))
            self.agent_table.setItem(row, 4, QTableWidgetItem(agent.model_name))
            enabled_item = QTableWidgetItem("✓" if agent.enabled else "✗")
            enabled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.agent_table.setItem(row, 5, enabled_item)

    def _on_selection_changed(self) -> None:
        selected_rows = self.agent_table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            agent = self.config_manager.get_agent(row)
            if agent:
                self.combo_agent_type.setCurrentText(agent.agent_type)
                self.edit_provider.setText(agent.provider_name)
                self.edit_api_key.setText(agent.api_key)
                self.edit_base_url.setText(agent.base_url)
                self.combo_model_name.setCurrentText(agent.model_name)
                self.check_enabled.setChecked(agent.enabled)
        self._update_button_states()

    def _update_button_states(self) -> None:
        has_selection = len(self.agent_table.selectedIndexes()) > 0
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _get_current_config(self) -> AgentConfig:
        agent_type_text = self.combo_agent_type.currentText()
        agent_type = agent_type_text.split(" ")[0] if " " in agent_type_text else agent_type_text
        return AgentConfig(
            agent_type=agent_type,
            provider_name=self.edit_provider.text().strip(),
            api_key=self.edit_api_key.text().strip(),
            base_url=self.edit_base_url.text().strip(),
            model_name=self.combo_model_name.currentText().strip(),
            enabled=self.check_enabled.isChecked()
        )

    def _add_agent(self) -> None:
        config = self._get_current_config()
        if not config.provider_name or not config.model_name:
            QMessageBox.warning(self, "警告", "请填写提供商名称和模型名称")
            return
        self.config_manager.add_agent(config)
        self._load_agents()
        self.config_changed.emit()

    def _edit_agent(self) -> None:
        selected = self.agent_table.selectedIndexes()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要编辑的 Agent")
            return
        row = selected[0].row()
        agent = self.config_manager.get_agent(row)
        if not agent:
            QMessageBox.warning(self, "错误", "无法读取 Agent 配置")
            return
        for i in range(self.combo_agent_type.count()):
            if agent.agent_type in self.combo_agent_type.itemText(i):
                self.combo_agent_type.setCurrentIndex(i)
                break
        self.edit_provider.setText(agent.provider_name)
        self.edit_api_key.setText(agent.api_key)
        self.edit_base_url.setText(agent.base_url)
        self.combo_model_name.setCurrentText(agent.model_name)
        self.check_enabled.setChecked(agent.enabled)

    def _apply_edit(self) -> None:
        config = self._get_current_config()
        if not config.provider_name or not config.model_name:
            QMessageBox.warning(self, "警告", "请填写提供商名称和模型名称")
            return
        selected = self.agent_table.selectedIndexes()
        if selected:
            row = selected[0].row()
            self.config_manager.update_agent(row, config)
        else:
            self.config_manager.add_agent(config)
        self._load_agents()
        self.config_changed.emit()
        QMessageBox.information(self, "成功", "配置已应用")

    def _delete_agent(self) -> None:
        selected = self.agent_table.selectedIndexes()
        if not selected:
            return
        row = selected[0].row()
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除选中的 Agent 配置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.delete_agent(row)
            self._load_agents()
            self.config_changed.emit()

    def _save_config(self) -> None:
        self.config_manager.set_matlab_path(self.edit_matlab_path.text().strip())
        if self.config_manager.save():
            QMessageBox.information(self, "成功", "配置已保存")
        else:
            QMessageBox.warning(self, "失败", "配置保存失败")

    def _toggle_key_visibility(self) -> None:
        if self.edit_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🔒")
        else:
            self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁")

    def _validate_base_url(self) -> None:
        url = self.edit_base_url.text().strip()
        if not url:
            self.label_url_status.setText("")
            return
        import re
        if re.match(r'^https?://.+', url):
            self.label_url_status.setText("OK")
            self.label_url_status.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        else:
            self.label_url_status.setText("!")
            self.label_url_status.setStyleSheet("color: #f14c4c; font-weight: bold;")
            self.label_url_status.setToolTip("URL应以 http:// 或 https:// 开头")

    def _browse_matlab(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "选择 MATLAB 安装目录"
        )
        if path:
            self.edit_matlab_path.setText(path)
