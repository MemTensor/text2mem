# moved from text2mem/models_service_providers.py
from __future__ import annotations
import logging
import os
from typing import Dict, Any, Optional, Union, List

from .models_service import (
    BaseEmbeddingModel,
    BaseGenerationModel,
    EmbeddingResult,
    GenerationResult,
    ModelsService,
)
from text2mem.core.config import Text2MemConfig, ModelConfig

logger = logging.getLogger("text2mem.models_service_providers")


class MockEmbeddingModel(BaseEmbeddingModel):
    def __init__(self, model_name: str = "mock-embedding"):
        self.model_name = model_name
        self.dimension = 384
        logger.info(f"✅ Mock嵌入模型初始化: {model_name}")
    def embed_text(self, text: str) -> EmbeddingResult:
        import hashlib, random
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % 10000
        random.seed(seed)
        embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
        length = sum(x * x for x in embedding) ** 0.5
        embedding = [x / length for x in embedding]
        tokens = len(text.split())
        return EmbeddingResult(text=text, embedding=embedding, model=self.model_name, tokens_used=tokens)
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        return [self.embed_text(text) for text in texts]
    def get_dimension(self) -> int:
        return self.dimension


class MockGenerationModel(BaseGenerationModel):
    def __init__(self, model_name: str = "mock-generation"):
        self.model_name = model_name
        logger.info(f"✅ Mock生成模型初始化: {model_name}")
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        responses = {
            "summarize": "这是对文本的总结：文本讨论了重要概念和关键思想。",
            "label": "技术, 创新, 研究",
            "question": "这是对您问题的模拟回答。我是一个模拟模型，不提供真实的AI功能。",
            "hello": "你好！我是Text2Mem的模拟模型。我可以帮助演示功能，但不提供实际的AI能力。",
        }
        response = "这是一个模拟响应，用于演示功能。在实际使用中，这里会是真实的AI生成内容。"
        for key, text in responses.items():
            if key.lower() in prompt.lower():
                response = text
                break
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response.split())
        return GenerationResult(
            text=response,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
    def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        import json
        if "标签" in prompt or "label" in prompt.lower():
            result = {"labels": ["技术", "创新", "研究"]}
        elif "摘要" in prompt or "summary" in prompt.lower():
            result = {"summary": "这是一段模拟的文本摘要。"}
        else:
            if "type" in schema and schema["type"] == "object" and "properties" in schema:
                result = {}
                for key, prop in schema["properties"].items():
                    if prop.get("type") == "string":
                        result[key] = f"模拟{key}值"
                    elif prop.get("type") == "number":
                        result[key] = 42
                    elif prop.get("type") == "boolean":
                        result[key] = True
                    elif prop.get("type") == "array":
                        result[key] = ["模拟项目1", "模拟项目2"]
                    else:
                        result[key] = None
            else:
                result = {"result": "模拟结构化响应"}
        response = json.dumps(result, ensure_ascii=False)
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response.split())
        return GenerationResult(
            text=response,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )


class MockModelsService(ModelsService):
    def __init__(self, config: Optional[ModelConfig] = None):
        self.embedding_model = MockEmbeddingModel()
        self.generation_model = MockGenerationModel()
        logger.info("✅ Mock模型服务初始化完成")


def create_mock_models_service(config: Optional[Union[Text2MemConfig, Dict[str, Any]]] = None) -> MockModelsService:
    if config is None:
        config = {}
    elif isinstance(config, Text2MemConfig):
        config = config.model
    return MockModelsService(config)  # config currently unused


def create_ollama_models_service(config: Optional[Union[Text2MemConfig, ModelConfig, Dict[str, Any]]] = None) -> 'ModelsService':
    from .models_service_ollama import create_models_service_from_config
    if config is None:
        model_cfg: ModelConfig = ModelConfig.load_ollama_config()
    elif isinstance(config, Text2MemConfig):
        model_cfg = config.model
    elif isinstance(config, ModelConfig):
        model_cfg = config
    else:
        model_cfg = ModelConfig.load_ollama_config()
    return create_models_service_from_config(model_cfg)


def create_openai_models_service(config: Optional[Union[Text2MemConfig, ModelConfig, Dict[str, Any]]] = None) -> 'ModelsService':
    from .models_service_openai import create_openai_models_service as _create_openai_service
    if config is None:
        model_cfg: ModelConfig = ModelConfig.load_openai_config()
    elif isinstance(config, Text2MemConfig):
        model_cfg = config.model
    elif isinstance(config, ModelConfig):
        model_cfg = config
    else:
        model_cfg = ModelConfig.load_openai_config()
    return _create_openai_service(model_cfg)


def create_models_service(mode: str = "auto", config: Optional[Union[Text2MemConfig, ModelConfig, Dict[str, Any]]] = None) -> 'ModelsService':
    if isinstance(config, Text2MemConfig):
        model_cfg: ModelConfig = config.model
    elif isinstance(config, ModelConfig):
        model_cfg = config
    else:
        model_cfg = ModelConfig.from_env()
    if mode == "auto":
        env_mode = os.getenv("MODEL_SERVICE", "").lower()
        if env_mode in ("mock", "ollama", "openai"):
            mode = env_mode
        else:
            if model_cfg.embedding_provider == "openai" or model_cfg.generation_provider == "openai":
                mode = "openai"
            elif model_cfg.embedding_provider == "ollama" or model_cfg.generation_provider == "ollama":
                mode = "ollama"
            else:
                mode = "mock"
    logger.info(f"🔄 创建模型服务：{mode} 模式")
    if mode == "mock":
        return create_mock_models_service()
    if mode == "ollama":
        model_cfg.embedding_provider = "ollama"
        model_cfg.generation_provider = "ollama"
        return create_ollama_models_service(model_cfg)
    if mode == "openai":
        model_cfg.embedding_provider = "openai"
        model_cfg.generation_provider = "openai"
        return create_openai_models_service(model_cfg)
    raise ValueError(f"未知的模型服务模式: {mode}")


def create_models_service_from_env() -> 'ModelsService':
    from .models_service_ollama import create_models_service_from_config
    model_cfg = ModelConfig.from_env()
    return create_models_service_from_config(model_cfg)
