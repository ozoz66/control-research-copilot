# -*- coding: utf-8 -*-
"""
仿真执行Agent (Simulator) - AutoControl-Scientist
从EngineerAgent拆分而来，负责MATLAB仿真执行、结果分析与自动调参
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from global_context import GlobalContext
from agents.base import BaseAgent
from output_manager import OutputManager
from logger_config import get_logger
from prompts import PromptTemplates

logger = get_logger(__name__)


@dataclass
class MatlabExecutionResult:
    """MATLAB执行结果"""
    success: bool
    stdout: str
    stderr: str
    figures: List[str]  # 生成的图像文件路径
    data: Dict[str, Any]  # 导出的数据


class MatlabEngine:
    """
    MATLAB引擎封装类
    支持两种执行模式:
    1. matlab.engine (需要兼容的Python版本)
    2. 命令行调用 (通用，无版本限制)
    """

    def __init__(self, matlab_path: Optional[str] = None):
        self.matlab_path = matlab_path or self._find_matlab_path()
        self.engine = None
        self._is_connected = False
        self._use_cli_mode = False

    def _find_matlab_path(self) -> str:
        """自动查找MATLAB安装路径"""
        import platform

        if platform.system() == "Windows":
            possible_paths = [
                r"D:\Program Files\MATLAB\R2024a",
                r"D:\Program Files\MATLAB\R2023b",
                r"C:\Program Files\MATLAB\R2024a",
                r"C:\Program Files\MATLAB\R2023b",
                r"C:\Program Files\MATLAB\R2023a",
            ]
            for p in possible_paths:
                if Path(p).exists():
                    return p
        return ""

    def connect(self) -> bool:
        """连接MATLAB引擎"""
        try:
            import matlab.engine

            shared_sessions = matlab.engine.find_matlab()
            if shared_sessions:
                self.engine = matlab.engine.connect_matlab(shared_sessions[0])
                logger.info("已连接到现有MATLAB会话: %s", shared_sessions[0])
            else:
                logger.info("启动新的MATLAB引擎...")
                self.engine = matlab.engine.start_matlab()
                logger.info("MATLAB引擎启动成功")

            self._is_connected = True
            self._use_cli_mode = False
            return True

        except ImportError:
            logger.info("matlab.engine未安装，切换到命令行模式")
            return self._connect_cli_mode()
        except Exception as e:
            logger.warning("MATLAB引擎连接失败: %s，切换到命令行模式", e)
            return self._connect_cli_mode()

    def _connect_cli_mode(self) -> bool:
        """使用命令行模式连接"""
        if not self.matlab_path:
            logger.error("未找到MATLAB安装路径，请在GUI的'API与模型配置'页面设置MATLAB路径")
            return False

        matlab_exe = Path(self.matlab_path) / "bin" / "matlab.exe"
        if not matlab_exe.exists():
            matlab_exe = Path(self.matlab_path) / "bin" / "win64" / "matlab.exe"

        if not matlab_exe.exists():
            logger.error("未找到MATLAB可执行文件: %s", matlab_exe)
            return False

        logger.info("命令行模式: 使用 %s", matlab_exe)
        self._use_cli_mode = True
        self._is_connected = True
        return True

    def disconnect(self):
        """断开MATLAB引擎连接"""
        if self.engine:
            try:
                self.engine.quit()
            except Exception as e:
                logger.warning("关闭MATLAB引擎时出错: %s", e)
            self.engine = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        if self._use_cli_mode:
            return self._is_connected
        return self._is_connected and self.engine is not None

    def execute_script(
        self,
        script_content: str,
        working_dir: str,
        script_name: str = "simulation_main.m"
    ) -> MatlabExecutionResult:
        """执行MATLAB脚本"""
        script_path = Path(working_dir) / script_name
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        if self._use_cli_mode:
            return self._execute_cli(script_path, working_dir)
        else:
            return self._execute_engine(script_path, working_dir, script_name)

    @staticmethod
    def _validate_path_safe(value: str, label: str) -> None:
        """校验路径/脚本名不含危险字符，防止MATLAB命令注入"""
        dangerous = set(';|&$`!><"')
        found = dangerous.intersection(value)
        if found:
            raise ValueError(f"{label} 包含非法字符 {found}，拒绝执行")

    def _execute_cli(self, script_path: Path, working_dir: str) -> MatlabExecutionResult:
        """通过命令行执行MATLAB脚本"""
        import subprocess

        matlab_exe = Path(self.matlab_path) / "bin" / "matlab.exe"
        if not matlab_exe.exists():
            matlab_exe = Path(self.matlab_path) / "bin" / "win64" / "matlab.exe"

        script_name = script_path.stem

        # 校验路径安全性
        self._validate_path_safe(str(working_dir), "working_dir")
        self._validate_path_safe(str(script_name), "script_name")

        # 转义路径中的单引号
        safe_working_dir = str(working_dir).replace("'", "''")
        safe_script_name = str(script_name).replace("'", "''")

        matlab_cmd = [
            str(matlab_exe),
            "-batch",
            f"cd('{safe_working_dir}'); run('{safe_script_name}'); exit;"
        ]

        logger.info("执行MATLAB命令: %s", " ".join(matlab_cmd))

        try:
            result = subprocess.run(
                matlab_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=working_dir
            )

            figures = list(Path(working_dir).glob("*.png")) + \
                      list(Path(working_dir).glob("*.fig"))

            success = result.returncode == 0

            return MatlabExecutionResult(
                success=success,
                stdout=result.stdout,
                stderr=result.stderr,
                figures=[str(f) for f in figures],
                data={}
            )

        except subprocess.TimeoutExpired:
            return MatlabExecutionResult(
                success=False,
                stdout="",
                stderr="MATLAB执行超时（超过5分钟）",
                figures=[],
                data={}
            )
        except Exception as e:
            return MatlabExecutionResult(
                success=False,
                stdout="",
                stderr=f"执行失败: {str(e)}",
                figures=[],
                data={}
            )

    def _execute_engine(
        self,
        script_path: Path,
        working_dir: str,
        script_name: str
    ) -> MatlabExecutionResult:
        """通过matlab.engine执行脚本"""
        if not self.is_connected:
            return MatlabExecutionResult(
                success=False,
                stdout="",
                stderr="MATLAB引擎未连接",
                figures=[],
                data={}
            )

        self.engine.cd(working_dir, nargout=0)

        import io
        stdout = io.StringIO()
        stderr = io.StringIO()

        try:
            script_func_name = script_name.replace('.m', '')
            safe_script_func_name = script_func_name.replace("'", "''")
            self.engine.eval(f"run('{safe_script_func_name}')", nargout=0,
                           stdout=stdout, stderr=stderr)

            figures = list(Path(working_dir).glob("*.png")) + \
                      list(Path(working_dir).glob("*.fig"))

            return MatlabExecutionResult(
                success=True,
                stdout=stdout.getvalue(),
                stderr=stderr.getvalue(),
                figures=[str(f) for f in figures],
                data={}
            )

        except Exception as e:
            return MatlabExecutionResult(
                success=False,
                stdout=stdout.getvalue(),
                stderr=f"{stderr.getvalue()}\n异常: {str(e)}",
                figures=[],
                data={}
            )

    def execute_with_retry(
        self,
        script_content: str,
        working_dir: str,
        max_retries: int = 3,
        fix_callback=None
    ) -> MatlabExecutionResult:
        """带自愈循环的MATLAB执行"""
        current_code = script_content

        for attempt in range(max_retries):
            logger.info("MATLAB执行尝试 %d/%d", attempt + 1, max_retries)

            result = self.execute_script(current_code, working_dir)

            if result.success:
                logger.info("MATLAB执行成功")
                return result

            if fix_callback and attempt < max_retries - 1:
                logger.warning("执行失败，尝试自动修复... 错误信息: %s", result.stderr[:500])

                fixed_code = fix_callback(result.stderr, current_code)
                if fixed_code and fixed_code != current_code:
                    current_code = fixed_code
                    continue

            break

        return result


class SimulatorAgent(BaseAgent):
    """
    仿真执行Agent
    负责连接MATLAB引擎、执行仿真代码、分析结果并自动调参
    """

    _default_system_prompt = "你是一位MATLAB仿真专家和控制系统工程师。请生成完整、可运行的MATLAB代码，包含清晰的注释和规范的变量命名。"

    def __init__(self, matlab_path: Optional[str] = None, output_manager: Optional[OutputManager] = None):
        super().__init__("Simulator", "simulator")
        self.matlab_engine = MatlabEngine(matlab_path)
        self.output_manager = output_manager

    async def execute(self, context: GlobalContext) -> GlobalContext:
        """
        执行仿真任务：读取context.matlab_code → 连接MATLAB → 执行+重试 → 分析+调参 → 写回结果
        """
        context.log_execution(self.name, "MATLAB仿真执行", "started")

        matlab_code = context.matlab_code
        if not matlab_code or not matlab_code.strip():
            context.log_execution(self.name, "MATLAB仿真执行", "failed", "无MATLAB代码可执行")
            return context

        # 获取工作目录
        if self.output_manager and self.output_manager.paper_dir:
            working_dir_path = self.output_manager.get_matlab_working_dir()
        else:
            working_dir_path = Path("./output")
            working_dir_path.mkdir(exist_ok=True)

        # 连接MATLAB引擎
        if not self.matlab_engine.connect():
            context.log_execution(self.name, "MATLAB引擎连接", "failed")
            # 保存代码供手动执行
            if self.output_manager:
                m_file_path = self.output_manager.save_matlab_code(matlab_code, "simulation_main.m")
            else:
                m_file_path = working_dir_path / "simulation_main.m"
                with open(m_file_path, 'w', encoding='utf-8') as f:
                    f.write(matlab_code)
            context.matlab_m_file_path = str(m_file_path)
            return context

        # 执行仿真（带自愈循环），确保 disconnect 一定被调用
        working_dir = str(working_dir_path.absolute())
        try:
            def fix_code_callback(error_msg: str, code: str) -> str:
                """代码修复回调 - 通过LLM自动修复MATLAB代码"""
                if self.api_config and self.api_config.api_key:
                    fix_prompt = PromptTemplates.simulator_fix_code(error_msg, code)
                    try:
                        import concurrent.futures
                        import asyncio as aio

                        def run_async_in_new_loop():
                            new_loop = aio.new_event_loop()
                            aio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(self._call_llm(fix_prompt))
                            finally:
                                new_loop.close()

                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            fixed = pool.submit(run_async_in_new_loop).result(timeout=120)

                        if fixed and fixed.strip():
                            return self._extract_code_block(fixed, "matlab")
                    except Exception as e:
                        logger.error("LLM代码修复失败: %s", e)
                return code

            result = self.matlab_engine.execute_with_retry(
                matlab_code,
                working_dir,
                max_retries=3,
                fix_callback=fix_code_callback
            )

            # 处理结果
            if result.success:
                context.figure_paths = [Path(f).name for f in result.figures]
                context.simulation_results = {
                    "stdout": result.stdout,
                    "figures": result.figures,
                    "figures_relative": context.figure_paths,
                    "data": result.data
                }
                context.log_execution(self.name, "MATLAB仿真执行", "success")

                # 仿真结果分析 + 自动调参重跑
                if self.api_config and self.api_config.api_key:
                    context = await self._analyze_and_refine_simulation(
                        context, matlab_code, working_dir
                    )
            else:
                context.error_log.append(f"MATLAB仿真失败: {result.stderr}")
                context.log_execution(self.name, "MATLAB仿真执行", "failed", result.stderr)
        finally:
            self.matlab_engine.disconnect()

        return context

    async def _analyze_and_refine_simulation(
        self,
        context: GlobalContext,
        matlab_code: str,
        working_dir: str,
        max_refinements: int = 2
    ) -> GlobalContext:
        """使用LLM分析仿真结果，判断结果是否合理，不合理则自动调参重跑。"""
        for attempt in range(max_refinements):
            analysis_prompt = PromptTemplates.simulator_analysis(context)
            analysis_result = await self._call_llm(analysis_prompt)

            if not analysis_result:
                break

            analysis = self._parse_analysis_result(analysis_result)
            context.simulation_results["analysis"] = analysis

            if analysis.get("acceptable", True):
                context.log_execution(
                    self.name, "仿真结果分析", "success",
                    f"仿真结果合格: {analysis.get('summary', '')}"
                )
                break

            context.log_execution(
                self.name, "仿真结果分析", "warning",
                f"仿真结果不合格 (第{attempt+1}次): {analysis.get('issues', [])}"
            )

            refine_prompt = PromptTemplates.simulator_refine(
                matlab_code, analysis
            )
            refined_code = await self._call_llm(refine_prompt)
            if not refined_code or not refined_code.strip():
                break

            refined_code = self._extract_code_block(refined_code, "matlab")
            if refined_code == matlab_code:
                break

            matlab_code = refined_code
            context.matlab_code = matlab_code

            if self.matlab_engine.is_connected:
                result = self.matlab_engine.execute_script(
                    matlab_code, working_dir
                )
                if result.success:
                    context.figure_paths = [Path(f).name for f in result.figures]
                    context.simulation_results.update({
                        "stdout": result.stdout,
                        "figures": result.figures,
                        "figures_relative": context.figure_paths,
                        "data": result.data
                    })
                    context.log_execution(
                        self.name, f"仿真重跑(第{attempt+2}次)", "success"
                    )
                else:
                    context.log_execution(
                        self.name, f"仿真重跑(第{attempt+2}次)", "failed",
                        result.stderr[:200]
                    )
                    break

        return context


    def _parse_analysis_result(self, response: str) -> Dict:
        """解析LLM仿真分析结果"""
        try:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            candidates = []
            brace_depth = 0
            start = -1
            for i, ch in enumerate(response):
                if ch == '{':
                    if brace_depth == 0:
                        start = i
                    brace_depth += 1
                elif ch == '}':
                    brace_depth -= 1
                    if brace_depth == 0 and start >= 0:
                        candidates.append(response[start:i+1])
                        start = -1
            for candidate in reversed(candidates):
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "acceptable" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.warning("解析仿真分析结果失败: %s", e)
        return {"acceptable": False, "summary": "分析结果解析失败，建议人工检查",
                "issues": ["LLM返回的分析结果格式不正确"], "score": 50}
