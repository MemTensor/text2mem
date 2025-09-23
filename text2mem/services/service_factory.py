"""Service factory: compose provider models into a ModelsService.

Goals
- Providers expose embedding/generation model classes only.
- This factory decides which providers to use (mock/ollama/openai/auto),
  constructs the models, and returns a configured ModelsService.
- Centralize env/config resolution to avoid duplication in providers.

Public API
- create_models_service(mode: str = "auto", config: Optional[Union[Text2MemConfig, ModelConfig]] = None) -> ModelsService
- create_models_service_from_env() -> ModelsService
"""
from __future__ import annotations
import os
import logging
from typing import Optional, Tuple, Union

from text2mem.core.config import Text2MemConfig, ModelConfig
from .models_service import ModelsService, BaseEmbeddingModel, BaseGenerationModel

logger = logging.getLogger("text2mem.service_factory")


def _resolve_mode_and_config(
    mode: str | None,
    config: Optional[Union[Text2MemConfig, ModelConfig]]
) -> Tuple[str, ModelConfig]:
    if isinstance(config, Text2MemConfig):
        model_cfg: ModelConfig = config.model
    elif isinstance(config, ModelConfig):
        model_cfg = config
    else:
        model_cfg = ModelConfig.from_env()

    resolved_mode = (mode or os.getenv("MODEL_SERVICE") or "auto").lower()
    if resolved_mode == "auto":
        if model_cfg.embedding_provider == "openai" or model_cfg.generation_provider == "openai":
            resolved_mode = "openai"
        elif model_cfg.embedding_provider == "ollama" or model_cfg.generation_provider == "ollama":
            resolved_mode = "ollama"
        else:
            resolved_mode = "mock"
    return resolved_mode, model_cfg


def _build_mock_models() -> Tuple[BaseEmbeddingModel, BaseGenerationModel]:
    from .models_service_mock import MockEmbeddingModel, MockGenerationModel
    return MockEmbeddingModel(), MockGenerationModel()


def _build_ollama_models(cfg: ModelConfig) -> Tuple[BaseEmbeddingModel, BaseGenerationModel]:
    from .models_service_ollama import OllamaEmbeddingModel, OllamaGenerationModel
    emb = OllamaEmbeddingModel(model_name=cfg.embedding_model, base_url=cfg.embedding_base_url)
    gen = OllamaGenerationModel(model_name=cfg.generation_model, base_url=cfg.generation_base_url)
    return emb, gen


def _build_openai_models(cfg: ModelConfig) -> Tuple[BaseEmbeddingModel, BaseGenerationModel]:
    from .models_service_openai import OpenAIEmbeddingModel, OpenAIGenerationModel
    emb = OpenAIEmbeddingModel(
        model_name=cfg.embedding_model,
        api_key=cfg.openai_api_key,
        api_base=cfg.openai_api_base,
        organization=cfg.openai_organization,
    )
    gen = OpenAIGenerationModel(
        model_name=cfg.generation_model,
        api_key=cfg.openai_api_key,
        api_base=cfg.openai_api_base,
        organization=cfg.openai_organization,
    )
    return emb, gen


def create_models_service(
    mode: str = "auto",
    config: Optional[Union[Text2MemConfig, ModelConfig]] = None,
) -> ModelsService:
    resolved_mode, model_cfg = _resolve_mode_and_config(mode, config)
    logger.info(f"🔧 Creating ModelsService via service_factory: mode={resolved_mode}")

    if resolved_mode == "mock":
        emb, gen = _build_mock_models()
    elif resolved_mode == "ollama":
        # Force providers to be consistent
        model_cfg.embedding_provider = "ollama"
        model_cfg.generation_provider = "ollama"
        emb, gen = _build_ollama_models(model_cfg)
    elif resolved_mode == "openai":
        model_cfg.embedding_provider = "openai"
        model_cfg.generation_provider = "openai"
        emb, gen = _build_openai_models(model_cfg)
    else:
        raise ValueError(f"Unknown service mode: {resolved_mode}")

    return ModelsService(embedding_model=emb, generation_model=gen)


def create_models_service_from_env() -> ModelsService:
    cfg = ModelConfig.from_env()
    return create_models_service(mode="auto", config=cfg)
