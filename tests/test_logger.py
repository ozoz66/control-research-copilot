# -*- coding: utf-8 -*-
"""
Logger 配置单元测试
"""

import pytest
import logging
from pathlib import Path
import tempfile

from logger_config import (
    setup_logger, get_logger, LOG_LEVELS
)


class TestLoggerSetup:
    """测试 logger 配置"""

    def test_setup_logger_default(self):
        """测试使用默认配置创建 logger"""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logger_with_level(self):
        """测试指定日志级别"""
        logger = setup_logger("test_logger_debug", level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_setup_logger_with_file(self):
        """测试指定日志文件"""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
            log_file = f.name

        try:
            logger = setup_logger(
                "test_logger_file",
                log_file=log_file
            )

            # 检查是否有文件处理器
            file_handlers = [
                h for h in logger.handlers
                if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) > 0
        finally:
            Path(log_file).unlink(missing_ok=True)

    def test_get_logger_existing(self):
        """测试获取已存在的 logger"""
        first = setup_logger("test_get_logger")
        second = get_logger("test_get_logger")
        assert first is second

    def test_log_levels_mapping(self):
        """测试日志级别映射"""
        assert LOG_LEVELS["DEBUG"] == logging.DEBUG
        assert LOG_LEVELS["INFO"] == logging.INFO
        assert LOG_LEVELS["WARNING"] == logging.WARNING
        assert LOG_LEVELS["ERROR"] == logging.ERROR
        assert LOG_LEVELS["CRITICAL"] == logging.CRITICAL

    def test_logger_output(self, caplog):
        """测试 logger 输出"""
        with caplog.at_level(logging.INFO):
            logger = setup_logger("test_output")
            logger.info("Test message")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "Test message" in caplog.records[0].message
