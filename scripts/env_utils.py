"""Environment and console utilities for Text2Mem CLI."""
from __future__ import annotations
import os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / '.env'

def echo(msg: str):
    print(msg, flush=True)

def load_env_file(file_path: Path):
    if not file_path.exists():
        return {}
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  # skip comments/blank
                continue
            m = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
            if not m:
                continue
            k, v = m.groups()
            env_vars[k] = v
            if k not in os.environ:
                os.environ[k] = v
    return env_vars

def ensure_env_loaded():
    if ENV_PATH.exists():
        load_env_file(ENV_PATH)

def which(name: str):
    for p in os.environ.get('PATH','').split(os.pathsep):
        c = Path(p) / name
        if c.exists() and os.access(c, os.X_OK):
            return str(c)
    return None
