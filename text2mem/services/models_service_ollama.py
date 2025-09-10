# moved from text2mem/models_service_ollama.py
from __future__ import annotations
import logging
import json
from typing import List, Dict, Any, Optional, Union

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from .models_service import (
    BaseEmbeddingModel,
    BaseGenerationModel,
    EmbeddingResult,
    GenerationResult,
    ModelsService,
)
from text2mem.core.config import ModelConfig

logger = logging.getLogger("text2mem.models_service_ollama")


class OllamaEmbeddingModel(BaseEmbeddingModel):
    def __init__(self, model_name: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        if not HAS_HTTPX:
            raise ImportError("需要安装 httpx 以支持 Ollama API")
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=60.0)
        logger.info(f"✅ Ollama嵌入模型初始化: {model_name} @ {base_url}")
    def embed_text(self, text: str) -> EmbeddingResult:
        try:
            response = self.client.post(f"{self.base_url}/api/embeddings", json={"model": self.model_name, "prompt": text})
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]
            logger.debug(f"✅ Ollama嵌入生成完成，维度: {len(embedding)}")
            return EmbeddingResult(text=text, embedding=embedding, model=self.model_name, tokens_used=len(text.split()))
        except Exception as e:
            logger.error(f"❌ Ollama嵌入生成失败: {e}")
            raise
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        return [self.embed_text(text) for text in texts]
    def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        return self.embed_batch(texts)
    def get_dimension(self) -> int:
        dimension_map = {"nomic-embed-text": 768, "mxbai-embed-large": 1024}
        return dimension_map.get(self.model_name, 768)
    def embed(self, texts: Union[str, List[str]]) -> EmbeddingResult:
        if isinstance(texts, str):
            return self.embed_text(texts)
        else:
            results = self.embed_batch(texts)
            return results[0] if results else None


class OllamaGenerationModel(BaseGenerationModel):
    def __init__(self, model_name: str = "qwen2:0.5b", base_url: str = "http://localhost:11434"):
        if not HAS_HTTPX:
            raise ImportError("需要安装 httpx 以支持 Ollama API")
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=120.0)
        logger.info(f"✅ Ollama生成模型初始化: {model_name} @ {base_url}")
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "top_p": kwargs.get("top_p", 0.9),
                        "num_predict": kwargs.get("max_tokens", 512),
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            generated_text = data["response"]
            prompt_tokens = len(prompt.split())
            completion_tokens = len(generated_text.split())
            logger.debug(f"✅ Ollama文本生成完成，输出长度: {len(generated_text)}")
            return GenerationResult(
                text=generated_text.strip(),
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        except Exception as e:
            logger.error(f"❌ Ollama文本生成失败: {e}")
            raise
    def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        structured_prompt = f"""{prompt}

请严格按照以下JSON格式回复，不要包含其他内容：
{json.dumps(schema, ensure_ascii=False, indent=2)}

JSON:"""
        return self.generate(structured_prompt, **kwargs)


class ModelFactory:
    @staticmethod
    def create_embedding_model(config: ModelConfig) -> BaseEmbeddingModel:
        if config.embedding_provider == "ollama":
            return OllamaEmbeddingModel(model_name=config.embedding_model, base_url=config.embedding_base_url)
        elif config.embedding_provider == "openai":
            try:
                from .models_service_openai import OpenAIEmbeddingModel
                return OpenAIEmbeddingModel(
                    model_name=config.embedding_model,
                    api_key=config.openai_api_key,
                    api_base=config.openai_api_base,
                    organization=config.openai_organization,
                )
            except ImportError as e:
                logger.error(f"❌ 导入OpenAI模块失败: {e}")
                raise ImportError("使用OpenAI模型需要安装openai库: pip install openai")
        else:
            raise ValueError(f"不支持的嵌入提供商: {config.embedding_provider}")

    @staticmethod
    def create_generation_model(config: ModelConfig) -> BaseGenerationModel:
        if config.generation_provider == "ollama":
            return OllamaGenerationModel(model_name=config.generation_model, base_url=config.generation_base_url)
        elif config.generation_provider == "openai":
            try:
                from .models_service_openai import OpenAIGenerationModel
                return OpenAIGenerationModel(
                    model_name=config.generation_model,
                    api_key=config.openai_api_key,
                    api_base=config.openai_api_base,
                    organization=config.openai_organization,
                )
            except ImportError as e:
                logger.error(f"❌ 导入OpenAI模块失败: {e}")
                raise ImportError("使用OpenAI模型需要安装openai库: pip install openai")
        else:
            raise ValueError(f"不支持的生成提供商: {config.generation_provider}")


def create_models_service_from_config(config: ModelConfig) -> ModelsService:
    embedding_model = ModelFactory.create_embedding_model(config)
    generation_model = ModelFactory.create_generation_model(config)
    return ModelsService(embedding_model=embedding_model, generation_model=generation_model)
