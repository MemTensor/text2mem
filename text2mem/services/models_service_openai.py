# moved from text2mem/models_service_openai.py
from __future__ import annotations
import logging
import json
import os
from typing import List, Dict, Any, Optional

try:
    import openai
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .models_service import (
    BaseEmbeddingModel,
    BaseGenerationModel,
    EmbeddingResult,
    GenerationResult,
    ModelsService,
)
from text2mem.core.config import ModelConfig

logger = logging.getLogger("text2mem.models_service_openai")


class OpenAIEmbeddingModel(BaseEmbeddingModel):
    def __init__(self, model_name: str = "text-embedding-3-small", api_key: Optional[str] = None, api_base: Optional[str] = None, organization: Optional[str] = None):
        if not HAS_OPENAI:
            raise ImportError("需要安装 openai 以支持 OpenAI API")
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.organization = organization
        if not self.api_key:
            raise ValueError("未提供 OpenAI API 密钥，请通过参数或 OPENAI_API_KEY 环境变量设置")
        client_kwargs = {"api_key": self.api_key}
        if self.api_base:
            client_kwargs["base_url"] = self.api_base
            logger.info(f"使用自定义API端点: {self.api_base}")
        if self.organization:
            client_kwargs["organization"] = self.organization
        self.client = OpenAI(**client_kwargs)
        self._dimension_map = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072, "text-embedding-ada-002": 1536}
        logger.info(f"✅ OpenAI嵌入模型初始化: {model_name}")
    def embed_text(self, text: str) -> EmbeddingResult:
        try:
            response = self.client.embeddings.create(model=self.model_name, input=text, encoding_format="float")
            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens
            logger.debug(f"✅ OpenAI嵌入生成完成，维度: {len(embedding)}, 使用token: {tokens_used}")
            return EmbeddingResult(text=text, embedding=embedding, model=self.model_name, tokens_used=tokens_used)
        except Exception as e:
            logger.error(f"❌ OpenAI嵌入生成失败: {e}")
            raise
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        try:
            response = self.client.embeddings.create(model=self.model_name, input=texts, encoding_format="float")
            results = []
            for i, embedding_data in enumerate(response.data):
                results.append(EmbeddingResult(text=texts[i], embedding=embedding_data.embedding, model=self.model_name, tokens_used=0))
            total_tokens = response.usage.total_tokens
            logger.debug(f"✅ OpenAI批量嵌入生成完成，{len(texts)}条文本，总token: {total_tokens}")
            return results
        except Exception as e:
            logger.error(f"❌ OpenAI批量嵌入生成失败: {e}")
            raise
    def get_dimension(self) -> int:
        return self._dimension_map.get(self.model_name, 1536)


class OpenAIGenerationModel(BaseGenerationModel):
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: Optional[str] = None, api_base: Optional[str] = None, organization: Optional[str] = None):
        if not HAS_OPENAI:
            raise ImportError("需要安装 openai 以支持 OpenAI API")
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.organization = organization
        if not self.api_key:
            raise ValueError("未提供 OpenAI API 密钥，请通过参数或 OPENAI_API_KEY 环境变量设置")
        client_kwargs = {"api_key": self.api_key}
        if self.api_base:
            client_kwargs["base_url"] = self.api_base
            logger.info(f"使用自定义API端点: {self.api_base}")
        if self.organization:
            client_kwargs["organization"] = self.organization
        self.client = OpenAI(**client_kwargs)
        logger.info(f"✅ OpenAI生成模型初始化: {model_name}")
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        try:
            import os, re
            # Resolve language: explicit kwarg -> env -> auto-detect -> default 'en'
            lang = (kwargs.get("lang") or os.getenv("TEXT2MEM_LANG") or "en").lower()
            if "lang" not in kwargs and re.search(r"[\u4e00-\u9fff]", prompt):
                lang = "zh"

            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 512)
            top_p = kwargs.get("top_p", 1.0)
            system_msg = "您是一个有用的AI助手。" if lang == "zh" else "You are a helpful AI assistant."

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )
            generated_text = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            logger.debug(f"✅ OpenAI文本生成完成，输出长度: {len(generated_text)}, 总token: {total_tokens}")
            return GenerationResult(text=generated_text.strip(), model=self.model_name, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)
        except Exception as e:
            logger.error(f"❌ OpenAI文本生成失败: {e}")
            raise
    def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        try:
            import os, re
            # Resolve language: explicit kwarg -> env -> auto-detect -> default 'en'
            lang = (kwargs.get("lang") or os.getenv("TEXT2MEM_LANG") or "en").lower()
            if "lang" not in kwargs and re.search(r"[\u4e00-\u9fff]", prompt):
                lang = "zh"

            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens", 1024)
            system_msg = (
                "您是一个专业的AI助手，可以输出结构化数据。"
                if lang == "zh"
                else "You are a professional AI assistant that can output structured JSON."
            )
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            generated_text = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            logger.debug(f"✅ OpenAI结构化输出生成完成，总token: {total_tokens}")
            return GenerationResult(text=generated_text.strip(), model=self.model_name, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens, metadata={"schema": schema})
        except Exception as e:
            logger.error(f"❌ OpenAI结构化输出生成失败: {e}")
            raise


class OpenAIModelFactory:
    @staticmethod
    def create_embedding_model(config: ModelConfig) -> BaseEmbeddingModel:
        if config.embedding_provider != "openai":
            raise ValueError("配置不是OpenAI嵌入模型")
        return OpenAIEmbeddingModel(model_name=config.embedding_model, api_key=config.openai_api_key, api_base=config.openai_api_base, organization=config.openai_organization)
    @staticmethod
    def create_generation_model(config: ModelConfig) -> BaseGenerationModel:
        if config.generation_provider != "openai":
            raise ValueError("配置不是OpenAI生成模型")
        return OpenAIGenerationModel(model_name=config.generation_model, api_key=config.openai_api_key, api_base=config.openai_api_base, organization=config.openai_organization)


def create_openai_models_service(config: ModelConfig) -> ModelsService:
    embedding_model = OpenAIModelFactory.create_embedding_model(config)
    generation_model = OpenAIModelFactory.create_generation_model(config)
    return ModelsService(embedding_model=embedding_model, generation_model=generation_model)
