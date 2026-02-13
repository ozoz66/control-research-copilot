# -*- coding: utf-8 -*-
"""
全局上下文模块 - AutoControl-Scientist
定义Agent之间数据传递的核心数据结构

本模块实现Relay System协议，确保各Agent之间的数据流转顺畅。
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path


class WorkflowStage(Enum):
    """
    工作流阶段枚举

    定义研究自动化流程的各个阶段
    """
    IDLE = "idle"                        # 空闲状态
    LITERATURE_REVIEW = "literature"     # Agent A: 文献检索
    TOPIC_DESIGN = "topic"               # Agent A: 课题设计
    MATH_DERIVATION = "derivation"       # Agent B: 数学推导
    STABILITY_ANALYSIS = "stability"     # Agent B: 稳定性分析
    MATLAB_SIMULATION = "matlab"         # Agent C: MATLAB代码生成
    MATLAB_EXECUTION = "matlab_exec"     # Simulator: MATLAB仿真执行
    DSP_CODE_GEN = "dsp"                 # Agent C: DSP代码生成
    PAPER_STRUCTURE = "structure"        # Agent D: 论文结构设计
    PAPER_WRITING = "paper"              # Agent D: 论文撰写
    COMPLETED = "completed"              # 完成
    ERROR = "error"                      # 错误状态
    PAUSED = "paused"                    # 暂停状态


@dataclass
class ResearchConfig:
    """
    研究配置数据类

    存储用户在GUI中选择的研究方向配置
    """
    # 主算法
    main_algorithm_key: str = ""
    main_algorithm_name: str = ""

    # 性能目标列表
    performance_objectives: List[Dict[str, str]] = field(default_factory=list)

    # 复合架构
    feedback_controller_key: str = ""
    feedback_controller_name: str = ""
    feedforward_controller_key: str = ""
    feedforward_controller_name: str = ""
    observer_key: str = ""
    observer_name: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchConfig':
        """从字典创建实例"""
        config = cls()

        main_algo = data.get("main_algorithm", {})
        config.main_algorithm_key = main_algo.get("key", "")
        config.main_algorithm_name = main_algo.get("name", "")

        config.performance_objectives = data.get("performance_objectives", [])

        composite = data.get("composite_architecture", {})
        feedback = composite.get("feedback", {})
        config.feedback_controller_key = feedback.get("key", "")
        config.feedback_controller_name = feedback.get("name", "")

        feedforward = composite.get("feedforward", {})
        config.feedforward_controller_key = feedforward.get("key", "")
        config.feedforward_controller_name = feedforward.get("name", "")

        observer = composite.get("observer", {})
        config.observer_key = observer.get("key", "")
        config.observer_name = observer.get("name", "")

        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "main_algorithm": {
                "key": self.main_algorithm_key,
                "name": self.main_algorithm_name
            },
            "performance_objectives": self.performance_objectives,
            "composite_architecture": {
                "feedback": {
                    "key": self.feedback_controller_key,
                    "name": self.feedback_controller_name
                },
                "feedforward": {
                    "key": self.feedforward_controller_key,
                    "name": self.feedforward_controller_name
                },
                "observer": {
                    "key": self.observer_key,
                    "name": self.observer_name
                }
            }
        }

    def get_description(self) -> str:
        """获取配置的文字描述"""
        parts = [self.main_algorithm_name]

        if self.feedback_controller_name and "无" not in self.feedback_controller_name:
            parts.append(f"+ {self.feedback_controller_name}")

        if self.observer_name and "无" not in self.observer_name:
            parts.append(f"+ {self.observer_name}")

        if self.performance_objectives:
            objectives = [obj.get("name", "").split("(")[0].strip()
                         for obj in self.performance_objectives]
            parts.append(f"实现 {', '.join(objectives)}")

        return " ".join(parts)


@dataclass
class GlobalContext:
    """
    全局上下文

    在Agent之间传递数据的核心数据结构，实现Relay System协议。
    每个Agent读取其需要的输入，写入其产出的输出。
    """

    # ============================================================
    # 输入配置 (来自GUI)
    # ============================================================
    research_config: Dict[str, Any] = field(default_factory=dict)

    # ============================================================
    # Agent A 输出: 架构师 (文献检索与课题设计)
    # ============================================================
    literature_results: List[Dict[str, str]] = field(default_factory=list)
    """
    文献检索结果列表
    格式: [{"title": "", "authors": "", "abstract": "", "url": "", "year": "", "source": ""}]
    """

    research_topic: str = ""
    """研究课题 (中文)"""

    research_topic_en: str = ""
    """研究课题 (英文)"""

    innovation_points: List[str] = field(default_factory=list)
    """创新点列表"""

    research_gap: str = ""
    """研究空白分析"""

    research_motivation: str = ""
    """研究动机说明"""

    # ============================================================
    # Agent B 输出: 理论家 (数学推导与稳定性分析)
    # ============================================================
    system_model_latex: str = ""
    """系统数学模型 (LaTeX格式)"""

    mathematical_assumptions: List[str] = field(default_factory=list)
    """数学假设列表"""

    control_law_latex: str = ""
    """控制律推导 (LaTeX格式)"""

    observer_design_latex: str = ""
    """观测器设计 (LaTeX格式)"""

    lyapunov_function: str = ""
    """Lyapunov函数"""

    stability_proof_latex: str = ""
    """稳定性证明 (LaTeX格式)"""

    convergence_analysis: str = ""
    """收敛性分析"""

    parameter_tuning_guide: str = ""
    """参数整定指南"""

    # ============================================================
    # Agent C 输出: 工程师 (MATLAB仿真与DSP代码)
    # ============================================================
    # MATLAB相关
    matlab_code: str = ""
    """MATLAB仿真代码"""

    matlab_m_file_path: str = ""
    """.m文件保存路径"""

    simulation_results: Dict[str, Any] = field(default_factory=dict)
    """
    仿真结果
    格式: {"stdout": "", "figures": [], "data": {}, "metrics": {}}
    """

    figure_paths: List[str] = field(default_factory=list)
    """生成的图像文件路径列表"""

    simulation_metrics: Dict[str, float] = field(default_factory=dict)
    """
    仿真性能指标
    格式: {"max_error": 0.0, "rms_error": 0.0, "settling_time": 0.0, ...}
    """

    # DSP代码相关
    dsp_c_code: str = ""
    """TMS320F28335 DSP C代码 (主文件)"""

    dsp_header_code: str = ""
    """DSP头文件代码"""

    dsp_isr_code: str = ""
    """中断服务程序代码"""

    dsp_file_paths: List[str] = field(default_factory=list)
    """DSP代码文件路径列表"""

    # ============================================================
    # Agent D 输出: 撰稿人 (IEEE论文撰写)
    # ============================================================
    paper_structure: Dict[str, Any] = field(default_factory=dict)
    """论文结构/思维导图 (JSON格式)"""

    paper_latex: str = ""
    """完整的IEEE格式论文LaTeX代码"""

    paper_sections: Dict[str, str] = field(default_factory=dict)
    """
    论文各章节内容
    格式: {"abstract": "", "introduction": "", "methodology": "", ...}
    """

    paper_file_path: str = ""
    """论文LaTeX文件路径"""

    bibtex_entries: List[str] = field(default_factory=list)
    """参考文献BibTeX条目"""

    # ============================================================
    # 元数据与状态跟踪
    # ============================================================
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    """会话ID"""

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    """创建时间"""

    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    """最后更新时间"""

    current_stage: WorkflowStage = WorkflowStage.IDLE
    """当前工作流阶段"""

    progress_percent: int = 0
    """整体进度百分比 (0-100)"""

    error_log: List[str] = field(default_factory=list)
    """错误日志"""

    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    """
    执行日志
    格式: [{"timestamp": "", "agent": "", "action": "", "status": "", "details": ""}]
    """

    redo_request: Optional[Dict[str, str]] = None
    """
    Agent请求重做上游任务
    格式: {"agent": "architect", "reason": "..."}
    由当前Agent在执行中设置，由编排器检查并处理
    """

    supervision_history: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    """
    监督评估历史记录
    格式: {
        "agent_key": [
            {
                "iteration": 1,
                "timestamp": "2024-01-01T12:00:00",
                "score": 75.0,
                "passed": false,
                "issues": ["问题1", "问题2"],
                "suggestions": ["建议1", "建议2"],
                "rollback_to": null
            },
            ...
        ]
    }
    """

    redo_count: Dict[str, int] = field(default_factory=dict)
    """
    Redo请求计数器（防止无限循环）
    格式: {"architect": 2, "theorist": 1}
    记录每个Agent被请求重做的次数
    """

    # ============================================================
    # 辅助方法
    # ============================================================

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()

    def set_stage(self, stage: WorkflowStage, progress: int = None):
        """
        设置当前阶段

        Args:
            stage: 工作流阶段
            progress: 进度百分比（可选）
        """
        self.current_stage = stage
        if progress is not None:
            self.progress_percent = progress
        self.update_timestamp()

    def log_execution(
        self,
        agent: str,
        action: str,
        status: str,
        details: str = ""
    ):
        """
        记录执行日志

        Args:
            agent: Agent名称
            action: 执行的动作
            status: 状态 (started, success, failed, warning)
            details: 详细信息
        """
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "action": action,
            "status": status,
            "details": details
        })
        self.update_timestamp()

    def log_supervision(
        self,
        agent_key: str,
        iteration: int,
        score: float,
        passed: bool,
        issues: List[str],
        suggestions: List[str],
        rollback_to: Optional[str] = None
    ):
        """
        记录监督评估结果

        Args:
            agent_key: Agent标识
            iteration: 迭代次数（1-based）
            score: 评分（0-100）
            passed: 是否通过
            issues: 问题列表
            suggestions: 建议列表
            rollback_to: 回退目标
        """
        if agent_key not in self.supervision_history:
            self.supervision_history[agent_key] = []

        self.supervision_history[agent_key].append({
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "passed": passed,
            "issues": issues,
            "suggestions": suggestions,
            "rollback_to": rollback_to
        })
        self.update_timestamp()

    def get_latest_supervision_score(self, agent_key: str) -> Optional[float]:
        """
        获取指定Agent的最新监督评分

        Args:
            agent_key: Agent标识

        Returns:
            最新评分，如果没有历史记录则返回None
        """
        if agent_key not in self.supervision_history:
            return None
        if not self.supervision_history[agent_key]:
            return None
        return self.supervision_history[agent_key][-1]["score"]

    def clear_stage_outputs(self, stage: 'WorkflowStage'):
        """
        清除指定阶段及之后阶段的输出数据（用于回退）

        Args:
            stage: 要清除的起始阶段
        """
        # 定义每个阶段对应的输出字段
        stage_fields = {
            WorkflowStage.LITERATURE_REVIEW: [
                'literature_results', 'research_topic', 'research_topic_en',
                'innovation_points', 'research_gap', 'research_motivation'
            ],
            WorkflowStage.MATH_DERIVATION: [
                'system_model_latex', 'mathematical_assumptions', 'control_law_latex',
                'observer_design_latex', 'lyapunov_function', 'stability_proof_latex',
                'convergence_analysis', 'parameter_tuning_guide'
            ],
            WorkflowStage.MATLAB_SIMULATION: [
                'matlab_code', 'matlab_m_file_path'
            ],
            WorkflowStage.MATLAB_EXECUTION: [
                'simulation_results', 'figure_paths', 'simulation_metrics'
            ],
            WorkflowStage.DSP_CODE_GEN: [
                'dsp_c_code', 'dsp_header_code', 'dsp_isr_code', 'dsp_file_paths'
            ],
            WorkflowStage.PAPER_WRITING: [
                'paper_structure', 'paper_latex', 'paper_sections',
                'paper_file_path', 'bibtex_entries'
            ],
        }

        fields_to_clear = stage_fields.get(stage, [])
        for field_name in fields_to_clear:
            if hasattr(self, field_name):
                attr = getattr(self, field_name)
                if isinstance(attr, str):
                    setattr(self, field_name, "")
                elif isinstance(attr, list):
                    setattr(self, field_name, [])
                elif isinstance(attr, dict):
                    setattr(self, field_name, {})

        self.update_timestamp()

    def log_error(self, error_msg: str):
        """记录错误"""
        self.error_log.append(f"[{datetime.now().isoformat()}] {error_msg}")
        self.update_timestamp()

    def get_parsed_config(self) -> ResearchConfig:
        """获取解析后的研究配置"""
        return ResearchConfig.from_dict(self.research_config)

    # ============================================================
    # 序列化方法
    # ============================================================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            # 配置
            "research_config": self.research_config,

            # Agent A 输出
            "literature_results": self.literature_results,
            "research_topic": self.research_topic,
            "research_topic_en": self.research_topic_en,
            "innovation_points": self.innovation_points,
            "research_gap": self.research_gap,
            "research_motivation": self.research_motivation,

            # Agent B 输出
            "system_model_latex": self.system_model_latex,
            "mathematical_assumptions": self.mathematical_assumptions,
            "control_law_latex": self.control_law_latex,
            "observer_design_latex": self.observer_design_latex,
            "lyapunov_function": self.lyapunov_function,
            "stability_proof_latex": self.stability_proof_latex,
            "convergence_analysis": self.convergence_analysis,
            "parameter_tuning_guide": self.parameter_tuning_guide,

            # Agent C 输出
            "matlab_code": self.matlab_code,
            "matlab_m_file_path": self.matlab_m_file_path,
            "simulation_results": self.simulation_results,
            "figure_paths": self.figure_paths,
            "simulation_metrics": self.simulation_metrics,
            "dsp_c_code": self.dsp_c_code,
            "dsp_header_code": self.dsp_header_code,
            "dsp_isr_code": self.dsp_isr_code,
            "dsp_file_paths": self.dsp_file_paths,

            # Agent D 输出
            "paper_structure": self.paper_structure,
            "paper_latex": self.paper_latex,
            "paper_sections": self.paper_sections,
            "paper_file_path": self.paper_file_path,
            "bibtex_entries": self.bibtex_entries,

            # 元数据
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_stage": self.current_stage.value,
            "progress_percent": self.progress_percent,
            "error_log": self.error_log,
            "execution_log": self.execution_log,
            "supervision_history": self.supervision_history,
            "redo_count": self.redo_count
        }

    def save_to_file(self, path: str):
        """
        保存上下文到JSON文件

        Args:
            path: 文件路径
        """
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, path: str) -> 'GlobalContext':
        """
        从JSON文件加载上下文

        Args:
            path: 文件路径

        Returns:
            GlobalContext实例
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ctx = cls()

        # 逐字段赋值
        for key, value in data.items():
            if key == "current_stage":
                ctx.current_stage = WorkflowStage(value)
            elif hasattr(ctx, key):
                setattr(ctx, key, value)

        return ctx

    def get_summary(self) -> str:
        """
        获取上下文摘要信息

        Returns:
            摘要字符串
        """
        config = self.get_parsed_config()

        summary = f"""
========== 研究上下文摘要 ==========
会话ID: {self.session_id}
当前阶段: {self.current_stage.value}
进度: {self.progress_percent}%

【研究配置】
{config.get_description()}

【研究课题】
{self.research_topic if self.research_topic else '待生成'}

【创新点】
{chr(10).join(f'  - {p}' for p in self.innovation_points) if self.innovation_points else '  待生成'}

【产出状态】
- 文献检索: {'✓ ' + str(len(self.literature_results)) + '篇' if self.literature_results else '✗'}
- 数学推导: {'✓' if self.control_law_latex else '✗'}
- MATLAB仿真: {'✓' if self.matlab_code else '✗'}
- DSP代码: {'✓' if self.dsp_c_code else '✗'}
- 论文撰写: {'✓' if self.paper_latex else '✗'}

【错误记录】
{chr(10).join(self.error_log[-3:]) if self.error_log else '无错误'}
========================================
"""
        return summary


# ============================================================
# 便捷工厂函数
# ============================================================

def create_context_from_gui_config(gui_config: Dict[str, Any]) -> GlobalContext:
    """
    从GUI配置创建新的上下文

    Args:
        gui_config: GUI返回的配置字典

    Returns:
        初始化的GlobalContext
    """
    ctx = GlobalContext()
    ctx.research_config = gui_config
    ctx.set_stage(WorkflowStage.IDLE, 0)
    ctx.log_execution("System", "上下文初始化", "success",
                     f"配置: {ctx.get_parsed_config().get_description()}")
    return ctx


if __name__ == "__main__":
    # 测试代码
    test_config = {
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

    # 创建上下文
    ctx = create_context_from_gui_config(test_config)

    # 模拟Agent A输出
    ctx.research_topic = "基于扩展状态观测器的自适应滑模控制抖振消除方法研究"
    ctx.innovation_points = ["新型ESO设计", "自适应趋近律", "抖振消除策略"]
    ctx.set_stage(WorkflowStage.TOPIC_DESIGN, 20)

    # 打印摘要
    print(ctx.get_summary())

    # 保存到文件
    ctx.save_to_file("./output/test_context.json")
    print("上下文已保存到 ./output/test_context.json")

    # 从文件加载
    loaded_ctx = GlobalContext.load_from_file("./output/test_context.json")
    print(f"\n加载的研究课题: {loaded_ctx.research_topic}")
