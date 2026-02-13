# -*- coding: utf-8 -*-
"""Prompt模板管理模块"""

from .prompt_loader import PromptLoader
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from global_context import GlobalContext


class PromptTemplates:
    """
    Agent提示词模板集合
    提供各Agent所需的prompt模板渲染
    """
    
    _loader = PromptLoader(domain="control_systems")

    @classmethod
    def architect_literature_search(cls, config: Dict[str, Any]) -> str:
        """
        架构师Agent文献检索与课题设计提示词
        """
        main_algo = config.get("main_algorithm", {}).get("name", "")
        objectives = [obj.get("name", "") for obj in config.get("performance_objectives", [])]
        composite = config.get("composite_architecture", {})
        feedback = composite.get("feedback", {}).get("name", "")
        feedforward = composite.get("feedforward", {}).get("name", "")
        observer = composite.get("observer", {}).get("name", "")
        custom_topic = config.get("custom_topic", "")

        if custom_topic:
            topic_section = f"自定义研究方向: {custom_topic}"
        else:
            topic_section = f"""主算法: {main_algo}
性能目标: {', '.join(objectives) if objectives else '未指定'}
反馈控制: {feedback}
前馈控制: {feedforward}
观测器: {observer}"""

        return cls._loader.load("architect", "literature_search", topic_section=topic_section)

    @classmethod
    def theorist_derivation(cls, context: 'GlobalContext') -> str:
        """
        理论家Agent数学推导提示词
        """
        config = context.research_config
        main_algo = config.get("main_algorithm", {}).get("name", "")
        objectives = [obj.get("name", "") for obj in config.get("performance_objectives", [])]
        composite = config.get("composite_architecture", {})
        feedback = composite.get("feedback", {}).get("name", "")
        observer = composite.get("observer", {}).get("name", "")
        app_scenario = config.get("application_scenario", {}).get("name", "")

        innovation_points_text = (
            chr(10).join(f'- {p}' for p in context.innovation_points) 
            if context.innovation_points else '待定'
        )
        
        research_gap_section = ""
        if context.research_gap:
            research_gap_section = f"""
【研究空白与动机】
{context.research_gap}

{context.research_motivation if context.research_motivation else ''}
"""

        return cls._loader.load(
            "theorist", "derivation",
            research_topic=context.research_topic,
            main_algo=main_algo,
            objectives=', '.join(objectives) if objectives else '未指定',
            feedback=feedback,
            observer=observer,
            app_scenario=app_scenario if app_scenario else '通用运动控制系统',
            innovation_points_text=innovation_points_text,
            research_gap_section=research_gap_section
        )

    @classmethod
    def engineer_matlab(cls, context: 'GlobalContext') -> str:
        """
        工程师Agent MATLAB仿真代码生成提示词
        """
        config = context.research_config
        main_algo = config.get("main_algorithm", {}).get("name", "")
        objectives = [obj.get("name", "") for obj in config.get("performance_objectives", [])]
        app_scenario = config.get("application_scenario", {}).get("name", "")

        control_law_preview = ""
        if context.control_law_latex:
            control_law_preview = context.control_law_latex[:5000]
            if len(context.control_law_latex) > 5000:
                control_law_preview += "\n... (更多内容省略)"

        innovation_points_text = (
            chr(10).join(f'- {p}' for p in context.innovation_points) 
            if context.innovation_points else '(无特定创新点)'
        )

        observer_preview = context.observer_design_latex if context.observer_design_latex else '(无观测器设计或待定)'
        
        assumptions_preview = ""
        if context.mathematical_assumptions:
            assumptions_preview = f"\n【数学假设】\n{context.mathematical_assumptions[:2000]}"

        tuning_guide_preview = ""
        if context.parameter_tuning_guide:
            tuning_guide_preview = f"\n【参数整定指南】\n{context.parameter_tuning_guide[:1500]}"

        return cls._loader.load(
            "engineer", "matlab_simulation",
            research_topic=context.research_topic,
            main_algo=main_algo,
            objectives=', '.join(objectives) if objectives else '未指定',
            app_scenario=app_scenario if app_scenario else '通用运动控制系统',
            innovation_points_text=innovation_points_text,
            control_law_preview=control_law_preview,
            observer_preview=observer_preview,
            assumptions_preview=assumptions_preview,
            tuning_guide_preview=tuning_guide_preview
        )

    @classmethod
    def dsp_code(cls, context: 'GlobalContext') -> str:
        """
        DSP编码器Agent提示词
        """
        matlab_code_preview = context.matlab_code[:3000] if context.matlab_code else "待定义"
        control_law_latex = context.control_law_latex[:1500] if context.control_law_latex else "见MATLAB代码"
        
        return cls._loader.load(
            "dsp_coder", "dsp_generation",
            matlab_code_preview=matlab_code_preview,
            control_law_latex=control_law_latex
        )

    @classmethod
    def simulator_fix_code(cls, error_msg: str, code: str) -> str:
        """仿真代码自动修复提示词"""
        return cls._loader.load(
            "simulator", "fix_code",
            error_msg=error_msg[:1000],
            code=code
        )

    @classmethod
    def simulator_analysis(cls, context: 'GlobalContext') -> str:
        """仿真结果分析提示词"""
        stdout = context.simulation_results.get("stdout", "")
        figures = context.simulation_results.get("figures", [])
        metrics = context.simulation_metrics or {}
        
        return cls._loader.load(
            "simulator", "analysis",
            research_topic=context.research_topic,
            matlab_code_preview=context.matlab_code[:1500] if context.matlab_code else '(无)',
            stdout_preview=stdout[:2000] if stdout else '(无输出)',
            metrics_json=json.dumps(metrics, ensure_ascii=False) if metrics else '(无)',
            figures_list=', '.join([Path(f).name for f in figures]) if figures else '(无图像)'
        )

    @classmethod
    def simulator_refine(cls, matlab_code: str, analysis: Dict[str, Any]) -> str:
        """仿真参数优化提示词"""
        issues = analysis.get("issues", [])
        suggestions = analysis.get("parameter_suggestions", {})
        
        return cls._loader.load(
            "simulator", "refine",
            issues_text='\n'.join(f'- {issue}' for issue in issues),
            suggestions_json=json.dumps(suggestions, ensure_ascii=False, indent=2) if suggestions else '(无具体建议)',
            matlab_code=matlab_code
        )


__all__ = ['PromptLoader', 'PromptTemplates']
