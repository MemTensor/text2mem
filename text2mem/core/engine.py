"""
Text2Mem 核心引擎（core/engine.py）

负责协调适配器、模型验证和执行流程，集成LLM和嵌入模型服务。
"""
from typing import Dict, Any, Optional
import json
import logging
from pathlib import Path

from .models import IR
from .validate import validate_ir
from text2mem.adapters.base import BaseAdapter, ExecutionResult
from text2mem.services.models_service import ModelsService, get_models_service

# 配置日志
logger = logging.getLogger("text2mem.engine")


class Text2MemEngine:
    """Text2Mem 核心引擎"""

    def __init__(
        self,
        config=None,
        adapter: BaseAdapter = None,
        models_service: Optional[ModelsService] = None,
        schema_path: Optional[str] = None,
        validate_schema: bool = False,
    ):
        # 支持两种初始化方式：配置对象 或 直接传递适配器
        if config is not None:
            # 从配置创建适配器
            from text2mem.adapters.sqlite_adapter import SQLiteAdapter

            self.adapter = SQLiteAdapter(config.database.path)
            self.models_service = models_service
        else:
            # 传统方式
            self.adapter = adapter
            self.models_service = models_service or get_models_service()

        self.logger = logging.getLogger("text2mem.engine")
        self._validate_schema = validate_schema

        # 加载schema
        if schema_path is None:
            # core/engine.py -> ../../schema/text2mem-ir-v1.json
            schema_path = Path(__file__).resolve().parent.parent / "schema" / "text2mem-ir-v1.json"

        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        self.logger.info(
            f"引擎初始化完成 - 适配器: {self.adapter.__class__.__name__}, "
            f"模型服务: {self.models_service.__class__.__name__}"
        )

    def set_models_service(self, models_service: ModelsService):
        """设置模型服务"""
        self.models_service = models_service
        self.logger.info(f"模型服务已更新: {models_service.__class__.__name__}")

    async def process_ir(self, ir: Dict[str, Any]):
        """处理IR请求（异步版本）"""
        try:
            # 调用同步版本
            result = self.execute(ir)
            return result
        except Exception as e:
            self.logger.error(f"处理IR失败: {e}")
            # 返回失败结果
            return ExecutionResult(success=False, data={}, error=str(e))

    def execute(self, ir: Dict[str, Any]) -> Dict[str, Any]:
        """执行IR操作"""
        # 可选：执行Schema验证
        if self._validate_schema:
            validation_result = validate_ir(ir, self.schema)
            if not validation_result.valid:
                raise ValueError(f"IR验证失败: {validation_result.error}")

        # 解析为IR对象
        ir_obj = IR.model_validate(ir)

        # 执行操作
        result = self.adapter.execute(ir_obj)

        self.logger.info(f"执行 {ir['op']} 操作完成")
        return result
