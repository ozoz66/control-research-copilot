import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from global_context import GlobalContext
from agents.base import BaseAgent
from logger_config import get_logger
from prompts import PromptTemplates

logger = get_logger(__name__)


@dataclass
class MathematicalDerivation:
    """数学推导结果数据类"""
    system_model: str = ""          # 系统模型LaTeX
    assumptions: List[str] = field(default_factory=list)  # 数学假设
    control_law: str = ""           # 控制律LaTeX
    lyapunov_function: str = ""     # Lyapunov函数
    stability_proof: str = ""       # 稳定性证明
    parameter_conditions: str = ""   # 参数条件
    convergence_analysis: str = ""   # 收敛性分析


class TheoristAgent(BaseAgent):
    """
    理论家Agent (Agent B)
    负责严格的数学推导和稳定性分析
    """

    def __init__(self):
        """
        初始化理论家Agent
        """
        super().__init__("Theorist", "theorist")
        self._load_theory_kb()

    def _load_theory_kb(self):
        """从YAML加载理论知识库"""
        kb_path = Path(__file__).parent.parent / "prompts" / "control_systems" / "theory_kb.yaml"
        try:
            import yaml

            with open(kb_path, 'r', encoding='utf-8') as f:
                self.theory_kb = yaml.safe_load(f)
            logger.info("成功加载理论知识库: %s", kb_path)
        except Exception as e:
            logger.error("加载理论知识库失败: %s", e)
            self.theory_kb = {
                "control_laws": {},
                "lyapunov_templates": {},
                "stability_proof_templates": {},
                "parameter_tuning_guides": {}
            }

    @property
    def CONTROL_LAW_TEMPLATES(self):
        return self.theory_kb.get("control_laws", {})

    @property
    def LYAPUNOV_TEMPLATES(self):
        return self.theory_kb.get("lyapunov_templates", {})

    @property
    def STABILITY_PROOF_TEMPLATES(self):
        return self.theory_kb.get("stability_proof_templates", {})

    async def execute(self, context: GlobalContext) -> GlobalContext:
        """
        执行理论家任务

        Args:
            context: 全局上下文

        Returns:
            更新后的全局上下文
        """
        context.log_execution(self.name, "数学推导", "started")

        # 分析控制策略配置
        config = context.research_config
        control_type = self._determine_control_type(config)

        # 步骤1: 建立系统模型
        system_model = self._generate_system_model(config)
        context.log_execution(self.name, "系统建模", "success")

        # 步骤2: 生成数学假设
        assumptions = self._generate_assumptions(config)
        context.mathematical_assumptions = assumptions

        # 步骤3: 设计控制律 - 必须配置API
        if self.api_config is None or not self.api_config.api_key:
            raise RuntimeError(
                "Theorist Agent 必须配置 API 才能进行数学推导。"
                "请在配置中设置有效的 API Key 和 Base URL。"
            )
        derivation = await self._derive_with_llm(context, control_type)

        # 更新上下文
        # 保存系统模型（修复P0问题：system_model_latex未保存）
        context.system_model_latex = system_model

        context.control_law_latex = self._assemble_full_derivation(
            system_model,
            assumptions,
            derivation
        )
        context.stability_proof_latex = derivation.stability_proof
        context.lyapunov_function = derivation.lyapunov_function
        context.parameter_tuning_guide = self._generate_tuning_guide(control_type)

        # 生成观测器设计（修复P0问题：observer_design_latex从未生成）
        observer_key = config.get("composite_architecture", {}).get("observer", {}).get("key", "")
        if observer_key and observer_key != "none":
            context.observer_design_latex = self._generate_observer_design(observer_key, control_type)
        else:
            context.observer_design_latex = ""

        context.log_execution(self.name, "数学推导", "success",
                            f"控制类型: {control_type}")

        return context

    def _determine_control_type(self, config: Dict[str, Any]) -> str:
        """
        根据配置确定控制类型

        Args:
            config: 研究配置

        Returns:
            控制类型标识
        """
        main_algo = config.get("main_algorithm", {}).get("key", "")
        feedback = config.get("composite_architecture", {}).get("feedback", {}).get("key", "")
        observer = config.get("composite_architecture", {}).get("observer", {}).get("key", "")
        objectives = [obj.get("key", "") for obj in config.get("performance_objectives", [])]

        # 优先级判断
        if "finite_time" in objectives:
            return "finite_time_smc"
        elif observer == "eso":
            return "eso_based"
        elif main_algo == "adaptive" and feedback == "smc":
            return "adaptive_smc"
        elif feedback == "smc":
            return "smc"
        else:
            return "pid"

    def _generate_observer_design(self, observer_key: str, control_type: str) -> str:
        """
        生成观测器设计LaTeX

        Args:
            observer_key: 观测器类型（eso, luenberger, kalman等）
            control_type: 控制类型

        Returns:
            观测器设计的LaTeX代码
        """
        if observer_key == "eso":
            return r"""
\section{扩展状态观测器设计}

设计三阶扩展状态观测器(ESO)估计系统状态和总扰动:
\begin{equation}
\begin{cases}
\dot{\hat{x}}_1 = \hat{x}_2 + \beta_1 (x_1 - \hat{x}_1) \\
\dot{\hat{x}}_2 = \hat{x}_3 + \beta_2 (x_1 - \hat{x}_1) + b_0 u \\
\dot{\hat{x}}_3 = \beta_3 (x_1 - \hat{x}_1)
\end{cases}
\end{equation}

其中 $\hat{x}_1, \hat{x}_2$ 为状态估计值，$\hat{x}_3$ 为总扰动估计值，$\beta_1, \beta_2, \beta_3$ 为观测器增益。

\textbf{增益设计:} 选择 $\beta_i$ 使观测器特征多项式为 $(\lambda + \omega_o)^3$，其中 $\omega_o$ 为观测器带宽。
"""
        elif observer_key == "luenberger":
            return r"""
\section{Luenberger观测器设计}

设计全阶Luenberger观测器估计系统状态:
\begin{equation}
\dot{\hat{x}} = A\hat{x} + Bu + L(y - C\hat{x})
\end{equation}

其中 $L$ 为观测器增益矩阵，通过配置观测器极点确定。

\textbf{增益矩阵:} 选择 $L$ 使 $(A - LC)$ 的特征值位于左半平面，且比控制器极点更快（通常快2-5倍）。
"""
        elif observer_key == "kalman":
            return r"""
\section{Kalman滤波器设计}

考虑带有过程噪声和测量噪声的随机系统，设计Kalman滤波器:
\begin{equation}
\begin{aligned}
\dot{\hat{x}} &= A\hat{x} + Bu + K_f(y - C\hat{x}) \\
K_f &= PC^T R^{-1}
\end{aligned}
\end{equation}

其中 $P$ 满足Riccati方程:
\begin{equation}
\dot{P} = AP + PA^T - PC^T R^{-1} CP + Q
\end{equation}

$Q$ 为过程噪声协方差矩阵，$R$ 为测量噪声协方差矩阵。
"""
        else:
            return r"""
\section{状态观测器}

对于不可直接测量的状态，设计观测器进行估计。观测器设计应确保估计误差收敛速度快于控制回路。
"""

    def _generate_system_model(self, config: Dict[str, Any]) -> str:
        """生成系统数学模型"""
        return r"""
\section{系统模型}

考虑如下二阶非线性不确定系统:
\begin{equation}
\begin{cases}
\dot{x}_1 = x_2 \\
\dot{x}_2 = f(x) + g(x)u + d(t)
\end{cases}
\end{equation}

其中$x = [x_1, x_2]^T \in \mathbb{R}^2$为系统状态（位置和速度），$u \in \mathbb{R}$为控制输入，$f(x)$为系统非线性项，$g(x) > 0$为控制增益，$d(t)$为外部扰动。

控制目标: 设计控制律$u$使系统输出$y = x_1$能够跟踪期望轨迹$x_d(t)$，即:
\begin{equation}
\lim_{t \to \infty} |x_1(t) - x_d(t)| = 0
\end{equation}

定义跟踪误差:
\begin{equation}
e = x_d - x_1, \quad \dot{e} = \dot{x}_d - x_2
\end{equation}
"""

    def _generate_assumptions(self, config: Dict[str, Any]) -> List[str]:
        """生成数学假设列表"""
        assumptions = [
            r"系统状态$x_1$, $x_2$可测量或可通过观测器估计",
            r"期望轨迹$x_d(t)$及其各阶导数有界且已知",
            r"系统非线性项$f(x)$满足Lipschitz连续条件",
            r"控制增益$g(x)$有界，即存在$0 < g_{min} \leq g(x) \leq g_{max}$"
        ]

        # 根据配置添加特定假设
        observer = config.get("composite_architecture", {}).get("observer", {}).get("key", "")
        objectives = [obj.get("key", "") for obj in config.get("performance_objectives", [])]

        if observer == "eso":
            assumptions.append(r"总扰动$f(x) + d(t)$的导数有界")

        if "finite_time" in objectives:
            assumptions.append(r"初始状态有界，即$\|x(0)\| < \infty$")

        return assumptions

    async def _derive_with_llm(
        self,
        context: GlobalContext,
        control_type: str
    ) -> MathematicalDerivation:
        """
        使用LLM生成定制化的数学推导

        Args:
            context: 全局上下文
            control_type: 控制类型

        Returns:
            数学推导结果
        """
        derivation = MathematicalDerivation()

        prompt = PromptTemplates.theorist_derivation(context)
        prompt += f"\n\n控制策略类型: {control_type}"
        prompt += f"\n创新点需要在推导中体现: {context.innovation_points}"
        prompt += self._get_feedback_prompt_section()
        prompt += """

注意: 如果你发现上游Agent(architect)的课题设计严重不合理或无法进行数学推导，
可以在响应JSON中包含如下字段来请求重做:
{"request_redo": {"agent": "architect", "reason": "具体原因"}}"""

        try:
            logger.info("开始调用LLM进行数学推导...")
            # 数学推导需要较长时间
            latex_content = await self._call_llm(
                prompt, timeout=300, max_retries=2,
                system_prompt="你是一位控制理论专家，擅长非线性控制系统的数学建模、控制律设计和Lyapunov稳定性分析。请输出严格的LaTeX格式数学推导，确保公式正确、逻辑完整。",
                temperature=0.4
            )
            logger.info("LLM返回内容长度: %d 字符", len(latex_content))

            # 检查是否包含重做请求
            self._check_redo_request(latex_content, context)

            # 解析响应，提取各部分
            derivation = self._parse_latex_response(latex_content)
            logger.info("LaTeX响应解析完成")

        except Exception as e:
            logger.error("LLM调用失败: %s", e)
            raise RuntimeError(
                f"LLM数学推导失败: {e}\n"
                "请检查: 1) API Key是否有效 2) 网络连接是否正常 3) 模型名称是否正确"
            )

        return derivation

    def _parse_latex_response(self, latex_content: str) -> MathematicalDerivation:
        """解析LLM返回的LaTeX内容，提取控制律、Lyapunov函数和稳定性证明"""
        derivation = MathematicalDerivation()

        # 保存完整内容作为控制律
        derivation.control_law = latex_content

        # 提取 Lyapunov 函数部分 - 优先匹配section/subsection标题，使用最后一个匹配
        lyap_section_kws = [r'\\(?:sub)?section\{[^}]*[Ll]yapunov[^}]*\}',
                            r'\\(?:sub)?section\{[^}]*李雅普诺夫[^}]*\}']
        lyap_inline_kws = [r'lyapunov', r'李雅普诺夫', r'选取.*?函数']
        lyap_start = -1
        # 先尝试匹配section标题（更精确）
        for kw in lyap_section_kws:
            for match in re.finditer(kw, latex_content, re.IGNORECASE):
                lyap_start = match.start()  # 取最后一个匹配
        # 没有section标题，用内联关键词（取最后一个匹配，通常在推导后段）
        if lyap_start < 0:
            for kw in lyap_inline_kws:
                for match in re.finditer(kw, latex_content, re.IGNORECASE):
                    lyap_start = match.start()

        if lyap_start >= 0:
            # 找到 Lyapunov 段落，提取到下一个 section/subsection 或结尾
            lyap_end_match = re.search(
                r'\\(?:section|subsection)\{',
                latex_content[lyap_start + 10:]
            )
            lyap_end = lyap_start + 10 + lyap_end_match.start() if lyap_end_match else len(latex_content)
            derivation.lyapunov_function = latex_content[lyap_start:lyap_end].strip()
        else:
            # 回退：提取 V = ... 公式
            lyap_match = re.search(
                r'(?:V\s*=\s*\\frac.*?(?:\\end\{equation\}|\\\\|\n\n))',
                latex_content, re.DOTALL
            )
            if lyap_match:
                derivation.lyapunov_function = lyap_match.group().strip()

        # 提取稳定性证明部分 - 优先匹配section标题，使用最后一个匹配
        stab_section_kws = [r'\\(?:sub)?section\{[^}]*[Ss]tability[^}]*\}',
                            r'\\(?:sub)?section\{[^}]*稳定性[^}]*\}']
        stab_inline_kws = [r'\\begin\{theorem\}', r'\\begin\{proof\}',
                           r'稳定性证明', r'稳定性分析',
                           r'[Ss]tability [Pp]roof', r'[Ss]tability [Aa]nalysis']
        stab_start = -1
        for kw in stab_section_kws:
            for match in re.finditer(kw, latex_content, re.IGNORECASE):
                stab_start = match.start()
        if stab_start < 0:
            for kw in stab_inline_kws:
                for match in re.finditer(kw, latex_content, re.IGNORECASE):
                    stab_start = match.start()

        if stab_start >= 0:
            # 找到稳定性证明段，提取到下一个 section 或文末
            stab_end_match = re.search(
                r'\\section\{',
                latex_content[stab_start + 10:]
            )
            stab_end = stab_start + 10 + stab_end_match.start() if stab_end_match else len(latex_content)
            derivation.stability_proof = latex_content[stab_start:stab_end].strip()
        else:
            # 回退：查找含 \dot{V} 或 Barbalat 的段落
            proof_match = re.search(
                r'(?:.*\\dot\{V\}.*(?:\n.*){0,20})',
                latex_content
            )
            if proof_match:
                derivation.stability_proof = proof_match.group().strip()

        # 改进的回退逻辑：尝试更智能的提取
        if not derivation.lyapunov_function:
            # 尝试提取任何包含V(x)或V(e)的equation环境
            v_equations = re.findall(
                r'\\begin\{equation\}.*?V.*?\\end\{equation\}',
                latex_content, re.DOTALL | re.IGNORECASE
            )
            if v_equations:
                # 取最长的equation（通常是完整的Lyapunov函数定义）
                derivation.lyapunov_function = max(v_equations, key=len)
                logger.warning("使用回退方式提取Lyapunov函数")
            else:
                # 最终回退：从完整内容中截取一段
                logger.warning("无法精确提取Lyapunov函数，将使用完整推导")
                derivation.lyapunov_function = latex_content[:2000] + "\n...(Lyapunov函数部分，详见完整推导)"

        if not derivation.stability_proof:
            # 尝试提取任何包含theorem或proof环境的部分
            proof_blocks = re.findall(
                r'\\begin\{(?:theorem|proof)\}.*?\\end\{(?:theorem|proof)\}',
                latex_content, re.DOTALL | re.IGNORECASE
            )
            if proof_blocks:
                derivation.stability_proof = "\n\n".join(proof_blocks)
                logger.warning("使用回退方式提取稳定性证明")
            else:
                # 最终回退
                logger.warning("无法精确提取稳定性证明，将使用完整推导")
                derivation.stability_proof = latex_content[:3000] + "\n...(稳定性证明部分，详见完整推导)"

        return derivation

    def _assemble_full_derivation(
        self,
        system_model: str,
        assumptions: List[str],
        derivation: MathematicalDerivation
    ) -> str:
        """组装完整的数学推导文档"""
        # 格式化假设
        assumptions_latex = r"""
\section{基本假设}
\begin{assumption}
""" + r"""
\end{assumption}
\begin{assumption}
""".join(assumptions) + r"""
\end{assumption}
"""

        full_latex = fr"""
% ========================================
% AutoControl-Scientist 自动生成的数学推导
% ========================================

{system_model}

{assumptions_latex}

\section{{控制律设计}}
{derivation.control_law}

\section{{稳定性分析}}

\subsection{{Lyapunov函数选取}}
{derivation.lyapunov_function}

\subsection{{稳定性证明}}
{derivation.stability_proof}
"""
        return full_latex

    def _generate_tuning_guide(self, control_type: str) -> str:
        """生成参数整定指南"""
        guides = self.theory_kb.get("parameter_tuning_guides", {})
        default_guide = guides.get("pid", "暂无该控制类型的整定指南。")
        return guides.get(control_type, default_guide)



if __name__ == "__main__":
    # 测试代码
    import asyncio

    async def test():
        # 创建测试上下文
        from global_context import GlobalContext
        ctx = GlobalContext()
        ctx.research_config = {
            "main_algorithm": {"key": "adaptive", "name": "自适应控制"},
            "performance_objectives": [
                {"key": "chattering_elimination", "name": "消除抖动"},
                {"key": "finite_time", "name": "有限时间收敛"}
            ],
            "composite_architecture": {
                "feedback": {"key": "smc", "name": "滑模控制"},
                "feedforward": {"key": "none", "name": "无"},
                "observer": {"key": "eso", "name": "扩展状态观测器"}
            }
        }
        ctx.research_topic = "基于ESO的自适应有限时间滑模控制方法"
        ctx.innovation_points = [
            "设计新型有限时间趋近律",
            "ESO与自适应律协同设计",
            "抖振消除与收敛速度的平衡"
        ]

        # 创建Agent
        agent = TheoristAgent()

        # 执行
        print("开始执行理论家Agent...")
        ctx = await agent.execute(ctx)

        # 输出结果
        print(f"\n{'='*60}")
        print("【控制律LaTeX预览（前1000字符）】")
        print(ctx.control_law_latex[:1000])
        print(f"\n{'='*60}")
        print("【参数整定指南预览】")
        print(ctx.parameter_tuning_guide[:500])

    asyncio.run(test())
