# -*- coding: utf-8 -*-
"""
撰稿人Agent (Agent D) - AutoControl-Scientist
负责将研究成果整理为IEEE Transactions格式的学术论文
"""

import re
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from global_context import GlobalContext
from agents.base import BaseAgent
from llm_client import call_llm_api
from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class PaperStructure:
    """论文结构数据类"""
    title: str = ""
    title_cn: str = ""
    abstract: str = ""
    abstract_cn: str = ""
    keywords: List[str] = field(default_factory=list)
    sections: Dict[str, str] = field(default_factory=dict)
    references: List[Dict[str, str]] = field(default_factory=list)
    figures: List[Dict[str, str]] = field(default_factory=list)
    tables: List[Dict[str, str]] = field(default_factory=list)


class MindMapGenerator:
    """
    思维导图生成器
    生成论文结构的可视化表示
    """

    @staticmethod
    def generate_structure(context: GlobalContext) -> Dict[str, Any]:
        """
        根据研究内容生成论文结构思维导图

        Args:
            context: 全局上下文

        Returns:
            思维导图结构（JSON格式）
        """
        structure = {
            "title": context.research_topic,
            "children": [
                {
                    "name": "1. Introduction",
                    "children": [
                        {"name": "1.1 Research Background"},
                        {"name": "1.2 Literature Review"},
                        {"name": "1.3 Motivation and Contributions"},
                        {"name": "1.4 Paper Organization"}
                    ]
                },
                {
                    "name": "2. Problem Formulation",
                    "children": [
                        {"name": "2.1 System Model"},
                        {"name": "2.2 Assumptions"},
                        {"name": "2.3 Control Objectives"}
                    ]
                },
                {
                    "name": "3. Controller Design",
                    "children": [
                        {"name": "3.1 Observer Design"},
                        {"name": "3.2 Control Law Design"},
                        {"name": "3.3 Parameter Adaptation"}
                    ]
                },
                {
                    "name": "4. Stability Analysis",
                    "children": [
                        {"name": "4.1 Lyapunov Function"},
                        {"name": "4.2 Stability Proof"},
                        {"name": "4.3 Convergence Analysis"}
                    ]
                },
                {
                    "name": "5. Simulation Results",
                    "children": [
                        {"name": "5.1 Simulation Setup"},
                        {"name": "5.2 Tracking Performance"},
                        {"name": "5.3 Disturbance Rejection"},
                        {"name": "5.4 Comparative Study"}
                    ]
                },
                {
                    "name": "6. Conclusion",
                    "children": [
                        {"name": "6.1 Summary"},
                        {"name": "6.2 Future Work"}
                    ]
                }
            ]
        }

        return structure

    @staticmethod
    def to_latex_outline(structure: Dict[str, Any], level: int = 0) -> str:
        """
        将思维导图转换为LaTeX大纲

        Args:
            structure: 思维导图结构
            level: 当前层级

        Returns:
            LaTeX大纲字符串
        """
        indent = "  " * level
        result = []

        name = structure.get("name", structure.get("title", ""))
        if level == 0:
            result.append(f"% Paper Outline: {name}")
        else:
            result.append(f"{indent}% {name}")

        for child in structure.get("children", []):
            result.append(MindMapGenerator.to_latex_outline(child, level + 1))

        return "\n".join(result)


class ScribeAgent(BaseAgent):
    """
    撰稿人Agent (Agent D)
    负责将研究成果整理为IEEE Transactions格式的学术论文

    工作流程:
    1. 生成论文结构思维导图
    2. 撰写各章节内容
    3. 整合数学推导和仿真结果
    4. 生成完整的LaTeX论文
    """

    _default_system_prompt = (
        "你是一位IEEE Transactions期刊的资深审稿人和学术论文撰写专家。"
        "请使用规范的学术英语撰写论文内容，输出纯LaTeX格式。"
        "要求：(1) 公式使用equation/align环境并编号；"
        "(2) 定理和证明使用theorem/proof环境；"
        "(3) 避免使用第一人称（we/our改为被动语态或this paper）；"
        "(4) 引用使用\\cite{}格式；"
        "(5) 图表使用figure/table环境并添加label；"
        "(6) 语言自然流畅，避免模板化表述。"
    )

    # IEEE论文LaTeX模板
    IEEE_TEMPLATE = r"""
\documentclass[journal]{IEEEtran}

%% 常用宏包
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{algorithmic}
\usepackage{algorithm}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{bm}
\usepackage{subfig}
\usepackage{array}
\usepackage{url}
\usepackage{hyperref}

%% 定理环境
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}{Lemma}
\newtheorem{proposition}{Proposition}
\newtheorem{corollary}{Corollary}
\newtheorem{assumption}{Assumption}
\newtheorem{remark}{Remark}
\newtheorem{definition}{Definition}
\newtheorem{problem}{Problem}

%% 自定义命令
\newcommand{\R}{\mathbb{R}}
\newcommand{\norm}[1]{\left\|#1\right\|}
\newcommand{\abs}[1]{\left|#1\right|}

\begin{document}

\title{%(title)s}

\author{
    \IEEEauthorblockN{AutoControl-Scientist}
    \IEEEauthorblockA{
        Automatically Generated Paper\\
        Date: %(date)s
    }
}

\maketitle

\begin{abstract}
%(abstract)s
\end{abstract}

\begin{IEEEkeywords}
%(keywords)s
\end{IEEEkeywords}

%(content)s

%(acknowledgment)s

%(appendix)s

\bibliographystyle{IEEEtran}
\bibliography{references}

\end{document}
"""

    # 章节内容模板
    SECTION_TEMPLATES = {
        "introduction": r"""
\section{Introduction}

%(background)s

%(literature_review)s

%(motivation)s

The main contributions of this paper are summarized as follows:
\begin{itemize}
%(contributions)s
\end{itemize}

%(organization)s
""",
        "problem_formulation": r"""
\section{Problem Formulation}

\subsection{System Model}
%(system_model)s

\subsection{Assumptions}
%(assumptions)s

\subsection{Control Objectives}
%(objectives)s
""",
        "controller_design": r"""
\section{Controller Design}

%(observer_design)s

%(control_law)s

%(adaptation_law)s
""",
        "stability_analysis": r"""
\section{Stability Analysis}

%(lyapunov)s

%(proof)s

%(convergence)s
""",
        "simulation": r"""
\section{Simulation Results}

\subsection{Simulation Setup}
%(setup)s

\subsection{Tracking Performance}
%(tracking)s

\subsection{Disturbance Rejection}
%(disturbance)s

\subsection{Comparative Study}
%(comparison)s
""",
        "conclusion": r"""
\section{Conclusion}

%(summary)s

%(future_work)s
""",
        "related_work": r"""
\section{Related Work}

%(related_work_content)s
""",
        "acknowledgment": r"""
\section*{Acknowledgment}
The authors would like to thank the reviewers for their valuable comments.
""",
        "appendix": r"""
\appendices
\section{Proof of Theorem 1}
%(appendix_content)s
"""
    }

    def __init__(self, output_dir: str = "./output"):
        """
        初始化撰稿人Agent

        Args:
            output_dir: 输出目录
        """
        super().__init__("Scribe", "scribe")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.output_manager = None  # 由Orchestrator注入
        self.supervisor = None  # 可选：由GUI注入SupervisorAgent，用于逐节评审

    async def execute(self, context: GlobalContext) -> GlobalContext:
        """
        执行撰稿人任务 - 迭代式论文撰写流程

        流程:
        1. 生成论文结构骨架
        2. 分章节LLM生成初稿
        3. 生成BibTeX参考文献并验证引用一致性
        4. 组装完整论文
        5. 图表与正文交叉引用校验
        6. 论文润色（查重/降重提示）
        7. 保存

        Args:
            context: 全局上下文

        Returns:
            更新后的全局上下文
        """
        context.log_execution(self.name, "论文撰写", "started")

        # 步骤1: 生成论文结构思维导图
        structure = MindMapGenerator.generate_structure(context)
        context.paper_structure = structure
        context.log_execution(self.name, "论文结构设计", "success")

        # 步骤1.5: 如果有监督反馈，记录日志
        if self.supervisor_feedback:
            context.log_execution(self.name, "收到监督反馈", "info", self.supervisor_feedback)

        # 步骤2: 生成各章节内容 - 必须配置API
        if self.api_config is None or not self.api_config.api_key:
            raise RuntimeError(
                "Scribe Agent 必须配置 API 才能撰写论文。"
                "请在配置中设置有效的 API Key 和 Base URL。"
            )
        sections = await self._generate_sections_with_llm(context)
        context.paper_sections = sections

        # 步骤3: 生成BibTeX参考文献条目
        bibtex_entries = await self._generate_bibtex(context)
        context.bibtex_entries = bibtex_entries
        context.log_execution(self.name, "参考文献生成", "success",
                            f"生成{len(bibtex_entries)}条BibTeX条目")

        # 步骤4: 验证引用一致性（正文中的\cite{}与BibTeX条目匹配）
        sections = self._verify_citations(sections, bibtex_entries, context)
        context.paper_sections = sections

        # 步骤5: 组装完整论文
        paper_latex = self._assemble_paper(context, sections)
        context.paper_latex = paper_latex

        # 步骤6: 图表与正文交叉引用校验
        xref_issues = self._validate_cross_references(paper_latex, context)
        if xref_issues:
            context.log_execution(self.name, "交叉引用校验", "warning",
                                f"发现{len(xref_issues)}个问题: {'; '.join(xref_issues[:3])}")
            # 尝试自动修复
            paper_latex = await self._fix_cross_references(
                paper_latex, xref_issues, context
            )
            context.paper_latex = paper_latex
        else:
            context.log_execution(self.name, "交叉引用校验", "success")

        # 步骤7: 论文润色 - 改善语言质量，减少模板化表述
        paper_latex = await self._polish_paper(paper_latex, context)
        context.paper_latex = paper_latex

        # 步骤8: 保存到文件
        self._save_paper(context)
        self._save_bibtex(context)

        context.log_execution(self.name, "论文撰写", "success")

        return context

    def _build_prior_sections_context(self, sections: Dict[str, str]) -> str:
        """构建已完成章节的摘要上下文，用于保持后续章节的连贯性"""
        if not sections:
            return ""
        parts = ["\n\n【已完成章节摘要 - 请保持符号、术语和表述风格一致】"]
        for name, content in sections.items():
            # 截取每个章节的核心部分（前600字符）
            preview = content[:600].strip()
            if len(content) > 600:
                preview += "..."
            parts.append(f"[{name}]: {preview}")
        return "\n".join(parts)

    async def _generate_and_evaluate_section(
        self,
        section_name: str,
        prompt: str,
        context: GlobalContext,
        max_retries: int = 2
    ) -> str:
        """
        生成章节内容，若有supervisor则逐节评审，不通过则带反馈重新生成。

        Args:
            section_name: 章节名称
            prompt: 生成该章节的prompt
            context: 全局上下文
            max_retries: 最大重试次数

        Returns:
            章节内容
        """
        content = await self._call_llm(prompt)
        if not content:
            raise RuntimeError(f"LLM未能生成{section_name}，请检查API配置")

        # 无supervisor时直接返回
        if not self.supervisor:
            return content

        for attempt in range(max_retries):
            try:
                eval_result = await self.supervisor.evaluate_section(
                    section_name, content, context
                )
            except Exception as e:
                context.log_execution(
                    self.name, f"章节评审({section_name})", "warning",
                    f"评审调用失败: {e}"
                )
                break

            context.log_execution(
                self.name, f"章节评审({section_name})",
                "success" if eval_result.passed else "warning",
                f"评分: {eval_result.score}/100"
            )

            if eval_result.passed:
                break

            # 不通过，带反馈重新生成
            feedback_parts = []
            if eval_result.issues:
                feedback_parts.append("问题: " + "; ".join(eval_result.issues))
            if eval_result.suggestions:
                feedback_parts.append("建议: " + "; ".join(eval_result.suggestions))
            feedback_text = "\n".join(feedback_parts)

            retry_prompt = prompt + f"""

【监督Agent评审反馈 - 请根据以下意见改进输出】
{feedback_text}

请重新生成该章节，务必解决上述问题。"""

            content = await self._call_llm(retry_prompt)
            if not content:
                raise RuntimeError(f"LLM未能重新生成{section_name}，请检查API配置")

        return content

    async def _generate_sections_with_llm(
        self,
        context: GlobalContext
    ) -> Dict[str, str]:
        """
        使用LLM生成所有章节内容（逐章节传递上下文保持连贯性，逐节评审）

        Args:
            context: 全局上下文

        Returns:
            章节内容字典
        """
        sections = {}

        # 生成摘要
        abstract_prompt = self._build_abstract_prompt(context)
        abstract_prompt += self._get_feedback_prompt_section()
        abstract_prompt += """

注意: 如果你发现上游Agent的输出（如仿真结果、控制律推导）严重不满足论文撰写要求，
可以在响应中包含如下JSON字段来请求重做:
{"request_redo": {"agent": "engineer", "reason": "具体原因"}}"""
        sections["abstract"] = await self._generate_and_evaluate_section(
            "abstract", abstract_prompt, context
        )

        # 生成引言 - 传入摘要作为上下文
        intro_prompt = self._build_introduction_prompt(context)
        intro_prompt += self._build_prior_sections_context(sections)
        sections["introduction"] = await self._generate_and_evaluate_section(
            "introduction", intro_prompt, context
        )

        # 生成问题描述章节
        problem_prompt = self._build_problem_prompt(context)
        problem_prompt += self._build_prior_sections_context(sections)
        sections["problem_formulation"] = await self._generate_and_evaluate_section(
            "problem_formulation", problem_prompt, context
        )

        # 生成控制器设计章节
        controller_prompt = self._build_controller_prompt(context)
        controller_prompt += self._build_prior_sections_context(sections)
        sections["controller_design"] = await self._generate_and_evaluate_section(
            "controller_design", controller_prompt, context
        )

        # 生成稳定性分析章节
        stability_prompt = self._build_stability_prompt(context)
        stability_prompt += self._build_prior_sections_context(sections)
        sections["stability_analysis"] = await self._generate_and_evaluate_section(
            "stability_analysis", stability_prompt, context
        )

        # 生成仿真结果章节
        simulation_prompt = self._build_simulation_prompt(context)
        simulation_prompt += self._build_prior_sections_context(sections)
        sections["simulation"] = await self._generate_and_evaluate_section(
            "simulation", simulation_prompt, context
        )

        # 生成结论章节
        sections["conclusion"] = await self._generate_conclusion_with_llm(context, sections)
        if not sections["conclusion"]:
            raise RuntimeError("LLM未能生成结论章节，请检查API配置")

        return sections

    async def _generate_conclusion_with_llm(
        self, context: GlobalContext, prior_sections: Optional[Dict[str, str]] = None
    ) -> str:
        """使用LLM生成结论"""
        prompt = f"""
请为以下研究课题撰写学术论文的结论部分（英文，IEEE风格）：

研究课题: {context.research_topic}
创新点: {context.innovation_points}

要求:
1. 总结本文的主要贡献（3-4句话）
2. 强调方法的优势和实验验证结果
3. 提出2-3个未来研究方向
4. 使用正式的学术英语，避免第一人称

输出纯LaTeX格式的结论章节。
"""
        if prior_sections:
            prompt += self._build_prior_sections_context(prior_sections)
        result = await self._call_llm(prompt)
        return result if result else self._generate_conclusion(context)

    def _build_abstract_prompt(self, context: GlobalContext) -> str:
        """构建摘要生成提示词"""
        return f"""
请为以下研究撰写学术论文摘要（英文，150-250词）：

研究课题: {context.research_topic}
创新点: {context.innovation_points}
主要方法: {context.research_config.get('main_algorithm', {}).get('name', '')}
控制律核心: {context.control_law_latex[:300] if context.control_law_latex else '(待定)'}

要求:
1. 第1句：简明说明研究问题和动机（This paper addresses / investigates...）
2. 第2-3句：概述所提方法的核心思想和关键技术
3. 第4句：强调主要创新点（与现有方法的区别）
4. 第5-6句：总结仿真/实验结果（用具体指标描述，如"tracking error is reduced by..."）
5. 使用正式的学术英语，避免第一人称，避免"In this paper"开头

请直接输出摘要文本，不要包含LaTeX环境标签。
"""

    def _build_introduction_prompt(self, context: GlobalContext) -> str:
        """构建引言生成提示词"""
        return f"""
请为以下研究撰写学术论文引言章节（英文，IEEE风格）：

研究课题: {context.research_topic}
研究领域: {context.research_config.get('main_algorithm', {}).get('name', '')}
创新点: {context.innovation_points}
文献摘要: {[lit.get('title', '') for lit in context.literature_results[:5]]}

要求:
1. 介绍研究背景（1段）
2. 文献综述（2-3段）
3. 研究动机（1段）
4. 列出本文贡献（itemize环境）
5. 说明论文组织结构（1段）

输出纯LaTeX格式的引言章节，使用\\section{{Introduction}}开头。
"""

    def _build_problem_prompt(self, context: GlobalContext) -> str:
        """构建问题描述章节提示词"""
        return f"""
请为以下研究撰写学术论文的问题描述章节（英文，IEEE风格）：

研究课题: {context.research_topic}
控制策略: {context.research_config.get('main_algorithm', {}).get('name', '')}
数学假设: {context.mathematical_assumptions}

要求:
1. 建立系统数学模型（使用equation环境）
2. 列出基本假设（使用assumption环境）
3. 明确控制目标
4. 使用规范的数学符号

输出纯LaTeX格式，使用\\section{{Problem Formulation}}开头。
"""

    def _build_controller_prompt(self, context: GlobalContext) -> str:
        """构建控制器设计章节提示词"""
        return f"""
请为以下研究撰写学术论文的控制器设计章节（英文，IEEE风格）：

研究课题: {context.research_topic}
控制律: {context.control_law_latex[:2000] if context.control_law_latex else '滑模控制'}
创新点: {context.innovation_points}

要求:
1. 详细推导控制律设计过程
2. 如有观测器，说明观测器设计
3. 给出参数选择建议
4. 使用align环境展示公式推导

输出纯LaTeX格式，使用\\section{{Controller Design}}开头。
"""

    def _build_stability_prompt(self, context: GlobalContext) -> str:
        """构建稳定性分析章节提示词"""
        return f"""
请为以下研究撰写学术论文的稳定性分析章节（英文，IEEE风格）：

Lyapunov函数: {context.lyapunov_function if context.lyapunov_function else 'V = 0.5*s^2'}
稳定性证明: {context.stability_proof_latex[:2000] if context.stability_proof_latex else ''}

要求:
1. 选取合适的Lyapunov函数
2. 严格证明系统稳定性
3. 分析收敛性
4. 使用theorem和proof环境

输出纯LaTeX格式，使用\\section{{Stability Analysis}}开头。
"""

    def _build_simulation_prompt(self, context: GlobalContext) -> str:
        """构建仿真结果章节提示词"""
        # 使用文件名而非完整路径
        figures = context.figure_paths if context.figure_paths else []
        figure_names = [Path(f).name for f in figures]
        return f"""
请为以下研究撰写学术论文的仿真结果章节（英文，IEEE风格）：

研究课题: {context.research_topic}
仿真图像文件名: {figure_names}
性能目标: {[obj.get('name', '') for obj in context.research_config.get('performance_objectives', [])]}

要求:
1. 描述仿真设置和参数
2. 分析跟踪性能
3. 分析抗扰动性能
4. 与传统方法对比
5. 使用figure和table环境

输出纯LaTeX格式，使用\\section{{Simulation Results}}开头。
"""

    # ============ 参考文献生成与引用验证 ============

    async def _generate_bibtex(self, context: GlobalContext) -> List[str]:
        """
        基于检索到的文献列表生成BibTeX条目

        Args:
            context: 全局上下文

        Returns:
            BibTeX条目字符串列表
        """
        literature = context.literature_results[:15]
        if not literature:
            return []

        lit_text = "\n".join([
            f"- {lit.get('title', '')} ({lit.get('year', '')}) "
            f"by {', '.join(lit.get('authors', [])[:3]) if isinstance(lit.get('authors'), list) else lit.get('authors', '')} "
            f"[{lit.get('source', '')}]"
            for lit in literature
        ])

        prompt = f"""请将以下文献列表转换为BibTeX格式。每条文献生成一个完整的BibTeX条目。

【文献列表】
{lit_text}

要求:
1. 每条使用 @article 或 @inproceedings 格式
2. cite key 使用 "作者姓_年份" 格式（如 wang_2023）
3. 包含 title, author, journal/booktitle, year, volume, pages 等字段
4. 如果缺少具体信息（如volume, pages），可以合理补充或省略
5. 确保所有条目格式正确

请直接输出所有BibTeX条目，不要其他文字。"""

        response = await self._call_llm(prompt)
        if not response:
            return []

        # 解析BibTeX条目
        entries = []
        current_entry = []
        brace_depth = 0
        for line in response.split('\n'):
            if line.strip().startswith('@'):
                current_entry = [line]
                brace_depth = line.count('{') - line.count('}')
            elif current_entry:
                current_entry.append(line)
                brace_depth += line.count('{') - line.count('}')
                if brace_depth <= 0:
                    entry_text = '\n'.join(current_entry)
                    # 验证BibTeX条目包含必要字段
                    if self._is_valid_bibtex_entry(entry_text):
                        entries.append(entry_text)
                    current_entry = []
                    brace_depth = 0

        return entries

    @staticmethod
    def _is_valid_bibtex_entry(entry: str) -> bool:
        """验证BibTeX条目是否包含必要字段"""
        # 必须以 @type{key 开头
        if not re.match(r'@\w+\{[\w\-]+', entry.strip()):
            return False
        # 必须包含 title 字段
        if not re.search(r'title\s*=', entry, re.IGNORECASE):
            return False
        # 必须包含 year 或 date 字段
        if not re.search(r'(?:year|date)\s*=', entry, re.IGNORECASE):
            return False
        return True

    def _verify_citations(
        self,
        sections: Dict[str, str],
        bibtex_entries: List[str],
        context: GlobalContext
    ) -> Dict[str, str]:
        """
        验证并修复论文正文中的引用与BibTeX条目的一致性

        检查:
        1. 正文中的 \\cite{key} 是否都有对应的BibTeX条目
        2. BibTeX中的条目是否在正文中被引用
        3. 引用标记的格式是否正确

        Args:
            sections: 章节内容
            bibtex_entries: BibTeX条目列表
            context: 全局上下文

        Returns:
            修复后的章节内容
        """
        # 提取所有BibTeX cite keys
        available_keys = set()
        for entry in bibtex_entries:
            match = re.search(r'@\w+\{(\w+)', entry)
            if match:
                available_keys.add(match.group(1))

        if not available_keys:
            return sections

        # 扫描正文中的 \cite{} 引用
        all_content = "\n".join(sections.values())
        cited_keys = set(re.findall(r'\\cite\{([^}]+)\}', all_content))
        # 展开多引用 \cite{a,b,c}
        expanded_cited = set()
        for key_group in cited_keys:
            for k in key_group.split(','):
                expanded_cited.add(k.strip())

        # 找出正文中引用了但BibTeX中没有的key
        missing_keys = expanded_cited - available_keys
        # 找出BibTeX中有但正文未引用的key
        unused_keys = available_keys - expanded_cited

        if missing_keys:
            context.log_execution(
                self.name, "引用验证", "warning",
                f"正文引用但BibTeX中缺失: {missing_keys}"
            )
            # 将缺失的引用替换为最接近的可用key或移除
            for section_name, content in sections.items():
                for missing_key in missing_keys:
                    # 简单策略：移除无效引用中的缺失key
                    content = re.sub(
                        rf'\\cite\{{[^}}]*{re.escape(missing_key)}[^}}]*\}}',
                        lambda m: self._fix_cite_group(m.group(), missing_key, available_keys),
                        content
                    )
                sections[section_name] = content

        if unused_keys:
            context.log_execution(
                self.name, "引用验证", "info",
                f"BibTeX中有但正文未引用: {unused_keys}"
            )

        return sections

    @staticmethod
    def _fix_cite_group(cite_text: str, missing_key: str, available_keys: set) -> str:
        """修复引用组中的缺失key"""
        match = re.search(r'\\cite\{([^}]+)\}', cite_text)
        if not match:
            return cite_text
        keys = [k.strip() for k in match.group(1).split(',')]
        keys = [k for k in keys if k != missing_key and k in available_keys]
        if keys:
            return f"\\cite{{{', '.join(keys)}}}"
        return ""  # 所有key都无效，移除整个引用

    # ============ 交叉引用校验 ============

    def _validate_cross_references(
        self,
        paper_latex: str,
        context: GlobalContext
    ) -> List[str]:
        """
        校验图表与正文之间的交叉引用

        检查:
        1. \\ref{fig:xxx} 是否有对应的 \\label{fig:xxx}
        2. \\ref{tab:xxx} 是否有对应的 \\label{tab:xxx}
        3. 图片文件 \\includegraphics{xxx} 是否存在
        4. \\label 是否有对应的 \\ref

        Args:
            paper_latex: LaTeX源码
            context: 全局上下文

        Returns:
            问题列表
        """
        issues = []

        # 提取所有 \label 和 \ref
        labels = set(re.findall(r'\\label\{([^}]+)\}', paper_latex))
        refs = set(re.findall(r'\\ref\{([^}]+)\}', paper_latex))

        # 检查 ref 是否有对应 label
        for ref in refs:
            if ref not in labels:
                issues.append(f"\\ref{{{ref}}} 无对应 \\label")

        # 检查 label 是否被引用
        for label in labels:
            if label not in refs:
                issues.append(f"\\label{{{label}}} 未被引用")

        # 检查图片文件是否存在
        image_files = re.findall(r'\\includegraphics(?:\[.*?\])?\{([^}]+)\}', paper_latex)
        for img in image_files:
            # 检查是否在figure_paths中
            img_basename = Path(img).name
            found = any(
                Path(fp).name == img_basename for fp in context.figure_paths
            ) if context.figure_paths else False

            if not found and context.figure_paths:
                issues.append(f"图片 {img} 不在已生成的图像列表中")

        return issues

    async def _fix_cross_references(
        self,
        paper_latex: str,
        issues: List[str],
        context: GlobalContext
    ) -> str:
        """
        使用LLM修复交叉引用问题

        Args:
            paper_latex: 当前LaTeX
            issues: 问题列表
            context: 全局上下文

        Returns:
            修复后的LaTeX
        """
        # 修复图片引用问题
        if context.figure_paths:
            actual_figures = [Path(fp).name for fp in context.figure_paths]

            # 找到所有 \includegraphics 引用
            def replace_figure(match):
                """逐个替换图片引用为实际存在的图片"""
                options = match.group(1) or ""
                old_path = match.group(2)
                old_name = Path(old_path).name
                # 如果文件名已经在实际图片列表中，保持不变
                if old_name in actual_figures:
                    return match.group(0)
                # 否则替换为列表中对应索引的图片（循环使用）
                replace_figure._index = getattr(replace_figure, '_index', -1) + 1
                idx = replace_figure._index % len(actual_figures)
                return f"\\includegraphics{options}{{{actual_figures[idx]}}}"

            replace_figure._index = -1
            paper_latex = re.sub(
                r'\\includegraphics(\[.*?\])?\{([^}]+)\}',
                replace_figure,
                paper_latex
            )

        return paper_latex

    # ============ 论文润色 ============

    async def _polish_paper(
        self, paper_latex: str, context: GlobalContext
    ) -> str:
        """
        论文润色 - 改善语言质量，检查学术规范

        步骤:
        1. 检查常见的模板化/AI生成痕迹
        2. 让LLM对摘要和结论进行润色
        3. 标注潜在的查重风险段落

        Args:
            paper_latex: 论文LaTeX
            context: 全局上下文

        Returns:
            润色后的LaTeX
        """
        # 检测常见的AI生成模板化表述
        template_phrases = [
            "In this paper, we propose",
            "The main contributions of this paper",
            "The remainder of this paper is organized as follows",
            "Simulation results demonstrate the effectiveness",
            "has attracted considerable attention",
        ]

        detected = [p for p in template_phrases if p.lower() in paper_latex.lower()]

        if not detected:
            context.log_execution(self.name, "论文润色", "success", "未检测到明显模板化表述")
            return paper_latex

        # 用LLM润色摘要和引言（最容易被查重的部分）
        prompt = f"""请润色以下学术论文的LaTeX代码，减少模板化表述，使语言更加自然和专业。

【检测到的模板化表述】
{chr(10).join(f'- "{p}"' for p in detected)}

【需要润色的LaTeX内容（仅摘要和引言部分）】
请从以下论文中提取摘要和引言部分并润色：
{paper_latex[:3000]}

要求:
1. 保持学术严谨性
2. 改变句式结构，避免过于套路的表述
3. 保留所有数学公式和引用不变
4. 只返回润色后的摘要和引言LaTeX代码

返回格式：
===ABSTRACT===
润色后的摘要
===INTRODUCTION===
润色后的引言
"""
        polished = await self._call_llm(prompt)

        if polished:
            # 尝试替换摘要
            abstract_match = re.search(
                r'===ABSTRACT===\s*(.*?)\s*===INTRODUCTION===',
                polished, re.DOTALL
            )
            intro_match = re.search(
                r'===INTRODUCTION===\s*(.*)',
                polished, re.DOTALL
            )

            if abstract_match:
                new_abstract = abstract_match.group(1).strip()
                if new_abstract and len(new_abstract) > 50:
                    # 替换原摘要
                    paper_latex = re.sub(
                        r'(\\begin\{abstract\}).*?(\\end\{abstract\})',
                        f'\\1\n{new_abstract}\n\\2',
                        paper_latex,
                        flags=re.DOTALL
                    )

            context.log_execution(self.name, "论文润色", "success",
                                f"已润色，修改了{len(detected)}处模板化表述")

        return paper_latex

    # ============ 保存BibTeX ============

    def _save_bibtex(self, context: GlobalContext):
        """保存BibTeX参考文献文件"""
        if not context.bibtex_entries:
            return

        output_dir = self._get_output_dir()
        bibtex_content = "\n\n".join(context.bibtex_entries)
        bibtex_path = output_dir / "references.bib"
        with open(bibtex_path, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        logger.info("BibTeX参考文献已保存至: %s", bibtex_path)

    def _assemble_paper(
        self,
        context: GlobalContext,
        sections: Dict[str, str]
    ) -> str:
        """
        组装完整的LaTeX论文

        Args:
            context: 全局上下文
            sections: 章节内容字典

        Returns:
            完整的LaTeX源码
        """
        # 组合所有章节内容
        content = "\n\n".join([
            sections.get("introduction", ""),
            sections.get("related_work", ""),
            sections.get("problem_formulation", ""),
            sections.get("controller_design", ""),
            sections.get("stability_analysis", ""),
            sections.get("simulation", ""),
            sections.get("conclusion", "")
        ])

        # 生成关键词
        config = context.research_config
        keywords = [
            config.get("main_algorithm", {}).get("name", "").split("(")[0].strip(),
            config.get("composite_architecture", {}).get("feedback", {}).get("name", "").split("(")[0].strip(),
            config.get("composite_architecture", {}).get("observer", {}).get("name", "").split("(")[0].strip(),
            "stability analysis",
            "motion control"
        ]
        keywords = [k for k in keywords if k and k != "无"]

        # 填充模板 - 优先使用英文标题
        paper_title = context.research_topic_en if context.research_topic_en else context.research_topic
        paper = self.IEEE_TEMPLATE % {
            "title": paper_title,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "abstract": sections.get("abstract", self._generate_abstract(context)),
            "keywords": ", ".join(keywords[:5]),
            "content": content,
            "acknowledgment": self.SECTION_TEMPLATES.get("acknowledgment", ""),
            "appendix": ""
        }

        return paper

    def _generate_abstract(self, context: GlobalContext) -> str:
        """生成默认摘要（LLM调用失败时的回退）"""
        topic = context.research_topic or "advanced control method"
        innovations = ", ".join(context.innovation_points[:3]) if context.innovation_points else "novel control strategy"
        return (
            f"This paper presents a study on {topic}. "
            f"The main contributions include: {innovations}. "
            f"Simulation results demonstrate the effectiveness of the proposed method."
        )

    def _generate_conclusion(self, context: GlobalContext) -> str:
        """生成默认结论（LLM调用失败时的回退）"""
        topic = context.research_topic or "the proposed method"
        return (
            f"\\section{{Conclusion}}\n\n"
            f"In this paper, a novel control approach for {topic} has been proposed. "
            f"The stability of the closed-loop system has been rigorously analyzed using Lyapunov theory. "
            f"Simulation results have verified the effectiveness of the proposed method. "
            f"Future work will focus on experimental validation and extension to multi-axis systems."
        )

    def _get_output_dir(self) -> Path:
        """获取输出目录，优先使用output_manager的paper目录"""
        if self.output_manager and hasattr(self.output_manager, 'paper_dir') and self.output_manager.paper_dir:
            paper_dir = Path(self.output_manager.paper_dir)
            paper_dir.mkdir(parents=True, exist_ok=True)
            return paper_dir
        return self.output_dir

    def _save_paper(self, context: GlobalContext):
        """保存论文到文件"""
        output_dir = self._get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存LaTeX文件
        latex_path = output_dir / f"paper_{timestamp}.tex"
        with open(latex_path, 'w', encoding='utf-8') as f:
            f.write(context.paper_latex)

        # 保存思维导图结构
        structure_path = output_dir / f"paper_structure_{timestamp}.json"
        with open(structure_path, 'w', encoding='utf-8') as f:
            json.dump(context.paper_structure, f, indent=2, ensure_ascii=False)

        # 保存章节分离文件
        for section_name, content in context.paper_sections.items():
            section_path = output_dir / f"section_{section_name}_{timestamp}.tex"
            with open(section_path, 'w', encoding='utf-8') as f:
                f.write(content)

        context.paper_file_path = str(latex_path)
        logger.info("论文已保存至: %s", latex_path)


if __name__ == "__main__":
    # 测试代码
    import asyncio

    async def test():
        # 创建测试上下文
        from global_context import GlobalContext
        ctx = GlobalContext()
        ctx.research_config = {
            "main_algorithm": {"key": "adaptive", "name": "自适应控制 (Adaptive Control)"},
            "performance_objectives": [
                {"key": "chattering_elimination", "name": "消除抖动 (Chattering Elimination)"},
                {"key": "high_precision", "name": "高精度跟踪 (High Precision Tracking)"}
            ],
            "composite_architecture": {
                "feedback": {"key": "smc", "name": "滑模控制 (Sliding Mode Control)"},
                "feedforward": {"key": "none", "name": "无 (None)"},
                "observer": {"key": "eso", "name": "扩展状态观测器 (ESO)"}
            }
        }
        ctx.research_topic = "Adaptive Sliding Mode Control with Extended State Observer for High-Precision Motion Systems"
        ctx.innovation_points = [
            "A novel chattering-free sliding mode control law is proposed",
            "An improved ESO design with faster convergence is developed",
            "Rigorous finite-time stability analysis is provided"
        ]
        ctx.control_law_latex = r"\dot{s} = -k \text{sat}(s/\epsilon)"
        ctx.lyapunov_function = r"V = \frac{1}{2}s^2"
        ctx.stability_proof_latex = r"\dot{V} \leq -\eta V"
        ctx.figure_paths = ["simulation_results.png"]
        ctx.literature_results = [
            {"title": "Sliding Mode Control: Theory and Applications"},
            {"title": "Extended State Observer Based Control"}
        ]
        ctx.mathematical_assumptions = [
            "The system states are measurable",
            "The disturbance is bounded"
        ]

        # 创建Agent
        agent = ScribeAgent()

        # 执行
        print("开始执行撰稿人Agent...")
        ctx = await agent.execute(ctx)

        # 输出结果
        print(f"\n{'='*60}")
        print(f"论文LaTeX代码长度: {len(ctx.paper_latex)} 字符")
        print(f"\n【摘要预览】")
        print(ctx.paper_sections.get("abstract", "")[:500])
        print(f"\n{'='*60}")
        print("论文已生成！")

    asyncio.run(test())
