# -*- coding: utf-8 -*-
"""
结构化 JSON 日志 - AutoControl-Scientist

提供:
- JsonFormatter: 将日志输出为 JSON 格式（便于 ELK/Loki 采集）
- enable_json_logging: 快速切换指定 logger 到 JSON 格式
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional


class JsonFormatter(logging.Formatter):
    """
    JSON 格式日志输出。

    每条日志输出为单行 JSON，包含:
    - timestamp (ISO 8601)
    - level
    - logger
    - message
    - module / funcName / lineno
    - exc_info (异常时)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = traceback.format_exception(*record.exc_info)

        # 附加 extra 属性（排除 logging 内部字段）
        _builtin = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        for key, value in record.__dict__.items():
            if key not in _builtin and key not in log_entry:
                try:
                    json.dumps(value)  # 确保可序列化
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)

        return json.dumps(log_entry, ensure_ascii=False)


def enable_json_logging(
    logger_name: Optional[str] = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    将指定 logger（或 root logger）切换到 JSON 格式输出。

    Args:
        logger_name: logger 名称，None 表示 root logger
        level: 日志级别

    Returns:
        配置后的 logger
    """
    target_logger = logging.getLogger(logger_name)
    target_logger.setLevel(level)

    # 移除现有 handler，避免重复
    for handler in target_logger.handlers[:]:
        target_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    target_logger.addHandler(handler)

    return target_logger
