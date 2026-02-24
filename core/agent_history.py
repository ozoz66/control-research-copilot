# -*- coding: utf-8 -*-
"""
Agent交互历史记录 - AutoControl-Scientist

记录Agent执行过程中的所有交互，便于调试和追溯
"""

import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """交互类型枚举"""
    LLM_REQUEST = "llm_request"       # LLM请求
    LLM_RESPONSE = "llm_response"     # LLM响应
    AGENT_START = "agent_start"       # Agent开始执行
    AGENT_COMPLETE = "agent_complete" # Agent完成执行
    AGENT_ERROR = "agent_error"       # Agent执行错误
    SUPERVISOR_EVAL = "supervisor_eval"  # 监督评估
    USER_CONFIRM = "user_confirm"     # 用户确认
    USER_MODIFY = "user_modify"       # 用户修改
    USER_ROLLBACK = "user_rollback"   # 用户回退
    CHECKPOINT_SAVE = "checkpoint_save"   # 检查点保存
    CHECKPOINT_LOAD = "checkpoint_load"   # 检查点加载


@dataclass
class InteractionRecord:
    """单条交互记录"""
    timestamp: str
    interaction_type: str
    agent_key: str
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


class AgentHistory:
    """
    Agent交互历史管理器
    
    功能:
    - 记录所有Agent交互
    - 支持按Agent/类型过滤
    - 导出为JSON/Markdown
    - 支持分页查询
    
    用法示例:
        history = AgentHistory()
        
        # 记录LLM请求
        history.record(
            InteractionType.LLM_REQUEST,
            "architect",
            {"prompt": "...", "model": "gpt-4"}
        )
        
        # 记录LLM响应
        history.record(
            InteractionType.LLM_RESPONSE,
            "architect",
            {"response": "...", "tokens": 1500}
        )
        
        # 查询历史
        records = history.query(agent_key="architect", limit=10)
        
        # 导出
        history.export_json("history.json")
    """
    
    def __init__(self, max_records: int = 5000):
        """
        初始化历史管理器
        
        Args:
            max_records: 最大记录数，超出后自动清理旧记录
        """
        self._max_records = max_records
        self._records: deque[InteractionRecord] = deque(maxlen=max_records)
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def record(
        self,
        interaction_type: InteractionType,
        agent_key: str,
        content: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> InteractionRecord:
        """
        记录一条交互
        
        Args:
            interaction_type: 交互类型
            agent_key: Agent标识
            content: 交互内容
            metadata: 元数据
            
        Returns:
            创建的记录
        """
        record = InteractionRecord(
            timestamp=datetime.now().isoformat(),
            interaction_type=interaction_type.value,
            agent_key=agent_key,
            content=content or {},
            metadata=metadata or {},
        )
        
        self._records.append(record)
        logger.debug("记录交互: %s - %s", interaction_type.value, agent_key)
        return record
    
    def record_llm_request(
        self,
        agent_key: str,
        prompt: str,
        model: str = "",
        system_prompt: str = "",
        **kwargs
    ) -> InteractionRecord:
        """记录LLM请求（便捷方法）"""
        return self.record(
            InteractionType.LLM_REQUEST,
            agent_key,
            {
                "prompt": prompt[:2000] if len(prompt) > 2000 else prompt,
                "prompt_length": len(prompt),
                "model": model,
                "system_prompt": system_prompt[:500] if len(system_prompt) > 500 else system_prompt,
                **kwargs
            }
        )
    
    def record_llm_response(
        self,
        agent_key: str,
        response: str,
        tokens_used: int = 0,
        elapsed_time: float = 0,
        **kwargs
    ) -> InteractionRecord:
        """记录LLM响应（便捷方法）"""
        return self.record(
            InteractionType.LLM_RESPONSE,
            agent_key,
            {
                "response": response[:2000] if len(response) > 2000 else response,
                "response_length": len(response),
                "tokens_used": tokens_used,
                "elapsed_time": elapsed_time,
                **kwargs
            }
        )
    
    def record_agent_start(self, agent_key: str, stage: str = "") -> InteractionRecord:
        """记录Agent开始执行"""
        return self.record(
            InteractionType.AGENT_START,
            agent_key,
            {"stage": stage}
        )
    
    def record_agent_complete(
        self,
        agent_key: str,
        stage: str = "",
        outputs: Dict[str, Any] = None
    ) -> InteractionRecord:
        """记录Agent完成执行"""
        return self.record(
            InteractionType.AGENT_COMPLETE,
            agent_key,
            {"stage": stage, "outputs": outputs or {}}
        )
    
    def record_agent_error(
        self,
        agent_key: str,
        error: str,
        stage: str = ""
    ) -> InteractionRecord:
        """记录Agent执行错误"""
        return self.record(
            InteractionType.AGENT_ERROR,
            agent_key,
            {"error": error, "stage": stage}
        )
    
    def record_supervisor_eval(
        self,
        agent_key: str,
        score: float,
        passed: bool,
        issues: List[str] = None,
        suggestions: List[str] = None
    ) -> InteractionRecord:
        """记录监督评估"""
        return self.record(
            InteractionType.SUPERVISOR_EVAL,
            agent_key,
            {
                "score": score,
                "passed": passed,
                "issues": issues or [],
                "suggestions": suggestions or [],
            }
        )
    
    def record_user_action(
        self,
        action_type: InteractionType,
        agent_key: str,
        details: str = ""
    ) -> InteractionRecord:
        """记录用户操作"""
        return self.record(action_type, agent_key, {"details": details})
    
    def query(
        self,
        agent_key: Optional[str] = None,
        interaction_type: Optional[InteractionType] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[InteractionRecord]:
        """
        查询历史记录
        
        Args:
            agent_key: 按Agent过滤
            interaction_type: 按类型过滤
            start_time: 起始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            limit: 返回最大条数
            offset: 偏移量
            
        Returns:
            匹配的记录列表
        """
        results: list[InteractionRecord] = list(self._records)

        if agent_key:
            results = [r for r in results if r.agent_key == agent_key]
        
        if interaction_type:
            type_value = interaction_type.value
            results = [r for r in results if r.interaction_type == type_value]
        
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]
        
        return results[offset:offset + limit]
    
    def get_agent_summary(self, agent_key: str) -> Dict[str, Any]:
        """获取Agent交互摘要"""
        agent_records = [r for r in self._records if r.agent_key == agent_key]
        
        if not agent_records:
            return {"agent_key": agent_key, "total_records": 0}
        
        type_counts = {}
        for r in agent_records:
            type_counts[r.interaction_type] = type_counts.get(r.interaction_type, 0) + 1
        
        # 计算LLM调用统计
        llm_requests = [r for r in agent_records if r.interaction_type == "llm_request"]
        llm_responses = [r for r in agent_records if r.interaction_type == "llm_response"]
        
        total_tokens = sum(r.content.get("tokens_used", 0) for r in llm_responses)
        avg_response_time = 0
        if llm_responses:
            times = [r.content.get("elapsed_time", 0) for r in llm_responses]
            avg_response_time = sum(times) / len(times)
        
        return {
            "agent_key": agent_key,
            "total_records": len(agent_records),
            "type_counts": type_counts,
            "llm_calls": len(llm_requests),
            "total_tokens": total_tokens,
            "avg_response_time": round(avg_response_time, 2),
            "first_record": agent_records[0].timestamp,
            "last_record": agent_records[-1].timestamp,
        }
    
    def get_session_summary(self) -> Dict[str, Any]:
        """获取当前会话摘要"""
        records = list(self._records)
        agent_keys = set(r.agent_key for r in records)

        return {
            "session_id": self._session_id,
            "total_records": len(records),
            "agents": list(agent_keys),
            "agent_summaries": {
                key: self.get_agent_summary(key) for key in agent_keys
            }
        }
    
    def export_json(self, path: str) -> bool:
        """导出为JSON文件"""
        try:
            records = list(self._records)
            data = {
                "session_id": self._session_id,
                "export_time": datetime.now().isoformat(),
                "total_records": len(records),
                "records": [r.to_dict() for r in records]
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("已导出交互历史到: %s", path)
            return True
        except Exception as e:
            logger.error("导出交互历史失败: %s", e)
            return False
    
    def export_markdown(self, path: str) -> bool:
        """导出为Markdown文件"""
        try:
            records = list(self._records)
            lines = [
                "# Agent交互历史",
                "",
                f"会话ID: `{self._session_id}`",
                "",
                f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                f"总记录数: {len(records)}",
                "",
                "---",
                "",
            ]

            # 按Agent分组
            agent_records: Dict[str, List[InteractionRecord]] = {}
            for r in records:
                if r.agent_key not in agent_records:
                    agent_records[r.agent_key] = []
                agent_records[r.agent_key].append(r)
            
            for agent_key, records in agent_records.items():
                lines.append(f"## {agent_key}")
                lines.append(f"")
                lines.append(f"共 {len(records)} 条记录")
                lines.append(f"")
                
                for r in records[:50]:  # 每个Agent最多显示50条
                    time_str = r.timestamp.split('T')[1][:8]
                    lines.append(f"### [{time_str}] {r.interaction_type}")
                    lines.append(f"")
                    
                    if r.content:
                        lines.append("```json")
                        content_str = json.dumps(r.content, ensure_ascii=False, indent=2)
                        if len(content_str) > 1000:
                            content_str = content_str[:1000] + "\n... (truncated)"
                        lines.append(content_str)
                        lines.append("```")
                        lines.append("")
                
                if len(records) > 50:
                    lines.append(f"*（还有 {len(records) - 50} 条记录未显示）*")
                    lines.append("")
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            logger.info("已导出交互历史到: %s", path)
            return True
        except Exception as e:
            logger.error("导出交互历史失败: %s", e)
            return False
    
    def clear(self) -> None:
        """清空所有记录"""
        self._records.clear()
        logger.info("已清空交互历史")
    
    @classmethod
    def load_from_json(cls, path: str) -> "AgentHistory":
        """从JSON文件加载"""
        history = cls()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            history._session_id = data.get("session_id", history._session_id)
            
            for record_data in data.get("records", []):
                record = InteractionRecord(
                    timestamp=record_data["timestamp"],
                    interaction_type=record_data["interaction_type"],
                    agent_key=record_data["agent_key"],
                    content=record_data.get("content", {}),
                    metadata=record_data.get("metadata", {}),
                )
                history._records.append(record)
            
            logger.info("已加载 %d 条交互记录", len(history._records))
        except Exception as e:
            logger.error("加载交互历史失败: %s", e)
        
        return history


# 全局历史实例
_global_history: Optional[AgentHistory] = None


def get_agent_history() -> AgentHistory:
    """获取全局Agent历史实例"""
    global _global_history
    if _global_history is None:
        _global_history = AgentHistory()
    return _global_history
