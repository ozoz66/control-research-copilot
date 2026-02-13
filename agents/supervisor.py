# -*- coding: utf-8 -*-
"""
监督Agent (Agent S) - AutoControl-Scientist
负责评估各Agent输出质量并决定是否需要改进
完全使用LLM进行内容质量评估，不使用固定模板打分
"""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

from global_context import GlobalContext
from agents.base import BaseAgent
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationResult:
    """评估结果数据类"""
    agent_name: str
    score: float  # 0-100
    passed: bool
    issues: List[str]
    suggestions: List[str]
    rollback_to: Optional[str] = None  # 回退目标agent_key，如 "theorist"


class SupervisorAgent(BaseAgent):
    """
    监督Agent - 完全使用LLM评估其他Agent的输出质量

    评估流程:
    1. 检查是否有内容可评估（无内容直接失败）
    2. 调用LLM进行深度评估（内容质量、学术规范、逻辑一致性）
    3. 返回LLM的评分和建议

    注意: 不使用固定模板打分，完全依赖LLM判断
    """

    PASS_THRESHOLD = 80  # 默认通过阈值
    MAX_ITERATIONS = 3   # 最大迭代次数

    # 按阶段差异化阈值：数学推导和论文要求更高
    STAGE_THRESHOLDS = {
        "architect": 75,
        "theorist": 85,
        "engineer": 78,
        "simulator": 78,
        "dsp_coder": 75,
        "scribe": 85,
    }

    def __init__(self):
        super().__init__("Supervisor", "supervisor")

    async def evaluate(self, agent_key: str, context: GlobalContext) -> EvaluationResult:
        """
        评估Agent输出 - 完全使用LLM评估，不做本地判断

        Args:
            agent_key: Agent标识 (architect/theorist/engineer/scribe)
            context: 全局上下文

        Returns:
            评估结果

        Raises:
            RuntimeError: API未配置或调用失败时
        """
        # 必须使用LLM评估
        if not self.api_config or not self.api_config.api_key:
            raise RuntimeError(
                "Supervisor Agent 必须配置 API 才能进行质量评估。"
                "请在配置中设置有效的 API Key 和 Base URL。"
            )

        # 直接调用LLM进行评估，让LLM判断内容是否完整
        try:
            llm_result = await self._llm_evaluate(agent_key, context)
            return llm_result
        except Exception as e:
            raise RuntimeError(f"LLM评估失败: {e}")

    async def _llm_evaluate(self, agent_key: str, context: GlobalContext) -> EvaluationResult:
        """使用LLM进行深度质量评估"""
        prompt = self._build_evaluation_prompt(agent_key, context)
        response = await self._call_llm(prompt, timeout=120, agent_key=f"supervisor_{agent_key}")

        return self._parse_llm_evaluation(agent_key, response)

    def _build_evaluation_prompt(self, agent_key: str, context: GlobalContext) -> str:
        """构建LLM评估提示词"""
        prompts = {
            "architect": self._build_architect_prompt,
            "theorist": self._build_theorist_prompt,
            "engineer": self._build_engineer_prompt,
            "simulator": self._build_simulator_prompt,
            "dsp_coder": self._build_dsp_coder_prompt,
            "scribe": self._build_scribe_prompt,
        }
        if agent_key in prompts:
            return prompts[agent_key](context)
        # 未知 agent 返回通用评估 prompt
        return self._build_generic_prompt(agent_key, context)

    def _build_architect_prompt(self, context: GlobalContext) -> str:
        return f"""你是控制系统领域的学者，请评估以下AI生成的研究课题设计。

【研究课题】
{context.research_topic}

【创新点】
{chr(10).join(f'- {p}' for p in context.innovation_points) if context.innovation_points else '(无)'}

【研究空白分析】
{context.research_gap[:1000] if context.research_gap else '(无)'}

【检索到的文献】
{self._format_literature(context.literature_results)}

请评估以下方面:
1. 课题是否有明确的研究方向和目标
2. 创新点是否具体可行
3. 研究空白分析是否合理

评分标准：
- 90-100分：课题完整、创新点明确、研究空白分析充分
- 80-89分：课题基本完整，有小问题需要改进
- 70-79分：课题有明显不足，需要较大改进
- 60分以下：课题不完整或有严重问题

如果发现问题的根源在上游Agent（如theorist的数学推导有漏洞），请在rollback_to字段指定应回退到哪个Agent重做。
可选的rollback_to值: "architect"(文献课题), "theorist"(数学推导), "engineer"(MATLAB仿真), "dsp_coder"(DSP代码), "scribe"(论文撰写)。
如果不需要回退，rollback_to设为null。

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=80为通过), "issues": ["问题1", "问题2"], "suggestions": ["建议1", "建议2"], "rollback_to": null}}

只返回JSON，不要其他文字。"""

    def _build_theorist_prompt(self, context: GlobalContext) -> str:
        # 获取完整内容用于评估
        control_law = context.control_law_latex if context.control_law_latex else "(无)"
        lyapunov = context.lyapunov_function if context.lyapunov_function else "(无)"
        stability = context.stability_proof_latex if context.stability_proof_latex else "(无)"

        # 大幅提高截断限制，确保supervisor能看到完整内容
        # 只在内容极长时才截断（>10000字符），避免评估不准
        if len(control_law) > 10000:
            control_law = control_law[:10000] + "\n...(内容过长已截断)"
        if len(stability) > 10000:
            stability = stability[:10000] + "\n...(内容过长已截断)"
        if len(lyapunov) > 5000:
            lyapunov = lyapunov[:5000] + "\n...(内容过长已截断)"

        # 获取历史评分，作为参考基准
        history = context.supervision_history.get("theorist", [])
        history_str = ""
        if history:
            history_str = "\n【历史评分参考】\n"
            for h in history:
                history_str += f"第{h['iteration']}次: {h['score']}分 - {'通过' if h['passed'] else '未通过'}\n"
            history_str += "\n【重要】如果本次内容已针对性改进，请给予适当提升分数；如果仍有同样问题，才应降低分数。避免无理由的评分波动。\n"

        return f"""你是控制理论领域的学者，请评估以下AI生成的数学推导。

【研究课题】
{context.research_topic}

【控制律设计】
{control_law}

【Lyapunov函数】
{lyapunov}

【稳定性证明】
{stability}
{history_str}
请评估以下方面:
1. 控制律设计是否完整（需包含显式的u(x)表达式，不能只有框架）
2. 数学推导是否有基本的逻辑（推导步骤连贯，无明显跳跃）
3. 是否包含稳定性分析（Lyapunov函数+导数分析+稳定性结论）

【明确的评分标准】：
- 90-100分：三个方面都完整且严谨，推导逻辑清晰，可以直接用于论文
- 85-89分：三个方面都有，但某些细节需要完善（如参数整定未明确、部分推导略简略）
- 80-84分：三个方面都有，但某一方面有明显不足（如控制律设计不够详细、或稳定性证明有小漏洞）
- 75-79分：缺少某个重要组成部分（如Lyapunov函数未给出具体形式、或控制律只有文字描述无公式）
- 70-74分：多个方面都有明显不足，但基本框架存在
- 60-69分：推导严重不完整，只有框架性描述
- <60分：推导缺失或有严重逻辑错误

【评分原则】：
1. 如果AI已根据上次建议改进，且改进合理，应该给予更高分数（至少+5分）
2. 如果改进导致其他部分变差，只扣相应部分的分（不应大幅降分）
3. 同样内容在不同评估中应给出相近分数（误差不超过±3分）

如果问题根源在上游Agent，请在rollback_to字段指定回退目标(architect/theorist/engineer/dsp_coder/scribe)，否则设为null。

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=85为通过), "issues": ["具体问题1", "具体问题2"], "suggestions": ["针对性建议1", "针对性建议2"], "rollback_to": null}}

【重要】issues和suggestions必须具体明确，不要使用"不够完整"这种模糊描述，而应指出具体缺少什么。

只返回JSON。"""

    def _build_engineer_prompt(self, context: GlobalContext) -> str:
        matlab_code = context.matlab_code if context.matlab_code else "(无)"

        # 提高截断限制到8000字符（优化：让supervisor看到更完整的代码）
        if len(matlab_code) > 8000:
            matlab_code = matlab_code[:8000] + "\n% ...(代码过长已截断)"

        return f"""请评估以下AI生成的MATLAB仿真代码。

【MATLAB代码】
```matlab
{matlab_code}
```

请评估:
1. MATLAB代码是否包含基本的仿真逻辑（系统模型、控制器、仿真循环）
2. 代码结构是否清晰，变量命名是否规范
3. 是否包含图形输出和保存代码

评分标准：
- 90-100分：代码完整可运行
- 80-89分：代码基本完整
- 70-79分：代码有明显不足
- 60分以下：代码不完整

如果问题根源在上游Agent，请在rollback_to字段指定回退目标(architect/theorist/engineer/simulator/dsp_coder/scribe)，否则设为null。

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=80为通过), "issues": ["问题1"], "suggestions": ["建议1"], "rollback_to": null}}

只返回JSON。"""

    def _build_simulator_prompt(self, context: GlobalContext) -> str:
        stdout = context.simulation_results.get("stdout", "") if context.simulation_results else ""
        figures = context.simulation_results.get("figures", []) if context.simulation_results else []
        metrics = context.simulation_metrics or {}

        if len(stdout) > 2000:
            stdout = stdout[:2000] + "\n...(输出过长已截断)"

        return f"""请评估以下MATLAB仿真的执行结果。

【研究课题】
{context.research_topic}

【仿真输出】
{stdout if stdout else '(无输出)'}

【生成的图像】
{', '.join([Path(f).name for f in figures]) if figures else '(无图像)'}

【性能指标】
{json.dumps(metrics, ensure_ascii=False) if metrics else '(无)'}

请评估:
1. 仿真是否成功完成（有输出结果和图像）
2. 结果是否合理（误差收敛、控制量合理、无严重抖振）
3. 图像是否成功生成

评分标准：
- 90-100分：仿真成功，结果合理，图像完整
- 80-89分：仿真成功，结果基本合理
- 70-79分：仿真有问题或结果不理想
- 60分以下：仿真失败或结果严重不合理

如果问题根源在上游Agent（如代码有bug），请在rollback_to字段指定回退目标(architect/theorist/engineer/simulator/dsp_coder/scribe)，否则设为null。

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=80为通过), "issues": ["问题1"], "suggestions": ["建议1"], "rollback_to": null}}

只返回JSON。"""

    def _build_dsp_coder_prompt(self, context: GlobalContext) -> str:
        dsp_c = context.dsp_c_code if context.dsp_c_code else "(无)"
        dsp_h = context.dsp_header_code if context.dsp_header_code else "(无)"

        # 提高截断限制（优化：让supervisor看到更完整的DSP代码）
        if len(dsp_c) > 5000:
            dsp_c = dsp_c[:5000] + "\n// ...(代码过长已截断)"
        if len(dsp_h) > 2000:
            dsp_h = dsp_h[:2000] + "\n// ...(代码过长已截断)"

        return f"""请评估以下AI生成的DSP嵌入式代码。

【DSP C代码】
```c
{dsp_c}
```

【DSP头文件】
```c
{dsp_h}
```

请评估:
1. 代码是否符合TMS320F28335 DSP规范
2. 是否包含必要的初始化和中断服务程序
3. 代码结构是否清晰

评分标准：
- 90-100分：代码完整可编译
- 80-89分：代码基本完整
- 70-79分：代码有明显不足
- 60分以下：代码不完整

如果问题根源在上游Agent，请在rollback_to字段指定回退目标(architect/theorist/engineer/dsp_coder/scribe)，否则设为null。

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=80为通过), "issues": ["问题1"], "suggestions": ["建议1"], "rollback_to": null}}

只返回JSON。"""

    def _build_generic_prompt(self, agent_key: str, context: GlobalContext) -> str:
        """通用评估prompt，用于未知agent"""
        return f"""请评估Agent [{agent_key}] 的输出质量。

当前研究课题: {context.research_topic if context.research_topic else '(未设置)'}

请给出一个基本评估。

评分标准：
- 90-100分：输出完整且高质量
- 80-89分：输出基本完整
- 70-79分：输出有明显不足
- 60分以下：输出不完整

请以JSON格式返回:
{{"score": 80, "passed": true, "issues": [], "suggestions": [], "rollback_to": null}}

只返回JSON。"""

    def _build_scribe_prompt(self, context: GlobalContext) -> str:
        paper = context.paper_latex if context.paper_latex else "(无)"
        if len(paper) > 5000:
            paper = paper[:5000] + "\n% ...(内容过长已截断)"

        return f"""请评估以下AI生成的学术论文。

【论文LaTeX】
```latex
{paper}
```

请评估:
1. 论文是否包含基本结构（摘要、引言、方法、结论）
2. 内容是否有实质性

评分标准：
- 90-100分：论文结构完整、内容充实
- 80-89分：论文基本完整
- 70-79分：论文有明显不足
- 60分以下：论文不完整

如果问题根源在上游Agent，请在rollback_to字段指定回退目标(architect/theorist/engineer/dsp_coder/scribe)，否则设为null。

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=80为通过), "issues": ["问题1"], "suggestions": ["建议1"], "rollback_to": null}}

只返回JSON。"""

    def _format_literature(self, literature_results: List[Dict]) -> str:
        """格式化文献列表"""
        if not literature_results:
            return "(无)"

        formatted = []
        for i, lit in enumerate(literature_results[:5], 1):  # 最多显示5篇
            title = lit.get('title', '未知标题')
            year = lit.get('year', '未知年份')
            contribution = lit.get('key_contribution', '')
            formatted.append(f"{i}. {title} ({year})")
            if contribution:
                formatted.append(f"   贡献: {contribution[:100]}")

        if len(literature_results) > 5:
            formatted.append(f"... 共{len(literature_results)}篇文献")

        return '\n'.join(formatted)

    def _parse_llm_evaluation(self, agent_key: str, response: str) -> EvaluationResult:
        """解析LLM返回的评估结果，支持从纯文本中提取信息"""
        data = None

        # 策略1: 直接解析JSON
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 策略1.5: 从 ```json ... ``` 代码块中提取
        if data is None:
            code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if code_block_match:
                try:
                    data = json.loads(code_block_match.group(1).strip())
                except json.JSONDecodeError:
                    pass

        # 策略2: 从文本中提取JSON对象（找最后一个完整的{}块，通常LLM会把JSON放在最后）
        if data is None:
            json_candidates = []
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
                        json_candidates.append(response[start:i+1])
                        start = -1

            # 尝试解析每个候选JSON（优先最后一个，通常是总结性JSON）
            for candidate in reversed(json_candidates):
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "score" in parsed:
                        data = parsed
                        break
                except json.JSONDecodeError:
                    continue

        # 策略3: 从纯文本中提取评分和问题（LLM没有返回JSON时的降级方案）
        if data is None:
            logger.warning("无法从LLM响应中提取JSON，尝试文本解析")
            score = self._extract_score_from_text(response)
            issues = self._extract_issues_from_text(response)
            suggestions = self._extract_suggestions_from_text(response)

            return EvaluationResult(
                agent_name=agent_key,
                score=score,
                passed=score >= self.PASS_THRESHOLD,
                issues=issues,
                suggestions=suggestions,
                rollback_to=None
            )

        # 从解析的JSON中提取字段
        score = float(data.get("score", 0))
        threshold = self.STAGE_THRESHOLDS.get(agent_key, self.PASS_THRESHOLD)
        passed = data.get("passed", score >= threshold)
        # 如果LLM说passed但分数低于阈值，以阈值为准
        if score < threshold:
            passed = False
        issues = data.get("issues", [])
        suggestions = data.get("suggestions", [])

        if isinstance(issues, str):
            issues = [issues]
        if isinstance(suggestions, str):
            suggestions = [suggestions]

        VALID_AGENT_KEYS = {"architect", "theorist", "engineer", "simulator", "dsp_coder", "scribe"}
        rollback_to = data.get("rollback_to", None)
        if rollback_to and (not isinstance(rollback_to, str) or rollback_to not in VALID_AGENT_KEYS):
            rollback_to = None

        return EvaluationResult(
            agent_name=agent_key,
            score=score,
            passed=passed,
            issues=issues,
            suggestions=suggestions,
            rollback_to=rollback_to
        )

    def _extract_score_from_text(self, text: str) -> float:
        """从纯文本中提取评分"""
        # 匹配 "评分: 85" 或 "score: 85" 或 "85分" 或 "85/100" 等
        patterns = [
            r'(?:评分|score|得分)\s*[:：]\s*(\d+)',
            r'(\d+)\s*/\s*100',
            r'(\d+)\s*分',
            r'(?:给出|给予|打)\s*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                if 0 <= score <= 100:
                    return score
        # 无法从文本提取评分时，默认给65分（不通过，触发重评估）
        return 65.0

    def _extract_issues_from_text(self, text: str) -> List[str]:
        """从纯文本中提取问题列表"""
        issues = []
        # 匹配 "问题" 或 "不足" 段落后面的列表项
        lines = text.split('\n')
        in_issues_section = False
        for line in lines:
            stripped = line.strip()
            if re.search(r'(问题|不足|缺点|issue|problem|weakness)', stripped, re.IGNORECASE):
                in_issues_section = True
                continue
            if re.search(r'(建议|优点|suggestion|improvement|strength)', stripped, re.IGNORECASE):
                in_issues_section = False
                continue
            if in_issues_section and stripped:
                # 清理列表标记
                cleaned = re.sub(r'^[\-\*\d+\.、]+\s*', '', stripped)
                if cleaned and len(cleaned) > 5:
                    issues.append(cleaned)
        return issues[:5]  # 最多5条

    def _extract_suggestions_from_text(self, text: str) -> List[str]:
        """从纯文本中提取建议列表"""
        suggestions = []
        lines = text.split('\n')
        in_suggestions_section = False
        for line in lines:
            stripped = line.strip()
            if re.search(r'(建议|改进|suggestion|improvement|recommend)', stripped, re.IGNORECASE):
                in_suggestions_section = True
                continue
            if re.search(r'(总结|结论|conclusion|overall|总体)', stripped, re.IGNORECASE):
                in_suggestions_section = False
                continue
            if in_suggestions_section and stripped:
                cleaned = re.sub(r'^[\-\*\d+\.、]+\s*', '', stripped)
                if cleaned and len(cleaned) > 5:
                    suggestions.append(cleaned)
        return suggestions[:5]

    async def evaluate_section(
        self,
        section_name: str,
        section_content: str,
        context: GlobalContext
    ) -> EvaluationResult:
        """
        评估论文单个章节的质量

        Args:
            section_name: 章节名称 (如 "abstract", "introduction")
            section_content: 章节内容
            context: 全局上下文

        Returns:
            评估结果
        """
        if not self.api_config or not self.api_config.api_key:
            raise RuntimeError("Supervisor Agent 必须配置 API 才能进行章节评审。")

        prompt = self._build_section_evaluation_prompt(section_name, section_content, context)
        response = await self._call_llm(
            prompt,
            timeout=90,
            agent_key=f"supervisor_scribe_section_{section_name}",
        )
        return self._parse_llm_evaluation(f"scribe_section_{section_name}", response)

    def _build_section_evaluation_prompt(
        self, section_name: str, content: str, context: GlobalContext
    ) -> str:
        """构建单节评审prompt"""
        if len(content) > 3000:
            content = content[:3000] + "\n% ...(内容过长已截断)"

        return f"""你是IEEE Transactions期刊的审稿人，请评估以下论文章节的质量。

【研究课题】
{context.research_topic}

【章节名称】
{section_name}

【章节内容】
{content}

请评估以下方面:
1. 内容是否完整，是否覆盖了该章节应有的要素
2. 语言是否规范（学术英语，无语法错误）
3. 数学公式是否正确使用LaTeX格式
4. 逻辑是否连贯
5. 是否有明显的模板化/AI生成痕迹

评分标准：
- 90-100分：内容完整、语言规范、逻辑清晰
- 80-89分：基本完整，有小问题
- 70-79分：有明显不足
- 60分以下：内容不完整或有严重问题

请以JSON格式返回:
{{"score": 你的评分(0-100整数), "passed": true或false(>=80为通过), "issues": ["问题1", "问题2"], "suggestions": ["建议1", "建议2"], "rollback_to": null}}

只返回JSON。"""

    def should_retry(self, result: EvaluationResult, iteration: int) -> bool:
        """判断是否需要重试（仅在未通过时重试）"""
        return not result.passed and iteration < self.MAX_ITERATIONS
