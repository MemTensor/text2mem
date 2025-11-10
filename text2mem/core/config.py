# moved from text2mem/config.py
from __future__ import annotations
import os
import re
import logging
from dataclasses import dataclass, field
import json
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)
_ENV_LOADED = False


def load_env_vars() -> None:
    """Load environment variables from .env file"""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    # core/config.py -> project root .env at ../../.env
    dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not dotenv_path.exists():
        logger.debug(".env file not found")
        _ENV_LOADED = True
        return
    try:
        env_content = dotenv_path.read_text(encoding='utf-8')
        for line in env_content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
            if match:
                key, value = match.groups()
                if key not in os.environ:
                    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    comment_pos = value.find('#')
                    if comment_pos >= 0:
                        value = value[:comment_pos].strip()
                    os.environ[key] = value
        _ENV_LOADED = True
    except Exception as e:
        logger.warning(f"Error loading .env file: {e}")
        _ENV_LOADED = True


load_env_vars()


@dataclass
class ModelConfig:
    """Model Configuration"""
    # Global provider (applies to both unless explicitly overridden)
    provider: str = "ollama"

    # Providers can still be overridden per role if needed
    embedding_provider: str = "ollama"
    generation_provider: str = "ollama"

    # Effective models used by factories (resolved from provider-specific defaults)
    embedding_model: str = "nomic-embed-text"
    generation_model: str = "qwen2:0.5b"

    # Consolidated Ollama endpoint (used for both embedding and generation)
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    openai_organization: Optional[str] = None

    # Common generation settings
    request_timeout: int = 60
    max_retries: int = 3
    batch_size: int = 10
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 0.9
    
    # Search configuration
    search_alpha: float = 0.7  # Semantic similarity weight
    search_beta: float = 0.3  # Keyword matching weight
    search_phrase_bonus: float = 0.2  # Exact phrase match bonus
    search_default_limit: int = 10  # Default search limit
    search_max_limit: int = 100  # Maximum search limit
    search_default_k: int = 5  # Default top-k results

    @property
    def embedding_base_url(self) -> str:
        # Back-compat: factories read these attributes
        return self.ollama_base_url if self.embedding_provider == "ollama" else ""

    @property
    def generation_base_url(self) -> str:
        # Back-compat: factories read these attributes
        return self.ollama_base_url if self.generation_provider == "ollama" else ""

    @classmethod
    def from_env(cls) -> 'ModelConfig':
        """Load config with sensible precedence and provider-aware defaults.
        Precedence:
          1) Specific overrides: TEXT2MEM_EMBEDDING_PROVIDER / TEXT2MEM_GENERATION_PROVIDER
          2) General provider: TEXT2MEM_PROVIDER or MODEL_SERVICE
          3) Hard-coded defaults
        Models:
          - If provider is ollama: prefer TEXT2MEM_EMBEDDING_MODEL / TEXT2MEM_GENERATION_MODEL; fallback to
            TEXT2MEM_OLLAMA_* then to built-ins (nomic-embed-text / qwen2:0.5b)
          - If provider is openai: prefer TEXT2MEM_*; fallback to OPENAI_* and built-ins (text-embedding-3-small / gpt-3.5-turbo)
          Mismatched models will be warned and replaced with provider defaults.
        """
        load_env_vars()

        general_provider = (os.getenv("TEXT2MEM_PROVIDER") or os.getenv("MODEL_SERVICE") or "ollama").lower()
        embedding_provider = (os.getenv("TEXT2MEM_EMBEDDING_PROVIDER") or general_provider).lower()
        generation_provider = (os.getenv("TEXT2MEM_GENERATION_PROVIDER") or general_provider).lower()

        # Defaults
        OPENAI_DEFAULT_EMBED = "text-embedding-3-small"
        OPENAI_DEFAULT_GEN = "gpt-3.5-turbo"
        OLLAMA_DEFAULT_EMBED = "nomic-embed-text"
        OLLAMA_DEFAULT_GEN = "qwen2:0.5b"

        # Optional dict-like model configuration
        models_map = None
        models_raw = os.getenv("TEXT2MEM_MODELS")
        if models_raw:
            try:
                models_map = json.loads(models_raw)
            except Exception as _e:
                logger.warning("Failed to parse TEXT2MEM_MODELS, ignoring configuration")
                models_map = None

        # Resolve embedding model & base_url
        embed_model_env = os.getenv("TEXT2MEM_EMBEDDING_MODEL") or os.getenv("OPENAI_EMBEDDING_MODEL") or os.getenv("OLLAMA_EMBEDDING_MODEL")
        if embedding_provider == "ollama":
            # prefer dict mapping if provided
            if models_map and isinstance(models_map.get("ollama"), dict):
                ollama_cfg = models_map["ollama"]
                embedding_model = ollama_cfg.get("embedding") or ollama_cfg.get("embed") or OLLAMA_DEFAULT_EMBED
                ollama_base_url = (
                    ollama_cfg.get("base_url")
                    or os.getenv("TEXT2MEM_OLLAMA_BASE_URL")
                    or os.getenv("OLLAMA_BASE_URL")
                    or os.getenv("TEXT2MEM_EMBEDDING_BASE_URL")
                    or "http://localhost:11434"
                )
            else:
                embedding_model = embed_model_env or os.getenv("TEXT2MEM_OLLAMA_EMBEDDING_MODEL") or OLLAMA_DEFAULT_EMBED
                ollama_base_url = os.getenv("TEXT2MEM_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL") or os.getenv("TEXT2MEM_EMBEDDING_BASE_URL") or "http://localhost:11434"
            if embed_model_env and embed_model_env.startswith("text-embedding-"):
                logger.warning("Detected OpenAI embedding model mismatch with provider=ollama, falling back to default ollama embedding model")
                embedding_model = OLLAMA_DEFAULT_EMBED
        else:  # openai
            if models_map and isinstance(models_map.get("openai"), dict):
                openai_cfg = models_map["openai"]
                embedding_model = openai_cfg.get("embedding") or openai_cfg.get("embed") or OPENAI_DEFAULT_EMBED
            else:
                embedding_model = embed_model_env or os.getenv("TEXT2MEM_OPENAI_EMBEDDING_MODEL") or OPENAI_DEFAULT_EMBED
            # keep ollama base url around in case generation uses ollama
            ollama_base_url = os.getenv("TEXT2MEM_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
            if embed_model_env and not embed_model_env.startswith("text-embedding-"):
                logger.warning("Detected non-OpenAI embedding model mismatch with provider=openai, falling back to default openai embedding model")
                embedding_model = OPENAI_DEFAULT_EMBED

        # Resolve generation model and ensure we have an ollama_base_url
        gen_model_env = os.getenv("TEXT2MEM_GENERATION_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("OLLAMA_MODEL")
        if generation_provider == "ollama":
            if models_map and isinstance(models_map.get("ollama"), dict):
                generation_model = models_map["ollama"].get("generation") or models_map["ollama"].get("gen") or OLLAMA_DEFAULT_GEN
            else:
                generation_model = gen_model_env or os.getenv("TEXT2MEM_OLLAMA_GENERATION_MODEL") or OLLAMA_DEFAULT_GEN
            if 'ollama_base_url' not in locals():
                ollama_base_url = os.getenv("TEXT2MEM_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL") or os.getenv("TEXT2MEM_GENERATION_BASE_URL") or "http://localhost:11434"
            if gen_model_env and gen_model_env.startswith("gpt-"):
                logger.warning("Detected OpenAI generation model mismatch with provider=ollama, falling back to default ollama generation model")
                generation_model = OLLAMA_DEFAULT_GEN
        else:  # openai
            if models_map and isinstance(models_map.get("openai"), dict):
                generation_model = models_map["openai"].get("generation") or models_map["openai"].get("gen") or OPENAI_DEFAULT_GEN
            else:
                generation_model = gen_model_env or os.getenv("TEXT2MEM_OPENAI_GENERATION_MODEL") or OPENAI_DEFAULT_GEN
            if 'ollama_base_url' not in locals():
                ollama_base_url = os.getenv("TEXT2MEM_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
            if gen_model_env and not gen_model_env.startswith("gpt-"):
                logger.warning("Detected non-OpenAI generation model mismatch with provider=openai, falling back to default openai generation model")
                generation_model = OPENAI_DEFAULT_GEN

        return cls(
            provider=general_provider,
            embedding_provider=embedding_provider,
            generation_provider=generation_provider,
            embedding_model=embedding_model,
            generation_model=generation_model,
            ollama_base_url=ollama_base_url,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("OPENAI_API_BASE"),
            openai_organization=os.getenv("OPENAI_ORGANIZATION"),
            request_timeout=int(os.getenv("TEXT2MEM_REQUEST_TIMEOUT", "60")),
            max_retries=int(os.getenv("TEXT2MEM_MAX_RETRIES", "3")),
            batch_size=int(os.getenv("TEXT2MEM_BATCH_SIZE", "10")),
            temperature=float(os.getenv("TEXT2MEM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("TEXT2MEM_MAX_TOKENS", "512")),
            top_p=float(os.getenv("TEXT2MEM_TOP_P", "0.9")),
            search_alpha=float(os.getenv("TEXT2MEM_SEARCH_ALPHA", "0.7")),
            search_beta=float(os.getenv("TEXT2MEM_SEARCH_BETA", "0.3")),
            search_phrase_bonus=float(os.getenv("TEXT2MEM_SEARCH_PHRASE_BONUS", "0.2")),
            search_default_limit=int(os.getenv("TEXT2MEM_SEARCH_DEFAULT_LIMIT", "10")),
            search_max_limit=int(os.getenv("TEXT2MEM_SEARCH_MAX_LIMIT", "100")),
            search_default_k=int(os.getenv("TEXT2MEM_SEARCH_DEFAULT_K", "5")),
        )

    @classmethod
    def for_ollama(
        cls,
        embedding_model: Optional[str] = None,
        generation_model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> 'ModelConfig':
        load_env_vars()
        default_embedding_model = os.getenv("TEXT2MEM_OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        default_generation_model = os.getenv("TEXT2MEM_OLLAMA_GENERATION_MODEL", "qwen2:0.5b")
        default_base_url = os.getenv("TEXT2MEM_OLLAMA_BASE_URL", "http://localhost:11434")
        return cls(
            provider="ollama",
            embedding_provider="ollama",
            generation_provider="ollama",
            embedding_model=embedding_model or default_embedding_model,
            generation_model=generation_model or default_generation_model,
            ollama_base_url=base_url or default_base_url,
        )

    @classmethod
    def load_ollama_config(cls) -> 'ModelConfig':
        load_env_vars()
        return cls.for_ollama()

    @classmethod
    def for_openai(
        cls,
        embedding_model: Optional[str] = None,
        generation_model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> 'ModelConfig':
        load_env_vars()
        default_embedding_model = os.getenv("TEXT2MEM_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        default_generation_model = os.getenv("TEXT2MEM_OPENAI_GENERATION_MODEL", "gpt-3.5-turbo")
        api_key_value = api_key or os.getenv("OPENAI_API_KEY")
        api_base_value = api_base or os.getenv("OPENAI_API_BASE")
        if not api_key_value:
            logger.warning("OpenAI API key not set, please set OPENAI_API_KEY in .env file or environment variables")
        return cls(
            provider="openai",
            embedding_provider="openai",
            generation_provider="openai",
            embedding_model=embedding_model or default_embedding_model,
            generation_model=generation_model or default_generation_model,
            openai_api_key=api_key_value,
            openai_api_base=api_base_value,
            openai_organization=os.getenv("OPENAI_ORGANIZATION"),
        )

    @classmethod
    def load_openai_config(cls) -> 'ModelConfig':
        load_env_vars()
        return cls.for_openai()


@dataclass
class DatabaseConfig:
    path: str = ":memory:"
    enable_wal: bool = True
    timeout: int = 30
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            path=os.getenv("TEXT2MEM_DB_PATH", ":memory:"),
            enable_wal=os.getenv("TEXT2MEM_DB_WAL", "true").lower() == "true",
            timeout=int(os.getenv("TEXT2MEM_DB_TIMEOUT", "30")),
        )


@dataclass
class Text2MemConfig:
    model: ModelConfig
    database: DatabaseConfig
    schema_path: Optional[str] = None
    log_level: str = field(default_factory=lambda: os.getenv("TEXT2MEM_LOG_LEVEL", "INFO"))
    @classmethod
    def from_env(cls) -> 'Text2MemConfig':
        return cls(
            model=ModelConfig.from_env(),
            database=DatabaseConfig.from_env(),
            schema_path=os.getenv("TEXT2MEM_SCHEMA_PATH"),
            log_level=os.getenv("TEXT2MEM_LOG_LEVEL", "INFO"),
        )
    @classmethod
    def default(cls) -> 'Text2MemConfig':
        return cls(model=ModelConfig(), database=DatabaseConfig(), log_level=os.getenv("TEXT2MEM_LOG_LEVEL", "INFO"))
    @classmethod
    def for_ollama(cls) -> 'Text2MemConfig':
        return cls(model=ModelConfig.load_ollama_config(), database=DatabaseConfig.from_env(), log_level=os.getenv("TEXT2MEM_LOG_LEVEL", "INFO"))
    @classmethod
    def for_openai(cls) -> 'Text2MemConfig':
        return cls(model=ModelConfig.load_openai_config(), database=DatabaseConfig.from_env(), log_level=os.getenv("TEXT2MEM_LOG_LEVEL", "INFO"))
