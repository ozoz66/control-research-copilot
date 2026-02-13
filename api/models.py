# -*- coding: utf-8 -*-
"""
Pydantic request/response models for AutoControl-Scientist API.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Canonical option dictionaries used by workflow/agents.
MAIN_ALGORITHMS: Dict[str, str] = {
    "adaptive": "Adaptive Control",
    "ilc": "Iterative Learning Control",
    "repetitive": "Repetitive Control",
    "robust": "Robust Control",
    "mpc": "Model Predictive Control",
    "optimal": "Optimal Control",
    "neural_network": "Neural Network Control",
    "fuzzy": "Fuzzy Control",
    "reinforcement": "Reinforcement Learning",
    "fault_tolerant": "Fault-Tolerant Control",
    "nonlinear": "Nonlinear Control",
    "stochastic": "Stochastic Control",
    "distributed": "Distributed Control",
    "cooperative": "Cooperative Control",
    "event_triggered": "Event-Triggered Control",
}

PERFORMANCE_OBJECTIVES: Dict[str, str] = {
    "chattering_elimination": "Chattering Elimination",
    "finite_time": "Finite-time Convergence",
    "fast_transient": "Fast Transient Response",
    "high_precision": "High Precision Tracking",
    "disturbance_rejection": "Disturbance Rejection",
    "robustness": "Robustness Enhancement",
    "energy_saving": "Energy Saving",
    "overshoot_reduction": "Overshoot Reduction",
    "noise_attenuation": "Noise Attenuation",
    "steady_state_error": "Steady-State Error Elimination",
    "bandwidth_extension": "Bandwidth Extension",
    "stability_margin": "Stability Margin Enhancement",
    "anti_windup": "Anti-Windup",
    "constraint_handling": "Constraint Handling",
}

FEEDBACK_CONTROLLERS: Dict[str, str] = {
    "none": "None",
    "pid": "PID Controller",
    "smc": "Sliding Mode Control",
    "backstepping": "Backstepping",
    "h_infinity": "H-infinity",
    "lqr": "LQR",
    "lqg": "LQG",
    "pole_placement": "Pole Placement",
    "passivity_based": "Passivity-Based",
    "feedback_linearization": "Feedback Linearization",
    "dynamic_inversion": "Dynamic Inversion",
    "mu_synthesis": "Mu-Synthesis",
    "gain_scheduling": "Gain Scheduling",
}

FEEDFORWARD_CONTROLLERS: Dict[str, str] = {
    "none": "None",
    "zpetc": "ZPETC",
    "inverse_dynamics": "Inverse Dynamics",
    "iterative_ff": "Iterative Feedforward",
    "model_based_ff": "Model-Based Feedforward",
    "preview_control": "Preview Control",
    "acceleration_ff": "Acceleration Feedforward",
    "friction_compensation": "Friction Compensation",
    "gravity_compensation": "Gravity Compensation",
    "inertia_ff": "Inertia Feedforward",
}

OBSERVERS: Dict[str, str] = {
    "none": "None",
    "eso": "Extended State Observer",
    "smo": "Sliding Mode Observer",
    "dob": "Disturbance Observer",
    "kalman": "Kalman Filter",
    "ekf": "Extended Kalman Filter",
    "ukf": "Unscented Kalman Filter",
    "luenberger": "Luenberger Observer",
    "high_gain": "High-Gain Observer",
    "adaptive_observer": "Adaptive Observer",
    "unknown_input": "Unknown Input Observer",
    "finite_time_observer": "Finite-Time Observer",
    "neural_observer": "Neural Observer",
}


class ChoiceItem(BaseModel):
    """Canonical key/name pair used in workflow configuration."""

    key: str = Field(default="", description="Stable key, e.g. `adaptive`")
    name: str = Field(default="", description="Display name")


class CompositeArchitecture(BaseModel):
    """Composite control architecture."""

    feedback: ChoiceItem = Field(default_factory=lambda: ChoiceItem(key="pid", name=FEEDBACK_CONTROLLERS["pid"]))
    feedforward: ChoiceItem = Field(default_factory=lambda: ChoiceItem(key="none", name=FEEDFORWARD_CONTROLLERS["none"]))
    observer: ChoiceItem = Field(default_factory=lambda: ChoiceItem(key="none", name=OBSERVERS["none"]))


def _slugify_key(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return token.strip("_")


def _normalize_option(
    value: Any,
    known_options: Dict[str, str],
    default_key: str,
) -> Dict[str, str]:
    raw_key = ""
    raw_name = ""

    if isinstance(value, ChoiceItem):
        raw_key = (value.key or "").strip()
        raw_name = (value.name or "").strip()
    elif isinstance(value, dict):
        raw_key = str(value.get("key", "") or "").strip()
        raw_name = str(value.get("name", "") or "").strip()
    elif isinstance(value, str):
        raw_name = value.strip()

    key = _slugify_key(raw_key) if raw_key else ""
    name = raw_name

    if not key and name:
        lowered = name.lower()
        for candidate_key, candidate_name in known_options.items():
            if lowered == candidate_key.lower() or lowered == candidate_name.lower():
                key = candidate_key
                name = candidate_name
                break

    if not key and name:
        key = _slugify_key(name)

    if not key:
        key = default_key

    if key in known_options and not name:
        name = known_options[key]
    elif not name:
        name = key

    return {"key": key, "name": name}


def _normalize_performance_objectives(values: Any) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    seen: set[str] = set()

    if isinstance(values, list):
        for item in values:
            obj = _normalize_option(item, PERFORMANCE_OBJECTIVES, "fast_transient")
            if obj["key"] in seen:
                continue
            seen.add(obj["key"])
            normalized.append(obj)

    if normalized:
        return normalized

    return [
        _normalize_option("fast_transient", PERFORMANCE_OBJECTIVES, "fast_transient"),
        _normalize_option("overshoot_reduction", PERFORMANCE_OBJECTIVES, "fast_transient"),
    ]


def _normalize_composite_architecture(value: Any) -> Dict[str, Dict[str, str]]:
    if isinstance(value, str):
        lowered = value.lower()
        feedback: Any = ChoiceItem(key="pid", name=FEEDBACK_CONTROLLERS["pid"])
        feedforward: Any = ChoiceItem(key="none", name=FEEDFORWARD_CONTROLLERS["none"])
        observer: Any = ChoiceItem(key="none", name=OBSERVERS["none"])

        if "smc" in lowered or "sliding" in lowered:
            feedback = ChoiceItem(key="smc", name=FEEDBACK_CONTROLLERS["smc"])
        if "zpetc" in lowered or "feedforward" in lowered:
            feedforward = ChoiceItem(key="zpetc", name=FEEDFORWARD_CONTROLLERS["zpetc"])
        if "eso" in lowered:
            observer = ChoiceItem(key="eso", name=OBSERVERS["eso"])
        elif "dob" in lowered:
            observer = ChoiceItem(key="dob", name=OBSERVERS["dob"])
        elif "kalman" in lowered:
            observer = ChoiceItem(key="kalman", name=OBSERVERS["kalman"])

        return {
            "feedback": _normalize_option(feedback, FEEDBACK_CONTROLLERS, "pid"),
            "feedforward": _normalize_option(feedforward, FEEDFORWARD_CONTROLLERS, "none"),
            "observer": _normalize_option(observer, OBSERVERS, "none"),
        }

    payload: Dict[str, Any]
    if isinstance(value, CompositeArchitecture):
        payload = value.model_dump()
    elif isinstance(value, dict):
        payload = value
    else:
        payload = {}

    return {
        "feedback": _normalize_option(payload.get("feedback"), FEEDBACK_CONTROLLERS, "pid"),
        "feedforward": _normalize_option(payload.get("feedforward"), FEEDFORWARD_CONTROLLERS, "none"),
        "observer": _normalize_option(payload.get("observer"), OBSERVERS, "none"),
    }


class ResearchRequest(BaseModel):
    """Request body for starting a research workflow."""

    main_algorithm: Union[ChoiceItem, str] = Field(
        default_factory=lambda: ChoiceItem(
            key="adaptive",
            name=MAIN_ALGORITHMS["adaptive"],
        ),
        description="Main control algorithm. Preferred: {key, name}.",
    )
    performance_objectives: Union[List[ChoiceItem], List[str]] = Field(
        default_factory=lambda: [
            ChoiceItem(
                key="fast_transient",
                name=PERFORMANCE_OBJECTIVES["fast_transient"],
            ),
            ChoiceItem(
                key="overshoot_reduction",
                name=PERFORMANCE_OBJECTIVES["overshoot_reduction"],
            ),
        ],
        description="Performance objective list. Preferred: [{key, name}, ...].",
    )
    composite_architecture: Union[CompositeArchitecture, str] = Field(
        default_factory=CompositeArchitecture,
        description="Composite control architecture. Preferred: nested key/name object.",
    )
    custom_topic: Optional[str] = Field(
        default=None,
        description="Optional custom topic. If provided, upstream agents may prioritize it.",
    )

    def to_research_config(self) -> Dict[str, Any]:
        """Normalize API request into workflow/agent expected schema."""
        config: Dict[str, Any] = {
            "main_algorithm": _normalize_option(self.main_algorithm, MAIN_ALGORITHMS, "adaptive"),
            "performance_objectives": _normalize_performance_objectives(self.performance_objectives),
            "composite_architecture": _normalize_composite_architecture(self.composite_architecture),
        }
        if self.custom_topic:
            config["custom_topic"] = self.custom_topic.strip()
        return config


class ConfirmRequest(BaseModel):
    """Stage confirmation request."""

    modification: Optional[str] = Field(default=None, description="Optional free-form modification.")
    rollback_to: Optional[str] = Field(
        default=None,
        description="Optional rollback target stage key (e.g. `derivation`).",
    )


class ResearchStartResponse(BaseModel):
    """Start workflow response."""

    session_id: str
    message: str = "Research workflow started."


class ResearchStatusResponse(BaseModel):
    """Workflow status response."""

    session_id: str
    state: str
    progress: int = 0
    current_stage: str = ""
    error: Optional[str] = None


class AgentSummary(BaseModel):
    """Per-agent aggregated metrics."""

    agent_key: str
    llm_calls: int = 0
    total_tokens: int = 0
    avg_response_time: float = 0.0


class HistoryResponse(BaseModel):
    """Session history summary response."""

    session_id: str
    total_records: int = 0
    agents: List[str] = Field(default_factory=list)
    agent_summaries: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health response."""

    status: str = "ok"
    version: str = "1.0.0"
    active_sessions: int = 0
