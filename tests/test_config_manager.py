# -*- coding: utf-8 -*-
"""
ConfigManager 单元测试
"""

import pytest
import json
import tempfile
from pathlib import Path

from config_manager import (
    ConfigManager, AgentConfig, AppSettings
)


class TestAgentConfig:
    """测试 AgentConfig 数据类"""

    def test_agent_config_creation(self):
        """测试 AgentConfig 创建"""
        config = AgentConfig(
            agent_type="architect",
            provider_name="OpenAI",
            api_key="test-key-12345",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4",
            enabled=True
        )
        assert config.agent_type == "architect"
        assert config.provider_name == "OpenAI"
        assert config.api_key == "test-key-12345"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model_name == "gpt-4"
        assert config.enabled is True

    def test_agent_config_to_dict(self):
        """测试 AgentConfig 转换为字典"""
        config = AgentConfig(
            agent_type="theorist",
            provider_name="Anthropic",
            api_key="test-key",
            base_url="https://api.anthropic.com",
            model_name="claude-3-opus",
            enabled=False
        )
        config_dict = config.to_dict()
        assert config_dict["agent_type"] == "theorist"
        assert config_dict["provider_name"] == "Anthropic"
        assert config_dict["api_key"] == "***key"  # 应该被掩码
        assert config_dict["enabled"] is False


class TestAppSettings:
    """测试 AppSettings 数据类"""

    def test_app_settings_defaults(self):
        """测试 AppSettings 默认值"""
        settings = AppSettings()
        assert settings.matlab_path == ""
        assert settings.last_project == ""

    def test_app_settings_with_values(self):
        """测试 AppSettings 带值创建"""
        settings = AppSettings(
            matlab_path="/usr/local/MATLAB/R2023a",
            last_project="test_project"
        )
        assert settings.matlab_path == "/usr/local/MATLAB/R2023a"
        assert settings.last_project == "test_project"


class TestConfigManager:
    """测试 ConfigManager"""

    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            config_data = {
                "agents": [],
                "settings": {
                    "matlab_path": "",
                    "last_project": ""
                }
            }
            json.dump(config_data, f)
            temp_path = Path(f.name)
        yield temp_path
        # 清理
        if temp_path.exists():
            temp_path.unlink()

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """创建 ConfigManager 实例"""
        return ConfigManager(config_file=str(temp_config_file))

    def test_add_agent(self, config_manager):
        """测试添加 Agent"""
        config = AgentConfig(
            agent_type="architect",
            provider_name="OpenAI",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4",
            enabled=True
        )
        config_manager.add_agent(config)
        assert len(config_manager.get_all_agents()) == 1

    def test_get_agent_by_type(self, config_manager):
        """测试按类型获取 Agent"""
        config = AgentConfig(
            agent_type="theorist",
            provider_name="Anthropic",
            api_key="test-key",
            base_url="https://api.anthropic.com",
            model_name="claude-3-opus",
            enabled=True
        )
        config_manager.add_agent(config)

        result = config_manager.get_agent_by_type("theorist")
        assert result is not None
        assert result.agent_type == "theorist"

    def test_update_agent(self, config_manager):
        """测试更新 Agent"""
        config = AgentConfig(
            agent_type="engineer",
            provider_name="OpenAI",
            api_key="old-key",
            base_url="https://api.openai.com/v1",
            model_name="gpt-3.5",
            enabled=True
        )
        config_manager.add_agent(config)

        # 更新
        updated = AgentConfig(
            agent_type="engineer",
            provider_name="OpenAI",
            api_key="new-key",
            base_url="https://api.openai.com/v1",
            model_name="gpt-4",
            enabled=True
        )
        config_manager.update_agent(0, updated)

        agent = config_manager.get_agent(0)
        assert agent.api_key == "new-key"
        assert agent.model_name == "gpt-4"

    def test_delete_agent(self, config_manager):
        """测试删除 Agent"""
        config = AgentConfig(
            agent_type="dsp_coder",
            provider_name="Local",
            api_key="test-key",
            base_url="http://localhost:8080",
            model_name="llama-2",
            enabled=True
        )
        config_manager.add_agent(config)

        assert len(config_manager.get_all_agents()) == 1
        config_manager.delete_agent(0)
        assert len(config_manager.get_all_agents()) == 0

    def test_set_matlab_path(self, config_manager):
        """测试设置 MATLAB 路径"""
        config_manager.set_matlab_path("/usr/local/MATLAB/R2023a")
        assert config_manager.settings.matlab_path == "/usr/local/MATLAB/R2023a"
