"""Mock models service provider and legacy factory helpers.

This module hosts the in-process mock embedding/generation models used for
tests and demos, plus a thin compatibility layer for the legacy
``create_models_service`` entry points. New code should prefer
``text2mem.services.service_factory``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Union

from text2mem.core.config import ModelConfig, Text2MemConfig

from .models_service import (
	BaseEmbeddingModel,
	BaseGenerationModel,
	EmbeddingResult,
	GenerationResult,
	ModelsService,
)

logger = logging.getLogger("text2mem.models_service_mock")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _contains_chinese(text: str) -> bool:
	try:
		import re

		return re.search(r"[\u4e00-\u9fff]", text or "") is not None
	except Exception:
		return False


def _resolve_lang(kwargs: Dict[str, Any], fallback_prompt: str = "") -> str:
	"""Choose language code 'zh' or 'en' based on kwargs.lang or prompt content."""

	lang = (kwargs.get("lang") or os.getenv("TEXT2MEM_LANG") or "en").lower()
	if "lang" not in kwargs and _contains_chinese(fallback_prompt):
		lang = "zh"
	return lang


def _mock_value_from_schema(prop: Dict[str, Any], lang: str = "en") -> Any:
	"""Return a simple mock value that conforms to a JSON Schema property."""

	schema_type = (prop or {}).get("type")
	if schema_type == "string":
		return "模拟字符串" if lang == "zh" else "mock string"
	if schema_type == "number":
		return 42
	if schema_type == "integer":
		return 7
	if schema_type == "boolean":
		return True
	if schema_type == "array":
		items = prop.get("items") or {"type": "string"}
		return [
			_mock_value_from_schema(items, lang),
			_mock_value_from_schema(items, lang),
		]
	if schema_type == "object":
		subprops = (prop or {}).get("properties") or {}
		return {k: _mock_value_from_schema(v, lang) for k, v in subprops.items()}
	return None


class MockEmbeddingModel(BaseEmbeddingModel):
	def __init__(self, model_name: str = "mock-embedding"):
		self.model_name = model_name
		self.dimension = 384
		self.provider = "mock"
		self.provider_name = "mock"
		logger.info("✅ Mock嵌入模型初始化: %s", model_name)

	def embed_text(self, text: str) -> EmbeddingResult:
		import hashlib
		import random

		seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % 10000
		random.seed(seed)
		embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
		length = sum(x * x for x in embedding) ** 0.5
		embedding = [x / length for x in embedding]
		tokens = len(text.split())
		return EmbeddingResult(
			text=text,
			embedding=embedding,
			model=self.model_name,
			tokens_used=tokens,
		)

	def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
		return [self.embed_text(text) for text in texts]

	def get_dimension(self) -> int:
		return self.dimension


class MockGenerationModel(BaseGenerationModel):
	def __init__(self, model_name: str = "mock-generation"):
		self.model_name = model_name
		logger.info("✅ Mock生成模型初始化: %s", model_name)

	def generate(self, prompt: str, **kwargs) -> GenerationResult:
		lang = _resolve_lang(kwargs, prompt)
		if lang == "zh":
			responses = {
				"summarize": "这是对文本的总结：文本讨论了重要概念和关键思想。",
				"label": "技术, 创新, 研究",
				"question": "这是对您问题的模拟回答。我是一个模拟模型，不提供真实的AI功能。",
				"hello": "你好！我是Text2Mem的模拟模型。我可以帮助演示功能，但不提供实际的AI能力。",
			}
			default_response = "这是一个模拟响应，用于演示功能。在实际使用中，这里会是真实的AI生成内容。"
		else:
			responses = {
				"summarize": "This is a summary of the text: it discusses key concepts and main ideas.",
				"label": "technology, innovation, research",
				"question": "This is a mock answer to your question. I'm a mock model and do not provide real AI capabilities.",
				"hello": "Hello! I'm the Text2Mem mock model. I can help demonstrate features but do not provide real AI capabilities.",
			}
			default_response = "This is a mock response for demonstration. In real usage, this would be produced by an actual AI model."

		response = default_response
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

		lang = _resolve_lang(kwargs, prompt)
		if "切分" in prompt or "split" in prompt.lower():
			result = {
				"splits": [
					{
						"title": "部分1" if lang == "zh" else "Part 1",
						"text": "第一段内容……" if lang == "zh" else "First section...",
					},
					{
						"title": "第二节" if lang == "zh" else "Section 2",
						"text": "第二段内容更长……" if lang == "zh" else "Second section is longer...",
					},
					{
						"title": "第三节" if lang == "zh" else "Section 3",
						"text": "第三段内容。" if lang == "zh" else "Third section.",
					},
				]
			}
			response = json.dumps(result, ensure_ascii=False)
		else:
			if "label" in prompt.lower() or "标签" in prompt:
				result = {
					"labels": ["技术", "创新", "研究"]
					if lang == "zh"
					else ["technology", "innovation", "research"]
				}
			elif "summary" in prompt.lower() or "摘要" in prompt:
				result = {
					"summary": "这是一段模拟的文本摘要。"
					if lang == "zh"
					else "This is a mock text summary."
				}
			else:
				if isinstance(schema, dict) and schema.get("type") == "object" and "properties" in schema:
					result = {
						key: _mock_value_from_schema(value, lang)
						for key, value in schema["properties"].items()
					}
				else:
					result = {
						"result": "模拟结构化响应" if lang == "zh" else "mock structured response"
					}
			response = json.dumps(result, ensure_ascii=False)

		prompt_tokens = len(prompt.split())
		completion_tokens = len(response.split())
		return GenerationResult(
			text=response,
			model=self.model_name,
			prompt_tokens=prompt_tokens,
			completion_tokens=completion_tokens,
			total_tokens=prompt_tokens + completion_tokens,
			metadata={"schema": schema},
		)


class MockModelsService(ModelsService):
	def __init__(self, config: Optional[ModelConfig] = None):
		self.embedding_model = MockEmbeddingModel()
		self.generation_model = MockGenerationModel()
		logger.info("✅ Mock模型服务初始化完成 (deprecated path)")


def create_mock_models_service(
	config: Optional[Union[Text2MemConfig, Dict[str, Any]]] = None,
) -> MockModelsService:
	"""Deprecated: use service_factory.create_models_service(mode='mock')."""

	if config is None:
		config = {}
	elif isinstance(config, Text2MemConfig):
		config = config.model
	return MockModelsService(config)


def create_ollama_models_service(
	config: Optional[Union[Text2MemConfig, ModelConfig, Dict[str, Any]]] = None,
) -> ModelsService:
	"""Create a ModelsService for Ollama provider (legacy compatibility)."""

	if isinstance(config, Text2MemConfig):
		cfg = config.model
	elif config is not None and (
		hasattr(config, "embedding_provider") or hasattr(config, "generation_provider")
	):
		cfg = config
	else:
		cfg = ModelConfig.load_ollama_config()

	from .models_service_ollama import create_models_service_from_config

	return create_models_service_from_config(cfg)


def create_openai_models_service(
	config: Optional[Union[Text2MemConfig, ModelConfig, Dict[str, Any]]] = None,
) -> ModelsService:
	"""Create a ModelsService for OpenAI provider (legacy compatibility)."""

	if isinstance(config, Text2MemConfig):
		cfg = config.model
	elif config is not None and (
		hasattr(config, "embedding_provider") or hasattr(config, "generation_provider")
	):
		cfg = config
	else:
		cfg = ModelConfig.load_openai_config()

	from .models_service_openai import create_openai_models_service as _create_openai_service

	return _create_openai_service(cfg)


def create_models_service(
	mode: str = "auto",
	config: Optional[Union[Text2MemConfig, ModelConfig, Dict[str, Any]]] = None,
) -> ModelsService:
	"""Legacy facade kept for tests and existing imports."""

	if isinstance(config, Text2MemConfig):
		cfg = config.model
	elif config is not None and (
		hasattr(config, "embedding_provider") or hasattr(config, "generation_provider")
	):
		cfg = config
	else:
		cfg = ModelConfig.from_env()

	resolved_mode = (mode or os.getenv("MODEL_SERVICE") or "auto").lower()
	if resolved_mode == "auto":
		env_mode = os.getenv("MODEL_SERVICE", "").lower()
		if env_mode in ("mock", "ollama", "openai"):
			resolved_mode = env_mode
		else:
			if (
				getattr(cfg, "embedding_provider", "") == "openai"
				or getattr(cfg, "generation_provider", "") == "openai"
			):
				resolved_mode = "openai"
			elif (
				getattr(cfg, "embedding_provider", "") == "ollama"
				or getattr(cfg, "generation_provider", "") == "ollama"
			):
				resolved_mode = "ollama"
			else:
				resolved_mode = "mock"

	logger.info("🔄 创建模型服务：%s 模式", resolved_mode)
	if resolved_mode == "openai":
		return create_openai_models_service(cfg)
	if resolved_mode == "ollama":
		return create_ollama_models_service(cfg)
	if resolved_mode == "mock":
		return create_mock_models_service(cfg)
	raise ValueError(f"未知的模型服务模式: {resolved_mode}")


def create_models_service_from_env() -> ModelsService:
	from .service_factory import create_models_service_from_env as _factory_env

	return _factory_env()
