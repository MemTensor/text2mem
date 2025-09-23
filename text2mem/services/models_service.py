# moved from text2mem/models_service.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import os
from dataclasses import dataclass
import logging
import json
import re
import uuid
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


class StructuredSplitError(ValueError):
    def __init__(self, message: str, trace_id: Optional[str] = None, prompt_snippet: Optional[str] = None):
        super().__init__(message)
        self.trace_id = trace_id or str(uuid.uuid4())
        self.prompt_snippet = prompt_snippet


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
        # Debug hooks
        self.debug_last_split_prompt = None
        self.debug_last_split_raw_output = None
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

    def generate_summary(self, texts: List[str], focus: Optional[str] = None, max_tokens: int = 256, lang: str | None = None) -> GenerationResult:
        combined_text = "\n".join(texts)
        lang = (lang or "en").lower()
        if lang == "zh":
            prompt = f"""请为以下内容生成摘要，最多{max_tokens}个token。

内容：
{combined_text}
"""
            if focus:
                prompt += f"\n特别关注：{focus}"
        else:
            prompt = f"""Summarize the following content concisely in up to {max_tokens} tokens.

Content:
{combined_text}
"""
            if focus:
                prompt += f"\nFocus on: {focus}"
        return self.generation_model.generate(prompt, max_tokens=max_tokens, lang=lang)

    def suggest_labels(self, text: str, existing_labels: List[str] = None, lang: str | None = None) -> GenerationResult:
        lang = (lang or "en").lower()
        if lang == "zh":
            prompt = f"""为以下内容建议3-5个标签，用逗号分隔。

内容：{text}
"""
            if existing_labels:
                prompt += f"\n已有标签：{', '.join(existing_labels)}"
        else:
            prompt = f"""Suggest 3-5 labels for the following content, separated by commas.

Content: {text}
"""
            if existing_labels:
                prompt += f"\nExisting labels: {', '.join(existing_labels)}"
        return self.generation_model.generate(prompt, max_tokens=50, lang=lang)

    def analyze_split_points(self, text: str, strategy: str = "auto_by_patterns", lang: str | None = None) -> GenerationResult:
        raise NotImplementedError("analyze_split_points has been deprecated; use split() with a strategy instead")

    # -------------------------------
    # Service-level structured helpers
    # -------------------------------
    def _parse_json_loose(self, s: str, expect: str = "object") -> Any:
        """Best-effort JSON extraction.
        expect: 'object' or 'array'
        """
        try:
            return json.loads(s)
        except Exception:
            pass
        if expect == "array":
            try:
                start = s.find('[')
                end = s.rfind(']')
                if start != -1 and end != -1 and end > start:
                    return json.loads(s[start:end+1])
            except Exception:
                pass
        else:
            try:
                start = s.find('{')
                end = s.rfind('}')
                if start != -1 and end != -1 and end > start:
                    return json.loads(s[start:end+1])
            except Exception:
                pass
        return None

    def generate_json(self, prompt: str, expect: str = "object", max_tokens: int = 512, lang: Optional[str] = None, timeout: Optional[float] = None) -> GenerationResult:
        """High-level structured generation.
        - Prefer provider's structured API when present (e.g., OpenAI's JSON mode).
        - Otherwise, add minimal instruction and parse JSON loosely.
        Returns GenerationResult with text set to canonical JSON string.
        """
        base_result: GenerationResult
        # If provider supports structured, nudge with minimal schema
        schema_hint = {"type": "array", "items": {"type": "object"}} if expect == "array" else {"type": "object"}
        try:
            if hasattr(self.generation_model, "generate_structured") and callable(getattr(self.generation_model, "generate_structured")):
                base_result = self.generation_model.generate_structured(prompt, schema_hint, max_tokens=max_tokens, lang=lang or "en", timeout=timeout)
            else:
                raise AttributeError("no structured support")
        except Exception:
            # Fallback plain generate with an explicit instruction
            if lang and lang.lower() == "zh":
                instr = "仅输出一个JSON{}，不要添加任何解释、注释或前后缀。".format("数组" if expect == "array" else "对象")
            else:
                instr = "Output a JSON {} only, with no explanation or prefix/suffix.".format("array" if expect == "array" else "object")
            prompt2 = f"{prompt}\n\n{instr}"
            base_result = self.generation_model.generate(prompt2, max_tokens=max_tokens, lang=lang or "en", timeout=timeout)

        parsed = self._parse_json_loose(base_result.text, expect=expect)
        if parsed is not None:
            canon = json.dumps(parsed, ensure_ascii=False)
            return GenerationResult(
                text=canon,
                model=base_result.model,
                prompt_tokens=base_result.prompt_tokens,
                completion_tokens=base_result.completion_tokens,
                total_tokens=base_result.total_tokens,
                metadata={"expect": expect},
            )
        # Last resort: return as-is
        return base_result

    # -------------------------------
    # New split() unified entry
    # -------------------------------
    def split(
        self,
        text: str,
        strategy: str = "by_sentences",
        params: Optional[Dict[str, Any]] = None,
        lang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Unified split interface: by_sentences | by_chunks | custom.

        Returns list of {text, title?, range?} in document order, deduped, truncated to params.max_splits (default 100).
        """
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        params = params or {}
        max_splits_global = params.get("max_splits") if isinstance(params, dict) else None
        if not isinstance(max_splits_global, int) or max_splits_global <= 0:
            max_splits_global = 100

        strategy = (strategy or "by_sentences").lower()
        lang = (lang or params.get("lang") or "en").lower()
        if lang == "auto":
            lang = self._detect_lang_simple(text)

        if strategy == "by_sentences":
            seg_conf = (params.get("by_sentences") if isinstance(params, dict) else None) or {}
            seg_lang = (seg_conf.get("lang") or lang or "auto").lower()
            if seg_lang == "auto":
                seg_lang = self._detect_lang_simple(text)
            max_sentences = seg_conf.get("max_sentences")
            if max_sentences is not None and (not isinstance(max_sentences, int) or max_sentences <= 0):
                raise ValueError("by_sentences.max_sentences must be a positive integer or None")
            items = self._split_by_sentences(text, seg_lang, max_sentences)
            items = self._dedupe_order(items)
            return items[:max_splits_global]

        if strategy == "by_chunks":
            ch_conf = (params.get("by_chunks") if isinstance(params, dict) else None) or {}
            chunk_size = ch_conf.get("chunk_size")
            num_chunks = ch_conf.get("num_chunks")
            if num_chunks is not None:
                if not isinstance(num_chunks, int) or num_chunks <= 0:
                    raise ValueError("by_chunks.num_chunks must be a positive integer")
                items = self._split_by_num_chunks(text, num_chunks)
            else:
                if chunk_size is None:
                    chunk_size = 500
                if not isinstance(chunk_size, int) or chunk_size <= 0:
                    raise ValueError("by_chunks.chunk_size must be a positive integer")
                items = self._split_by_chunk_size(text, chunk_size)
            items = self._dedupe_order(items)
            return items[:max_splits_global]

        if strategy == "custom":
            cu_conf = (params.get("custom") if isinstance(params, dict) else None) or {}
            instruction = cu_conf.get("instruction")
            if not instruction or not isinstance(instruction, str):
                raise ValueError("custom.instruction is required and must be a string")
            llm_max_splits = cu_conf.get("max_splits")
            if not isinstance(llm_max_splits, int) or llm_max_splits <= 0:
                llm_max_splits = 10

            prompt = self._build_custom_prompt(text=text, instruction=instruction, max_splits=llm_max_splits, lang=lang)
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "text": {"type": "string", "minLength": 1},
                        "range": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                    "oneOf": [
                        {"required": ["text"]},
                        {"required": ["range"]},
                    ],
                },
            }
            # Call structured generation only; errors bubble up as StructuredSplitError
            timeout_sec = 20.0
            try:
                timeout_sec = float(cu_conf.get("timeout", timeout_sec))
            except Exception:
                pass
            try:
                res = self.generation_model.generate_structured(prompt, schema=schema, max_tokens=min(1024, max(256, len(text)//4)), lang=lang, timeout=timeout_sec)
                self.debug_last_split_prompt = prompt
                self.debug_last_split_raw_output = res.text
            except Exception as e:
                raise StructuredSplitError(f"structured generation failed: {type(e).__name__}: {e}", prompt_snippet=prompt[:500])

            data = self._parse_json_loose(res.text, expect="array")
            if not isinstance(data, list):
                raise StructuredSplitError("model did not return an array", prompt_snippet=prompt[:500])
            items = self._normalize_split_items(data, text, llm_max_splits)
            items = self._dedupe_order(items)
            return items[:max_splits_global]

        raise ValueError("strategy must be one of: by_sentences|by_chunks|custom")

    # -------------------------------
    # Helpers for split
    # -------------------------------
    def _detect_lang_simple(self, text: str) -> str:
        if re.search(r"[\u4e00-\u9fff]|[。！？；：]", text or ""):
            return "zh"
        return "en"

    def _split_by_sentences(self, text: str, lang: str, max_sentences: Optional[int]) -> List[Dict[str, Any]]:
        if not text:
            return []
        if lang == "zh":
            # Split on Chinese sentence enders, keep delimiters.
            parts = re.split(r"([。！？；])", text)
        else:
            parts = re.split(r"([.!?])", text)
        # Recombine delimiter with sentence
        sentences: List[str] = []
        buf = ""
        for i in range(0, len(parts), 2):
            seg = parts[i]
            delim = parts[i+1] if i+1 < len(parts) else ""
            chunk = (seg or "") + (delim or "")
            if chunk:
                sentences.append(chunk)
        if not sentences:
            sentences = [text]
        # Merge by max_sentences
        if max_sentences is None:
            blocks = sentences
        else:
            blocks = []
            for i in range(0, len(sentences), max_sentences):
                blocks.append("".join(sentences[i:i+max_sentences]))
        # Align ranges with rolling find
        return self._align_ranges_by_find(text, [{"text": b} for b in blocks])

    def _split_by_chunk_size(self, text: str, chunk_size: int) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        i = 0
        n = len(text)
        while i < n:
            j = min(n, i + chunk_size)
            items.append({"text": text[i:j], "range": [i, j]})
            i = j
        return items

    def _split_by_num_chunks(self, text: str, num_chunks: int) -> List[Dict[str, Any]]:
        n = len(text)
        if num_chunks <= 1 or n == 0:
            return [{"text": text, "range": [0, n]}] if text else []
        base = n // num_chunks
        rem = n % num_chunks
        items: List[Dict[str, Any]] = []
        start = 0
        for k in range(num_chunks):
            size = base + (1 if k < rem else 0)
            end = start + size
            items.append({"text": text[start:end], "range": [start, end]})
            start = end
        return items

    def _build_custom_prompt(self, text: str, instruction: str, max_splits: int, lang: str) -> str:
        if (lang or "en").lower() == "zh":
            return (
                "请将下面的文本按指令切分为不超过 {n} 段，并**仅**返回一个 JSON 数组（不添加任何解释）。\n\n"
                "每个数组元素是一个对象，字段规范如下（请严格遵守）：\n"
                "- \"title\": 可选字符串，小标题\n"
                "- \"text\": 可选字符串，表示该段的原文内容\n"
                "- \"range\": 可选整数数组 [start, end]（半开区间，按原文字符索引）\n"
                "- 以上三者中，至少提供 \"text\" 或 \"range\" 之一；禁止输出除上述以外的字段。\n"
                "- 结果中的段落顺序必须与原文一致，禁止打乱或改写原文内容。\n\n"
                "指令：\n{instr}\n\n文本：\n{text}\n"
            ).format(n=max_splits, instr=instruction, text=text)
        return (
            "Split the following text into at most {n} segments and return a JSON ARRAY ONLY (no explanations).\n\n"
            "Each item MUST be an OBJECT with the following fields (strict):\n"
            "- \"title\": optional string (subtitle)\n"
            "- \"text\":  optional string (verbatim content of the segment)\n"
            "- \"range\": optional integer array [start, end) with character indices from the original text\n"
            "- Provide AT LEAST ONE of \"text\" or \"range\"; DO NOT include any fields other than the above.\n"
            "- Preserve the original order of the text; do not paraphrase.\n\n"
            "Instruction:\n{instr}\n\nText:\n{text}\n"
        ).format(n=max_splits, instr=instruction, text=text)

    def _normalize_split_items(self, items: List[Any], source_text: str, max_splits: int) -> List[Dict[str, Any]]:
        """Enforce schema, project to {text?, title?, range?}, fill text from range, align missing ranges, drop invalid, cap to max_splits."""
        normalized: List[Dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            # Strip unknown fields; keep only whitelist
            title = it.get("title") if isinstance(it.get("title"), str) else None
            text = it.get("text") if isinstance(it.get("text"), str) else None
            rng = it.get("range") if isinstance(it.get("range"), list) and len(it.get("range")) == 2 else None
            if rng is not None:
                try:
                    s, e = int(rng[0]), int(rng[1])
                    s = max(0, min(s, len(source_text)))
                    e = max(s, min(e, len(source_text)))
                    rng = [s, e]
                except Exception:
                    rng = None
            if not text and rng is not None:
                s, e = rng
                text = source_text[s:e]
            if not text and rng is None:
                # Must provide at least text or range
                continue
            if text is not None and len(text) == 0:
                continue
            normalized.append({"title": title, "text": text, "range": rng})
            if len(normalized) >= max_splits:
                break
        # Align ranges for items missing range but with text
        aligned = self._align_ranges_by_find(source_text, normalized)
        return aligned[:max_splits]

    def _align_ranges_by_find(self, doc: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pos = 0
        out: List[Dict[str, Any]] = []
        for it in items:
            t = (it.get("text") or "") if isinstance(it.get("text"), str) else ""
            rng = it.get("range") if isinstance(it.get("range"), list) and len(it.get("range")) == 2 else None
            if rng is not None:
                s, e = int(rng[0]), int(rng[1])
                s = max(0, min(s, len(doc)))
                e = max(s, min(e, len(doc)))
                out.append({**it, "range": [s, e], "text": t or doc[s:e]})
                pos = e
                continue
            if not t:
                # Nothing to align
                out.append({**it, "range": None})
                continue
            idx = doc.find(t, pos)
            if idx == -1:
                # try compact match without spaces
                compact_t = "".join(t.split())
                compact_doc = "".join(doc[pos:].split())
                idx2 = compact_doc.find(compact_t)
                if idx2 == -1:
                    out.append({**it, "range": None})
                    continue
                out.append({**it, "range": None})
                continue
            s = idx
            e = idx + len(t)
            pos = e
            out.append({**it, "range": [s, e]})
        return out

    def _dedupe_order(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates while preserving order (by text+range key). Drop empty text."""
        seen: set = set()
        out: List[Dict[str, Any]] = []
        for it in items:
            original_text = it.get("text") or ""
            # Use strip only for emptiness check, but preserve original text content
            if not original_text.strip():
                continue
            rng = it.get("range") if isinstance(it.get("range"), list) else None
            key = (original_text, tuple(rng) if rng else None)
            if key in seen:
                continue
            seen.add(key)
            out.append({"text": original_text, "title": it.get("title"), "range": rng})
        return out

class PromptTemplates:
    SUMMARIZE_TEMPLATE = (
        "请为以下记忆内容生成简洁摘要：\n\n"
        "记忆内容：\n"
        "{content}\n\n"
        "要求：\n"
        "- 保留关键信息\n"
        "- 控制在{max_tokens}个token以内\n"
        "{focus_instruction}\n\n"
        "摘要："
    )


_models_service_instance: Optional[ModelsService] = None


def get_models_service() -> ModelsService:
    global _models_service_instance
    if _models_service_instance is None:
        _models_service_instance = ModelsService()
    return _models_service_instance


def set_models_service(service: ModelsService):
    global _models_service_instance
    _models_service_instance = service
