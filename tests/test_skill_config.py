# -*- coding: utf-8 -*-

from config_manager import AgentConfig


def test_agent_config_skill_defaults_from_dict():
    cfg = AgentConfig.from_dict(
        {
            "agent_type": "architect",
            "provider_name": "OpenAI",
            "api_key": "test",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4",
        }
    )
    assert cfg.skill_enabled is True
    assert cfg.skill_max_files == 8
    assert cfg.skill_paths == ["./skills"]
    assert "*.md" in cfg.skill_include_globs
