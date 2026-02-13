# -*- coding: utf-8 -*-
"""
Shared workflow stage definitions.

This module centralizes stage ordering so GUI/API code can reason about
rollback targets without depending on legacy orchestrator implementations.
"""

from typing import List, Dict


WORKFLOW_GRAPH: List[Dict[str, str]] = [
    {
        "stage_key": "literature",
        "agent_key": "architect",
        "description": "Agent A: 文献检索与课题设计",
    },
    {
        "stage_key": "derivation",
        "agent_key": "theorist",
        "description": "Agent B: 数学推导",
    },
    {
        "stage_key": "simulation",
        "agent_key": "engineer",
        "description": "Agent C: MATLAB代码生成",
    },
    {
        "stage_key": "sim_run",
        "agent_key": "simulator",
        "description": "Simulator: MATLAB仿真执行",
    },
    {
        "stage_key": "dsp_code",
        "agent_key": "dsp_coder",
        "description": "Agent E: DSP代码生成",
    },
    {
        "stage_key": "paper",
        "agent_key": "scribe",
        "description": "Agent D: 论文撰写",
    },
]


def find_stage_index(stage_or_agent_key: str) -> int:
    """
    Find stage index by stage_key or agent_key.
    Returns -1 when not found.
    """
    for idx, node in enumerate(WORKFLOW_GRAPH):
        if stage_or_agent_key in (node["stage_key"], node["agent_key"]):
            return idx
    return -1
