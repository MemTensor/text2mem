# moved from text2mem/models_service.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import json
from datetime import datetime

logger = logging.getLogger("text2mem.models_service")


@dataclass
class EmbeddingResult:
    text: str
    embedding: List[float]
    model: str
    tokens_used: int = 0
    @property
    def vector(self) -> List[float]:
        return self.embedding
    @property
    def dimension(self) -> int:
        return len(self.embedding)
    @property
    def model_name(self) -> str:
        return self.model


@dataclass
class GenerationResult:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: Optional[Dict[str, Any]] = None
    @property
    def model_name(self) -> str:
        return self.model
    @property
    def usage(self) -> Optional[Dict[str, Any]]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class BaseEmbeddingModel(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> EmbeddingResult: ...
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]: ...
    @abstractmethod
    def get_dimension(self) -> int: ...


class BaseGenerationModel(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> GenerationResult: ...
    @abstractmethod
    def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult: ...


class DummyEmbeddingModel(BaseEmbeddingModel):
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.model_name = "dummy-embedding"
    def embed_text(self, text: str) -> EmbeddingResult:
        import hashlib, struct
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        vector = []
        for i in range(0, len(hash_bytes), 4):
            chunk = hash_bytes[i:i+4].ljust(4, b'\0')
            float_val = struct.unpack('f', chunk)[0]
            vector.append(float_val)
        while len(vector) < self.dimension:
            vector.extend(vector[:min(len(vector), self.dimension - len(vector))])
        vector = vector[:self.dimension]
        norm = sum(x*x for x in vector) ** 0.5
        if norm > 0:
            vector = [x/norm for x in vector]
        return EmbeddingResult(text=text, embedding=vector, model=self.model_name, tokens_used=len(text.split()))
    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        return [self.embed_text(text) for text in texts]
    def get_dimension(self) -> int:
        return self.dimension


class DummyGenerationModel(BaseGenerationModel):
    def __init__(self):
        self.model_name = "dummy-llm"
    def generate(self, prompt: str, **kwargs) -> GenerationResult:
        if "摘要" in prompt or "总结" in prompt:
            response = "这是一个自动生成的摘要。实际应用中会调用真实的LLM API。"
        elif "澄清" in prompt or "问题" in prompt:
            response = "请提供更多详细信息以便我更好地理解您的需求。"
        elif "标签" in prompt or "分类" in prompt:
            response = "重要, 工作, 会议"
        elif "分割" in prompt:
            response = "建议在以下位置分割: [100, 250, 400]"
        else:
            response = f"基于提示生成的响应: {prompt[:50]}..."
        return GenerationResult(
            text=response,
            model=self.model_name,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(response.split()),
            total_tokens=len(prompt.split()) + len(response.split()),
            metadata={"timestamp": datetime.now().isoformat()},
        )
    def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        if "clarify" in prompt.lower():
            structured_output = {
                "question": "请提供更多详细信息",
                "missing_slots": ["时间", "地点", "人物"],
                "suggestions": ["今天", "明天", "办公室", "Alice", "Bob"],
            }
        elif "summary" in prompt.lower():
            structured_output = {
                "summary": "这是结构化摘要",
                "key_points": ["要点1", "要点2", "要点3"],
                "confidence": 0.8,
            }
        else:
            structured_output = {"result": "结构化输出"}
        return GenerationResult(
            text=json.dumps(structured_output, ensure_ascii=False),
            model=self.model_name,
            prompt_tokens=len(prompt.split()),
            completion_tokens=50,
            total_tokens=len(prompt.split()) + 50,
            metadata={"schema": schema},
        )


class ModelsService:
    def __init__(self, embedding_model: Optional[BaseEmbeddingModel] = None, generation_model: Optional[BaseGenerationModel] = None):
        self.embedding_model = embedding_model or DummyEmbeddingModel()
        self.generation_model = generation_model or DummyGenerationModel()
        logger.info(
            f"模型服务初始化: 嵌入模型={self.embedding_model.__class__.__name__}, 生成模型={self.generation_model.__class__.__name__}"
        )

    def encode_memory(self, text: str) -> EmbeddingResult:
        return self.embedding_model.embed_text(text)

    def compute_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        if len(vector1) != len(vector2):
            raise ValueError("向量维度不匹配")
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        norm1 = sum(a * a for a in vector1) ** 0.5
        norm2 = sum(b * b for b in vector2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def semantic_search(self, query: str, memory_vectors: List[Dict[str, Any]], k: int = 10) -> List[Dict[str, Any]]:
        query_result = self.embedding_model.embed_text(query)
        query_vector = query_result.vector
        scored_memories = []
        for memory in memory_vectors:
            if 'vector' in memory and memory['vector']:
                similarity = self.compute_similarity(query_vector, memory['vector'])
                scored_memories.append({**memory, 'similarity': similarity})
        scored_memories.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return scored_memories[:k]

    def generate_summary(self, texts: List[str], focus: Optional[str] = None, max_tokens: int = 256) -> GenerationResult:
        combined_text = "\n".join(texts)
        prompt = f"""请为以下内容生成摘要，最多{max_tokens}个token。

内容：
{combined_text}
"""
        if focus:
            prompt += f"\n特别关注：{focus}"
        return self.generation_model.generate(prompt, max_tokens=max_tokens)

    def suggest_labels(self, text: str, existing_labels: List[str] = None) -> GenerationResult:
        prompt = f"""为以下内容建议3-5个标签，用逗号分隔。

内容：{text}
"""
        if existing_labels:
            prompt += f"\n已有标签：{', '.join(existing_labels)}"
        return self.generation_model.generate(prompt, max_tokens=50)

    def analyze_split_points(self, text: str, strategy: str = "auto_by_patterns") -> GenerationResult:
        prompt = f"""分析以下文本的结构，建议分割点。策略：{strategy}

文本：
{text}

请返回分割位置的索引列表，例如：[100, 250, 400]
"""
        return self.generation_model.generate(prompt, max_tokens=100)

    def assess_importance(self, text: str, context: Optional[str] = None) -> GenerationResult:
        prompt = f"""评估以下内容的重要性等级（低/中/高/紧急）。

内容：{text}
"""
        if context:
            prompt += f"\n上下文：{context}"
        return self.generation_model.generate(prompt, max_tokens=20)


class PromptTemplates:
    SUMMARIZE_TEMPLATE = """请为以下记忆内容生成简洁摘要：

记忆内容：
{content}

要求：
- 保留关键信息
- 控制在{max_tokens}个token以内
{focus_instruction}

摘要："""


_models_service_instance: Optional[ModelsService] = None


def get_models_service() -> ModelsService:
    global _models_service_instance
    if _models_service_instance is None:
        _models_service_instance = ModelsService()
    return _models_service_instance


def set_models_service(service: ModelsService):
    global _models_service_instance
    _models_service_instance = service
