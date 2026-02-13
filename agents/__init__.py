# -*- coding: utf-8 -*-
"""
AutoControl-Scientist Agent模块
包含所有研究自动化Agent的实现

Agent协作流程:
1. ArchitectAgent (Agent A) - 文献检索与课题设计
2. TheoristAgent (Agent B) - 数学推导与稳定性分析
3. EngineerAgent (Agent C) - MATLAB仿真
4. DSPCoderAgent (Agent E) - DSP代码生成
5. ScribeAgent (Agent D) - IEEE论文撰写
6. SupervisorAgent (Agent S) - 质量评估与改进监督
"""

from .base import (
    BaseAgent,
    AgentType,
    APIConfig,
    SupervisorFeedback,
    RedoRequest,
)
from .architect import ArchitectAgent
from .theorist import TheoristAgent
from .engineer import EngineerAgent
from .dsp_coder import DSPCoderAgent
from .scribe import ScribeAgent
from .simulator import SimulatorAgent
from .supervisor import SupervisorAgent

__all__ = [
    # Base classes and types
    'BaseAgent',
    'AgentType',
    'APIConfig',
    'SupervisorFeedback',
    'RedoRequest',
    # Agent implementations
    'ArchitectAgent',
    'TheoristAgent',
    'EngineerAgent',
    'SimulatorAgent',
    'DSPCoderAgent',
    'ScribeAgent',
    'SupervisorAgent',
]
