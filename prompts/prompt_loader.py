# -*- coding: utf-8 -*-
"""
Prompt模板加载器 - AutoControl-Scientist
从YAML文件加载并渲染Prompt模板
"""

import yaml
from pathlib import Path
from typing import Dict, Optional


class PromptLoader:
    """
    YAML Prompt模板加载器

    从 prompts/<domain>/ 目录加载YAML模板文件，
    支持变量替换渲染。
    """

    def __init__(self, domain: str = "control_systems"):
        self.domain = domain
        self.prompts_dir = Path(__file__).parent / domain
        self._cache: Dict[str, dict] = {}

        if not self.prompts_dir.exists():
            raise FileNotFoundError(
                f"Prompt模板目录不存在: {self.prompts_dir}"
            )

    def load(self, agent_name: str, prompt_key: str, **kwargs) -> str:
        """
        加载并渲染prompt模板

        Args:
            agent_name: Agent名称 (architect, theorist, engineer, etc.)
            prompt_key: 模板键名
            **kwargs: 模板变量

        Returns:
            渲染后的prompt字符串
        """
        if agent_name not in self._cache:
            yaml_path = self.prompts_dir / f"{agent_name}.yaml"
            if not yaml_path.exists():
                raise FileNotFoundError(
                    f"Prompt模板文件不存在: {yaml_path}"
                )
            with open(yaml_path, 'r', encoding='utf-8') as f:
                self._cache[agent_name] = yaml.safe_load(f)

        prompts = self._cache[agent_name].get("prompts", {})
        if prompt_key not in prompts:
            raise KeyError(
                f"模板 '{prompt_key}' 在 {agent_name}.yaml 中不存在"
            )

        template = prompts[prompt_key]["template"]
        return template.format(**kwargs)

    def get_available_prompts(self, agent_name: str) -> list:
        """获取指定Agent的所有可用模板键名"""
        if agent_name not in self._cache:
            yaml_path = self.prompts_dir / f"{agent_name}.yaml"
            if not yaml_path.exists():
                return []
            with open(yaml_path, 'r', encoding='utf-8') as f:
                self._cache[agent_name] = yaml.safe_load(f)

        return list(self._cache[agent_name].get("prompts", {}).keys())

    def reload(self, agent_name: Optional[str] = None):
        """重新加载模板（清除缓存）"""
        if agent_name:
            self._cache.pop(agent_name, None)
        else:
            self._cache.clear()

    def set_domain(self, domain: str):
        """切换研究领域"""
        self.domain = domain
        self.prompts_dir = Path(__file__).parent / domain
        self._cache.clear()
        if not self.prompts_dir.exists():
            raise FileNotFoundError(
                f"Prompt模板目录不存在: {self.prompts_dir}"
            )
