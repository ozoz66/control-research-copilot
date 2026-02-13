# -*- coding: utf-8 -*-
"""
Enhanced LLM API client for AutoControl-Scientist.

Supports:
- OpenAI-compatible and Anthropic-compatible APIs
- Streaming and non-streaming calls
- Retry with exponential backoff
- Optional interaction history recording
- Optional telemetry tracing
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import nullcontext
from typing import Callable, Optional

import aiohttp

from logger_config import get_logger

logger = get_logger(__name__)

try:
    from core.agent_history import get_agent_history

    HISTORY_AVAILABLE = True
except ImportError:  # pragma: no cover
    HISTORY_AVAILABLE = False

try:
    from core.telemetry import trace_llm_call

    TELEMETRY_AVAILABLE = True
except ImportError:  # pragma: no cover
    TELEMETRY_AVAILABLE = False


def _get_model_name(api_config) -> str:
    model = getattr(api_config, "model_name", None) or getattr(api_config, "model", None)
    if not model:
        raise RuntimeError("API配置缺少模型名称（model_name 或 model）")
    return str(model)


def _prepare_request_payload(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    system_prompt: str,
    temperature: float,
    stream: bool,
):
    headers = {"Content-Type": "application/json"}
    is_anthropic = "anthropic" in base_url.lower() or "claude" in model.lower()

    if is_anthropic:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        url = f"{base_url}/messages" if "/v1" in base_url else f"{base_url}/v1/messages"
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if stream:
            payload["stream"] = True
        if system_prompt:
            payload["system"] = system_prompt
        return is_anthropic, headers, url, payload

    headers["Authorization"] = f"Bearer {api_key}"
    url = f"{base_url}/chat/completions" if "/v1" in base_url else f"{base_url}/v1/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if stream:
        payload["stream"] = True
    return is_anthropic, headers, url, payload


async def call_llm_api_stream(
    api_config,
    prompt: str,
    on_chunk: Optional[Callable[[str], None]] = None,
    timeout: int = 180,
    max_retries: int = 3,
    max_tokens: int = 16384,
    system_prompt: str = "",
    temperature: float = 0.7,
    agent_key: str = "unknown",
) -> str:
    if api_config is None or not api_config.api_key:
        raise RuntimeError("API未配置，请在配置中设置有效的 API Key 和 Base URL")

    base_url = api_config.base_url.rstrip("/")
    api_key = api_config.api_key
    model = _get_model_name(api_config)

    if HISTORY_AVAILABLE:
        get_agent_history().record_llm_request(agent_key, prompt, model, system_prompt)
    start_time = time.time()

    is_anthropic, headers, url, payload = _prepare_request_payload(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        temperature=temperature,
        stream=True,
    )

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    last_error = None
    trace_context = trace_llm_call(agent_key, model, len(prompt)) if TELEMETRY_AVAILABLE else nullcontext()

    with trace_context:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            for attempt in range(max_retries):
                try:
                    logger.info(
                        "第%d次尝试流式调用API: %s... (超时: %d秒)",
                        attempt + 1,
                        url[:50],
                        timeout,
                    )
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if response.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                                await asyncio.sleep(2**attempt)
                                last_error = RuntimeError(f"API请求失败 ({response.status}): {error_text[:200]}")
                                continue
                            raise RuntimeError(f"API请求失败 ({response.status}): {error_text[:200]}")

                        full_response = ""
                        async for raw_line in response.content:
                            line = raw_line.decode("utf-8").strip()
                            if not line or line == "data: [DONE]":
                                continue
                            if not line.startswith("data: "):
                                continue
                            try:
                                data = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue

                            chunk_content = ""
                            if is_anthropic:
                                if data.get("type") == "content_block_delta":
                                    chunk_content = data.get("delta", {}).get("text", "")
                            else:
                                choices = data.get("choices", [])
                                if choices:
                                    chunk_content = choices[0].get("delta", {}).get("content", "")

                            if chunk_content:
                                full_response += chunk_content
                                if on_chunk:
                                    on_chunk(chunk_content)

                        if HISTORY_AVAILABLE:
                            get_agent_history().record_llm_response(
                                agent_key,
                                full_response,
                                tokens_used=0,
                                elapsed_time=time.time() - start_time,
                            )
                        return full_response

                except asyncio.TimeoutError:
                    last_error = RuntimeError(f"API请求超时（{timeout}秒）")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                except aiohttp.ClientError as e:
                    last_error = RuntimeError(f"网络连接错误: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue

    raise last_error or RuntimeError("API调用失败，已达最大重试次数")


async def call_llm_api(
    api_config,
    prompt: str,
    timeout: int = 180,
    max_retries: int = 3,
    max_tokens: int = 16384,
    system_prompt: str = "",
    temperature: float = 0.7,
    agent_key: str = "unknown",
) -> str:
    if api_config is None or not api_config.api_key:
        raise RuntimeError("API未配置，请在配置中设置有效的 API Key 和 Base URL")

    base_url = api_config.base_url.rstrip("/")
    api_key = api_config.api_key
    model = _get_model_name(api_config)

    if HISTORY_AVAILABLE:
        get_agent_history().record_llm_request(agent_key, prompt, model, system_prompt)
    start_time = time.time()

    is_anthropic, headers, url, payload = _prepare_request_payload(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        temperature=temperature,
        stream=False,
    )

    client_timeout = aiohttp.ClientTimeout(total=timeout)
    last_error = None

    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        for attempt in range(max_retries):
            try:
                logger.info(
                    "第%d次尝试调用API: %s... (超时: %d秒)",
                    attempt + 1,
                    url[:50],
                    timeout,
                )
                async with session.post(url, headers=headers, json=payload) as response:
                    logger.info("收到响应，状态码: %d", response.status)
                    response_text = await response.text()

                    if response.status != 200:
                        if response.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                            await asyncio.sleep(2**attempt)
                            last_error = RuntimeError(f"API请求失败 ({response.status}): {response_text[:200]}")
                            continue
                        raise RuntimeError(f"API请求失败 ({response.status}): {response_text[:200]}")

                    data = json.loads(response_text)

                    if is_anthropic:
                        content = data.get("content", [])
                        if not content or not isinstance(content, list):
                            raise RuntimeError("Anthropic API返回格式异常: 缺少 content 字段或 content 为空")
                        text_blocks = [b.get("text", "") for b in content if b.get("type") == "text"]
                        if not text_blocks:
                            text_blocks = [content[0].get("text", "")] if content else [""]
                        result = "\n".join(text_blocks)
                    else:
                        choices = data.get("choices", [])
                        if not choices or not isinstance(choices, list):
                            raise RuntimeError("OpenAI API返回格式异常: 缺少 choices 字段或 choices 为空")
                        result = choices[0].get("message", {}).get("content", "")

                    if HISTORY_AVAILABLE:
                        get_agent_history().record_llm_response(
                            agent_key,
                            result,
                            tokens_used=data.get("usage", {}).get("total_tokens", 0),
                            elapsed_time=time.time() - start_time,
                        )
                    return result

            except json.JSONDecodeError as e:
                last_error = RuntimeError(f"API响应JSON解析失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
            except asyncio.TimeoutError:
                last_error = RuntimeError(f"API请求超时（{timeout}秒）")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
            except aiohttp.ClientError as e:
                last_error = RuntimeError(f"网络连接错误: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue

    raise last_error or RuntimeError("API调用失败，已达最大重试次数")
