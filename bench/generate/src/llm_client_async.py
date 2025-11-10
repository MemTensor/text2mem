"""
Asynchronous LLM client
Supports concurrent requests, automatic retries, and rate limiting
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from bench.generate.src.llm_client import LLMConfig, LLMResponse


class AsyncLLMClient:
    """Asynchronous LLM client"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Read configuration from environment variables
        self.max_retries = int(os.getenv("TEXT2MEM_BENCH_GEN_RETRY_MAX", "3"))
        self.retry_delay = float(os.getenv("TEXT2MEM_BENCH_GEN_RETRY_DELAY", "2"))
        
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for the async client. Install with: pip install aiohttp")
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Asynchronously generate text (with retries)"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if self.config.provider == "openai":
                    return await self._generate_openai(prompt, temperature, max_tokens)
                elif self.config.provider == "ollama":
                    return await self._generate_ollama(prompt, temperature, max_tokens)
                elif self.config.provider == "anthropic":
                    return await self._generate_anthropic(prompt, temperature, max_tokens)
                else:
                    raise ValueError(f"Unsupported provider: {self.config.provider}")
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        raise RuntimeError(f"Max retries ({self.max_retries}) exceeded. Last error: {last_error}")
    
    async def _generate_openai(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """OpenAI async API call"""
        url = f"{self.config.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        data = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        async with self.session.post(url, json=data, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            
            return LLMResponse(
                content=result["choices"][0]["message"]["content"],
                usage=result.get("usage"),
                model=result.get("model"),
            )
    
    async def _generate_ollama(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """Ollama async API call"""
        url = f"{self.config.base_url}/api/generate"
        
        data = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }
        
        async with self.session.post(url, json=data) as response:
            response.raise_for_status()
            result = await response.json()
            
            return LLMResponse(
                content=result.get("response", ""),
                usage=None,
                model=result.get("model"),
            )
    
    async def _generate_anthropic(
        self,
        prompt: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> LLMResponse:
        """Anthropic async API call"""
        url = f"{self.config.base_url}/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }
        
        data = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        async with self.session.post(url, json=data, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            
            return LLMResponse(
                content=result["content"][0]["text"],
                usage=result.get("usage"),
                model=result.get("model"),
            )
    
    def test_connection(self) -> bool:
        """Connection test (synchronous placeholder)"""
        # The async client connection should be tested within an async context.
        # Return True here; actual testing occurs during the first request.
        return True


def create_async_llm_client(config: LLMConfig) -> AsyncLLMClient:
    """Create an asynchronous LLM client"""
    return AsyncLLMClient(config)
