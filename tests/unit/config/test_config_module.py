import os

from text2mem.core.config import ModelConfig, Text2MemConfig


def test_modelconfig_defaults_and_for_ollama_openai(monkeypatch):
    # Clear specific vars to test defaults
    for k in [
        "TEXT2MEM_EMBEDDING_PROVIDER", "TEXT2MEM_GENERATION_PROVIDER",
        "TEXT2MEM_DEFAULT_EMBEDDING_PROVIDER", "TEXT2MEM_DEFAULT_GENERATION_PROVIDER",
    ]:
        monkeypatch.delenv(k, raising=False)

    cfg = ModelConfig.from_env()
    assert cfg.embedding_provider in ("ollama", "openai")
    assert cfg.generation_provider in ("ollama", "openai")

    ollama = ModelConfig.for_ollama()
    assert ollama.embedding_provider == "ollama" and ollama.generation_provider == "ollama"

    openai = ModelConfig.for_openai()
    assert openai.embedding_provider == "openai" and openai.generation_provider == "openai"


def test_text2memconfig_from_env():
    cfg = Text2MemConfig.from_env()
    assert cfg.model and cfg.database
