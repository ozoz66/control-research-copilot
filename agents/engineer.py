# -*- coding: utf-8 -*-
"""
工程师Agent (Agent C) - AutoControl-Scientist
负责生成MATLAB仿真代码（仿真执行已拆分至SimulatorAgent）
"""

import re
from pathlib import Path
from typing import Optional

from global_context import GlobalContext
from agents.base import BaseAgent
from output_manager import OutputManager
from logger_config import get_logger
from prompts import PromptTemplates

logger = get_logger(__name__)


class EngineerAgent(BaseAgent):
    """
    工程师Agent (Agent C)
    负责生成MATLAB仿真代码，仿真执行由SimulatorAgent完成
    """

    _default_system_prompt = "你是一位MATLAB仿真专家和控制系统工程师。请生成完整、可运行的MATLAB代码，包含清晰的注释和规范的变量命名。"

    def __init__(self, matlab_path: Optional[str] = None, output_manager: Optional[OutputManager] = None):
        super().__init__("Engineer", "engineer")
        self.matlab_path = matlab_path
        self.output_manager = output_manager

    async def execute(self, context: GlobalContext) -> GlobalContext:
        """
        执行工程师任务 - 仅生成MATLAB代码

        Args:
            context: 全局上下文

        Returns:
            更新后的全局上下文
        """
        context.log_execution(self.name, "MATLAB代码生成", "started")

        # 数据完整性验证（优化交互：检查上游Agent输出）
        validation_warnings = []
        if not context.control_law_latex or len(context.control_law_latex) < 200:
            validation_warnings.append("控制律推导内容过短或缺失")
        if not context.lyapunov_function:
            validation_warnings.append("Lyapunov函数未定义")
        if not context.stability_proof_latex or len(context.stability_proof_latex) < 100:
            validation_warnings.append("稳定性证明内容过短或缺失")

        if validation_warnings:
            warning_msg = "数据完整性警告: " + "; ".join(validation_warnings)
            logger.warning(warning_msg)
            context.log_execution(self.name, "数据验证", "warning", warning_msg)
            # 不抛出异常，允许Engineer尝试生成代码（可能LLM能补全）

        # 使用LLM生成MATLAB代码
        matlab_prompt = PromptTemplates.engineer_matlab(context)
        matlab_prompt += self._get_feedback_prompt_section()
        matlab_prompt += """

注意: 如果你发现上游Agent的输出（如控制律推导）严重不满足要求导致无法生成仿真代码，
可以在响应JSON中包含如下字段来请求重做:
{"request_redo": {"agent": "theorist", "reason": "具体原因"}}"""

        if self.api_config is None or not self.api_config.api_key:
            raise RuntimeError(
                "Engineer Agent 必须配置 API 才能生成MATLAB代码。"
                "请在配置中设置有效的 API Key 和 Base URL。"
            )

        # 调用LLM生成代码
        matlab_code = await self._call_llm(matlab_prompt)
        if not matlab_code or not matlab_code.strip():
            raise RuntimeError("LLM未能生成有效的MATLAB代码，请检查API配置和网络连接。")

        # 检查是否包含重做请求
        self._check_redo_request(matlab_code, context)

        # 提取MATLAB代码块
        matlab_code = self._extract_matlab_code(matlab_code)

        context.matlab_code = matlab_code

        # 保存.m文件
        try:
            if self.output_manager and self.output_manager.paper_dir:
                working_dir_path = self.output_manager.get_matlab_working_dir()
            else:
                working_dir_path = Path("./output")
                working_dir_path.mkdir(parents=True, exist_ok=True)

            if self.output_manager:
                # 确保MATLAB代码目录存在
                matlab_dir = self.output_manager.code_dir / "matlab"
                matlab_dir.mkdir(parents=True, exist_ok=True)
                m_file_path = self.output_manager.save_matlab_code(matlab_code, "simulation_main.m")
            else:
                m_file_path = working_dir_path / "simulation_main.m"
                with open(m_file_path, 'w', encoding='utf-8') as f:
                    f.write(matlab_code)
            context.matlab_m_file_path = str(m_file_path)
            logger.info("MATLAB代码已保存到: %s", m_file_path)
        except Exception as e:
            error_msg = f"保存MATLAB代码失败: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        context.log_execution(self.name, "MATLAB代码生成", "success")
        return context

    def _extract_matlab_code(self, text: str) -> str:
        """从LLM响应中提取MATLAB代码并进行语法预验证"""
        code = self._extract_code_block(text, "matlab")
        code = self._validate_matlab_syntax(code)
        return code

    def _validate_matlab_syntax(self, code: str) -> str:
        """MATLAB代码基本语法预验证和修复"""
        lines = code.split('\n')
        fixed_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') and not stripped.startswith('#define'):
                continue
            fixed_lines.append(line)

        code = '\n'.join(fixed_lines)

        has_figure = 'figure' in code.lower()
        has_print_png = 'print' in code and 'png' in code
        has_plot = 'plot' in code.lower()

        if not has_figure and has_plot:
            code = re.sub(r'(?m)^(\s*plot\()', r'figure();\n\1', code, count=1)

        if has_figure and not has_print_png:
            code += "\n\n% Auto-save figures\nfigures = findall(0, 'Type', 'figure');\n"
            code += "for i = 1:length(figures)\n"
            code += "    print(figures(i), '-dpng', '-r300', sprintf('figure_%d.png', i));\n"
            code += "end\n"

        return code
