# -*- coding: utf-8 -*-
"""
BaseAgent 单元测试
"""

import pytest

from agents.base import (
    BaseAgent, AgentType, APIConfig,
    SupervisorFeedback, RedoRequest
)


class TestAgentType:
    """测试 AgentType 枚举"""

    def test_agent_type_values(self):
        """测试 AgentType 枚举值"""
        assert AgentType.ARCHITECT.value == "architect"
        assert AgentType.THEORIST.value == "theorist"
        assert AgentType.ENGINEER.value == "engineer"
        assert AgentType.DSP_CODER.value == "dsp_coder"
        assert AgentType.SCRIBE.value == "scribe"
        assert AgentType.SUPERVISOR.value == "supervisor"


class TestAPIConfig:
    """测试 APIConfig 数据类"""

    def test_api_config_creation(self):
        """测试 APIConfig 创建"""
        config = APIConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-test-key",
            model="gpt-4",
            timeout=60,
            max_retries=3
        )
        assert config.provider == "openai"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "sk-test-key"
        assert config.model == "gpt-4"
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_api_config_defaults(self):
        """测试 APIConfig 默认值"""
        config = APIConfig(
            provider="anthropic",
            base_url="https://api.anthropic.com",
            api_key="test-key",
            model="claude-3-opus"
        )
        assert config.timeout == 60  # 默认值
        assert config.max_retries == 3  # 默认值

    def test_api_config_to_dict(self):
        """测试 APIConfig 转换为字典"""
        config = APIConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-secret-key-12345",
            model="gpt-4",
            timeout=120,
            max_retries=5
        )
        config_dict = config.to_dict()
        assert config_dict["provider"] == "openai"
        assert config_dict["base_url"] == "https://api.openai.com/v1"
        assert config_dict["api_key"] == "***"  # 应该被掩码
        assert config_dict["model"] == "gpt-4"
        assert config_dict["timeout"] == 120
        assert config_dict["max_retries"] == 5


class TestSupervisorFeedback:
    """测试 SupervisorFeedback 数据类"""

    def test_supervisor_feedback_creation(self):
        """测试 SupervisorFeedback 创建"""
        feedback = SupervisorFeedback(
            agent="architect",
            score=85,
            strengths=["创新点明确", "文献综述全面"],
            weaknesses=["缺少具体的实验设计"],
            suggestions=["添加实验验证部分", "补充相关仿真结果"],
            redo_request=None
        )
        assert feedback.agent == "architect"
        assert feedback.score == 85
        assert len(feedback.strengths) == 2
        assert len(feedback.weaknesses) == 1
        assert len(feedback.suggestions) == 2
        assert feedback.redo_request is None

    def test_supervisor_feedback_with_redo(self):
        """测试带重做请求的反馈"""
        redo = RedoRequest(
            target_agent="theorist",
            reason="数学推导存在错误",
            stage="derivation"
        )
        feedback = SupervisorFeedback(
            agent="supervisor",
            score=60,
            strengths=[],
            weaknesses=["推导步骤不完整"],
            suggestions=["重新推导稳定性证明"],
            redo_request=redo
        )
        assert feedback.redo_request is not None
        assert feedback.redo_request.target_agent == "theorist"


class TestRedoRequest:
    """测试 RedoRequest 数据类"""

    def test_redo_request_creation(self):
        """测试 RedoRequest 创建"""
        request = RedoRequest(
            target_agent="engineer",
            reason="MATLAB 代码无法运行"
        )
        assert request.target_agent == "engineer"
        assert request.reason == "MATLAB 代码无法运行"
        assert request.stage is None

    def test_redo_request_with_stage(self):
        """测试带阶段信息的 RedoRequest"""
        request = RedoRequest(
            target_agent="dsp_coder",
            reason="DSP 代码存在编译错误",
            stage="code_generation"
        )
        assert request.target_agent == "dsp_coder"
        assert request.stage == "code_generation"


class MockAgent(BaseAgent):
    """用于测试的 Mock Agent"""

    def __init__(self):
        super().__init__(
            name="Mock Agent",
            agent_type=AgentType.ARCHITECT,
            description="测试用 Mock Agent"
        )

    async def execute(self, context):
        """模拟执行"""
        return context

    def _build_prompt(self, context):
        """模拟构建 prompt"""
        return "Mock prompt"


class TestBaseAgent:
    """测试 BaseAgent 类"""

    def test_base_agent_creation(self):
        """测试 BaseAgent 创建"""
        agent = MockAgent()
        assert agent.name == "Mock Agent"
        assert agent.agent_type == AgentType.ARCHITECT
        assert agent.description == "测试用 Mock Agent"
        assert agent.api_config is None
        assert agent.supervisor_feedback is None

    def test_set_api_config(self):
        """测试设置 API 配置"""
        agent = MockAgent()
        config = APIConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model="gpt-4"
        )
        agent.set_api_config(config)
        assert agent.api_config is config

    def test_set_supervisor_feedback(self):
        """测试设置监督反馈"""
        agent = MockAgent()
        feedback = SupervisorFeedback(
            agent="supervisor",
            score=90,
            strengths=["质量高"],
            weaknesses=[],
            suggestions=[]
        )
        agent.set_supervisor_feedback(feedback)
        assert agent.supervisor_feedback is feedback

    def test_get_feedback_prompt_section(self):
        """测试获取反馈 prompt 段落"""
        agent = MockAgent()
        # 无反馈
        assert agent._get_feedback_prompt_section() == ""

        # 有反馈
        feedback = SupervisorFeedback(
            agent="supervisor",
            score=70,
            strengths=["思路清晰"],
            weaknesses=["缺少推导细节"],
            suggestions=["补充稳定性分析"]
        )
        agent.set_supervisor_feedback(feedback)
        prompt = agent._get_feedback_prompt_section()
        assert "监督 Agent 反馈" in prompt
        assert "评分: 70/100" in prompt
        assert "思路清晰" in prompt
        assert "缺少推导细节" in prompt
        assert "补充稳定性分析" in prompt

    def test_repr(self):
        """测试 __repr__ 方法"""
        agent = MockAgent()
        repr_str = repr(agent)
        assert "MockAgent" in repr_str
        assert "Mock Agent" in repr_str
        assert "architect" in repr_str

    @pytest.mark.asyncio
    async def test_execute_not_implemented(self):
        """测试未实现 execute 方法时抛出异常"""
        class IncompleteAgent(BaseAgent):
            def __init__(self):
                super().__init__("Incomplete", AgentType.THEORIST)

        agent = IncompleteAgent()
        with pytest.raises(NotImplementedError):
            await agent.execute(None)

    def test_build_prompt_not_implemented(self):
        """测试未实现 _build_prompt 方法时抛出异常"""
        class IncompleteAgent(BaseAgent):
            def __init__(self):
                super().__init__("Incomplete", AgentType.ENGINEER)

        agent = IncompleteAgent()
        with pytest.raises(NotImplementedError):
            agent._build_prompt(None)

    @pytest.mark.asyncio
    async def test_call_llm_includes_local_skills_in_system_prompt(self, monkeypatch):
        agent = MockAgent()
        agent.api_config = APIConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model="gpt-4"
        )

        async def _fake_llm_call(api_config, prompt, system_prompt="", temperature=0.7, **kwargs):
            return f"SYSTEM::{system_prompt}\nPROMPT::{prompt}"

        monkeypatch.setattr("llm_client.call_llm_api", _fake_llm_call)
        monkeypatch.setattr("core.rag.build_rag_context", lambda prompt, cfg: "")
        monkeypatch.setattr(
            "core.skills.build_local_skill_context",
            lambda cfg, agent_name="": "Use concise mathematical notation."
        )

        result = await agent._call_llm("hello", system_prompt="base")
        assert "=== Local Skills ===" in result
        assert "Use concise mathematical notation." in result
