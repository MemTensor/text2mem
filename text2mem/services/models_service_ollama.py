# moved from text2mem/models_service_ollama.py
from __future__ import annotations
import logging
import json
import os
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
            raise ImportError("httpx is required to support Ollama API")
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=60.0)
        logger.info(f"✅ Ollama embedding model initialized: {model_name} @ {base_url}")
    def embed_text(self, text: str) -> EmbeddingResult:
        try:
            response = self.client.post(f"{self.base_url}/api/embeddings", json={"model": self.model_name, "prompt": text})
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]
            logger.debug(f"✅ Ollama embedding generated, dimension: {len(embedding)}")
            return EmbeddingResult(text=text, embedding=embedding, model=self.model_name, tokens_used=len(text.split()))
        except Exception as e:
            logger.error(f"❌ Ollama embedding generation failed: {e}")
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
            raise ImportError("httpx is required to support Ollama API")
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=120.0)
        logger.info(f"✅ Ollama generation model initialized: {model_name} @ {base_url}")
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        try:
            lang = (kwargs.get("lang") or os.getenv("TEXT2MEM_LANG") or "en").lower()
            if lang == "zh":
                language_hint = "Please answer in Chinese."
            elif lang == "en":
                language_hint = "Please respond in English."
            else:
                language_hint = f"Please respond in {lang}."
            prompt_payload = f"{language_hint}\n\n{prompt}" if language_hint else prompt

            timeout = kwargs.get("timeout", 30.0)
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt_payload,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "top_p": kwargs.get("top_p", 0.9),
                        "num_predict": kwargs.get("max_tokens", 512),
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            generated_text = data["response"]
            prompt_tokens = len(prompt.split())
            completion_tokens = len(generated_text.split())
            logger.debug(f"✅ Ollama text generation completed, output length: {len(generated_text)}")
            return GenerationResult(
                text=generated_text.strip(),
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        except Exception as e:
            logger.error(f"❌ Ollama text generation failed: {e}")
            raise
    def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        """Ask Ollama to return strict JSON by enabling options.format=json.

        Notes:
        - We keep the schema compact to reduce tokens.
        - Some models respond more reliably with a short, explicit instruction.
        - Fallback parsing is handled by the caller if needed.
        """
        lang = (kwargs.get("lang") or os.getenv("TEXT2MEM_LANG") or "en").lower()
        if lang == "zh":
            language_hint = "Please answer in Chinese."
        elif lang == "en":
            language_hint = "Please respond in English."
        else:
            language_hint = f"Please respond in {lang}."

        # Use concise prompt, request return JSON array (elements can contain title/text/range), not forcing given schema
        structured_prompt = (
            f"{prompt}\n\n"
            f"Output only a JSON array, do not add any explanations, comments or prefix/suffix. Array elements are objects with possible fields:\n"
            f"- title: optional, string\n- text: optional, string\n- range: optional, [start,end] two integers indicating range in original text\n"
        )
        structured_prompt = f"{language_hint}\n\n{structured_prompt}" if language_hint else structured_prompt
        try:
            timeout = kwargs.get("timeout", 30.0)
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": structured_prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.2),
                        "top_p": kwargs.get("top_p", 0.9),
                        "num_predict": kwargs.get("max_tokens", 512),
                        "format": "json",
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            generated_text = data.get("response", "").strip()
            prompt_tokens = len(structured_prompt.split())
            completion_tokens = len(generated_text.split())
            return GenerationResult(
                text=generated_text,
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        except Exception as e:
            logger.error(f"❌ Ollama structured output failed: {e}")
            # Fallback to normal generation (may contain extra text, upper layer does looser parsing)
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
                logger.error(f"❌ Failed to import OpenAI module: {e}")
                raise ImportError("Using OpenAI models requires openai library: pip install openai")
        else:
            raise ValueError(f"Unsupported embedding provider: {config.embedding_provider}")

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
                logger.error(f"❌ Failed to import OpenAI module: {e}")
                raise ImportError("Using OpenAI models requires openai library: pip install openai")
        else:
            raise ValueError(f"Unsupported generation provider: {config.generation_provider}")


def create_models_service_from_config(config: ModelConfig) -> ModelsService:
    embedding_model = ModelFactory.create_embedding_model(config)
    generation_model = ModelFactory.create_generation_model(config)
    return ModelsService(embedding_model=embedding_model, generation_model=generation_model)
