"""
Text2Mem Core Engine (core/engine.py)

Responsible for coordinating adapters, model validation, and execution flow, integrating LLM and embedding model services.
"""
from typing import Dict, Any, Optional
import json
import logging
from pathlib import Path

from .models import IR
from .validate import validate_ir
from text2mem.adapters.base import BaseAdapter, ExecutionResult
from text2mem.services.models_service import ModelsService, get_models_service

# Configure logging
logger = logging.getLogger("text2mem.engine")


class Text2MemEngine:
    """Text2Mem Core Engine"""

    def __init__(
        self,
        config=None,
        adapter: BaseAdapter = None,
        models_service: Optional[ModelsService] = None,
        schema_path: Optional[str] = None,
        validate_schema: bool = False,
    ):
        # Support two initialization methods: config object or direct adapter
        if config is not None:
            # Create adapter from config
            from text2mem.adapters.sqlite_adapter import SQLiteAdapter

            self.adapter = SQLiteAdapter(config.database.path)
            self.models_service = models_service
        else:
            # Traditional method
            self.adapter = adapter
            self.models_service = models_service or get_models_service()

        self.logger = logging.getLogger("text2mem.engine")
        self._validate_schema = validate_schema

        # Load schema
        if schema_path is None:
            # core/engine.py -> ../../schema/text2mem-ir-v1.json
            schema_path = Path(__file__).resolve().parent.parent / "schema" / "text2mem-ir-v1.json"

        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        self.logger.info(
            f"Engine initialized - Adapter: {self.adapter.__class__.__name__}, "
            f"Models service: {self.models_service.__class__.__name__}"
        )

    def set_models_service(self, models_service: ModelsService):
        """Set model service"""
        self.models_service = models_service
        self.logger.info(f"Models service updated: {models_service.__class__.__name__}")

    async def process_ir(self, ir: Dict[str, Any]):
        """Process IR request (async version)"""
        try:
            # Call synchronous version
            result = self.execute(ir)
            return result
        except Exception as e:
            self.logger.error(f"Failed to process IR: {e}")
            # Return failure result
            return ExecutionResult(success=False, data={}, error=str(e))

    def execute(self, ir: Dict[str, Any]) -> Dict[str, Any]:
        """Execute IR operation"""
        # Optional: perform schema validation
        if self._validate_schema:
            validation_result = validate_ir(ir, self.schema)
            if not validation_result.valid:
                raise ValueError(f"IR validation failed: {validation_result.error}")

        # Parse to IR object
        ir_obj = IR.model_validate(ir)

        # Execute operation
        result = self.adapter.execute(ir_obj)

        self.logger.info(f"Executed {ir['op']} operation successfully")
        return result
