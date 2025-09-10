# text2mem/adapters/base.py
"""
Text2Mem 适配器基类模块

该模块定义了适配器的接口规范和执行结果的数据结构。
所有具体的适配器实现（如SQLite适配器、Memory API适配器）都应继承BaseAdapter。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional, List, Union
from dataclasses import dataclass
from text2mem.core.models import IR


@dataclass
class ExecutionResult:
    """
    操作执行结果
    
    用于统一表示不同适配器的执行结果，包含成功状态、数据和错误信息。
    """
    success: bool  # 操作是否成功
    data: Optional[Any] = None  # 操作返回的数据
    error: Optional[str] = None  # 错误信息
    meta: Optional[Dict[str, Any]] = None  # 元数据（执行时间、SQL等）
    
    def __bool__(self) -> bool:
        """允许直接用于条件表达式，检查操作是否成功"""
        return self.success


class BaseAdapter(ABC):
    """
    适配器基类
    
    定义了Text2Mem适配器的接口规范。
    适配器负责将IR操作转换为具体的存储系统操作（如SQL查询、API调用）。
    """
    
    @abstractmethod
    def execute(self, ir: IR) -> ExecutionResult:
        """
        执行IR操作
        
        Args:
            ir: 要执行的IR对象
            
        Returns:
            ExecutionResult: 操作执行结果
            
        Raises:
            NotImplementedError: 当适配器不支持该操作时
        """
        pass
    
    def close(self) -> None:
        """
        关闭适配器连接
        
        用于释放适配器持有的资源（如数据库连接）。
        默认实现为空，具体适配器可以根据需要重写。
        """
        pass
