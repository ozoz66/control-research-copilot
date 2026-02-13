# -*- coding: utf-8 -*-
"""
架构师Agent (Agent A) - AutoControl-Scientist
负责文献检索、研究空白分析和创新课题设计
完全依赖LLM进行文献分析和课题生成
"""

import re
from typing import Dict, Any, List

from global_context import GlobalContext
from agents.base import BaseAgent
from logger_config import get_logger
from prompts import PromptTemplates

logger = get_logger(__name__)


class ArchitectAgent(BaseAgent):
    """
    架构师Agent (Agent A)
    负责文献检索、研究空白分析和创新课题设计

    完全依赖配置的LLM API进行：
    1. 文献综述和研究现状分析
    2. 研究空白识别
    3. 创新性研究课题设计
    4. 创新点提炼
    """

    # 控制算法领域的关键词映射（用于生成提示词）
    ALGORITHM_KEYWORDS = {
        "adaptive": ["adaptive control", "self-tuning", "parameter estimation", "MRAC", "自适应控制"],
        "ilc": ["iterative learning control", "ILC", "repetitive task", "迭代学习"],
        "repetitive": ["repetitive control", "periodic disturbance", "内模原理", "重复控制"],
        "robust": ["robust control", "H-infinity", "sliding mode", "uncertainty", "鲁棒控制"],
        "mpc": ["model predictive control", "MPC", "receding horizon", "预测控制"]
    }

    PERFORMANCE_KEYWORDS = {
        "chattering_elimination": ["chattering", "chattering-free", "smooth control", "抖振消除"],
        "finite_time": ["finite-time", "fixed-time", "prescribed-time", "有限时间"],
        "fast_transient": ["fast response", "transient performance", "快速响应"],
        "high_precision": ["high precision", "nanometer", "micro-positioning", "高精度"]
    }

    COMPONENT_KEYWORDS = {
        "smc": ["sliding mode", "SMC", "滑模控制"],
        "backstepping": ["backstepping", "recursive design", "反步控制"],
        "h_infinity": ["H-infinity", "H∞", "mixed sensitivity"],
        "pid": ["PID", "proportional integral derivative"],
        "eso": ["extended state observer", "ESO", "ADRC", "扩展状态观测器"],
        "smo": ["sliding mode observer", "SMO", "滑模观测器"],
        "dob": ["disturbance observer", "DOB", "扰动观测器"],
        "zpetc": ["zero phase error", "ZPETC", "零相位误差"]
    }

    def __init__(self):
        """初始化架构师Agent"""
        super().__init__("Architect", "architect")

    async def execute(self, context: GlobalContext) -> GlobalContext:
        """
        执行架构师任务

        Args:
            context: 全局上下文

        Returns:
            更新后的全局上下文
        """
        context.log_execution(self.name, "文献检索与课题设计", "started")

        # 检查API配置
        if self.api_config is None or not self.api_config.api_key:
            raise RuntimeError(
                "Architect Agent 必须配置 API 才能进行文献分析和课题设计。"
                "请在配置中设置有效的 API Key 和 Base URL。"
            )

        # 步骤1: 生成研究关键词（用于提示词）
        keywords = self._generate_search_keywords(context.research_config)
        context.log_execution(self.name, "关键词生成", "success",
                            f"生成{len(keywords)}个搜索关键词")

        # 步骤2: 使用LLM进行文献综述和课题设计
        analysis_result = await self._analyze_with_llm(context, keywords)

        # 更新上下文
        context.research_topic = analysis_result.get("proposed_topic", "")
        context.research_topic_en = analysis_result.get("proposed_topic_en", "")
        context.innovation_points = analysis_result.get("innovation_points", [])
        context.research_gap = analysis_result.get("research_gap", "")

        # 生成研究动机（修复P0问题：research_motivation从未生成）
        # 从research_gap和expected_contributions中提取
        research_gap = analysis_result.get("research_gap", "")
        contributions = analysis_result.get("expected_contributions", [])
        if research_gap:
            motivation_parts = [f"针对{research_gap}"]
            if contributions:
                motivation_parts.append("，本研究旨在")
                motivation_parts.append("；".join(contributions))
            context.research_motivation = "".join(motivation_parts)
        else:
            context.research_motivation = f"本研究针对{context.research_topic}领域的关键问题，提出创新性解决方案。"

        # 保存LLM生成的文献综述信息
        context.literature_results = analysis_result.get("literature_review", [])

        context.log_execution(self.name, "课题设计", "success",
                            f"研究课题: {context.research_topic[:50]}...")

        return context

    def _generate_search_keywords(self, config: Dict[str, Any]) -> List[str]:
        """
        根据研究配置生成搜索关键词

        Args:
            config: 研究配置

        Returns:
            关键词列表
        """
        keywords = []

        # 检查是否有自定义研究方向
        custom_topic = config.get("custom_topic", "")
        if custom_topic:
            words = re.split(r'[,，、\s]+', custom_topic)
            keywords.extend([w.strip() for w in words if len(w.strip()) > 1])
            keywords.append(custom_topic)
            return list(set(keywords))

        # 主算法关键词
        main_algo_key = config.get("main_algorithm", {}).get("key", "")
        if main_algo_key in self.ALGORITHM_KEYWORDS:
            keywords.extend(self.ALGORITHM_KEYWORDS[main_algo_key])

        # 性能目标关键词
        for obj in config.get("performance_objectives", []):
            obj_key = obj.get("key", "")
            if obj_key in self.PERFORMANCE_KEYWORDS:
                keywords.extend(self.PERFORMANCE_KEYWORDS[obj_key])

        # 复合架构关键词
        composite = config.get("composite_architecture", {})

        feedback_key = composite.get("feedback", {}).get("key", "")
        if feedback_key in self.COMPONENT_KEYWORDS:
            keywords.extend(self.COMPONENT_KEYWORDS[feedback_key])

        feedforward_key = composite.get("feedforward", {}).get("key", "")
        if feedforward_key in self.COMPONENT_KEYWORDS:
            keywords.extend(self.COMPONENT_KEYWORDS[feedforward_key])

        observer_key = composite.get("observer", {}).get("key", "")
        if observer_key in self.COMPONENT_KEYWORDS:
            keywords.extend(self.COMPONENT_KEYWORDS[observer_key])

        # 添加应用领域关键词
        keywords.extend(["motion control", "servo system", "precision positioning"])

        return list(set(keywords))

    async def _analyze_with_llm(
        self,
        context: GlobalContext,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """
        使用LLM进行文献综述、研究空白分析和课题设计

        Args:
            context: 全局上下文
            keywords: 研究关键词列表

        Returns:
            分析结果字典
        """
        config = context.research_config

        # 构建详细的提示词
        prompt = self._build_comprehensive_prompt(config, keywords)

        # 追加监督反馈
        prompt += self._get_feedback_prompt_section()

        try:
            logger.info("正在调用LLM进行文献分析和课题设计...")
            response_text = await self._call_llm(
                prompt, timeout=180,
                system_prompt="你是一位控制系统领域的资深研究员和博士生导师，具有丰富的文献综述和课题设计经验。请严格按照JSON格式输出结果。",
                temperature=0.4
            )
            logger.info("LLM返回内容长度: %d 字符", len(response_text))

            # 解析JSON响应
            result = self._parse_json_response(response_text)

            # 确保必要字段存在（改进：从配置生成默认值，而非通用值）
            if "proposed_topic" not in result or not result["proposed_topic"]:
                result["proposed_topic"] = self._generate_fallback_topic(config)
            if "innovation_points" not in result or not result["innovation_points"]:
                result["innovation_points"] = self._generate_fallback_innovations(config)
            if "research_gap" not in result or not result["research_gap"]:
                result["research_gap"] = self._generate_fallback_gap(config)

            return result

        except Exception as e:
            raise RuntimeError(
                f"LLM文献分析失败: {e}\n"
                "请检查: 1) API Key是否有效 2) 网络连接是否正常 3) 模型名称是否正确"
            )

    def _generate_fallback_topic(self, config: Dict[str, Any]) -> str:
        """从配置生成回退课题（当LLM失败时）"""
        main_algo = config.get("main_algorithm", {}).get("name", "先进控制")
        objectives = [obj.get("name", "") for obj in config.get("performance_objectives", [])]
        app_scenario = config.get("application_scenario", {}).get("name", "运动控制")

        obj_str = "、".join(objectives[:2]) if objectives else "高精度控制"
        return f"基于{main_algo}的{obj_str}{app_scenario}系统研究"

    def _generate_fallback_innovations(self, config: Dict[str, Any]) -> list:
        """从配置生成回退创新点"""
        main_algo = config.get("main_algorithm", {}).get("name", "控制方法")
        composite = config.get("composite_architecture", {})
        feedback = composite.get("feedback", {}).get("name", "")
        observer = composite.get("observer", {}).get("name", "")

        innovations = []
        if feedback:
            innovations.append(f"提出{main_algo}与{feedback}的复合控制策略")
        else:
            innovations.append(f"提出改进的{main_algo}控制策略")

        if observer and observer != "无":
            innovations.append(f"设计{observer}实现状态/扰动估计")

        innovations.append("严格的稳定性分析与收敛性证明")

        return innovations

    def _generate_fallback_gap(self, config: Dict[str, Any]) -> str:
        """从配置生成回退研究空白"""
        main_algo = config.get("main_algorithm", {}).get("name", "")
        app_scenario = config.get("application_scenario", {}).get("name", "")

        return f"现有{main_algo}方法在{app_scenario}领域应用时，对系统不确定性和外部扰动的处理能力有限，缺乏理论保证的高性能控制方案。"

    def _build_comprehensive_prompt(self, config: Dict[str, Any], keywords: List[str]) -> str:
        """
        构建综合性的LLM提示词，包含文献综述和课题设计任务

        Args:
            config: 研究配置
            keywords: 关键词列表

        Returns:
            完整的提示词
        """
        main_algo = config.get("main_algorithm", {}).get("name", "")
        objectives = [obj.get("name", "") for obj in config.get("performance_objectives", [])]
        composite = config.get("composite_architecture", {})
        feedback = composite.get("feedback", {}).get("name", "")
        feedforward = composite.get("feedforward", {}).get("name", "")
        observer = composite.get("observer", {}).get("name", "")
        custom_topic = config.get("custom_topic", "")
        app_scenario = config.get("application_scenario", {}).get("name", "")

        if custom_topic:
            topic_section = f"自定义研究方向: {custom_topic}"
        else:
            topic_section = f"""主算法: {main_algo}
性能目标: {', '.join(objectives) if objectives else '未指定'}
反馈控制: {feedback}
前馈控制: {feedforward}
观测器: {observer}
应用场景: {app_scenario if app_scenario else '通用运动控制系统'}"""

        keywords_str = ", ".join(keywords[:10])

        return f"""你是一位控制系统领域的资深研究员和博士生导师，请基于以下研究方向配置，完成文献综述和创新性课题设计。

【研究方向配置】
{topic_section}

【相关关键词】
{keywords_str}

【任务要求】

1. **文献综述** (基于你的专业知识)
   - 总结该领域近5年的研究热点和发展趋势
   - 列举5-10篇该领域的代表性论文（包括标题、作者、年份、主要贡献）
   - 分析现有方法的优缺点

2. **研究空白分析**
   - 识别现有研究的不足和局限性
   - 指出尚未解决的关键问题
   - 分析潜在的研究机会

3. **创新性课题设计**
   - 提出一个具有创新性和研究价值的课题
   - 课题应该能够解决识别出的研究空白
   - 确保课题具有理论意义和应用价值

4. **创新点提炼**
   - 明确3个具体的技术创新点
   - 每个创新点应该是可实现的、可验证的

【输出格式】
请以JSON格式输出，包含以下字段:
{{
    "literature_review": [
        {{"title": "论文标题", "authors": "作者", "year": 2023, "contribution": "主要贡献"}},
        ...
    ],
    "research_hotspots": ["热点1", "热点2", "热点3"],
    "existing_methods": [
        {{"method": "方法名称", "advantages": "优点", "limitations": "局限性"}}
    ],
    "research_gap": "研究空白分析（150-300字，详细说明现有研究的不足）",
    "proposed_topic": "研究课题（中文，30-50字）",
    "proposed_topic_en": "Research Topic (English, formal academic title)",
    "innovation_points": [
        "创新点1: 具体描述（说明创新之处和预期效果）",
        "创新点2: 具体描述",
        "创新点3: 具体描述"
    ],
    "expected_contributions": [
        "理论贡献: ...",
        "应用贡献: ..."
    ],
    "methodology_outline": "研究方法概述（100-200字）"
}}

请确保输出的JSON格式正确，可以被直接解析。"""

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析LLM返回的JSON响应

        Args:
            response_text: LLM响应文本

        Returns:
            解析后的字典
        """
        try:
            return self._extract_json_from_text(response_text)
        except ValueError as e:
            raise RuntimeError(f"LLM响应格式错误: {e}")


if __name__ == "__main__":
    # 测试代码
    import asyncio

    async def test():
        # 创建测试上下文
        ctx = GlobalContext()
        ctx.research_config = {
            "main_algorithm": {"key": "adaptive", "name": "自适应控制 (Adaptive Control)"},
            "performance_objectives": [
                {"key": "chattering_elimination", "name": "消除抖动 (Chattering Elimination)"},
                {"key": "finite_time", "name": "有限时间收敛 (Finite-time Convergence)"}
            ],
            "composite_architecture": {
                "feedback": {"key": "smc", "name": "滑模控制 (Sliding Mode Control)"},
                "feedforward": {"key": "none", "name": "无 (None)"},
                "observer": {"key": "eso", "name": "扩展状态观测器 (ESO)"}
            }
        }

        # 创建Agent
        agent = ArchitectAgent()

        # 执行
        print("开始执行架构师Agent...")
        ctx = await agent.execute(ctx)

        # 输出结果
        print(f"\n{'='*60}")
        print(f"【研究课题】\n{ctx.research_topic}")
        print(f"\n【创新点】")
        for i, point in enumerate(ctx.innovation_points, 1):
            print(f"  {i}. {point}")
        print(f"\n【研究空白】\n{ctx.research_gap}")

    asyncio.run(test())
