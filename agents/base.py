# -*- coding: utf-8 -*-
"""
Base Agent module for AutoControl-Scientist.
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union

from logger_config import get_logger

logger = get_logger(__name__)


class AgentType(Enum):
    """Supported agent types."""

    ARCHITECT = "architect"
    THEORIST = "theorist"
    ENGINEER = "engineer"
    DSP_CODER = "dsp_coder"
    SCRIBE = "scribe"
    SIMULATOR = "simulator"
    SUPERVISOR = "supervisor"


@dataclass
class APIConfig:
    """Unified API configuration."""

    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: int = 60
    max_retries: int = 3
    rag_enabled: bool = True
    rag_top_k: int = 4
    rag_min_score: float = 0.08
    rag_max_chunks_per_file: int = 2
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 200
    rag_max_context_chars: int = 5000
    rag_max_file_size_kb: int = 512
    rag_paths: List[str] = field(
        default_factory=lambda: ["./README.md", "./docs", "./prompts/control_systems"]
    )
    rag_include_globs: List[str] = field(
        default_factory=lambda: ["*.md", "*.txt", "*.rst", "*.yaml", "*.yml", "*.tex", "*.json", "*.py"]
    )
    skill_enabled: bool = True
    skill_max_context_chars: int = 4000
    skill_max_files: int = 8
    skill_max_file_size_kb: int = 256
    skill_paths: List[str] = field(default_factory=lambda: ["./skills"])
    skill_include_globs: List[str] = field(
        default_factory=lambda: ["*.md", "*.txt", "*.rst", "*.yaml", "*.yml"]
    )

    @property
    def model_name(self) -> str:
        """Compatibility alias used by AgentConfig and llm_client."""
        return self.model

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else "",
            "model": self.model,
            "model_name": self.model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rag_enabled": self.rag_enabled,
            "rag_top_k": self.rag_top_k,
            "rag_min_score": self.rag_min_score,
            "rag_max_chunks_per_file": self.rag_max_chunks_per_file,
            "rag_chunk_size": self.rag_chunk_size,
            "rag_chunk_overlap": self.rag_chunk_overlap,
            "rag_max_context_chars": self.rag_max_context_chars,
            "rag_max_file_size_kb": self.rag_max_file_size_kb,
            "rag_paths": list(self.rag_paths),
            "rag_include_globs": list(self.rag_include_globs),
            "skill_enabled": self.skill_enabled,
            "skill_max_context_chars": self.skill_max_context_chars,
            "skill_max_files": self.skill_max_files,
            "skill_max_file_size_kb": self.skill_max_file_size_kb,
            "skill_paths": list(self.skill_paths),
            "skill_include_globs": list(self.skill_include_globs),
        }


@dataclass
class RedoRequest:
    target_agent: str
    reason: str
    stage: Optional[str] = None


@dataclass
class SupervisorFeedback:
    agent: str
    score: float
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    redo_request: Optional[RedoRequest] = None


class ContextProtocol(Protocol):
    redo_request: Optional[Dict[str, str]]


class BaseAgent:
    """Common base class for all agents."""

    _default_system_prompt: str = ""
    _default_temperature: float = 0.5

    def __init__(
        self,
        name: str,
        agent_type: Union[str, AgentType],
        description: str = "",
        version: str = "1.0.0",
    ):
        self.name = name
        self.agent_type = agent_type
        self.description = description
        self.version = version
        self.api_config: Optional[Any] = None
        self.supervisor_feedback: Optional[Union[str, SupervisorFeedback]] = None

    def set_api_config(self, config: Any) -> None:
        self.api_config = config

    def set_supervisor_feedback(self, feedback: Union[str, SupervisorFeedback]) -> None:
        self.supervisor_feedback = feedback

    @staticmethod
    def _find_matching_brace(text: str, start: int) -> int:
        if start < 0 or start >= len(text) or text[start] != "{":
            return -1

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if escaped:
                escaped = False
                continue
            if in_string and ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return idx
        return -1

    def _get_feedback_prompt_section(self) -> str:
        if not self.supervisor_feedback:
            return ""

        if isinstance(self.supervisor_feedback, str):
            feedback = self.supervisor_feedback
            if len(feedback) > 5000:
                feedback = feedback[:5000] + "\n...(反馈过长已截断)"
            return f"\n\n【监督 Agent 反馈 - 请务必根据以下意见改进输出】\n{feedback}"

        feedback_lines = [
            "\n\n【监督 Agent 反馈 - 请务必根据以下意见改进输出】",
            f"评分: {self.supervisor_feedback.score}/100",
        ]

        if self.supervisor_feedback.strengths:
            feedback_lines.append("优点:")
            for item in self.supervisor_feedback.strengths[:5]:
                feedback_lines.append(f"  - {item[:200]}")

        if self.supervisor_feedback.weaknesses:
            feedback_lines.append("缺点:")
            for item in self.supervisor_feedback.weaknesses[:8]:
                feedback_lines.append(f"  - {item[:200]}")

        if self.supervisor_feedback.suggestions:
            feedback_lines.append("改进建议:")
            for item in self.supervisor_feedback.suggestions[:8]:
                feedback_lines.append(f"  - {item[:300]}")

        return "\n".join(feedback_lines)

    def _check_redo_request(
        self,
        llm_response: str,
        context: ContextProtocol,
    ) -> Optional[RedoRequest]:
        try:
            match = re.search(r'"request_redo"\s*:\s*\{', llm_response)
            if not match:
                return None

            brace_start = llm_response.find("{", match.start())
            brace_end = self._find_matching_brace(llm_response, brace_start)
            if brace_end < 0:
                return None

            redo_json_str = "{" + llm_response[match.start(): brace_end + 1] + "}"
            redo_data = json.loads(redo_json_str)
            redo = redo_data.get("request_redo", {})

            if isinstance(redo, dict) and redo.get("agent") and redo.get("reason"):
                context.redo_request = {
                    "agent": redo["agent"],
                    "reason": redo["reason"],
                }
                return RedoRequest(
                    target_agent=redo["agent"],
                    reason=redo["reason"],
                    stage=redo.get("stage"),
                )
        except (json.JSONDecodeError, AttributeError, KeyError, ValueError):
            return None
        return None

    async def execute(self, context: ContextProtocol) -> ContextProtocol:
        raise NotImplementedError(f"{self.__class__.__name__} 必须实现 execute 方法")

    def _build_prompt(self, context: ContextProtocol) -> str:
        raise NotImplementedError(f"{self.__class__.__name__} 必须实现 _build_prompt 方法")

    @staticmethod
    def _extract_json_from_text(text: str) -> dict:
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        brace_depth = 0
        start = text.find("{")
        if start == -1:
            raise ValueError("无法从文本中找到 JSON 对象")

        for i in range(start, len(text)):
            if text[i] == "{":
                brace_depth += 1
            elif text[i] == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        next_start = text.find("{", i + 1)
                        if next_start == -1:
                            break
                        start = next_start
        raise ValueError("无法从文本中提取有效 JSON 对象")

    @staticmethod
    def _extract_code_block(text: str, language: str = "matlab") -> str:
        pattern = rf"```(?:{language})?\s*([\s\S]*?)```"
        matches = [block.strip() for block in re.findall(pattern, text) if block.strip()]
        if matches:
            return "\n\n".join(matches)
        return text

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float | None = None,
        timeout: int = 180,
        max_retries: int = 3,
        max_tokens: int = 16384,
        agent_key: str | None = None,
    ) -> str:
        from core.rag import build_rag_context
        from core.skills import build_local_skill_context
        from llm_client import call_llm_api

        if not system_prompt:
            system_prompt = self._default_system_prompt
        if temperature is None:
            temperature = self._default_temperature

        raw_agent_type = self.agent_type.value if hasattr(self.agent_type, "value") else str(self.agent_type)
        skill_context = ""
        try:
            skill_context = build_local_skill_context(self.api_config, raw_agent_type)
        except Exception as e:
            logger.warning("Local skill loading failed, fallback to plain system prompt: %s", e)

        if skill_context:
            system_prompt = (
                f"{system_prompt}\n\n"
                "=== Local Skills ===\n"
                "Follow these local project skills as higher-priority guidance when applicable.\n\n"
                f"{skill_context}\n"
                "=== End Local Skills ==="
            )

        rag_context = ""
        try:
            rag_context = build_rag_context(prompt, self.api_config)
        except Exception as e:
            logger.warning("RAG retrieval failed, fallback to plain prompt: %s", e)

        augmented_prompt = prompt
        if rag_context:
            augmented_prompt = (
                f"{prompt}\n\n"
                "=== Retrieved Context ===\n"
                "Use retrieved references when useful. "
                "If there is conflict, prefer strict mathematical correctness.\n\n"
                f"{rag_context}\n"
                "=== End Retrieved Context ==="
            )

        return await call_llm_api(
            self.api_config,
            augmented_prompt,
            timeout=timeout,
            max_retries=max_retries,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            temperature=temperature,
            agent_key=agent_key or raw_agent_type,
        )

    def __repr__(self) -> str:
        if hasattr(self.agent_type, "value"):
            agent_type_str = getattr(self.agent_type, "value")
        else:
            agent_type_str = str(self.agent_type)
        return (
            f"<{self.__class__.__name__}(name='{self.name}', "
            f"type={agent_type_str}, version={self.version})>"
        )
