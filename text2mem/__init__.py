"""
Text2Mem: A Concise Local Memory Management System

Provides local memory storage, retrieval and intelligent operation capabilities.
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
from .services.models_service_mock import create_models_service
from .adapters.sqlite_adapter import SQLiteAdapter
from .adapters.base import ExecutionResult, BaseAdapter

