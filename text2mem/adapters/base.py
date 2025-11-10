# text2mem/adapters/base.py
"""
Text2Mem Adapter Base Module

This module defines the interface specification for adapters and the data structure for execution results.
All concrete adapter implementations (such as SQLite adapter, Memory API adapter) should inherit from BaseAdapter.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional, List, Union
from dataclasses import dataclass
from text2mem.core.models import IR


@dataclass
class ExecutionResult:
    """
    Operation Execution Result
    
    Used to uniformly represent execution results from different adapters, including success status, data, and error messages.
    """
    success: bool  # Whether operation succeeded
    data: Optional[Any] = None  # Data returned by operation
    error: Optional[str] = None  # Error message
    meta: Optional[Dict[str, Any]] = None  # Metadata (execution time, SQL, etc.)
    
    def __bool__(self) -> bool:
        """Allow direct use in conditional expressions to check if operation succeeded"""
        return self.success


class BaseAdapter(ABC):
    """
    Adapter Base Class
    
    Defines the interface specification for Text2Mem adapters.
    Adapters are responsible for converting IR operations into specific storage system operations (such as SQL queries, API calls).
    """
    
    @abstractmethod
    def execute(self, ir: IR) -> ExecutionResult:
        """
        Execute IR operation
        
        Args:
            ir: IR object to execute
            
        Returns:
            ExecutionResult: Operation execution result
            
        Raises:
            NotImplementedError: When adapter does not support this operation
        """
        pass
    
    def close(self) -> None:
        """
        Close adapter connection
        
        Used to release resources held by the adapter (such as database connections).
        Default implementation is empty, specific adapters can override as needed.
        """
        pass
