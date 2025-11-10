"""Configuration helpers for manage.py

Centralizes repeated .env grouping logic so manage.py stays slim.
"""
from __future__ import annotations
from typing import Dict

SECTIONS = {
	"Database Settings": ["DATABASE_PATH", "TEXT2MEM_DB_PATH", "TEXT2MEM_DB_WAL", "TEXT2MEM_DB_TIMEOUT"],
	"Embedding Model Settings": ["TEXT2MEM_EMBEDDING_PROVIDER", "TEXT2MEM_EMBEDDING_MODEL", "TEXT2MEM_EMBEDDING_BASE_URL"],
	"Generation Model Settings": [
		"TEXT2MEM_GENERATION_PROVIDER", "TEXT2MEM_GENERATION_MODEL", "TEXT2MEM_GENERATION_BASE_URL",
		"TEXT2MEM_TEMPERATURE", "TEXT2MEM_MAX_TOKENS", "TEXT2MEM_TOP_P"
	],
	"OpenAI Settings": ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_API_BASE", "OPENAI_ORGANIZATION"],
	"Ollama Settings": ["OLLAMA_BASE_URL", "OLLAMA_MODEL"],
	"Other Settings": ["MODEL_SERVICE", "TEXT2MEM_LOG_LEVEL", "TEXT2MEM_PROVIDER", "TEXT2MEM_MODELS"]
}


def generate_grouped_env(existing: Dict[str,str], provider: str) -> str:
	content = [f"# Text2Mem Environment Configuration", f"# Provider: {provider}", ""]
	for section, keys in SECTIONS.items():
		section_keys = [k for k in keys if k in existing]
		if not section_keys:
			continue
		content.append(f"# {section}")
		for k in section_keys:
			content.append(f"{k}={existing[k]}")
		content.append("")
	# any leftover custom keys
	covered = {k for keys in SECTIONS.values() for k in keys}
	leftover = [k for k in existing if k not in covered]
	if leftover:
		content.append("# Custom Settings")
		for k in leftover:
			content.append(f"{k}={existing[k]}")
	return "\n".join(content).rstrip() + "\n"

