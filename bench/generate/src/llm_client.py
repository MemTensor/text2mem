"""
LLM Client - Unified large language model client interface
Supports OpenAI, Ollama, and Anthropic
"""
from __future__ import annotations

import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str  # openai, ollama, anthropic
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    timeout: int = 120  # default value, can be overridden via environment variables
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> LLMConfig:
        """Create an LLM configuration from a dictionary"""
        # Resolve environment variable references
        api_key = config.get("api_key", "")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var)
        elif not api_key:
            # Attempt to read from environment variables
            if config["provider"] == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
            elif config["provider"] == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Resolve base_url
        base_url = config.get("base_url", "")
        if base_url and base_url.startswith("${") and base_url.endswith("}"):
            env_var = base_url[2:-1]
            base_url = os.getenv(env_var)
        elif not base_url:
            if config["provider"] == "openai":
                base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
            elif config["provider"] == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Read other parameters, preferring dictionary values over environment defaults
        temperature = config.get("temperature")
        if temperature is None:
            temperature = float(os.getenv("TEXT2MEM_BENCH_GEN_TEMPERATURE", "0.7"))
        
        max_tokens = config.get("max_tokens")
        if max_tokens is None:
            max_tokens = int(os.getenv("TEXT2MEM_BENCH_GEN_MAX_TOKENS", "4000"))
        
        timeout = config.get("timeout")
        if timeout is None:
            timeout = int(os.getenv("TEXT2MEM_BENCH_GEN_TIMEOUT", "120"))
        
        return cls(
            provider=config["provider"],
            model=config["model"],
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=config.get("top_p", 1.0),
            timeout=timeout,
        )


@dataclass
class LLMResponse:
    """LLM response object"""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None


class LLMClient:
    """Base class for LLM clients"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate text from a prompt"""
        raise NotImplementedError
    
    def test_connection(self) -> bool:
        """Test connection by making a minimal API call"""
        try:
            response = self.generate("Hello", max_tokens=5)
            return bool(response.content)
        except Exception:
            return False


class OpenAIClient(LLMClient):
    """OpenAI API client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
        
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            top_p=self.config.top_p,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            model=response.model,
        )


class OllamaClient(LLMClient):
    """Ollama API client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("Please install requests: pip install requests")
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call Ollama API"""
        url = f"{self.config.base_url}/api/generate"
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }
        
        response = self.requests.post(url, json=payload, timeout=self.config.timeout)
        response.raise_for_status()
        
        result = response.json()
        return LLMResponse(
            content=result["response"],
            model=self.config.model,
        )


class AnthropicClient(LLMClient):
    """Anthropic API client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
        
        self.client = Anthropic(api_key=config.api_key)
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Call Anthropic API"""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return LLMResponse(
            content=response.content[0].text,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            model=response.model,
        )


def create_llm_client(config: LLMConfig) -> LLMClient:
    """Factory: create an LLM client instance based on provider"""
    if config.provider == "openai":
        return OpenAIClient(config)
    elif config.provider == "ollama":
        return OllamaClient(config)
    elif config.provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
