# moved from text2mem/models_service.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
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
        if "summary" in prompt or "summary" in prompt:
            response = "This is an automatically generated summary. In actual use, real LLM API would be called."
        elif "clarification" in prompt or "question" in prompt:
            response = "Please provide more details so I can better understand your needs."
        elif "tags" in prompt or "classification" in prompt:
            response = "important, work, meeting"
        elif "split" in prompt:
            response = "Suggested split positions: [100, 250, 400]"
        else:
            response = f"Response generated based on prompt: {prompt[:50]}..."
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
                "question": "Please provide more details",
                "missing_slots": ["time", "location", "people"],
                "suggestions": ["today", "tomorrow", "office", "Alice", "Bob"],
            }
        elif "summary" in prompt.lower():
            structured_output = {
                "summary": "This is a structured summary",
                "key_points": ["Point 1", "Point 2", "Point 3"],
                "confidence": 0.8,
            }
        else:
            structured_output = {"result": "structured output"}
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
            f"Model service initialized: embedding model={self.embedding_model.__class__.__name__}, generation model={self.generation_model.__class__.__name__}"
        )

    def encode_memory(self, text: str) -> EmbeddingResult:
        return self.embedding_model.embed_text(text)

    def compute_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        if len(vector1) != len(vector2):
            raise ValueError("Vector dimension mismatch")
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
            prompt = f"""Generate a summary for the following content, maximum {max_tokens} tokens.

Content:
{combined_text}
"""
            if focus:
                prompt += f"\nSpecial focus: {focus}"
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
            prompt = f"""Suggest 3-5 tags for the following content, separated by commas.

Content:{text}
"""
            if existing_labels:
                prompt += f"\nExisting tags: {', '.join(existing_labels)}"
        else:
            prompt = f"""Suggest 3-5 labels for the following content, separated by commas.

Content: {text}
"""
            if existing_labels:
                prompt += f"\nExisting labels: {', '.join(existing_labels)}"
        return self.generation_model.generate(prompt, max_tokens=50, lang=lang)

    def analyze_split_points(self, text: str, strategy: str = "auto_by_patterns", lang: str | None = None) -> GenerationResult:
        lang = (lang or "en").lower()
        if lang == "zh":
            prompt = f"""Analyze the structure of the following text and suggest split points. Strategy: {strategy}

Text:
{text}

Please return a list of split position indexes, for example: [100, 250, 400]
"""
        else:
            prompt = f"""Analyze the structure of the following text and suggest split points. Strategy: {strategy}

Text:
{text}

Return index positions for splits, e.g., [100, 250, 400]
"""
        return self.generation_model.generate(prompt, max_tokens=120, lang=lang)

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

    def generate_json(self, prompt: str, expect: str = "object", max_tokens: int = 512, lang: Optional[str] = None) -> GenerationResult:
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
                base_result = self.generation_model.generate_structured(prompt, schema_hint, max_tokens=max_tokens, lang=lang or "en")
            else:
                raise AttributeError("no structured support")
        except Exception:
            # Fallback plain generate with an explicit instruction
            if lang and lang.lower() == "zh":
                instr = "Output only one JSON{}, do not add any explanations, comments or prefix/suffix.".format("array" if expect == "array" else "object")
            else:
                instr = "Output a JSON {} only, with no explanation or prefix/suffix.".format("array" if expect == "array" else "object")
            prompt2 = f"{prompt}\n\n{instr}"
            base_result = self.generation_model.generate(prompt2, max_tokens=max_tokens, lang=lang or "en")

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

    def split_custom(self, text: str, instruction: str, max_splits: int = 10, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """Split text via model with structured preference and robust fallbacks.

        Contract for outputs: list of segments, each is a dict with:
          - text: string (required)
          - title: optional string
          - range: optional [start, end] character indices in the original text

        Strategy:
          1) Try structured JSON via generate_json(expect='array') with a minimal schema.
          2) If unavailable, try to parse JSON from model output.
          3) Fallback to plain-text lines parsing.
          4) Normalize: trim, cap to max_splits, deduplicate, and approximate missing ranges.
        """
        lang = (lang or "en").lower()

        # Preferred: structured JSON generation
        if lang == "zh":
            prompt = (
                "Split the following text according to instructions into no more than {n} segments, return a JSON array.\n"
                "Each element is an object with fields: title(optional), text(required), range(optional, [start,end] index in original text).\n"
                "Instruction: {instr}\n\n"
                "Text:\n{content}\n"
            ).format(n=max_splits, instr=(instruction or "Split by topic"), content=text)
        else:
            prompt = (
                "Split the text into at most {n} segments according to the instruction and return a JSON array.\n"
                "Each item is an object with fields: title(optional), text(required), range(optional [start,end] indices).\n"
                "Instruction: {instr}\n\n"
                "Text:\n{content}\n"
            ).format(n=max_splits, instr=(instruction or "split by topics"), content=text)

        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "text": {"type": "string"},
                    "range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                "required": ["text"],
            },
        }

        try:
            # Use generate_json to prefer provider's structured mode when available
            structured = self.generate_json(prompt, expect="array", max_tokens=min(512, max(128, len(text)//5)), lang=lang)
            self.debug_last_split_prompt = prompt
            self.debug_last_split_raw_output = getattr(structured, "text", None)
            parsed = self._parse_json_loose(structured.text, expect="array")
        except Exception:
            parsed = None

        segments: List[Dict[str, Any]] = []
        if isinstance(parsed, list):
            for it in parsed[:max_splits]:
                if isinstance(it, dict):
                    seg_text = (it.get("text") or it.get("content") or "").strip()
                    if not seg_text:
                        # allow extracting any non-empty str value
                        for v in it.values():
                            if isinstance(v, str) and v.strip():
                                seg_text = v.strip(); break
                    if not seg_text:
                        continue
                    title = it.get("title") if isinstance(it.get("title"), str) else None
                    rng = it.get("range") if isinstance(it.get("range"), list) and len(it.get("range")) == 2 else None
                    segments.append({"text": seg_text, "title": title, "range": rng})
                elif isinstance(it, str) and it.strip():
                    segments.append({"text": it.strip()})

        if not segments:
            # Fallback: plain generation + heuristics
            plain_prompt = (
                f"Split the following text into at most {max_splits} plain-text segments, one per line.\n\n{text}\n"
                if lang != "zh"
                else f"Please split the following text into no more than {max_splits}  segments, output plain text line by line.\n\n{text}\n"
            )
            self.debug_last_split_prompt = plain_prompt
            res = self.generation_model.generate(plain_prompt, max_tokens=min(256, max(64, len(text)//6)), lang=lang)
            self.debug_last_split_raw_output = res.text
            out = (res.text or "").strip()
            lines = [ln.strip(" \t-•*#.") for ln in out.splitlines()]
            lines = [ln for ln in lines if ln]
            seen = set(); unique: List[str] = []
            for ln in lines:
                key = ln[:160]
                if key in seen:
                    continue
                seen.add(key)
                unique.append(ln)
                if len(unique) >= max_splits:
                    break
            segments = [{"text": s} for s in unique]

        # Normalize: approximate ranges for segments without range
        def _approx_ranges(doc: str, segs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            pos = 0
            norm: List[Dict[str, Any]] = []
            for seg in segs:
                t = (seg.get("text") or "").strip()
                if not t:
                    continue
                rng = seg.get("range")
                if isinstance(rng, list) and len(rng) == 2 and all(isinstance(x, int) for x in rng):
                    start, end = max(0, rng[0]), max(0, rng[1])
                    if start <= end <= len(doc):
                        norm.append({**seg, "range": [start, end]}); continue
                # naive forward search to avoid picking earlier duplicate chunks
                idx = doc.find(t, pos)
                if idx == -1:
                    # try a looser search by collapsing spaces
                    compact_t = "".join(t.split())
                    compact_doc = "".join(doc[pos:].split())
                    idx2 = compact_doc.find(compact_t)
                    if idx2 != -1:
                        # can't reliably map back; keep no range
                        norm.append({**seg, "range": None})
                        continue
                    norm.append({**seg, "range": None})
                    continue
                start = idx
                end = idx + len(t)
                pos = end
                norm.append({**seg, "range": [start, end]})
            return norm[:max_splits]

        segments = _approx_ranges(text, segments)
        if os.getenv("TEXT2MEM_DEBUG_SPLIT") == "1":
            print("==== DEBUG split_custom normalized (begin) ====")
            try:
                print(json.dumps(segments, ensure_ascii=False)[:2000])
            except Exception:
                print("<non-text output>")
            print("==== DEBUG split_custom normalized (end) ====")
        return segments

    def assess_importance(self, text: str, context: Optional[str] = None, lang: str | None = None) -> GenerationResult:
        lang = (lang or "en").lower()
        if lang == "zh":
            prompt = f"""Evaluate the importance level of the following content (low/medium/high/urgent).

Content:{text}
"""
            if context:
                prompt += f"\nContext: {context}"
        else:
            prompt = f"""Assess the importance level of the following content (low/normal/high/urgent).

Content: {text}
"""
            if context:
                prompt += f"\nContext: {context}"
        return self.generation_model.generate(prompt, max_tokens=20, lang=lang)


class PromptTemplates:
    SUMMARIZE_TEMPLATE = """Generate a concise summary for the following memory content:

Memory Content:
{content}

Requirements:
- Preserve key information
- Keep within {max_tokens} tokens
{focus_instruction}

Summary:"""


_models_service_instance: Optional[ModelsService] = None


def get_models_service() -> ModelsService:
    global _models_service_instance
    if _models_service_instance is None:
        _models_service_instance = ModelsService()
    return _models_service_instance


def set_models_service(service: ModelsService):
    global _models_service_instance
    _models_service_instance = service
