# Agent 交互优化总结

## 概述

本次优化主要针对 AutoControl-Scientist 项目的 Agent 交互系统进行了全面改进，提升了代码可维护性、用户体验和调试能力。

---

## 优化内容

### 1. 信号管理器 (SignalManager)

**文件**: `core/signal_manager.py`

**问题**: 之前的代码中存在大量重复的 `try/except` 信号断开连接代码，难以维护。

**解决方案**: 创建 `SignalManager` 类统一管理所有 PyQt6 信号连接。

**核心功能**:
- `register_group(name, connections)` - 注册信号组
- `activate_group(name)` - 激活信号组（自动连接）
- `deactivate_group(name)` - 停用信号组（自动断开）
- `switch_group(from, to)` - 切换信号组
- `deactivate_all()` - 停用所有信号组

**使用示例**:
```python
# 注册信号组
signal_manager.register_group("research_tab", [
    (orchestrator.log_message, on_log_message),
    (orchestrator.progress_updated, on_progress_updated),
])

# 切换信号组
signal_manager.deactivate_all()
signal_manager.activate_group("research_tab")
```

---

### 2. 交互配置 (InteractionConfig)

**文件**: `core/signal_manager.py`

**问题**: 用户无法自定义各阶段的确认行为。

**解决方案**: 创建 `InteractionConfig` 类允许用户配置交互行为。

**可配置项**:
- `confirm_stages` - 需要确认的阶段集合
- `auto_confirm_stages` - 自动跳过确认的阶段
- `supervision_threshold` - 低分强制确认阈值
- `max_auto_retry` - 最大自动重试次数
- `show_output_preview` - 是否显示产出预览
- `enable_topic_chat` - 是否启用课题对话

**快速模式**:
```python
config = get_interaction_config()
config.set_fast_mode(True)  # 跳过所有确认
```

---

### 3. Agent 交互历史 (AgentHistory)

**文件**: `core/agent_history.py`

**问题**: 难以追踪和调试 Agent 执行过程。

**解决方案**: 创建 `AgentHistory` 类记录所有 Agent 交互。

**记录类型**:
- `LLM_REQUEST` - LLM 请求
- `LLM_RESPONSE` - LLM 响应
- `AGENT_START` - Agent 开始执行
- `AGENT_COMPLETE` - Agent 完成执行
- `AGENT_ERROR` - Agent 错误
- `SUPERVISOR_EVAL` - 监督评估
- `USER_CONFIRM` - 用户确认
- `USER_MODIFY` - 用户修改
- `USER_ROLLBACK` - 用户回退

**核心功能**:
- `record()` - 记录交互
- `query()` - 查询历史
- `get_agent_summary()` - 获取 Agent 摘要
- `export_json()` - 导出 JSON
- `export_markdown()` - 导出 Markdown

**使用示例**:
```python
history = get_agent_history()

# 记录 LLM 请求
history.record_llm_request("architect", prompt, model)

# 记录 LLM 响应
history.record_llm_response("architect", response, tokens, time)

# 查询历史
records = history.query(agent_key="theorist", limit=10)

# 导出
history.export_json("history.json")
```

---

### 4. 增强 LLM 客户端

**文件**: `llm_client.py`

**改进**:
- 添加流式响应支持 (`call_llm_api_stream`)
- 集成交互历史记录
- 添加 `LLMClient` 封装类

**流式调用示例**:
```python
response = await call_llm_api_stream(
    api_config,
    prompt,
    on_chunk=lambda chunk: print(chunk, end=""),
    agent_key="architect"
)
```

**客户端封装**:
```python
client = LLMClient(api_config, agent_key="architect")
client.set_system_prompt("你是控制系统专家")
response = await client.chat("解释PID控制")
```

---

### 5. 交互配置面板

**文件**: `gui/interaction_panel.py`

**新增界面**:
- **交互配置面板** - 可视化配置各阶段确认行为
- **历史查看面板** - 查看和导出 Agent 交互历史

**功能**:
- 勾选需要确认的阶段
- 设置监督评分阈值
- 设置最大重试次数
- 刷新/导出/清空历史记录

---

### 6. MainWindow 优化

**文件**: `gui_main.py`

**改进**:
- 使用 `SignalManager` 替代重复的信号管理代码（约减少 60 行代码）
- 添加交互配置 Tab
- 记录用户操作到历史记录
- Tab 标签添加图标增强视觉效果

---

## 使用指南

### 快速开始

1. 运行应用程序
2. 在"交互配置"Tab 中配置需要确认的阶段
3. 启动研究流程
4. 查看"交互配置"面板中的历史记录

### 快速模式

如果想跳过所有阶段确认，自动运行完整流程：
1. 进入"交互配置"Tab
2. 点击"全不选 (快速模式)"
3. 设置合适的监督评分阈值（建议 60-70）
4. 点击"应用配置"

### 调试与追溯

1. 运行流程后，在"交互配置"Tab 刷新历史
2. 查看各 Agent 的 LLM 调用统计
3. 点击"导出 JSON"或"导出 Markdown"保存详细记录

---

## 文件变更清单

| 文件 | 状态 | 说明 |
|------|------|------|
| `core/signal_manager.py` | 新增 | 信号管理器和交互配置 |
| `core/agent_history.py` | 新增 | Agent 交互历史记录 |
| `core/__init__.py` | 修改 | 导出新模块 |
| `llm_client.py` | 重写 | 添加流式响应和历史记录 |
| `gui/interaction_panel.py` | 新增 | 交互配置面板 |
| `gui_main.py` | 修改 | 集成新功能 |

---

## 后续优化建议

1. **流式显示 Agent 输出** - 在阶段确认对话框中实时显示 LLM 生成内容
2. **交互配置持久化** - 将用户配置保存到文件
3. **历史记录可视化** - 添加图表展示 Token 消耗趋势
4. **批量研究支持** - 支持配置多个研究任务队列执行
