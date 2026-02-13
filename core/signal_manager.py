# -*- coding: utf-8 -*-
"""
信号管理器 - AutoControl-Scientist

统一管理PyQt6信号连接，避免重复的断开/连接代码
"""

from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# PyQt6 可选导入（Docker / CLI 环境无 Qt）
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    HAS_QT = True
except ImportError:
    HAS_QT = False


@dataclass
class SignalConnection:
    """信号连接记录"""
    signal: Any  # pyqtSignal when Qt available
    slot: Callable
    active: bool = True


class SignalManager:
    """
    信号管理器
    
    统一管理信号的连接和断开，支持命名组管理
    
    用法示例:
        manager = SignalManager()
        
        # 注册信号组
        manager.register_group("research_tab", [
            (orchestrator.log_message, on_log_message),
            (orchestrator.progress_updated, on_progress_updated),
        ])
        
        # 激活信号组（自动断开之前的连接）
        manager.activate_group("research_tab")
        
        # 停用信号组
        manager.deactivate_group("research_tab")
    """
    
    def __init__(self):
        self._groups: Dict[str, List[SignalConnection]] = {}
        self._active_groups: set = set()

        if not HAS_QT:
            logger.debug("PyQt6 不可用，SignalManager 将以 no-op 模式运行")

    def register_group(
        self, 
        group_name: str, 
        connections: List[tuple]
    ) -> None:
        """
        注册信号组
        
        Args:
            group_name: 组名称
            connections: 信号-槽对列表 [(signal, slot), ...]
        """
        if not HAS_QT:
            return
        self._groups[group_name] = [
            SignalConnection(signal=sig, slot=slot, active=False)
            for sig, slot in connections
        ]
        logger.debug("注册信号组: %s, 包含 %d 个连接", group_name, len(connections))
    
    def activate_group(self, group_name: str) -> bool:
        """
        激活信号组（连接所有信号）
        
        Args:
            group_name: 组名称
            
        Returns:
            是否成功激活
        """
        if not HAS_QT:
            return False
        if group_name not in self._groups:
            logger.warning("信号组不存在: %s", group_name)
            return False

        for conn in self._groups[group_name]:
            if not conn.active:
                try:
                    conn.signal.connect(conn.slot)
                    conn.active = True
                except Exception as e:
                    logger.error("连接信号失败: %s", e)

        self._active_groups.add(group_name)
        logger.debug("激活信号组: %s", group_name)
        return True

    def deactivate_group(self, group_name: str) -> bool:
        """
        停用信号组（断开所有信号）
        
        Args:
            group_name: 组名称
            
        Returns:
            是否成功停用
        """
        if not HAS_QT:
            return False
        if group_name not in self._groups:
            logger.warning("信号组不存在: %s", group_name)
            return False

        for conn in self._groups[group_name]:
            if conn.active:
                try:
                    conn.signal.disconnect(conn.slot)
                    conn.active = False
                except (TypeError, RuntimeError):
                    # 信号可能未连接，忽略错误
                    conn.active = False

        self._active_groups.discard(group_name)
        logger.debug("停用信号组: %s", group_name)
        return True
    
    def switch_group(self, from_group: str, to_group: str) -> bool:
        """
        切换信号组（停用from，激活to）
        
        Args:
            from_group: 要停用的组
            to_group: 要激活的组
            
        Returns:
            是否成功切换
        """
        self.deactivate_group(from_group)
        return self.activate_group(to_group)
    
    def deactivate_all(self) -> None:
        """停用所有信号组"""
        for group_name in list(self._active_groups):
            self.deactivate_group(group_name)
    
    def is_active(self, group_name: str) -> bool:
        """检查组是否激活"""
        return group_name in self._active_groups
    
    def get_active_groups(self) -> List[str]:
        """获取所有激活的组"""
        return list(self._active_groups)


class InteractionConfig:
    """
    交互配置
    
    允许用户自定义Agent交互行为
    """
    
    def __init__(self):
        # 需要用户确认的阶段
        self.confirm_stages: set = {
            "architect",   # 课题设计
            "theorist",    # 数学推导
            "engineer",    # 代码生成
            "simulator",   # 仿真执行
            "dsp_coder",   # DSP代码
            "scribe",      # 论文撰写
        }
        
        # 自动跳过确认的阶段（快速模式）
        self.auto_confirm_stages: set = set()
        
        # 是否显示监督评估详情
        self.show_supervision_details: bool = True
        
        # 监督评分阈值（低于此分数强制确认）
        self.supervision_threshold: float = 70.0
        
        # 是否启用课题对话优化
        self.enable_topic_chat: bool = True
        
        # 最大自动重试次数
        self.max_auto_retry: int = 2
        
        # 是否显示Agent产出内容预览
        self.show_output_preview: bool = True
        
        # 预览内容最大长度
        self.preview_max_length: int = 500
    
    def should_confirm(self, stage: str, score: float = 100.0) -> bool:
        """
        判断是否需要用户确认
        
        Args:
            stage: 阶段名称
            score: 监督评分
            
        Returns:
            是否需要确认
        """
        # 低分强制确认
        if score < self.supervision_threshold:
            return True
        
        # 自动确认列表中的阶段
        if stage in self.auto_confirm_stages:
            return False
        
        # 需要确认列表中的阶段
        return stage in self.confirm_stages
    
    def set_fast_mode(self, enabled: bool = True) -> None:
        """
        设置快速模式（跳过所有确认）
        
        Args:
            enabled: 是否启用
        """
        if enabled:
            self.auto_confirm_stages = self.confirm_stages.copy()
        else:
            self.auto_confirm_stages = set()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "confirm_stages": list(self.confirm_stages),
            "auto_confirm_stages": list(self.auto_confirm_stages),
            "show_supervision_details": self.show_supervision_details,
            "supervision_threshold": self.supervision_threshold,
            "enable_topic_chat": self.enable_topic_chat,
            "max_auto_retry": self.max_auto_retry,
            "show_output_preview": self.show_output_preview,
            "preview_max_length": self.preview_max_length,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InteractionConfig":
        """从字典创建"""
        config = cls()
        if "confirm_stages" in data:
            config.confirm_stages = set(data["confirm_stages"])
        if "auto_confirm_stages" in data:
            config.auto_confirm_stages = set(data["auto_confirm_stages"])
        if "show_supervision_details" in data:
            config.show_supervision_details = data["show_supervision_details"]
        if "supervision_threshold" in data:
            config.supervision_threshold = data["supervision_threshold"]
        if "enable_topic_chat" in data:
            config.enable_topic_chat = data["enable_topic_chat"]
        if "max_auto_retry" in data:
            config.max_auto_retry = data["max_auto_retry"]
        if "show_output_preview" in data:
            config.show_output_preview = data["show_output_preview"]
        if "preview_max_length" in data:
            config.preview_max_length = data["preview_max_length"]
        return config


# 全局交互配置实例
_interaction_config: Optional[InteractionConfig] = None


def get_interaction_config() -> InteractionConfig:
    """获取全局交互配置实例"""
    global _interaction_config
    if _interaction_config is None:
        _interaction_config = InteractionConfig()
    return _interaction_config
