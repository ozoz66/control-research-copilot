# ControlResearch Copilot

> Multi-agent copilot for control-systems research and implementation.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Beta-orange.svg)

[English](#english) | [中文](#中文)

---

<a id="english"></a>
## English

### Overview
ControlResearch Copilot is a multi-agent automation platform for control-systems research.
It orchestrates the full research workflow in one traceable, resumable pipeline:

```
Topic & Literature → Derivation → MATLAB Code → Simulation → DSP Code → Paper Draft
```

The project provides two interfaces:
- Desktop GUI (`PyQt6`) — visual workflow management with DAG, timeline, and chart dashboards
- HTTP API + WebSocket (`FastAPI`) — headless / remote operation with real-time event streaming

### Core Features
- 7 specialized LLM agents: `architect`, `theorist`, `engineer`, `simulator`, `dsp_coder`, `scribe`, `supervisor`
- Directed workflow execution with stage dependencies
- Stage confirmation and rollback to upstream phases
- Checkpoint-based resume after interruption
- Supervisor scoring and iterative revision
- Local RAG context injection before each LLM call (pure Python, zero external deps)
- Local skill files injection per agent
- Multi-provider LLM support (OpenAI-compatible, Anthropic-compatible)
- Encrypted API key storage (Fernet)
- Structured JSON logging + optional OpenTelemetry tracing
- Docker-ready deployment

### Agent Roles

| Agent | Role | Output |
|-------|------|--------|
| Architect | Literature review & topic design | Research topic, innovation points |
| Theorist | Mathematical derivation | Formulas, proofs |
| Engineer | MATLAB code generation | Simulation code |
| Simulator | MATLAB execution | Simulation results, plots |
| DSP Coder | DSP implementation | C/DSP code for embedded systems |
| Scribe | Paper writing | Academic paper draft |
| Supervisor | Quality evaluation | Score, feedback, improvement suggestions |

### Workflow
```text
literature (architect)
  ↓
derivation (theorist)
  ├─→ simulation (engineer)
  │     ↓
  │   sim_run (simulator)
  │     ↓
  │   dsp_code (dsp_coder)
  │
  └─→ paper (scribe)  [depends on: derivation + sim_run]
```

### Quick Start

#### 1. Requirements
- Python 3.9+
- Optional: MATLAB (for real MATLAB simulation execution)

#### 2. Install
```bash
pip install -e .
```

Development dependencies:
```bash
pip install -e ".[dev]"
```

API-only dependencies:
```bash
pip install -e ".[api]"
```

#### 3. Run GUI
```bash
python main.py
```

#### 4. Run API
```bash
python api_main.py
```

or:
```bash
uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: `http://127.0.0.1:8000/docs`

### Docker (API)
```bash
docker compose up --build
```

### Configuration
On first run, settings are created at:
- Windows: `%USERPROFILE%\.autocontrol_scientist\settings.json`
- Linux/macOS: `~/.autocontrol_scientist/settings.json`

Main configuration fields:
- LLM provider settings per agent: `provider_name`, `api_key`, `base_url`, `model_name`
- Optional `matlab_path`
- `output_dir` (default: `./output`)
- Per-agent RAG parameters: paths, globs, chunk sizes, scoring thresholds
- Per-agent Skills parameters: local file injection settings

Note: API keys are stored locally with Fernet encryption.

### API Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/research` | Create research session |
| `GET` | `/api/research/{session_id}/status` | Query status |
| `GET` | `/api/research/{session_id}/history` | Query summary history |
| `POST` | `/api/research/{session_id}/confirm` | Confirm stage (`rollback_to` supported) |
| `DELETE` | `/api/research/{session_id}` | Delete session |
| `WS` | `/api/ws/{session_id}` | Real-time event stream |

### Project Structure
```text
.
├── agents/                  # 7 specialized LLM agents
│   ├── base.py              # BaseAgent with LLM integration
│   ├── architect.py         # Literature & topic design
│   ├── theorist.py          # Mathematical derivation
│   ├── engineer.py          # MATLAB code generation
│   ├── simulator.py         # MATLAB execution
│   ├── dsp_coder.py         # DSP code generation
│   ├── scribe.py            # Paper writing
│   └── supervisor.py        # Quality evaluation & feedback
│
├── core/                    # Workflow orchestration & utilities
│   ├── workflow_engine.py   # Async workflow executor
│   ├── research_orchestrator.py  # Agent coordination
│   ├── workflow_definitions.py   # Stage graph definitions
│   ├── rag.py               # Local RAG (TF-IDF, chunking)
│   ├── skills.py            # Local skill file injection
│   ├── events.py            # EventEmitter (pub/sub)
│   ├── agent_history.py     # Interaction history tracking
│   ├── telemetry.py         # OpenTelemetry integration
│   ├── json_logging.py      # Structured logging
│   └── qt_adapter.py        # PyQt6 signal bridging
│
├── gui/                     # PyQt6 desktop interface
│   ├── main_window.py       # Main application window
│   ├── dashboard_tab.py     # Dashboard (DAG, timeline, charts)
│   ├── api_config_tab.py    # API configuration UI
│   └── ...                  # Tabs, dialogs, widgets
│
├── api/                     # FastAPI REST/WebSocket server
│   ├── app.py               # App factory
│   ├── routes.py            # API endpoints
│   ├── models.py            # Pydantic models
│   ├── session_manager.py   # Session lifecycle
│   └── ws_handler.py        # WebSocket event streaming
│
├── prompts/                 # YAML prompt templates
│   └── control_systems/     # Domain-specific prompts & knowledge base
│
├── skills/                  # Local skill files
├── tests/                   # Unit & integration tests
├── output/                  # Research output (per-session folders)
│
├── main.py                  # GUI entry point
├── api_main.py              # API entry point
├── config_manager.py        # Settings management (encrypted)
├── llm_client.py            # Unified LLM API client
├── global_context.py        # Shared data structures
├── output_manager.py        # Output file handling
├── pyproject.toml           # Project metadata & dependencies
├── Dockerfile               # Multi-stage Docker build
└── docker-compose.yml       # Docker Compose config
```

### Output Structure
Each research session creates:
```text
output/
└── 20260214_120000_[topic_name]/
    ├── context.json
    ├── checkpoints/
    │   ├── checkpoint_literature.json
    │   ├── checkpoint_derivation.json
    │   ├── checkpoint_simulation.json
    │   ├── checkpoint_sim_run.json
    │   ├── checkpoint_dsp_code.json
    │   └── checkpoint_paper.json
    ├── code/
    │   ├── matlab/
    │   └── dsp/
    └── paper/
        └── research_paper.md
```

### Development
```bash
# Lint & format
ruff check .
ruff format .

# Type check
mypy .

# Test
pytest tests -v
pytest tests --cov=. --cov-report=term-missing
```

### Contributing
Issues and pull requests are welcome.
Please include reproducible steps and test updates for behavior changes.

### License
MIT

---

<a id="中文"></a>
## 中文

### 项目简介
ControlResearch Copilot 是一个面向控制系统研究的多 Agent 自动化平台。
它将完整研究流程串联为可追踪、可回滚的一体化工作流：

```
选题与文献 → 数学推导 → MATLAB 代码 → 仿真 → DSP 代码 → 论文草稿
```

项目同时提供：
- 桌面 GUI（`PyQt6`）— 可视化工作流管理，含 DAG、时间线、图表仪表盘
- HTTP API + WebSocket（`FastAPI`）— 无头/远程操作，实时事件推送

### 核心特性
- 7 个专业 Agent 协同：`architect`、`theorist`、`engineer`、`simulator`、`dsp_coder`、`scribe`、`supervisor`
- 基于有向图的阶段依赖执行
- 阶段确认与回滚（可回退到任意上游阶段）
- 基于检查点的断点续跑
- `supervisor` 评分与改进建议
- 每次 LLM 调用前自动注入本地 RAG 上下文（纯 Python 实现，零外部依赖）
- 每个 Agent 注入本地 Skills 技能文件
- 多 LLM 提供商支持（OpenAI 兼容、Anthropic 兼容）
- API Key 本地 Fernet 加密存储
- 结构化 JSON 日志 + 可选 OpenTelemetry 链路追踪
- Docker 一键部署

### Agent 角色

| Agent | 职责 | 产出 |
|-------|------|------|
| Architect | 文献调研与选题设计 | 研究主题、创新点 |
| Theorist | 数学推导 | 公式、证明 |
| Engineer | MATLAB 代码生成 | 仿真代码 |
| Simulator | MATLAB 执行 | 仿真结果、图表 |
| DSP Coder | DSP 实现 | C/DSP 嵌入式代码 |
| Scribe | 论文撰写 | 学术论文草稿 |
| Supervisor | 质量评估 | 评分、反馈、改进建议 |

### 工作流
```text
literature (architect)
  ↓
derivation (theorist)
  ├─→ simulation (engineer)
  │     ↓
  │   sim_run (simulator)
  │     ↓
  │   dsp_code (dsp_coder)
  │
  └─→ paper (scribe)  [依赖: derivation + sim_run]
```

### 快速开始

#### 1. 环境要求
- Python 3.9+
- 可选：MATLAB（用于执行真实 MATLAB 仿真）

#### 2. 安装
```bash
pip install -e .
```

开发依赖：
```bash
pip install -e ".[dev]"
```

仅 API 依赖：
```bash
pip install -e ".[api]"
```

#### 3. 启动 GUI
```bash
python main.py
```

#### 4. 启动 API
```bash
python api_main.py
```

或：
```bash
uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
```

文档地址：`http://127.0.0.1:8000/docs`

### Docker（仅 API）
```bash
docker compose up --build
```

### 配置说明
首次运行会自动创建配置文件：
- Windows: `%USERPROFILE%\.autocontrol_scientist\settings.json`
- Linux/macOS: `~/.autocontrol_scientist/settings.json`

主要配置项：
- 每个 Agent 的 LLM 设置：`provider_name`、`api_key`、`base_url`、`model_name`
- 可选 `matlab_path`
- `output_dir`（默认 `./output`）
- 每个 Agent 的 RAG 参数：路径、glob 模式、分块大小、评分阈值
- 每个 Agent 的 Skills 参数：本地文件注入设置

说明：API Key 采用本地 Fernet 加密存储。

### API 概览
| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/research` | 创建研究会话 |
| `GET` | `/api/research/{session_id}/status` | 查询状态 |
| `GET` | `/api/research/{session_id}/history` | 查询历史摘要 |
| `POST` | `/api/research/{session_id}/confirm` | 阶段确认（支持 `rollback_to`） |
| `DELETE` | `/api/research/{session_id}` | 删除会话 |
| `WS` | `/api/ws/{session_id}` | 实时事件流 |

### 项目结构
```text
.
├── agents/                  # Agent 实现
├── core/                    # 工作流引擎、RAG、遥测、编排
├── gui/                     # PyQt6 界面层
├── api/                     # FastAPI 路由与会话管理
├── prompts/                 # Prompt 模板
├── skills/                  # 本地技能文件
├── tests/                   # 单元/集成测试
├── main.py                  # GUI 入口
├── api_main.py              # API 入口
└── pyproject.toml
```

### 产出结构
每次研究会话生成：
```text
output/
└── 20260214_120000_[主题名]/
    ├── context.json              # 完整会话上下文
    ├── checkpoints/              # 各阶段检查点
    ├── code/
    │   ├── matlab/               # MATLAB 仿真代码
    │   └── dsp/                  # DSP 嵌入式代码
    └── paper/
        └── research_paper.md     # 论文草稿
```

### 开发命令
```bash
# 代码检查与格式化
ruff check .
ruff format .

# 类型检查
mypy .

# 测试
pytest tests -v
pytest tests --cov=. --cov-report=term-missing
```

### 贡献
欢迎提交 Issue 和 Pull Request。
涉及行为变化时，请附上可复现步骤和相应测试更新。

### 许可证
MIT
