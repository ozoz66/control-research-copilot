# -*- coding: utf-8 -*-
"""
对话框模块

包含所有自定义对话框组件。
"""

import datetime
import html as _html
import json
import re
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QGroupBox, QWidget, QMessageBox, QSplitter,
    QLineEdit
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

from .widgets import make_selectable, style_button
from global_context import GlobalContext


class StageConfirmationDialog(QDialog):
    """阶段结果确认对话框 - 支持回退到已完成阶段"""

    def __init__(
        self,
        stage_name: str,
        eval_result: Optional[object],
        context: Optional[GlobalContext],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.stage_name = stage_name
        self.eval_result = eval_result
        self.context = context
        self.modification: Optional[str] = None
        self.rollback_to: Optional[str] = None  # 回退目标 agent_key
        self.setWindowTitle(f"阶段确认: {stage_name}")
        self.setMinimumSize(600, 500)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 阶段信息
        info_label = QLabel(f"阶段 [{self.stage_name}] 已完成，请确认结果：")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        make_selectable(info_label)
        layout.addWidget(info_label)

        # 显示当前阶段 Agent 产出的内容
        if self.context:
            content_text = self._get_stage_content()
            if content_text:
                content_group = QGroupBox("当前阶段产出内容")
                content_layout = QVBoxLayout(content_group)
                content_edit = QTextEdit()
                content_edit.setReadOnly(True)
                content_edit.setPlainText(content_text)
                content_edit.setMaximumHeight(250)
                content_edit.setStyleSheet("""
                    QTextEdit {
                        background-color: #2d2d2d;
                        color: #d4d4d4;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        font-family: Consolas, monospace;
                        font-size: 12px;
                    }
                """)
                content_layout.addWidget(content_edit)
                layout.addWidget(content_group)

        # 评估结果
        eval_group = QGroupBox("监督Agent评估结果")
        eval_layout = QVBoxLayout(eval_group)

        if self.eval_result:
            # 评分
            score = getattr(self.eval_result, "score", None)
            passed = getattr(self.eval_result, "passed", False)
            score_text = f"评分: {score}/100" if score is not None else "评分: N/A"
            score_label = QLabel(score_text)
            score_label.setStyleSheet(
                f"color: {'#4CAF50' if passed else '#f44336'}; "
                "font-size: 16px; font-weight: bold;"
            )
            make_selectable(score_label)
            eval_layout.addWidget(score_label)

            # 用 QTextEdit 展示完整评估内容
            eval_text_parts = []
            issues = getattr(self.eval_result, "issues", None)
            if issues:
                eval_text_parts.append("【发现的问题】")
                for issue in issues:
                    eval_text_parts.append(f"  • {issue}")
            suggestions = getattr(self.eval_result, "suggestions", None)
            if suggestions:
                eval_text_parts.append("\n【改进建议】")
                for suggestion in suggestions:
                    eval_text_parts.append(f"  • {suggestion}")
            rollback_rec = getattr(self.eval_result, "rollback_to", None)
            if rollback_rec:
                eval_text_parts.append(f"\n【回退建议】回退到: {rollback_rec}")

            if eval_text_parts:
                eval_text_edit = QTextEdit()
                eval_text_edit.setReadOnly(True)
                eval_text_edit.setPlainText("\n".join(eval_text_parts))
                eval_text_edit.setMaximumHeight(200)
                eval_text_edit.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e1e2e;
                        color: #cdd6f4;
                        border: 1px solid #45475a;
                        border-radius: 4px;
                        font-size: 12px;
                        padding: 6px;
                    }
                """)
                eval_layout.addWidget(eval_text_edit)
        else:
            no_eval_label = QLabel("监督评估未完成（可能评估解析失败或未启用监督Agent）")
            no_eval_label.setStyleSheet("color: #FF9800; font-style: italic;")
            make_selectable(no_eval_label)
            eval_layout.addWidget(no_eval_label)

        layout.addWidget(eval_group)

        # 修改意见输入
        modify_group = QGroupBox("修改意见 (可选)")
        modify_layout = QVBoxLayout(modify_group)
        self.modify_edit = QTextEdit()
        self.modify_edit.setPlaceholderText("如需修改，请输入您的修改意见...")
        self.modify_edit.setMaximumHeight(100)
        modify_layout.addWidget(self.modify_edit)
        layout.addWidget(modify_group)

        # 回退选择
        rollback_group = QGroupBox("回退到已完成阶段 (可选)")
        rollback_layout = QHBoxLayout(rollback_group)
        rollback_layout.addWidget(QLabel("回退到:"))
        self.combo_rollback = QComboBox()
        self.combo_rollback.addItem("不回退", "")

        # 动态添加回退选项
        try:
            from core.workflow_definitions import WORKFLOW_GRAPH, find_stage_index
            current_idx = find_stage_index(self.stage_name)
            for i in range(current_idx):
                node = WORKFLOW_GRAPH[i]
                self.combo_rollback.addItem(
                    f"{node['description']}", node['agent_key']
                )
        except (ImportError, Exception):
            pass

        self.combo_rollback.setMinimumWidth(250)
        rollback_layout.addWidget(self.combo_rollback)
        rollback_layout.addStretch()
        layout.addWidget(rollback_group)

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton("通过并继续")
        style_button(self.btn_confirm, "success")
        self.btn_confirm.clicked.connect(self._on_confirm)

        self.btn_modify = QPushButton("按修改意见重做")
        style_button(self.btn_modify, "primary")
        self.btn_modify.clicked.connect(self._on_modify)

        self.btn_rollback = QPushButton("回退重做")
        style_button(self.btn_rollback, "warning")
        self.btn_rollback.clicked.connect(self._on_rollback)

        self.btn_cancel = QPushButton("取消研究")
        style_button(self.btn_cancel, "danger")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_modify)
        btn_layout.addWidget(self.btn_rollback)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _get_stage_content(self) -> str:
        """获取当前阶段 Agent 产出的摘要文本"""
        ctx = self.context
        if not ctx:
            return ""

        name = self.stage_name
        if name in ("architect", "literature"):
            parts = []
            if getattr(ctx, "research_topic", None):
                parts.append(f"课题: {ctx.research_topic}")
            if getattr(ctx, "innovation_points", None):
                parts.append("创新点:\n" + "\n".join(f"  - {p}" for p in ctx.innovation_points))
            if getattr(ctx, "research_gap", None):
                parts.append(f"研究空白: {ctx.research_gap[:300]}")
            return "\n\n".join(parts)

        elif name in ("theorist", "derivation"):
            parts = []
            if getattr(ctx, "control_law_latex", None):
                # 完整显示控制律，不截断
                parts.append(f"控制律:\n{ctx.control_law_latex}")
            if getattr(ctx, "lyapunov_function", None):
                # 完整显示Lyapunov函数
                parts.append(f"Lyapunov函数:\n{ctx.lyapunov_function}")
            if getattr(ctx, "stability_proof_latex", None):
                # 完整显示稳定性证明
                parts.append(f"稳定性证明:\n{ctx.stability_proof_latex}")
            return "\n\n".join(parts)

        elif name in ("engineer", "simulation"):
            if getattr(ctx, "matlab_code", None):
                return f"MATLAB代码 (前500字符):\n{ctx.matlab_code[:500]}"
            return ""

        elif name in ("simulator", "sim_run"):
            parts = []
            sim_results = getattr(ctx, "simulation_results", None)
            if sim_results:
                stdout = sim_results.get("stdout", "")
                if stdout:
                    parts.append(f"仿真输出 (前300字符):\n{stdout[:300]}")
                figures = sim_results.get("figures", [])
                if figures:
                    parts.append(f"生成图像: {len(figures)} 个")
            metrics = getattr(ctx, "simulation_metrics", None)
            if metrics:
                parts.append(f"性能指标: {metrics}")
            return "\n\n".join(parts) if parts else "(仿真尚未执行)"

        elif name in ("dsp_coder", "dsp_code"):
            parts = []
            if getattr(ctx, "dsp_c_code", None):
                parts.append(f"DSP C代码 (前500字符):\n{ctx.dsp_c_code[:500]}")
            if getattr(ctx, "dsp_header_code", None):
                parts.append(f"DSP头文件 (前300字符):\n{ctx.dsp_header_code[:300]}")
            return "\n\n".join(parts)

        elif name in ("scribe", "paper"):
            if getattr(ctx, "paper_latex", None):
                return f"论文LaTeX (前500字符):\n{ctx.paper_latex[:500]}"
            return ""

        return ""

    def _on_confirm(self) -> None:
        self.modification = None
        self.rollback_to = None
        self.accept()

    def _on_modify(self) -> None:
        self.modification = self.modify_edit.toPlainText().strip()
        if not self.modification:
            QMessageBox.warning(self, "提示", "请输入修改意见")
            return
        self.rollback_to = None
        self.accept()

    def _on_rollback(self) -> None:
        target = self.combo_rollback.currentData()
        if not target:
            QMessageBox.warning(self, "提示", "请选择要回退到的阶段")
            return
        self.rollback_to = target
        self.modification = None
        self.accept()


class TopicConfirmationDialog(QDialog):
    """课题确认对话框 - 支持与 AI 多次对话修改"""

    # 内部信号，用于线程安全地传递 LLM 结果到主线程
    _llm_result_ready = pyqtSignal(str, str, str, str)  # topic, innovations, gap, explanation
    _llm_text_ready = pyqtSignal(str)
    _llm_finished = pyqtSignal()

    def __init__(
        self,
        context: GlobalContext,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.context = context
        self.parent_window = parent
        self._api_config: Optional[object] = None
        self._llm_busy = False  # 防止并发 LLM 调用

        # 从父窗口获取 API 配置
        if parent and hasattr(parent, "orchestrator"):
            agent = parent.orchestrator.agents.get("architect")
            if agent and hasattr(agent, "api_config"):
                self._api_config = agent.api_config

        # 连接内部信号
        self._llm_result_ready.connect(self._apply_llm_result)
        self._llm_text_ready.connect(self._show_llm_text)
        self._llm_finished.connect(self._on_llm_finished)

        self.setWindowTitle("研究课题确认与优化")
        self.setMinimumSize(800, 700)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Vertical)

        # ===== 上半部分: 课题内容 =====
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        info_label = QLabel("AI已生成研究课题，您可以直接修改或与AI对话进一步优化：")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        make_selectable(info_label)
        content_layout.addWidget(info_label)

        # 研究课题
        topic_group = QGroupBox("研究课题")
        topic_layout = QVBoxLayout(topic_group)
        self.topic_edit = QTextEdit()
        self.topic_edit.setPlainText(self.context.research_topic or "")
        self.topic_edit.setMaximumHeight(70)
        topic_layout.addWidget(self.topic_edit)
        content_layout.addWidget(topic_group)

        # 创新点
        innovation_group = QGroupBox("创新点")
        innovation_layout = QVBoxLayout(innovation_group)
        self.innovation_edit = QTextEdit()
        points = getattr(self.context, "innovation_points", None) or []
        innovations_text = "\n".join(f"• {p}" for p in points)
        self.innovation_edit.setPlainText(innovations_text)
        self.innovation_edit.setMaximumHeight(100)
        innovation_layout.addWidget(self.innovation_edit)
        content_layout.addWidget(innovation_group)

        # 研究空白
        gap_group = QGroupBox("研究空白分析")
        gap_layout = QVBoxLayout(gap_group)
        self.gap_edit = QTextEdit()
        self.gap_edit.setPlainText(getattr(self.context, "research_gap", "") or "")
        self.gap_edit.setMaximumHeight(80)
        gap_layout.addWidget(self.gap_edit)
        content_layout.addWidget(gap_group)

        splitter.addWidget(content_widget)

        # ===== 下半部分: AI对话区 =====
        chat_group = QGroupBox("与AI对话优化课题")
        chat_layout = QVBoxLayout(chat_group)

        # 对话历史显示
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        self.chat_display.setMinimumHeight(120)
        chat_layout.addWidget(self.chat_display)

        # 输入区
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入您的修改建议...")
        self.chat_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.chat_input)

        self.btn_send = QPushButton("发送")
        style_button(self.btn_send, "primary")
        self.btn_send.clicked.connect(self._send_message)
        input_layout.addWidget(self.btn_send)
        chat_layout.addLayout(input_layout)

        splitter.addWidget(chat_group)
        splitter.setSizes([350, 250])
        layout.addWidget(splitter)

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton("确认并继续")
        style_button(self.btn_confirm, "success")
        self.btn_confirm.clicked.connect(self.accept)

        self.btn_cancel = QPushButton("取消研究")
        style_button(self.btn_cancel, "danger")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_confirm)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _send_message(self) -> None:
        """发送消息给 AI"""
        if self._llm_busy:
            return
        message = self.chat_input.text().strip()
        if not message:
            return

        # 显示用户消息
        self._append_chat("用户", message, "#4ec9b0")
        self.chat_input.clear()

        # 获取当前课题内容
        current_topic = self.topic_edit.toPlainText().strip()
        current_innovations = self.innovation_edit.toPlainText().strip()
        current_gap = self.gap_edit.toPlainText().strip()

        # 模拟 AI 响应
        self._simulate_ai_response(message, current_topic, current_innovations, current_gap)

    def _append_chat(self, sender: str, message: str, color: str) -> None:
        """添加聊天消息（HTML-escaped）"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        safe_sender = _html.escape(sender)
        safe_message = _html.escape(message)
        html = f'<span style="color: #858585;">[{timestamp}]</span> '
        html += f'<span style="color: {color}; font-weight: bold;">{safe_sender}:</span> '
        html += f'<span style="color: #d4d4d4;">{safe_message}</span>'
        self.chat_display.append(html)

    def _simulate_ai_response(
        self, user_message: str, topic: str, innovations: str, gap: str
    ) -> None:
        """调用 LLM 优化课题内容，若无 API 配置则使用本地规则"""
        if self._api_config and getattr(self._api_config, "api_key", None):
            self._call_llm_for_topic(user_message, topic, innovations, gap)
            return

        # 本地回退逻辑
        self._local_topic_response(user_message, topic, innovations, gap)

    def _call_llm_for_topic(
        self, user_message: str, topic: str, innovations: str, gap: str
    ) -> None:
        """通过 LLM 优化课题"""
        self._llm_busy = True
        self.btn_send.setEnabled(False)
        self.chat_input.setEnabled(False)
        self._append_chat("AI助手", "正在思考...", "#858585")

        def _run():
            try:
                import asyncio
                from llm_client import call_llm_api

                prompt = f"""你是一个控制系统研究课题优化助手。
当前研究课题: {topic}
当前创新点: {innovations}
当前研究空白: {gap}

用户的修改建议: {user_message}

请根据用户建议优化课题。输出JSON格式:
{{"topic": "优化后的课题", "innovations": "优化后的创新点(每行一个，以•开头)", "gap": "优化后的研究空白", "explanation": "简要说明修改内容"}}
"""
                result = asyncio.run(call_llm_api(self._api_config, prompt))

                # 尝试解析 JSON
                json_match = re.search(r'\{[\s\S]*?\}', result)
                if json_match:
                    data = json.loads(json_match.group())
                    self._llm_result_ready.emit(
                        data.get("topic", topic),
                        data.get("innovations", innovations),
                        data.get("gap", gap),
                        data.get("explanation", "已优化"),
                    )
                    return

                # JSON 解析失败，直接显示响应
                self._llm_text_ready.emit(result[:500])
            except Exception as e:
                self._llm_text_ready.emit(
                    f"LLM调用失败({type(e).__name__})，请直接在编辑框中手动修改。"
                )
            finally:
                self._llm_finished.emit()

        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str, str, str, str)
    def _apply_llm_result(
        self, topic: str, innovations: str, gap: str, explanation: str
    ) -> None:
        """应用 LLM 返回的优化结果"""
        self.topic_edit.setPlainText(topic)
        self.innovation_edit.setPlainText(innovations)
        self.gap_edit.setPlainText(gap)
        self._append_chat("AI助手", explanation, "#569cd6")

    @pyqtSlot(str)
    def _show_llm_text(self, text: str) -> None:
        """显示 LLM 文本响应"""
        self._append_chat("AI助手", text, "#569cd6")

    @pyqtSlot()
    def _on_llm_finished(self) -> None:
        """LLM 调用完成，恢复 UI"""
        self._llm_busy = False
        self.btn_send.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()

    def _local_topic_response(
        self, user_message: str, topic: str, innovations: str, gap: str
    ) -> None:
        """本地规则回退（无 API 时使用）"""
        response = ""

        if "聚焦" in user_message or "具体" in user_message:
            new_topic = topic + "（聚焦于特定应用场景）"
            self.topic_edit.setPlainText(new_topic)
            response = "已将课题聚焦到更具体的应用场景。（提示：配置 API 后可获得 AI 优化建议）"
        elif "创新" in user_message:
            new_innovation = innovations + "\n• 提出新的理论分析框架"
            self.innovation_edit.setPlainText(new_innovation)
            response = "已添加新的创新点。（提示：配置 API 后可获得 AI 优化建议）"
        elif "简化" in user_message or "简洁" in user_message:
            words = topic.split("的")
            if len(words) > 1:
                self.topic_edit.setPlainText("的".join(words[-2:]))
            response = "已简化课题表述。（提示：配置 API 后可获得 AI 优化建议）"
        else:
            response = f"收到您的建议：{user_message}。请直接在上方编辑框中修改，或配置 API 以获得 AI 优化。"

        self._append_chat("AI助手", response, "#569cd6")

    def get_updated_context(self) -> GlobalContext:
        """获取用户修改后的上下文"""
        self.context.research_topic = self.topic_edit.toPlainText().strip()
        innovations_text = self.innovation_edit.toPlainText().strip()
        self.context.innovation_points = [
            line.lstrip("•").strip()
            for line in innovations_text.split("\n")
            if line.strip()
        ]
        self.context.research_gap = self.gap_edit.toPlainText().strip()
        return self.context
