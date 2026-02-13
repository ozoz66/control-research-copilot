# -*- coding: utf-8 -*-
"""
Agent Mock 测试 - 测试 LLM 返回结果的解析
"""

import pytest
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestArchitectAgentParsing:
    """ArchitectAgent 输出解析测试"""

    def test_parse_literature_json(self):
        """测试文献检索 JSON 解析"""
        # 模拟 LLM 返回的 JSON
        llm_response = '''
        {
            "literature_summary": [
                {
                    "title": "Adaptive Sliding Mode Control",
                    "authors": "Zhang et al.",
                    "year": "2023",
                    "key_contribution": "提出了新的自适应律"
                }
            ],
            "research_gap": "现有方法缺乏有限时间收敛保证",
            "proposed_topic": "基于ESO的有限时间自适应滑模控制",
            "innovation_points": ["创新点1", "创新点2"]
        }
        '''

        # 解析
        data = json.loads(llm_response)

        assert len(data["literature_summary"]) == 1
        assert data["research_gap"] is not None
        assert len(data["innovation_points"]) == 2

    def test_parse_malformed_json(self):
        """测试处理格式错误的 JSON"""
        # 模拟包含额外文本的 LLM 响应
        llm_response = '''
        好的，我来分析一下文献：

        ```json
        {
            "research_gap": "研究空白",
            "proposed_topic": "研究课题"
        }
        ```

        以上是我的分析。
        '''

        # 提取 JSON 部分
        import re
        json_match = re.search(r'\{[\s\S]*?\}', llm_response)
        assert json_match is not None

        data = json.loads(json_match.group())
        assert data["research_gap"] == "研究空白"


class TestTheoristAgentParsing:
    """TheoristAgent 输出解析测试"""

    def test_parse_latex_control_law(self):
        """测试控制律 LaTeX 解析"""
        latex_response = r'''
        \begin{equation}
        u = -k_1 \text{sign}(s) - k_2 s - \hat{d}
        \end{equation}

        其中 $s = e + \lambda \dot{e}$ 是滑模面。
        '''

        # 检查是否包含关键 LaTeX 元素
        assert r'\begin{equation}' in latex_response
        assert 'sign' in latex_response

    def test_parse_lyapunov_function(self):
        """测试 Lyapunov 函数解析"""
        latex_response = r'''
        选择 Lyapunov 函数：
        $$V = \frac{1}{2}s^2 + \frac{1}{2\gamma}\tilde{d}^2$$

        对 $V$ 求导：
        $$\dot{V} = s\dot{s} + \frac{1}{\gamma}\tilde{d}\dot{\tilde{d}}$$
        '''

        assert 'Lyapunov' in latex_response
        assert r'\dot{V}' in latex_response


class TestEngineerAgentParsing:
    """EngineerAgent 输出解析测试"""

    def test_parse_matlab_code(self):
        """测试 MATLAB 代码解析"""
        matlab_response = '''
        ```matlab
        %% 系统参数
        m = 1.0;  % 质量
        k = 10;   % 刚度

        %% 控制器设计
        function u = controller(x, xd)
            e = xd - x;
            u = 10 * e;
        end

        %% 仿真
        tspan = [0 10];
        [t, y] = ode45(@dynamics, tspan, [0; 0]);
        ```
        '''

        # 提取 MATLAB 代码
        import re
        code_match = re.search(r'```matlab\s*([\s\S]*?)\s*```', matlab_response)
        assert code_match is not None

        code = code_match.group(1)
        assert 'function' in code
        assert 'ode45' in code

    def test_parse_dsp_code(self):
        """测试 DSP C 代码解析"""
        dsp_response = '''
        ```c
        // controller.h
        #ifndef CONTROLLER_H
        #define CONTROLLER_H

        typedef struct {
            float32 error;
            float32 integral;
        } ControlState;

        void Controller_Init(ControlState* state);
        float32 Controller_Update(ControlState* state, float32 ref, float32 feedback);

        #endif
        ```
        '''

        import re
        code_match = re.search(r'```c\s*([\s\S]*?)\s*```', dsp_response)
        assert code_match is not None

        code = code_match.group(1)
        assert 'typedef struct' in code
        assert 'float32' in code


class TestSupervisorAgentParsing:
    """SupervisorAgent 输出解析测试"""

    def test_parse_evaluation_result(self):
        """测试评估结果解析"""
        eval_response = '''
        {
            "score": 85,
            "passed": true,
            "issues": ["公式推导步骤可以更详细"],
            "suggestions": ["建议增加参数敏感性分析"],
            "rollback_to": null
        }
        '''

        data = json.loads(eval_response)

        assert data["score"] == 85
        assert data["passed"] is True
        assert len(data["issues"]) == 1
        assert len(data["suggestions"]) == 1
        assert data["rollback_to"] is None

    def test_parse_failed_evaluation(self):
        """测试失败评估解析"""
        eval_response = '''
        {
            "score": 45,
            "passed": false,
            "issues": ["稳定性证明不完整", "缺少收敛性分析"],
            "suggestions": ["需要补充 Lyapunov 稳定性证明"],
            "rollback_to": "theorist"
        }
        '''

        data = json.loads(eval_response)

        assert data["score"] == 45
        assert data["passed"] is False
        assert data["rollback_to"] == "theorist"


class TestScribeAgentParsing:
    """ScribeAgent 输出解析测试"""

    def test_parse_paper_structure(self):
        """测试论文结构 JSON 解析"""
        structure_response = '''
        {
            "title": "基于ESO的自适应滑模控制方法研究",
            "sections": [
                {"name": "Abstract", "word_count": 200},
                {"name": "Introduction", "word_count": 800},
                {"name": "Problem Formulation", "word_count": 600},
                {"name": "Controller Design", "word_count": 1000},
                {"name": "Stability Analysis", "word_count": 800},
                {"name": "Simulation Results", "word_count": 600},
                {"name": "Conclusion", "word_count": 300}
            ]
        }
        '''

        data = json.loads(structure_response)

        assert data["title"] is not None
        assert len(data["sections"]) == 7

    def test_parse_latex_document(self):
        """测试 LaTeX 文档解析"""
        latex_response = r'''
        \documentclass[journal]{IEEEtran}
        \begin{document}
        \title{Test Paper}
        \author{Author Name}
        \maketitle

        \begin{abstract}
        This is the abstract.
        \end{abstract}

        \section{Introduction}
        Introduction text.

        \end{document}
        '''

        assert r'\documentclass' in latex_response
        assert r'\begin{abstract}' in latex_response
        assert r'\section{Introduction}' in latex_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
