# -*- coding: utf-8 -*-
"""
Configuration management for AutoControl-Scientist.
"""

import base64
import getpass
import hashlib
import json
import dataclasses
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

from logger_config import get_logger

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    agent_type: str
    provider_name: str
    api_key: str
    base_url: str
    model_name: str
    enabled: bool = True
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

    def to_dict(self, mask_api_key: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        if mask_api_key and self.api_key:
            data["api_key"] = f"***{self.api_key[-3:]}" if len(self.api_key) >= 3 else "***"
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        # Only pass keys that are valid dataclass fields, letting defaults handle the rest
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class AppSettings:
    agents: List[AgentConfig] = field(default_factory=list)
    matlab_path: str = ""
    last_project: str = ""
    output_dir: str = "./output"
    auto_save: bool = True
    language: str = "zh_CN"

    def to_dict(self, mask_api_keys: bool = True) -> Dict[str, Any]:
        return {
            "agents": [agent.to_dict(mask_api_key=mask_api_keys) for agent in self.agents],
            "matlab_path": self.matlab_path,
            "last_project": self.last_project,
            "output_dir": self.output_dir,
            "auto_save": self.auto_save,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        payload = data.get("settings", data)
        agents = [AgentConfig.from_dict(agent) for agent in data.get("agents", [])]
        return cls(
            agents=agents,
            matlab_path=payload.get("matlab_path", ""),
            last_project=payload.get("last_project", ""),
            output_dir=payload.get("output_dir", "./output"),
            auto_save=payload.get("auto_save", True),
            language=payload.get("language", "zh_CN"),
        )


class ConfigManager:
    DEFAULT_SETTINGS_FILE = "settings.json"

    def __init__(self, config_path: Optional[str] = None, config_file: Optional[str] = None):
        if config_path is None and config_file is not None:
            config_path = config_file

        if config_path is None:
            app_dir = Path.home() / ".autocontrol_scientist"
            app_dir.mkdir(exist_ok=True)
            self.config_path = app_dir / self.DEFAULT_SETTINGS_FILE
        else:
            self.config_path = Path(config_path)

        self._cipher = self._init_cipher()
        self.settings: AppSettings = AppSettings()
        self.load()

    def _init_cipher(self) -> Fernet:
        machine_id = f"{getpass.getuser()}@{str(Path.home())}".encode()
        salt = hashlib.sha256(str(Path.home()).encode()).digest()
        key = hashlib.pbkdf2_hmac("sha256", machine_id, salt, 100000)
        fernet_key = base64.urlsafe_b64encode(key[:32])
        return Fernet(fernet_key)

    def _encrypt_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        return self._cipher.encrypt(api_key.encode()).decode()

    def _decrypt_api_key(self, encrypted_key: str) -> str:
        if not encrypted_key:
            return ""
        try:
            return self._cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logger.warning("Failed to decrypt API key (discarded): %s", e)
            return ""

    def load(self) -> bool:
        if not self.config_path.exists():
            self._create_default_config()
            return True

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for agent_data in data.get("agents", []):
                if "api_key" in agent_data:
                    agent_data["api_key"] = self._decrypt_api_key(agent_data["api_key"])
            self.settings = AppSettings.from_dict(data)
            return True
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Invalid config file, fallback to defaults: %s", e)
            self._create_default_config()
            return False

    def save(self) -> bool:
        try:
            data = self.settings.to_dict(mask_api_keys=False)
            for agent_data in data.get("agents", []):
                if "api_key" in agent_data:
                    agent_data["api_key"] = self._encrypt_api_key(agent_data["api_key"])

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Failed to save config: %s", e)
            return False

    def _create_default_config(self):
        self.settings = AppSettings(
            agents=[
                AgentConfig(
                    agent_type="architect",
                    provider_name="OpenAI",
                    api_key="",
                    base_url="https://api.openai.com/v1",
                    model_name="gpt-4-turbo",
                    enabled=True,
                ),
                AgentConfig(
                    agent_type="theorist",
                    provider_name="OpenAI",
                    api_key="",
                    base_url="https://api.openai.com/v1",
                    model_name="gpt-4-turbo",
                    enabled=True,
                ),
                AgentConfig(
                    agent_type="engineer",
                    provider_name="OpenAI",
                    api_key="",
                    base_url="https://api.openai.com/v1",
                    model_name="gpt-4-turbo",
                    enabled=True,
                ),
                AgentConfig(
                    agent_type="simulator",
                    provider_name="OpenAI",
                    api_key="",
                    base_url="https://api.openai.com/v1",
                    model_name="gpt-4-turbo",
                    enabled=True,
                ),
                AgentConfig(
                    agent_type="dsp_coder",
                    provider_name="OpenAI",
                    api_key="",
                    base_url="https://api.openai.com/v1",
                    model_name="gpt-4-turbo",
                    enabled=True,
                ),
                AgentConfig(
                    agent_type="scribe",
                    provider_name="Anthropic",
                    api_key="",
                    base_url="https://api.anthropic.com",
                    model_name="claude-3-opus-20240229",
                    enabled=True,
                ),
                AgentConfig(
                    agent_type="supervisor",
                    provider_name="Anthropic",
                    api_key="",
                    base_url="https://api.anthropic.com",
                    model_name="claude-3-opus-20240229",
                    enabled=True,
                ),
            ],
            matlab_path="",
            output_dir="./output",
        )
        self.save()

    def add_agent(self, config: AgentConfig) -> bool:
        self.settings = AppSettings(
            agents=[*self.settings.agents, config],
            matlab_path=self.settings.matlab_path,
            last_project=self.settings.last_project,
            output_dir=self.settings.output_dir,
            auto_save=self.settings.auto_save,
            language=self.settings.language,
        )
        return self.save() if self.settings.auto_save else True

    def update_agent(self, index: int, config: AgentConfig) -> bool:
        if not (0 <= index < len(self.settings.agents)):
            return False
        new_agents = [
            config if i == index else a
            for i, a in enumerate(self.settings.agents)
        ]
        self.settings = AppSettings(
            agents=new_agents,
            matlab_path=self.settings.matlab_path,
            last_project=self.settings.last_project,
            output_dir=self.settings.output_dir,
            auto_save=self.settings.auto_save,
            language=self.settings.language,
        )
        return self.save() if self.settings.auto_save else True

    def delete_agent(self, index: int) -> bool:
        if not (0 <= index < len(self.settings.agents)):
            return False
        new_agents = [a for i, a in enumerate(self.settings.agents) if i != index]
        self.settings = AppSettings(
            agents=new_agents,
            matlab_path=self.settings.matlab_path,
            last_project=self.settings.last_project,
            output_dir=self.settings.output_dir,
            auto_save=self.settings.auto_save,
            language=self.settings.language,
        )
        return self.save() if self.settings.auto_save else True

    def get_agent(self, index: int) -> Optional[AgentConfig]:
        if 0 <= index < len(self.settings.agents):
            return self.settings.agents[index]
        return None

    def get_agent_by_type(self, agent_type: str) -> Optional[AgentConfig]:
        for agent in self.settings.agents:
            if agent.agent_type == agent_type and agent.enabled:
                return agent

        legacy_group_map = {
            "architect": "reasoning",
            "theorist": "reasoning",
            "engineer": "coding",
            "simulator": "coding",
            "dsp_coder": "coding",
            "scribe": "writing",
            "supervisor": "writing",
        }
        mapped_type = legacy_group_map.get(agent_type)
        if mapped_type:
            for agent in self.settings.agents:
                if agent.agent_type == mapped_type and agent.enabled:
                    return agent
        return None

    def get_all_agents(self) -> List[AgentConfig]:
        return self.settings.agents.copy()

    def find_fallback_config(self) -> Optional[AgentConfig]:
        for agent_type in [
            "architect",
            "theorist",
            "engineer",
            "simulator",
            "dsp_coder",
            "scribe",
            "supervisor",
            "reasoning",
            "coding",
            "writing",
        ]:
            config = self.get_agent_by_type(agent_type)
            if config and config.api_key:
                return config
        for agent in self.get_all_agents():
            if agent.enabled and agent.api_key:
                return agent
        return None

    def set_matlab_path(self, path: str) -> bool:
        self.settings.matlab_path = path
        return self.save() if self.settings.auto_save else True

    def set_output_dir(self, path: str) -> bool:
        self.settings.output_dir = path
        return self.save() if self.settings.auto_save else True


_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == "__main__":
    manager = get_config_manager()
    print(f"Config path: {manager.config_path}")
    print(f"Agent count: {len(manager.settings.agents)}")
    for i, agent in enumerate(manager.settings.agents):
        print(f"[{i}] {agent.agent_type}: {agent.provider_name} - {agent.model_name}")
