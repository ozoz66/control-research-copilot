# -*- coding: utf-8 -*-
"""
OpenTelemetry 可观测性封装 - AutoControl-Scientist

提供:
- 自动降级: OpenTelemetry 未安装时所有操作为 no-op
- trace_span: 通用 context manager
- trace_llm_call / trace_agent_execution / trace_workflow_stage: 专用 span
- init_telemetry: 初始化 TracerProvider
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# --- OpenTelemetry 可选导入 ---
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

# 尝试导入 OTLP exporter（可选）
_OTLP_AVAILABLE = False
if OTEL_AVAILABLE:
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        _OTLP_AVAILABLE = True
    except ImportError:
        pass

# --- 模块级状态 ---
_tracer: Any = None
_initialized = False


def init_telemetry(
    service_name: str = "autocontrol-scientist",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> None:
    """
    初始化 OpenTelemetry TracerProvider。

    Args:
        service_name: 服务名称
        otlp_endpoint: OTLP gRPC 端点 (如 "http://localhost:4317")
        enable_console: 是否同时输出到控制台
    """
    global _tracer, _initialized

    if not OTEL_AVAILABLE:
        logger.info("OpenTelemetry 未安装，tracing 将以 no-op 模式运行")
        _initialized = True
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint and _OTLP_AVAILABLE:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("OTLP exporter 已配置: %s", otlp_endpoint)

    if enable_console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)
    _initialized = True
    logger.info("OpenTelemetry 已初始化: service=%s", service_name)


def get_tracer() -> Any:
    """返回已配置的 tracer，未初始化或不可用时返回 None。"""
    return _tracer


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    通用 tracing context manager。

    用法::

        with trace_span("my_operation", {"key": "value"}):
            do_something()

    OpenTelemetry 不可用时直接 yield（no-op）。
    """
    if _tracer is None:
        yield None
        return

    with _tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        yield span


@contextmanager
def trace_llm_call(agent_key: str, model: str, prompt_length: int):
    """
    LLM API 调用专用 span。

    记录 agent_key、model、prompt_length 以及耗时。
    """
    attrs = {
        "llm.agent_key": agent_key,
        "llm.model": model,
        "llm.prompt_length": prompt_length,
    }
    start = time.time()
    with trace_span(f"llm_call.{agent_key}", attrs) as span:
        yield span
        if span is not None:
            span.set_attribute("llm.duration_s", round(time.time() - start, 3))


@contextmanager
def trace_agent_execution(agent_key: str, stage: str = ""):
    """
    Agent 执行专用 span。
    """
    attrs = {
        "agent.key": agent_key,
        "agent.stage": stage,
    }
    start = time.time()
    with trace_span(f"agent.{agent_key}", attrs) as span:
        yield span
        if span is not None:
            span.set_attribute("agent.duration_s", round(time.time() - start, 3))


@contextmanager
def trace_workflow_stage(stage_key: str, description: str = ""):
    """
    工作流阶段专用 span。
    """
    attrs = {
        "workflow.stage_key": stage_key,
        "workflow.description": description,
    }
    start = time.time()
    with trace_span(f"workflow.{stage_key}", attrs) as span:
        yield span
        if span is not None:
            span.set_attribute("workflow.duration_s", round(time.time() - start, 3))
