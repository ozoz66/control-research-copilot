# -*- coding: utf-8 -*-
"""
DSP编码器Agent (Agent E) - AutoControl-Scientist
专门负责将MATLAB控制算法转换为TMS320F28335 DSP C代码
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from global_context import GlobalContext
from agents.base import BaseAgent
from prompts import PromptTemplates
from logger_config import get_logger

logger = get_logger(__name__)


class DSPCodeGenerator:
    """
    TMS320F28335 DSP代码生成器
    将MATLAB控制算法转换为DSP C代码
    """

    # DSP代码模板 - 头文件
    HEADER_TEMPLATE = '''
/******************************************************************************
 * 文件名: control_algorithm.h
 * 描述:   控制算法头文件 - TMS320F28335 DSP
 * 作者:   AutoControl-Scientist (自动生成)
 * 日期:   {date}
 ******************************************************************************/

#ifndef CONTROL_ALGORITHM_H
#define CONTROL_ALGORITHM_H

#include "DSP2833x_Device.h"

// ===================== 宏定义 =====================
#define SAMPLE_PERIOD_MS    1.0f        // 采样周期 (ms)
#define SAMPLE_PERIOD_S     0.001f      // 采样周期 (s)

// 控制器参数 (根据实际系统调整)
{param_macros}

// ===================== 数据类型定义 =====================
typedef struct {{
    float32 position;           // 位置 (rad或m)
    float32 velocity;           // 速度 (rad/s或m/s)
    float32 acceleration;       // 加速度
    float32 reference;          // 参考输入
    float32 ref_velocity;       // 参考速度
    float32 error;              // 跟踪误差
    float32 error_prev;         // 上一采样误差
    float32 error_integral;     // 误差积分
    float32 control_output;     // 控制输出
    float32 disturbance_est;    // 扰动估计值
    Uint32 sample_count;        // 采样计数
}} ControlState;

// ESO状态结构体 (如使用扩展状态观测器)
typedef struct {{
    float32 z1;                 // 状态估计1 (位置)
    float32 z2;                 // 状态估计2 (速度)
    float32 z3;                 // 状态估计3 (扰动)
    float32 beta1;              // 观测器增益1
    float32 beta2;              // 观测器增益2
    float32 beta3;              // 观测器增益3
}} ESOState;

// 滑模控制状态 (如使用滑模控制)
typedef struct {{
    float32 s;                  // 滑模面
    float32 s_prev;             // 上一采样滑模面
    float32 reaching_law;       // 趋近律输出
    float32 equivalent_ctrl;    // 等效控制
}} SMCState;

// ===================== 函数声明 =====================
void Control_Init(void);
void Control_Reset(void);
void Control_SetReference(float32 ref);
float32 Control_Update(float32 feedback);
interrupt void Control_ISR(void);

// 辅助函数
float32 Saturate(float32 value, float32 min_val, float32 max_val);
float32 Sign(float32 value);
float32 Fal(float32 e, float32 alpha, float32 delta);

// ===================== 全局变量声明 =====================
extern ControlState g_ctrl_state;
extern ESOState g_eso_state;
extern SMCState g_smc_state;

#endif // CONTROL_ALGORITHM_H
'''

    # 默认参数宏定义
    DEFAULT_PARAM_MACROS = '''
// PID参数
#define KP                  50.0f       // 比例增益
#define KI                  10.0f       // 积分增益
#define KD                  5.0f        // 微分增益

// 滑模控制参数
#define SMC_LAMBDA          20.0f       // 滑模面参数
#define SMC_K               10.0f       // 切换增益
#define SMC_EPSILON         0.01f       // 边界层厚度

// ESO参数
#define ESO_BETA1           100.0f      // 观测器增益1
#define ESO_BETA2           300.0f      // 观测器增益2
#define ESO_BETA3           1000.0f     // 观测器增益3
#define ESO_B0              1.0f        // 控制增益

// 系统参数
#define CONTROL_MAX         10.0f       // 最大控制量
#define CONTROL_MIN         -10.0f      // 最小控制量
#define ENCODER_RESOLUTION  0.0001f     // 编码器分辨率 (rad/count)
#define PWM_PERIOD          3000        // PWM周期'''

    def __init__(self):
        """初始化DSP代码生成器"""
        self.date = datetime.now().strftime("%Y-%m-%d")

    def generate_header(self, param_macros: str = None) -> str:
        """
        生成头文件代码

        Args:
            param_macros: 参数宏定义（可选）

        Returns:
            头文件C代码
        """
        macros = param_macros if param_macros else self.DEFAULT_PARAM_MACROS
        return self.HEADER_TEMPLATE.format(
            date=self.date,
            param_macros=macros
        )

    def generate_minimal_header(self, control_strategy: str) -> str:
        """生成最小化的头文件"""
        return f'''// control_algorithm.h - LLM Generated
// Strategy: {control_strategy}
// Date: {datetime.now().strftime("%Y-%m-%d")}

#ifndef CONTROL_ALGORITHM_H
#define CONTROL_ALGORITHM_H

typedef float float32;
void Control_Init(void);
float32 Control_Update(float32 feedback);

#endif'''


class DSPCoderAgent(BaseAgent):
    """
    DSP编码器Agent (Agent E)
    专门负责将MATLAB代码转换为TMS320F28335 DSP C代码
    """

    _default_system_prompt = "你是一位嵌入式系统和DSP编程专家，擅长TMS320F28335 DSP开发。请生成完整、可编译的C代码，包含清晰的注释、规范的命名和必要的安全检查。"
    _default_temperature = 0.4

    def __init__(self):
        """初始化DSP编码器Agent"""
        super().__init__("DSPCoder", "dsp_coder")
        self.dsp_generator = DSPCodeGenerator()
        self.output_manager = None  # 由Orchestrator注入

    async def execute(self, context: GlobalContext) -> GlobalContext:
        """
        执行DSP代码生成任务

        Args:
            context: 全局上下文

        Returns:
            更新后的全局上下文
        """
        context.log_execution(self.name, "DSP代码生成", "started")

        # 检查LLM客户端
        if self.api_config is None or not self.api_config.api_key:
            raise RuntimeError(
                "DSPCoder Agent 必须配置 API 才能生成DSP代码。"
                "请在配置中设置有效的 API Key 和 Base URL。"
            )

        # 根据控制策略构建上下文信息
        research_config = context.research_config
        feedback_type = research_config.get("composite_architecture", {}).get("feedback", {}).get("key", "pid")
        observer_type = research_config.get("composite_architecture", {}).get("observer", {}).get("key", "none")

        # 确定控制策略描述
        control_strategy = f"{research_config.get('main_algorithm', {}).get('name', '未知')}"
        if feedback_type != "none":
            control_strategy += f" + {research_config.get('composite_architecture', {}).get('feedback', {}).get('name', '')}"
        if observer_type != "none":
            control_strategy += f" + {research_config.get('composite_architecture', {}).get('observer', {}).get('name', '')}"

        # 使用LLM生成DSP代码
        dsp_prompt = PromptTemplates.dsp_code(context)
        dsp_prompt += self._get_feedback_prompt_section()
        dsp_prompt += """

注意: 如果你发现上游Agent的输出（如MATLAB代码或控制律）严重不满足要求，
可以在响应中包含如下JSON字段来请求重做:
{"request_redo": {"agent": "engineer", "reason": "具体原因"}}"""
        llm_response = await self._call_llm(dsp_prompt)

        if not llm_response or not llm_response.strip():
            raise RuntimeError("LLM未能生成有效的DSP代码，请检查API配置和网络连接。")

        # 检查是否包含重做请求
        self._check_redo_request(llm_response, context)

        # 解析LLM返回的代码
        header_code, source_code, algorithm_code = self._parse_dsp_code(llm_response, control_strategy)

        # 保存到上下文
        context.dsp_header_code = header_code
        context.dsp_c_code = source_code
        context.dsp_isr_code = algorithm_code

        # 保存到文件（使用output_manager的项目目录）
        if self.output_manager:
            header_path = self.output_manager.save_dsp_code(header_code, "control_algorithm.h")
            source_path = self.output_manager.save_dsp_code(source_code, "control_algorithm.c")
        else:
            output_dir = Path("./output")
            output_dir.mkdir(exist_ok=True)
            header_path = output_dir / "control_algorithm.h"
            source_path = output_dir / "control_algorithm.c"
            with open(header_path, 'w', encoding='utf-8') as f:
                f.write(header_code)
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(source_code)

        context.dsp_file_paths = [str(header_path), str(source_path)]
        context.log_execution(self.name, "DSP代码生成", "success",
                            f"已生成: {header_path}, {source_path}")

        return context


    def _parse_dsp_code(self, llm_response: str, control_strategy: str) -> tuple:
        """
        解析LLM返回的DSP代码 - 基于内容特征分类代码块

        Args:
            llm_response: LLM返回的完整响应
            control_strategy: 控制策略描述

        Returns:
            (header_code, source_code, algorithm_code) 元组
        """
        # 先提取所有代码块
        all_blocks = re.findall(r'```(?:c|h)?\s*([\s\S]*?)```', llm_response)

        header_code = ""
        source_code = ""
        algorithm_code = ""

        # 按内容特征分类每个代码块
        for block in all_blocks:
            block = block.strip()
            if not block:
                continue

            is_header = (
                '#ifndef' in block or '#define' in block.split('\n')[0]
                or '.h' in block.split('\n')[0]
                or (block.count('typedef') > 0 and '#include' not in block.split('\n')[0])
            )
            has_control_func = (
                'Control_Update' in block or 'Control_ISR' in block
                or 'interrupt void' in block
            )
            is_source = (
                '.c' in block.split('\n')[0]
                or ('#include' in block.split('\n')[0] and not is_header)
                or has_control_func
            )

            if is_header and not header_code:
                header_code = block
            elif is_source and not source_code:
                source_code = block
            elif has_control_func and not algorithm_code:
                algorithm_code = block
            elif not source_code and not is_header:
                source_code = block

        # 回退：如果只有一个块
        if not header_code and not source_code and all_blocks:
            source_code = all_blocks[0].strip()
            header_code = self.dsp_generator.generate_minimal_header(control_strategy)

        if not header_code and source_code:
            header_code = self.dsp_generator.generate_minimal_header(control_strategy)

        if not algorithm_code:
            algorithm_code = source_code

        # 验证source_code包含关键函数
        if source_code and 'Control_Update' not in source_code and 'Control_ISR' not in source_code:
            logger.warning("DSP source code缺少Control_Update/Control_ISR函数")

        return header_code, source_code, algorithm_code
