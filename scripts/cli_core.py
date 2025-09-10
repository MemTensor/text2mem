"""CLI core utilities: environment loading, engine/service builders."""
from __future__ import annotations
import os, re, sys
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / '.env'


def echo(msg: str):  # lightweight importable echo
    print(msg, flush=True)


def load_env_file(file_path: Path):
    if not file_path.exists():
        return {}
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
            if m:
                k, v = m.groups()
                env_vars[k] = v
                if k not in os.environ:
                    os.environ[k] = v
    return env_vars


_env_cache = None

def ensure_env_loaded():
    global _env_cache
    if _env_cache is None:
        _env_cache = load_env_file(ENV_PATH) if ENV_PATH.exists() else {}
    return _env_cache


def build_models_service_from_env(explicit_mode: str | None = None):
    """Create & register global ModelsService based on env or explicit mode."""
    ensure_env_loaded()
    from text2mem.core.config import ModelConfig
    from text2mem.services.models_service import set_models_service
    from text2mem.services.models_service_providers import create_models_service

    mode = (explicit_mode or os.environ.get('MODEL_SERVICE') or 'auto').lower()
    if mode == 'openai':
        cfg = ModelConfig.load_openai_config()
    elif mode == 'ollama':
        cfg = ModelConfig.load_ollama_config()
    else:
        cfg = ModelConfig.from_env()
    service = create_models_service(mode=mode, config=cfg)
    set_models_service(service)
    return service


def build_engine_and_adapter(mode: str | None = None, db_path: str | None = None):
    from text2mem.core.engine import Text2MemEngine
    from text2mem.adapters.sqlite_adapter import SQLiteAdapter
    service = build_models_service_from_env(mode)
    db = db_path or os.environ.get('TEXT2MEM_DB_PATH') or './text2mem.db'
    adapter = SQLiteAdapter(db, models_service=service)
    engine = Text2MemEngine(adapter=adapter, models_service=service)
    return service, engine
