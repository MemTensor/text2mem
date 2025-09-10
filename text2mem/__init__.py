"""
Text2Mem: 一个简洁的本地记忆管理系统

提供本地记忆存储、检索和智能操作功能。
"""

__version__ = "0.1.0"

# Public API re-exports from subpackages
from .services.models_service import (
    EmbeddingResult,
    GenerationResult,
    BaseEmbeddingModel,
    BaseGenerationModel,
    ModelsService,
    get_models_service,
    set_models_service,
)

from .core.config import (
    ModelConfig,
    DatabaseConfig,
    Text2MemConfig,
)

from .core.engine import Text2MemEngine
from .services.models_service_providers import create_models_service
from .adapters.sqlite_adapter import SQLiteAdapter
from .adapters.base import ExecutionResult, BaseAdapter

